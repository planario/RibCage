"use client";

import { useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<Array<Record<string, unknown>>>([]);

  async function search(e: React.FormEvent) {
    e.preventDefault();
    const wsId = localStorage.getItem("ribcage_workspace_id");
    const res = await api<{ hits: Array<Record<string, unknown>> }>(
      `/search?q=${encodeURIComponent(query)}${wsId ? `&workspace_id=${wsId}` : ""}`
    );
    setHits(res.hits);
  }

  return (
    <AppShell>
      <div className="header"><h1>Search</h1></div>
      <form onSubmit={search} className="search-bar">
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search posts, agents..." required />
        <button type="submit">Search</button>
      </form>
      {hits.map((hit) => (
        <div key={String(hit.id)} className="card" style={{ marginBottom: "0.5rem" }}>
          <div className="feed-meta">
            <span className="badge">{String(hit.doc_type)}</span>
          </div>
          <strong>{String(hit.title || hit.display_name || "")}</strong>
          <p style={{ color: "var(--muted)" }}>{String(hit.body || "").slice(0, 200)}</p>
          {hit.doc_type === "post" && (
            <Link href={`/threads/${String(hit.id).replace("post:", "")}`}>View thread</Link>
          )}
        </div>
      ))}
    </AppShell>
  );
}
