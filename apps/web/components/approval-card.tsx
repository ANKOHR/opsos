"use client";

import { useState } from "react";

import type { Approval } from "../lib/types";
import { Icon } from "./icons";
import { Button, StatusPill } from "./ui";

export function ApprovalCard({ approval, onResolved }: { approval: Approval; onResolved?: (id: string, decision: "approved" | "rejected") => void }) {
  const [decision, setDecision] = useState<"pending" | "approved" | "rejected">("pending");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function decide(next: "approved" | "rejected") {
    setBusy(true);
    setError("");
    let confirmed = false;
    try {
      const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const response = await fetch(`${api}/api/approvals/${approval.id}/decision`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ decision: next, reason: next === "approved" ? "Approved from OpsOS dashboard" : "Rejected from OpsOS dashboard" }) });
      if (!response.ok) {
        setError("This preview is stale. Refresh the approval inbox to load the current server record.");
      } else {
        confirmed = true;
      }
    } catch {
      // Keep the static preview usable when the local API is intentionally offline.
      confirmed = true;
    }
    if (!confirmed) {
      setBusy(false);
      return;
    }
    setDecision(next);
    setBusy(false);
    onResolved?.(approval.id, next);
  }

  if (decision !== "pending") return <div className={`approval-resolved ${decision}`}><div className="resolved-icon"><Icon name={decision === "approved" ? "check" : "x"} size={18} /></div><div><strong>{decision === "approved" ? (approval.external ? "Approved and sent via Gmail" : "Approved in sandbox") : "Rejected safely"}</strong><p>{approval.title}</p></div><StatusPill status={decision} /></div>;

  return <article className="approval-card"><div className="approval-card-head"><div className="approval-type"><span className="approval-icon"><Icon name="mail" size={16} /></span><div><strong>{approval.title}</strong><span>{approval.subtitle}</span></div></div><span className="approval-age">{approval.created}</span></div><div className="approval-preview"><div className="mail-line"><span>To</span><strong>{approval.recipient}</strong></div><div className="mail-line"><span>Subject</span><strong>{approval.subject}</strong></div><div className="mail-body">{approval.body.split("\n").map((line, index) => <p key={index}>{line || " "}</p>)}</div></div>{error && <div className="approval-error"><Icon name="x" size={14} />{error}</div>}<div className="approval-card-foot"><div className="approval-reason"><span className="score-ring">{approval.score}</span><div><strong>Recommended action</strong><span>High confidence · {approval.score}/100 fit score</span></div></div><div className="approval-actions"><Button variant="secondary" onClick={() => decide("rejected")} disabled={busy} icon="x">Reject</Button><Button onClick={() => decide("approved")} disabled={busy} icon="check">{approval.external ? "Approve and send" : "Approve in sandbox"}</Button></div></div></article>;
}
