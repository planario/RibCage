"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type { Rib, User, Workspace } from "@ribcage/shared-types";

export default function DashboardPage() {
  const router = useRouter();
  const { user, workspace, ribs, setUser, setWorkspace, setRibs } = useAppStore();

  useEffect(() => {
    async function load() {
      try {
        const me = await api<User>("/auth/me");
        setUser(me);
        const wsId = localStorage.getItem("ribcage_workspace_id");
        if (!wsId) {
          router.push("/onboarding");
          return;
        }
        const ws = await api<Workspace>(`/workspaces/${wsId}`);
        setWorkspace(ws);
        const ribList = await api<Rib[]>(`/workspaces/${wsId}/ribs`);
        setRibs(ribList);
      } catch {
        router.push("/login");
      }
    }
    load();
  }, [router, setUser, setWorkspace, setRibs]);

  return (
    <AppShell>
      <div className="header">
        <h1>Dashboard</h1>
      </div>
      <p style={{ color: "var(--muted)", marginBottom: "1.5rem" }}>
        Welcome{user ? `, ${user.display_name}` : ""}. Select a Rib to view its feed.
      </p>
      <div style={{ display: "grid", gap: "0.75rem" }}>
        {ribs.map((rib) => (
          <Link key={rib.id} href={`/ribs/${rib.id}`} className="card feed-item">
            <strong>{rib.name}</strong>
            {rib.description && <p style={{ color: "var(--muted)", fontSize: "0.9rem" }}>{rib.description}</p>}
          </Link>
        ))}
      </div>
    </AppShell>
  );
}
