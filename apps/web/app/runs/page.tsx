import Link from "next/link";

import { AppShell } from "../../components/app-shell";
import { Icon } from "../../components/icons";
import { runs } from "../../lib/demo-data";
import { Button, PageIntro, SectionTitle, StatusPill } from "../../components/ui";

export default function RunsPage() {
  return <AppShell><PageIntro eyebrow="Execution history" title="Runs" description="Every workflow execution, decision and side effect in one trace." action={<Button variant="secondary" icon="refresh">Refresh</Button>} /><div className="filter-row"><div className="filter-search"><Icon name="search" size={16} /><span>Search runs, workflows or IDs</span></div><button className="filter-button">All statuses <Icon name="chevron" size={14} /></button><button className="filter-button">Last 30 days <Icon name="chevron" size={14} /></button></div><section className="panel runs-panel"><SectionTitle title="Recent runs" subtitle="Showing 5 of 342 runs" /><div className="table-wrap"><table><thead><tr><th>Run</th><th>Workflow</th><th>Trigger</th><th>Status</th><th>Runtime</th><th>Fit score</th><th /></tr></thead><tbody>{runs.map((run) => <tr key={run.id}><td><Link className="run-id" href={`/runs/${run.id}`}>{run.id}</Link><span className="muted-cell">{run.time}</span></td><td><strong>{run.workflow}</strong></td><td>{run.trigger}</td><td><StatusPill status={run.status} /></td><td>{run.duration}</td><td>{run.score !== "-" ? <span className="score-value">{run.score}<small>/100</small></span> : "-"}</td><td><Link className="row-open" href={`/runs/${run.id}`} aria-label={`Open ${run.id}`}><Icon name="arrow" size={16} /></Link></td></tr>)}</tbody></table></div></section></AppShell>;
}

