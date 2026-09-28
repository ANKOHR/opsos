from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from .database import init_db
from .gmail import (
    GmailConfigurationError,
    GmailConnector,
    authorization_url,
    create_oauth_state,
    encrypt_refresh_token,
    exchange_oauth_code,
    verify_oauth_state,
)
from .repository import Repository
from .runtime import WorkflowRuntime
from .schemas import (
    ApprovalDecision,
    EventIngestRequest,
    OrganizationContext,
    OverviewView,
    RunView,
)
from .security import get_context, require_write

repository = Repository()
logger = logging.getLogger(__name__)


def tools_for_organisation(organisation_id: str):
    from .tools import DemoToolRegistry

    connection = repository.gmail_connection(organisation_id, include_secret=True)
    if not connection:
        return DemoToolRegistry()
    encrypted_refresh_token = connection.get("encrypted_refresh_token")
    if not encrypted_refresh_token:
        raise GmailConfigurationError("Connected Gmail integration has no stored credential")
    return DemoToolRegistry(
        gmail_connector=GmailConnector.from_stored_connection(encrypted_refresh_token)
    )


runtime = WorkflowRuntime(repository, tool_factory=tools_for_organisation)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    repository.seed_demo()
    yield


app = FastAPI(
    title="OpsOS API",
    version="1.0.0",
    description="Auditable human-supervised AI operations runtime",
    lifespan=lifespan,
)

origins = [
    origin.strip()
    for origin in os.getenv(
        "API_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "opspilot-api",
        "mode": os.getenv("APP_ENV", "development"),
    }


@app.get("/api/integrations/gmail")
def gmail_status(context: OrganizationContext = Depends(get_context)) -> dict:
    connection = repository.gmail_connection(context.organization_id)
    if connection is None:
        return {"provider": "gmail", "status": "not_connected", "scopes": []}
    return {
        "provider": "gmail",
        "status": connection["status"],
        "account": connection["external_account"],
        "scopes": connection["scopes"],
        "last_sync_at": connection["last_sync_at"],
    }


@app.get("/api/integrations/gmail/oauth/start")
def gmail_oauth_start(
    organisation_id: str = Query(default="demo-org", min_length=1, max_length=80),
    user_id: str = Query(default="demo-operator", min_length=1, max_length=120),
) -> RedirectResponse:
    if os.getenv("APP_ENV", "development").lower() == "production":
        organisation_id = os.getenv("DEMO_ORG_ID", "demo-org")
        user_id = os.getenv("DEMO_OAUTH_USER_ID", "demo-operator")
    try:
        state = create_oauth_state(organisation_id, user_id)
        return RedirectResponse(authorization_url(state), status_code=307)
    except GmailConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/integrations/gmail/oauth/callback")
def gmail_oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    web_url = os.getenv("WEB_APP_URL", "http://localhost:3000").rstrip("/")
    if error:
        return RedirectResponse(f"{web_url}/integrations?gmail=denied", status_code=303)
    if not code or not state:
        return RedirectResponse(f"{web_url}/integrations?gmail=error", status_code=303)
    try:
        identity = verify_oauth_state(state)
        credentials = exchange_oauth_code(code, state)
        connector = GmailConnector.from_credentials(credentials)
        profile = connector.get_profile()
        encrypted = encrypt_refresh_token(str(credentials.refresh_token))
        connection = repository.upsert_gmail_connection(
            identity["organisation_id"],
            str(profile.get("emailAddress", "unknown")),
            list(credentials.scopes or []),
            encrypted,
        )
        repository.add_audit(
            identity["organisation_id"],
            identity["user_id"],
            "integration.connected",
            "integration",
            connection["id"],
            {"provider": "gmail", "external_account": connection["external_account"]},
        )
    except (GmailConfigurationError, ValueError, TypeError):
        logger.exception("Gmail OAuth callback failed")
        return RedirectResponse(f"{web_url}/integrations?gmail=error", status_code=303)
    return RedirectResponse(f"{web_url}/integrations?gmail=connected", status_code=303)


@app.get("/api/integrations/gmail/messages")
def gmail_messages(
    query: str = Query(default="", max_length=500),
    max_results: int = Query(default=20, ge=1, le=50),
    context: OrganizationContext = Depends(get_context),
) -> dict:
    try:
        tools = tools_for_organisation(context.organization_id)
        return tools.execute(
            "gmail.search", {"query": query, "max_results": max_results}, {"gmail.search"}
        )
    except GmailConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=409, detail="Gmail is not connected") from exc


@app.post("/api/integrations/gmail/sync")
def gmail_sync(
    query: str = Query(default="-label:processed", max_length=500),
    max_results: int = Query(default=20, ge=1, le=50),
    context: OrganizationContext = Depends(get_context),
) -> dict:
    require_write(context)
    try:
        from .jobs import sync_gmail_job

        message = sync_gmail_job.send(
            {
                "organisation_id": context.organization_id,
                "actor": context.user_id,
                "query": query,
                "max_results": max_results,
            }
        )
        repository.add_audit(
            context.organization_id,
            context.user_id,
            "gmail.sync.queued",
            "integration",
            f"gmail_{context.organization_id}",
        )
        return {"status": "queued", "job_id": message.message_id}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Unable to queue Gmail sync: {exc}") from exc


@app.get("/api/overview", response_model=OverviewView)
def overview(context: OrganizationContext = Depends(get_context)) -> dict:
    return repository.overview(context.organization_id)


@app.get("/api/workflows")
def workflows(context: OrganizationContext = Depends(get_context)) -> list[dict]:
    return repository.workflows(context.organization_id)


@app.get("/api/runs")
def runs(context: OrganizationContext = Depends(get_context)) -> list[dict]:
    return repository.runs(context.organization_id)


@app.get("/api/runs/{run_id}", response_model=RunView)
def run_detail(run_id: str, context: OrganizationContext = Depends(get_context)) -> dict:
    result = repository.run_view(context.organization_id, run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return result


@app.get("/api/approvals")
def approvals(context: OrganizationContext = Depends(get_context)) -> list[dict]:
    return repository.approvals(context.organization_id)


@app.get("/api/audit")
def audit(context: OrganizationContext = Depends(get_context)) -> list[dict]:
    return repository.audit(context.organization_id)


@app.post("/api/events", response_model=RunView)
def ingest_event(
    request: EventIngestRequest, context: OrganizationContext = Depends(get_context)
) -> dict:
    require_write(context)
    try:
        return runtime.process_event(context.organization_id, context.user_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/demo/inbound-lead", response_model=RunView)
def run_demo(context: OrganizationContext = Depends(get_context)) -> dict:
    require_write(context)
    request = EventIngestRequest(
        idempotency_key="demo-gmail-message-1948837284",
        payload={
            "from": "alice@example.com",
            "subject": "Invoice automation for our construction business",
            "body": "Hi, we are a 70-person construction company processing roughly 2,000 invoices per month. Could somebody show us what you have built?",
        },
    )
    try:
        return runtime.process_event(context.organization_id, context.user_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/approvals/{approval_id}/decision", response_model=RunView)
def decide_approval(
    approval_id: str,
    decision: ApprovalDecision,
    context: OrganizationContext = Depends(get_context),
) -> dict:
    require_write(context)
    try:
        return runtime.decide_approval(
            context.organization_id,
            context.user_id,
            approval_id,
            decision.decision,
            decision.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Approval not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/runs/{run_id}/replay", response_model=RunView)
def replay_run(run_id: str, context: OrganizationContext = Depends(get_context)) -> dict:
    require_write(context)
    try:
        return runtime.replay(context.organization_id, context.user_id, run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
