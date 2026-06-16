"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<Array<{ id: string; name: string; policy_pack: string; rules: Record<string, unknown> }>>([]);
  const [name, setName] = useState("");
  const [pack, setPack] = useState("private_team");
  const wsId = typeof window !== "undefined" ? localStorage.getItem("ribcage_workspace_id") : null;

  useEffect(() => {
    if (wsId) api<typeof policies>(`/policies?workspace_id=${wsId}`).then(setPolicies).catch(() => {});
  }, [wsId]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!wsId) return;
    await api("/policies", {
      method: "POST",
      body: JSON.stringify({ workspace_id: wsId, name, policy_pack: pack }),
    });
    const updated = await api<typeof policies>(`/policies?workspace_id=${wsId}`);
    setPolicies(updated);
    setName("");
  }

  return (
    <AppShell>
      <div className="header"><h1>Policy Console</h1></div>
      <form onSubmit={create} className="card" style={{ marginBottom: "1rem" }}>
        <div className="form-group">
          <label>Policy name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </div>
        <div className="form-group">
          <label>Policy pack</label>
          <select value={pack} onChange={(e) => setPack(e.target.value)}>
            <option value="open_lab">Open Lab</option>
            <option value="private_team">Private Team</option>
            <option value="enterprise">Enterprise</option>
          </select>
        </div>
        <button type="submit">Create policy</button>
      </form>
      {policies.map((p) => (
        <div key={p.id} className="card" style={{ marginBottom: "0.5rem" }}>
          <strong>{p.name}</strong> — {p.policy_pack}
          <pre style={{ fontSize: "0.8rem", color: "var(--muted)" }}>{JSON.stringify(p.rules, null, 2)}</pre>
        </div>
      ))}
    </AppShell>
  );
}
