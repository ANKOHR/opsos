"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { Icon, type IconName } from "./icons";

const primaryNav: { href: string; label: string; icon: IconName; count?: string }[] = [
  { href: "/", label: "Overview", icon: "activity" },
  { href: "/workflows", label: "Workflows", icon: "workflow" },
  { href: "/runs", label: "Runs", icon: "play" },
  { href: "/approvals", label: "Approvals", icon: "shield", count: "12" },
];

const secondaryNav: { href: string; label: string; icon: IconName }[] = [
  { href: "/integrations", label: "Integrations", icon: "link" },
  { href: "/analytics", label: "Analytics", icon: "chart" },
  { href: "/settings", label: "Settings", icon: "settings" },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const active = (href: string) => href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-row">
          <div className="brand-mark"><Icon name="spark" size={17} /></div>
          <div><div className="brand-name">OpsOS</div><div className="brand-subtitle">Command center</div></div>
        </div>

        <div className="workspace-picker">
          <div className="workspace-avatar">N</div>
          <div className="workspace-copy"><strong>Northstar Demo</strong><span>Demo workspace</span></div>
          <Icon name="chevron" size={15} />
        </div>

        <nav className="nav-section" aria-label="Primary navigation">
          <div className="nav-label">Workspace</div>
          {primaryNav.map((item) => <NavItem key={item.href} {...item} active={active(item.href)} />)}
        </nav>
        <nav className="nav-section" aria-label="Configuration navigation">
          <div className="nav-label">Configure</div>
          {secondaryNav.map((item) => <NavItem key={item.href} {...item} active={active(item.href)} />)}
        </nav>

        <div className="sidebar-spacer" />
        <div className="sandbox-card">
          <div className="sandbox-top"><span className="live-dot" /> Safe defaults</div>
          <p>Sandbox connectors are the default. Approved Gmail actions can use a configured live account.</p>
          <Link href="/integrations" className="sandbox-link">Review integrations <Icon name="arrow" size={14} /></Link>
        </div>
        <div className="user-card">
          <div className="user-avatar">H</div>
          <div className="workspace-copy"><strong>Henry</strong><span>Operator · online</span></div>
          <Icon name="more" size={16} />
        </div>
      </aside>
      <main className="main-content">
        <div className="topbar"><div className="breadcrumb"><span>Northstar Demo</span><b>/</b><strong>{pageName(pathname)}</strong></div><div className="topbar-actions"><button className="icon-button" aria-label="Search"><Icon name="search" size={18} /></button><button className="icon-button notification" aria-label="Notifications"><Icon name="inbox" size={18} /><span /></button><div className="topbar-separator" /><span className="environment-tag"><i /> Safe defaults</span></div></div>
        <div className="page-container">{children}</div>
      </main>
    </div>
  );
}

function NavItem({ href, label, icon, count, active }: { href: string; label: string; icon: IconName; count?: string; active: boolean }) {
  return <Link className={`nav-item ${active ? "active" : ""}`} href={href}><Icon name={icon} size={18} /><span>{label}</span>{count && <em>{count}</em>}</Link>;
}

function pageName(pathname: string) {
  if (pathname === "/") return "Overview";
  if (pathname.startsWith("/workflows")) return "Workflows";
  if (pathname.startsWith("/runs")) return "Runs";
  if (pathname.startsWith("/approvals")) return "Approvals";
  if (pathname.startsWith("/integrations")) return "Integrations";
  if (pathname.startsWith("/analytics")) return "Analytics";
  return "Settings";
}
