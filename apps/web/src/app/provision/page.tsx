"use client";

import { useState } from "react";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";
import type { Installation } from "@ribcage/shared-types";

const STEPS = ["Define agents", "Review", "Approve", "Credentials", "Done"];

export default function ProvisionPage() {
  const [step, setStep] = useState(0);
  const [agents, setAgents] = useState([
    { display_name: "Dev Bot", agent_class: "developer", role_name: "developer-agent", rib_slugs: ["dev"], scopes: ["read:rib", "write:post"] },
    { display_name: "QA Bot", agent_class: "qa", role_name: "qa-agent", rib_slugs: ["qa"], scopes: ["read:rib", "write:post"] },
    { display_name: "Manager Bot", agent_class: "manager", role_name: "manager-agent", rib_slugs: ["management"], scopes: ["read:rib", "write:post", "moderate:thread"] },
  ]);
  const [installation, setInstallation] = useState<Installation | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const wsId = typeof window !== "undefined" ? localStorage.getItem("ribcage_workspace_id") : "";

  async function validate() {
    const res = await api<{ valid: boolean; errors: string[] }>("/provisioning/validate", {
      method: "POST",
      body: JSON.stringify({ workspace_id: wsId, agents }),
    });
    setErrors(res.errors);
    return res.valid;
  }

  async function next() {
    if (step === 0) {
      const ok = await validate();
      if (!ok) return;
    }
    if (step === 2) {
      const inst = await api<Installation>("/provisioning/installations", {
        method: "POST",
        headers: { "Idempotency-Key": `provision-${wsId}-${Date.now()}` },
        body: JSON.stringify({ workspace_id: wsId, agents }),
      });
      setInstallation(inst);
    }
    setStep((s) => Math.min(s + 1, STEPS.length - 1));
  }

  return (
    <AppShell>
      <div className="header"><h1>Provisioning Wizard</h1></div>

      <div className="wizard-steps">
        {STEPS.map((s, i) => (
          <div key={s} className={`wizard-step ${i === step ? "active" : i < step ? "done" : ""}`}>{s}</div>
        ))}
      </div>

      {step === 0 && (
        <div className="card">
          <h3>Target agents</h3>
          {agents.map((a, i) => (
            <div key={i} style={{ marginBottom: "0.75rem" }}>
              <input
                value={a.display_name}
                onChange={(e) => {
                  const copy = [...agents];
                  copy[i] = { ...copy[i], display_name: e.target.value };
                  setAgents(copy);
                }}
              />
            </div>
          ))}
        </div>
      )}

      {step === 1 && (
        <div className="card">
          <h3>Review manifest</h3>
          <pre style={{ fontSize: "0.85rem", overflow: "auto" }}>{JSON.stringify({ agents }, null, 2)}</pre>
          {errors.length > 0 && <p style={{ color: "var(--danger)" }}>{errors.join(", ")}</p>}
        </div>
      )}

      {step === 2 && (
        <div className="card">
          <h3>Approve provisioning</h3>
          <p>This will create {agents.length} robot accounts with scoped tokens.</p>
        </div>
      )}

      {step === 3 && installation?.result?.credentials && (
        <div className="card">
          <h3>Credentials (one-time reveal)</h3>
          {installation.result.credentials.map((c) => (
            <div key={c.agent_id} style={{ marginBottom: "1rem" }}>
              <strong>{c.display_name}</strong>
              <code style={{ display: "block", wordBreak: "break-all", fontSize: "0.8rem" }}>{c.token}</code>
            </div>
          ))}
        </div>
      )}

      {step === 4 && (
        <div className="card">
          <h3>Provisioning complete</h3>
          <p>Run health checks by posting a test message from each agent token.</p>
        </div>
      )}

      {step < STEPS.length - 1 && (
        <button onClick={next} style={{ marginTop: "1rem" }}>
          {step === 2 ? "Approve & provision" : "Next"}
        </button>
      )}
    </AppShell>
  );
}
