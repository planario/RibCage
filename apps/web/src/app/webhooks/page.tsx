"use client";

import { useState } from "react";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";

export default function WebhooksPage() {
  const [url, setUrl] = useState("");
  const [secret, setSecret] = useState<string | null>(null);
  const wsId = typeof window !== "undefined" ? localStorage.getItem("ribcage_workspace_id") : null;

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!wsId) return;
    const res = await api<{ id: string; secret: string }>("/webhooks", {
      method: "POST",
      body: JSON.stringify({ workspace_id: wsId, url, event_types: ["post.created", "comment.created"] }),
    });
    setSecret(res.secret);
  }

  return (
    <AppShell>
      <div className="header"><h1>Webhooks</h1></div>
      <form onSubmit={create} className="card">
        <div className="form-group">
          <label>Endpoint URL</label>
          <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://..." required />
        </div>
        <button type="submit">Create webhook</button>
        {secret && (
          <p style={{ marginTop: "1rem", color: "var(--warning)" }}>
            Secret (save now): <code>{secret}</code>
          </p>
        )}
      </form>
    </AppShell>
  );
}
