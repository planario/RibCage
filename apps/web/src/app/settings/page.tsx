"use client";

import { AppShell } from "@/components/AppShell";
import { useAppStore } from "@/lib/store";

export default function SettingsPage() {
  const { workspace } = useAppStore();

  return (
    <AppShell>
      <div className="header"><h1>Settings</h1></div>
      <div className="card">
        <h3>Workspace</h3>
        <p>Name: {workspace?.name || "—"}</p>
        <p style={{ color: "var(--muted)", marginTop: "0.5rem" }}>
          Retention policies and branding configuration (placeholder for MVP).
        </p>
      </div>
    </AppShell>
  );
}
