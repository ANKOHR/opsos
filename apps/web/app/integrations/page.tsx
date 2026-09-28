"use client";

import { useEffect, useState } from "react";

import { AppShell } from "../../components/app-shell";
import { Icon } from "../../components/icons";
import { integrations } from "../../lib/demo-data";
import { Button, PageIntro, SectionTitle, StatusPill } from "../../components/ui";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type GmailStatus = {
  provider: "gmail";
  status: "connected" | "not_connected";
  account?: string;
  scopes?: string[];
  last_sync_at?: string | null;
};

export default function IntegrationsPage() {
  const [gmail, setGmail] = useState<GmailStatus>({ provider: "gmail", status: "not_connected" });
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const loadGmailStatus = async () => {
    try {
      const response = await fetch(`${API_URL}/api/integrations/gmail`, {
        headers: { "X-Organization-ID": "demo-org" },
        cache: "no-store",
      });
      if (!response.ok) throw new Error(`API returned ${response.status}`);
      setGmail(await response.json() as GmailStatus);
    } catch {
      setNotice("API unavailable. The dashboard remains in local sandbox mode.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadGmailStatus();
    const result = new URLSearchParams(window.location.search).get("gmail");
    if (result === "connected") setNotice("Gmail connected. Refresh status confirmed by OpsOS.");
    if (result === "denied") setNotice("Gmail connection was cancelled.");
    if (result === "error") setNotice("Gmail connection could not be completed.");
  }, []);

  const connectGmail = () => {
    window.location.href = `${API_URL}/api/integrations/gmail/oauth/start?organisation_id=demo-org&user_id=demo-operator`;
  };

  const syncGmail = async () => {
    setSyncing(true);
    setNotice(null);
    try {
      const response = await fetch(`${API_URL}/api/integrations/gmail/sync`, {
        method: "POST",
        headers: { "X-Organization-ID": "demo-org", "X-User-ID": "demo-operator" },
      });
      const result = await response.json() as { status?: string; detail?: string; job_id?: string };
      if (!response.ok) throw new Error(result.detail || `API returned ${response.status}`);
      setNotice(`Gmail sync queued (${result.job_id || "worker job"}).`);
      void loadGmailStatus();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to queue Gmail sync.");
    } finally {
      setSyncing(false);
    }
  };

  const gmailDetail = loading
    ? "Checking connection..."
    : gmail.status === "connected"
      ? `${gmail.account || "Connected account"}${gmail.last_sync_at ? ` · synced ${new Date(gmail.last_sync_at).toLocaleString()}` : ""}`
      : "OAuth connection required";

  return <AppShell><PageIntro eyebrow="Connect your stack" title="Integrations" description="Give workflows scoped access to the tools your team already uses." action={<Button icon="plus" onClick={connectGmail}>Connect Gmail</Button>} />{notice && <div className="integration-notice"><div className="notice-icon"><Icon name="shield" size={18} /></div><div><strong>{notice}</strong><span>Refresh tokens remain server-side. External actions stay approval-gated.</span></div><StatusPill status={gmail.status === "connected" ? "Protected" : "Review"} /></div>}<div className="integration-notice"><div className="notice-icon"><Icon name="shield" size={18} /></div><div><strong>Credentials stay server-side</strong><span>OpsOS never exposes refresh tokens to the browser. External actions remain approval-gated.</span></div><StatusPill status="Protected" /></div><section className="panel integrations-panel"><SectionTitle title="Connected tools" subtitle="4 connector slots · Gmail can use live OAuth" /><div className="integration-grid">{integrations.map((integration) => { const isGmail = integration.name === "Gmail"; const status = isGmail ? (gmail.status === "connected" ? "Connected" : "Not connected") : integration.status; const detail = isGmail ? gmailDetail : integration.detail; return <div className="integration-card" key={integration.name}><div className="integration-card-head"><div className={`integration-logo ${integration.name.toLowerCase().replace(" ", "-")}`}><Icon name={integration.icon as Parameters<typeof Icon>[0]["name"]} size={19} /></div><StatusPill status={status} /></div><h3>{integration.name}</h3><p>{integration.description}</p><div className="integration-card-foot"><span>{detail}</span><div className="button-row">{isGmail && gmail.status === "connected" && <Button variant="secondary" onClick={syncGmail} disabled={syncing}>{syncing ? "Queueing..." : "Sync"}</Button>}{isGmail && gmail.status !== "connected" && <Button variant="secondary" onClick={connectGmail}>Connect</Button>}<button className="more-button" aria-label={`Configure ${integration.name}`}><Icon name="more" size={16} /></button></div></div></div>; })}</div></section></AppShell>;
}
