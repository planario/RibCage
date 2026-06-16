"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAppStore } from "@/lib/store";
import { clearToken } from "@/lib/api";

const NAV = [
  { href: "/dashboard", label: "Feed" },
  { href: "/agents", label: "Agents" },
  { href: "/provision", label: "Provision" },
  { href: "/search", label: "Search" },
  { href: "/audit", label: "Audit" },
  { href: "/policies", label: "Policies" },
  { href: "/approvals", label: "Approvals" },
  { href: "/moderation", label: "Moderation" },
  { href: "/webhooks", label: "Webhooks" },
  { href: "/settings", label: "Settings" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, workspace, ribs } = useAppStore();

  return (
    <div className="layout">
      <aside className="sidebar">
        <h2>Ribcage</h2>
        {workspace && (
          <div style={{ fontSize: "0.85rem", color: "var(--muted)", marginBottom: "0.5rem" }}>
            {workspace.name}
          </div>
        )}
        <nav>
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={pathname === item.href ? "active" : ""}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        {ribs.length > 0 && (
          <>
            <h2 style={{ marginTop: "1rem" }}>Ribs</h2>
            {ribs.map((rib) => (
              <Link key={rib.id} href={`/ribs/${rib.id}`}>
                {rib.name}
              </Link>
            ))}
          </>
        )}
        <div style={{ marginTop: "auto", paddingTop: "1rem" }}>
          {user && <div style={{ fontSize: "0.8rem", color: "var(--muted)" }}>{user.display_name}</div>}
          <button
            className="secondary"
            style={{ width: "100%", marginTop: "0.5rem" }}
            onClick={() => {
              clearToken();
              window.location.href = "/login";
            }}
          >
            Logout
          </button>
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
