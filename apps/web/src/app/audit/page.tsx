"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";

interface AuditItem {
  id: string;
  event_type: string;
  actor_id: string | null;
  actor_type: string | null;
  resource_type: string | null;
  payload: Record<string, unknown>;
  created_at: string;
}

export default function AuditPage() {
  const [items, setItems] = useState<AuditItem[]>([]);
  const wsId = typeof window !== "undefined" ? localStorage.getItem("ribcage_workspace_id") : null;

  useEffect(() => {
    if (!wsId) return;
    api<{ items: AuditItem[] }>(`/audit/events?workspace_id=${wsId}`).then((r) => setItems(r.items));
  }, [wsId]);

  return (
    <AppShell>
      <div className="header"><h1>Audit Log</h1></div>
      {items.map((item) => (
        <div key={item.id} className="card timeline-item" style={{ marginBottom: "0.5rem" }}>
          <div className="feed-meta">
            <strong>{item.event_type}</strong>
            {item.actor_type && <span className={`badge ${item.actor_type}`}>{item.actor_type}</span>}
            <span>{new Date(item.created_at).toLocaleString()}</span>
          </div>
          <pre style={{ fontSize: "0.75rem", color: "var(--muted)", marginTop: "0.25rem" }}>
            {JSON.stringify(item.payload, null, 2)}
          </pre>
        </div>
      ))}
      {items.length === 0 && <p style={{ color: "var(--muted)" }}>No audit events yet.</p>}
    </AppShell>
  );
}
