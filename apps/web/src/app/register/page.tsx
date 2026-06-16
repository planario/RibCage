"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, setToken } from "@/lib/api";
import type { AuthResponse } from "@ribcage/shared-types";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    email: "",
    username: "",
    display_name: "",
    password: "",
  });
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const res = await api<AuthResponse>("/auth/register", {
        method: "POST",
        body: JSON.stringify(form),
      });
      setToken(res.access_token);
      router.push("/onboarding");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    }
  }

  return (
    <div className="auth-page">
      <div className="card auth-card">
        <h1 style={{ marginBottom: "1rem" }}>Create account</h1>
        <form onSubmit={handleSubmit}>
          {(["email", "username", "display_name", "password"] as const).map((field) => (
            <div className="form-group" key={field}>
              <label>{field.replace("_", " ")}</label>
              <input
                type={field === "password" ? "password" : field === "email" ? "email" : "text"}
                value={form[field]}
                onChange={(e) => setForm({ ...form, [field]: e.target.value })}
                required
              />
            </div>
          ))}
          {error && <p style={{ color: "var(--danger)", marginBottom: "1rem" }}>{error}</p>}
          <button type="submit" style={{ width: "100%" }}>Register</button>
        </form>
        <p style={{ marginTop: "1rem", textAlign: "center", color: "var(--muted)" }}>
          Have an account? <Link href="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
