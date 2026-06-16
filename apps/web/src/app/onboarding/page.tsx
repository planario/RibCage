"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type { User, Workspace } from "@ribcage/shared-types";

export default function OnboardingPage() {
  const router = useRouter();
  const { setUser, setWorkspace } = useAppStore();
  const [name, setName] = useState("My Workspace");
  const [error, setError] = useState("");

  useEffect(() => {
    api<User>("/auth/me").then(setUser).catch(() => router.push("/login"));
  }, [router, setUser]);

  async function createWorkspace(e: React.FormEvent) {
    e.preventDefault();
    try {
      const ws = await api<Workspace>("/workspaces", {
        method: "POST",
        body: JSON.stringify({ name }),
      });
      setWorkspace(ws);
      localStorage.setItem("ribcage_workspace_id", ws.id);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  return (
    <div className="auth-page">
      <div className="card auth-card">
        <h1>Create your workspace</h1>
        <p style={{ color: "var(--muted)", margin: "0.5rem 0 1rem" }}>
          Default Ribs (management, dev, qa, issues, requests) will be created automatically.
        </p>
        <form onSubmit={createWorkspace}>
          <div className="form-group">
            <label>Workspace name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
          <button type="submit" style={{ width: "100%" }}>Create workspace</button>
        </form>
      </div>
    </div>
  );
}
