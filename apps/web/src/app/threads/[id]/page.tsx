"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";
import type { ThreadResponse } from "@ribcage/shared-types";

export default function ThreadPage() {
  const params = useParams();
  const router = useRouter();
  const threadId = params.id as string;
  const [thread, setThread] = useState<ThreadResponse | null>(null);
  const [comment, setComment] = useState("");
  const [timeline, setTimeline] = useState<{ events: unknown[]; status_history: unknown[] } | null>(null);
  const [tab, setTab] = useState<"comments" | "timeline">("comments");

  async function load() {
    const [t, tl] = await Promise.all([
      api<ThreadResponse>(`/threads/${threadId}`),
      api<{ events: unknown[]; status_history: unknown[] }>(`/threads/${threadId}/timeline`),
    ]);
    setThread(t);
    setTimeline(tl);
  }

  useEffect(() => {
    load().catch(() => router.push("/login"));
  }, [threadId, router]);

  async function submitComment(e: React.FormEvent) {
    e.preventDefault();
    await api(`/threads/${threadId}/comments`, {
      method: "POST",
      body: JSON.stringify({ body: comment }),
    });
    setComment("");
    load();
  }

  async function changeStatus(status: string) {
    await api(`/threads/${threadId}/status-transitions`, {
      method: "POST",
      body: JSON.stringify({ status }),
    });
    load();
  }

  if (!thread) return <AppShell><p>Loading...</p></AppShell>;

  return (
    <AppShell>
      <div className="header">
        <div>
          <div className="feed-meta">
            <span className={`badge ${thread.post.author.type}`}>{thread.post.author.type}</span>
            <span className={`badge status-${thread.post.status}`}>{thread.post.status}</span>
          </div>
          <h1>{thread.post.title}</h1>
        </div>
        <select value={thread.post.status} onChange={(e) => changeStatus(e.target.value)}>
          {["open", "triaged", "in_progress", "blocked", "resolved", "archived"].map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <div className="card" style={{ marginBottom: "1rem" }}>
        <p>{thread.post.body}</p>
      </div>

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        <button className={tab === "comments" ? "" : "secondary"} onClick={() => setTab("comments")}>Comments</button>
        <button className={tab === "timeline" ? "" : "secondary"} onClick={() => setTab("timeline")}>Timeline</button>
      </div>

      {tab === "comments" ? (
        <>
          {thread.comments.map((c) => (
            <div key={c.id} className="card" style={{ marginBottom: "0.5rem" }}>
              <div className="feed-meta">
                <span className={`badge ${c.author.type}`}>{c.author.type}</span>
                <span>{new Date(c.created_at).toLocaleString()}</span>
              </div>
              <p>{c.body}</p>
            </div>
          ))}
          <form onSubmit={submitComment} className="card">
            <textarea value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Reply..." required />
            <button type="submit" style={{ marginTop: "0.5rem" }}>Comment</button>
          </form>
        </>
      ) : (
        <div className="card">
          {timeline?.events.map((e: unknown, i) => {
            const ev = e as { type: string; created_at: string };
            return (
              <div key={i} className="timeline-item">
                <strong>{ev.type}</strong>
                <div style={{ fontSize: "0.8rem", color: "var(--muted)" }}>{ev.created_at}</div>
              </div>
            );
          })}
        </div>
      )}
    </AppShell>
  );
}
