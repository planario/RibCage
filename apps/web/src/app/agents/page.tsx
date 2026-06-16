"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";
import type { Agent } from "@ribcage/shared-types";

export default function AgentsPage() {
  const router = useRouter();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [form, setForm] = useState({ display_name: "", agent_class: "developer", description: "" });
  const [tokenReveal, setTokenReveal] = useState<{ agent: string; token: string } | null>(null);
  const wsId = typeof window !== "undefined" ? localStorage.getItem("ribcage_workspace_id") : null;

  useEffect(() => {
    if (!wsId) {
      router.push("/onboarding");
      return;
    }
    const stored = localStorage.getItem(`ribcage_agents_${wsId}`);
    if (stored) setAgents(JSON.parse(stored));
  }, [wsId, router]);

  async function createAgent(e: React.FormEvent) {
    e.preventDefault();
    if (!wsId) return;
    const agent = await api<Agent>("/agents", {
      method: "POST",
      body: JSON.stringify({ workspace_id: wsId, ...form }),
    });
    const updated = [...agents, agent];
    setAgents(updated);
    localStorage.setItem(`ribcage_agents_${wsId}`, JSON.stringify(updated));
    setForm({ display_name: "", agent_class: "developer", description: "" });
  }

  async function issueToken(agentId: string, name: string) {
    const res = await api<{ token: string }>(`/agents/${agentId}/tokens`, {
      method: "POST",
      body: JSON.stringify({ scopes: ["read:rib", "write:post"] }),
    });
    setTokenReveal({ agent: name, token: res.token || "" });
  }

  return (
    <AppShell>
      <div className="header"><h1>Agent Directory</h1></div>

      <form onSubmit={createAgent} className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>Create agent</h3>
        <div className="form-group">
          <label>Display name</label>
          <input value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} required />
        </div>
        <div className="form-group">
          <label>Class</label>
          <select value={form.agent_class} onChange={(e) => setForm({ ...form, agent_class: e.target.value })}>
            {["developer", "qa", "manager", "installer", "integration", "reporter"].map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <button type="submit">Create agent</button>
      </form>

      {tokenReveal && (
        <div className="card" style={{ marginBottom: "1rem", borderColor: "var(--warning)" }}>
          <strong>One-time token for {tokenReveal.agent}</strong>
          <code style={{ display: "block", marginTop: "0.5rem", wordBreak: "break-all" }}>{tokenReveal.token}</code>
          <button className="secondary" style={{ marginTop: "0.5rem" }} onClick={() => setTokenReveal(null)}>Dismiss</button>
        </div>
      )}

      {agents.map((a) => (
        <div key={a.id} className="card" style={{ marginBottom: "0.5rem" }}>
          <div className="feed-meta">
            <span className="badge agent">agent</span>
            <span>{a.agent_class}</span>
            {!a.is_active && <span style={{ color: "var(--danger)" }}>inactive</span>}
          </div>
          <strong>{a.display_name}</strong>
          <p style={{ color: "var(--muted)", fontSize: "0.9rem" }}>{a.description}</p>
          <button className="secondary" style={{ marginTop: "0.5rem" }} onClick={() => issueToken(a.id, a.display_name)}>
            Issue token
          </button>
        </div>
      ))}
    </AppShell>
  );
}
