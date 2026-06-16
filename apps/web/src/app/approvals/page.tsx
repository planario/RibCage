"use client";

import { useState } from "react";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";

export default function ApprovalsPage() {
  const [action, setAction] = useState("create:agent");
  const [approvalId, setApprovalId] = useState("");
  const wsId = typeof window !== "undefined" ? localStorage.getItem("ribcage_workspace_id") : null;

  async function requestApproval() {
    if (!wsId) return;
    const res = await api<{ id: string }>("/approvals", {
      method: "POST",
      body: JSON.stringify({ workspace_id: wsId, action, payload: {} }),
    });
    setApprovalId(res.id);
  }

  async function grant() {
    await api(`/approvals/${approvalId}/grant`, {
      method: "POST",
      body: JSON.stringify({ note: "Approved via console" }),
    });
  }

  return (
    <AppShell>
      <div className="header"><h1>Approval Inbox</h1></div>
      <div className="card">
        <div className="form-group">
          <label>Action</label>
          <select value={action} onChange={(e) => setAction(e.target.value)}>
            <option value="create:agent">create:agent</option>
            <option value="issue:token">issue:token</option>
          </select>
        </div>
        <button onClick={requestApproval}>Request approval</button>
        {approvalId && (
          <div style={{ marginTop: "1rem" }}>
            <p>Pending: {approvalId}</p>
            <button onClick={grant}>Grant</button>
          </div>
        )}
      </div>
    </AppShell>
  );
}
