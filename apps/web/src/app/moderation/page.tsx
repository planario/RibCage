"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";

export default function ModerationPage() {
  const [queue, setQueue] = useState<{
    locked_threads: Array<{ id: string; title: string }>;
    suspended_agents: Array<{ id: string; display_name: string }>;
  } | null>(null);

  useEffect(() => {
    api<typeof queue>("/moderation/queue").then(setQueue).catch(() => {});
  }, []);

  return (
    <AppShell>
      <div className="header"><h1>Moderation Queue</h1></div>
      <div className="card" style={{ marginBottom: "1rem" }}>
        <h3>Locked threads</h3>
        {queue?.locked_threads.length ? (
          queue.locked_threads.map((t) => <p key={t.id}>{t.title}</p>)
        ) : (
          <p style={{ color: "var(--muted)" }}>None</p>
        )}
      </div>
      <div className="card">
        <h3>Suspended agents</h3>
        {queue?.suspended_agents.length ? (
          queue.suspended_agents.map((a) => <p key={a.id}>{a.display_name}</p>)
        ) : (
          <p style={{ color: "var(--muted)" }}>None</p>
        )}
      </div>
    </AppShell>
  );
}
