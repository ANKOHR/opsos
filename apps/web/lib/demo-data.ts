import type { Approval, RunStatus, TraceItem, Workflow } from "./types";

export const overviewMetrics = [
  { label: "Automations today", value: "342", change: "+18.4%", note: "vs. previous day", tone: "blue", icon: "spark" },
  { label: "Success rate", value: "97.1%", change: "+2.6%", note: "last 30 days", tone: "green", icon: "check" },
  { label: "Waiting approval", value: "12", change: "4 urgent", note: "needs attention", tone: "amber", icon: "shield" },
  { label: "AI spend", value: "£5.42", change: "£0.0186 / run", note: "today", tone: "violet", icon: "coin" },
] as const;

export const activity = [
  { time: "09:04:09", label: "Inbound Revenue Agent", detail: "Email sent in sandbox", status: "Succeeded", tone: "green", icon: "mail" },
  { time: "09:02:18", label: "Inbound Revenue Agent", detail: "Waiting for approval", status: "Review", tone: "amber", icon: "shield" },
  { time: "08:58:41", label: "AP Exception Agent", detail: "Duplicate invoice flagged", status: "Attention", tone: "red", icon: "file" },
  { time: "08:51:03", label: "Support Escalation Agent", detail: "Routed to Customer Success", status: "Succeeded", tone: "green", icon: "message" },
  { time: "08:44:27", label: "Inbound Revenue Agent", detail: "Company enriched", status: "Succeeded", tone: "green", icon: "globe" },
] as const;

export const workflows: Workflow[] = [
  {
    id: "inbound-revenue",
    name: "Inbound Revenue Agent",
    description: "Qualifies inbound enquiries and prepares the next best revenue action.",
    trigger: "Gmail · New message",
    status: "live",
    runs: 214,
    success: "98.6%",
    steps: [
      { id: "extract", label: "Extract enquiry", kind: "LLM structured", state: "complete" },
      { id: "crm", label: "Search CRM", kind: "Read", state: "complete" },
      { id: "research", label: "Research company", kind: "Read", state: "complete" },
      { id: "score", label: "Score opportunity", kind: "Deterministic", state: "complete" },
      { id: "draft", label: "Draft response", kind: "Write", state: "complete" },
      { id: "approval", label: "Request approval", kind: "Human gate", state: "approval" },
      { id: "send", label: "Send response", kind: "External", state: "next" },
    ],
  },
  {
    id: "ap-exception",
    name: "Accounts Payable Exception Agent",
    description: "Validates invoices, spots anomalies and routes exceptions to finance.",
    trigger: "Email · Invoice received",
    status: "live",
    runs: 86,
    success: "95.4%",
    steps: [
      { id: "extract", label: "Extract invoice", kind: "LLM structured", state: "complete" },
      { id: "validate", label: "Validate fields", kind: "Deterministic", state: "complete" },
      { id: "duplicate", label: "Check duplicate", kind: "Read", state: "complete" },
      { id: "route", label: "Route exception", kind: "Human gate", state: "approval" },
    ],
  },
  {
    id: "support-escalation",
    name: "Support Escalation Agent",
    description: "Classifies customer issues and routes the right context to a human owner.",
    trigger: "Support · Ticket created",
    status: "draft",
    runs: 42,
    success: "96.2%",
    steps: [
      { id: "classify", label: "Classify severity", kind: "LLM structured", state: "complete" },
      { id: "retrieve", label: "Retrieve context", kind: "Read", state: "complete" },
      { id: "draft", label: "Draft response", kind: "Write", state: "next" },
      { id: "route", label: "Route to owner", kind: "Human gate", state: "approval" },
    ],
  },
];

export const approvals: Approval[] = [
  {
    id: "apr_9a81",
    title: "Approve outbound reply to Alice Morgan",
    subtitle: "Inbound Revenue Agent · high-fit enquiry",
    recipient: "alice@example.com",
    subject: "Re: Invoice automation for Northstar Construction",
    body: "Hi Alice,\n\nThanks for reaching out. Your invoice volume sounds like a strong fit for an automation discovery session. I can show you how the workflow handles extraction, validation and exception routing.\n\nWould either Tuesday at 10:00 or Wednesday at 14:00 work?\n\nBest,\nHenry",
    score: 94,
    created: "2 min ago",
    runId: "run_5481",
  },
  {
    id: "apr_9a72",
    title: "Route invoice exception to Finance",
    subtitle: "Accounts Payable Exception Agent · £12,480",
    recipient: "finance-team",
    subject: "Duplicate supplier invoice detected",
    body: "Invoice INV-1844 matches a previously processed supplier invoice. The amount exceeds the automatic review threshold and needs an owner decision.",
    score: 88,
    created: "18 min ago",
    runId: "run_5474",
  },
];

export const runTrace: TraceItem[] = [
  { id: "1", step: "trigger", title: "Email received", detail: "alice@example.com · Invoice automation for our construction business", time: "09:02:11", duration: "42ms", tone: "blue", icon: "mail" },
  { id: "2", step: "extract", title: "Enquiry extracted", detail: "Structured output validated against LeadQualificationOutput", time: "09:02:12", duration: "140ms", tone: "violet", icon: "spark" },
  { id: "3", step: "crm_lookup", title: "CRM searched", detail: "No existing Northstar Construction record found", time: "09:02:13", duration: "92ms", tone: "blue", icon: "search" },
  { id: "4", step: "enrich", title: "Company enriched", detail: "70 employees · construction · demo-company-lookup", time: "09:02:15", duration: "118ms", tone: "blue", icon: "globe" },
  { id: "5", step: "score", title: "Opportunity scored 94/100", detail: "Clear need · meaningful volume · explicit purchase intent", time: "09:02:17", duration: "140ms", tone: "green", icon: "chart" },
  { id: "6", step: "draft", title: "Response draft created", detail: "Two candidate meeting slots added", time: "09:02:18", duration: "75ms", tone: "violet", icon: "edit" },
  { id: "7", step: "approval", title: "Waiting for approval", detail: "External action is paused until a human decides", time: "09:02:19", duration: "-", tone: "amber", icon: "shield" },
];

export const runs: { id: string; workflow: string; trigger: string; status: RunStatus; time: string; duration: string; score: string }[] = [
  { id: "run_5481", workflow: "Inbound Revenue Agent", trigger: "New sales enquiry", status: "waiting_for_approval", time: "2 min ago", duration: "8.4s", score: "94" },
  { id: "run_5480", workflow: "Support Escalation Agent", trigger: "Priority ticket", status: "succeeded", time: "12 min ago", duration: "5.1s", score: "-" },
  { id: "run_5474", workflow: "AP Exception Agent", trigger: "Invoice received", status: "waiting_for_approval", time: "18 min ago", duration: "4.8s", score: "88" },
  { id: "run_5469", workflow: "Inbound Revenue Agent", trigger: "New sales enquiry", status: "succeeded", time: "32 min ago", duration: "7.7s", score: "82" },
  { id: "run_5463", workflow: "AP Exception Agent", trigger: "Invoice received", status: "failed", time: "41 min ago", duration: "12.2s", score: "-" },
];

export const integrations = [
  { name: "Gmail", description: "Email events, drafts and approved outbound replies", icon: "mail", status: "Connected", detail: "Henry · synced 34s ago", tone: "green" },
  { name: "Google Calendar", description: "Availability lookup and meeting proposals", icon: "calendar", status: "Connected", detail: "Henry · synced 1m ago", tone: "green" },
  { name: "HubSpot", description: "Companies, deals and activity history", icon: "hubspot", status: "Sandbox", detail: "Demo connector · no live writes", tone: "amber" },
  { name: "Slack", description: "Internal alerts and approval notifications", icon: "message", status: "Not connected", detail: "Connect when ready", tone: "muted" },
];

export const analytics = [
  { label: "Mon", value: 62 }, { label: "Tue", value: 78 }, { label: "Wed", value: 71 }, { label: "Thu", value: 94 }, { label: "Fri", value: 86 }, { label: "Sat", value: 42 }, { label: "Sun", value: 55 },
];

