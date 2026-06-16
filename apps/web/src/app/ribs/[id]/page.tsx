"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { api, streamUrl } from "@/lib/api";
import type { FeedResponse, Post, Rib } from "@ribcage/shared-types";

export default function RibFeedPage() {
  const params = useParams();
  const router = useRouter();
  const ribId = params.id as string;
  const [rib, setRib] = useState<Rib | null>(null);
  const [feed, setFeed] = useState<Post[]>([]);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");

  const loadFeed = useCallback(async () => {
    const [ribData, feedData] = await Promise.all([
      api<Rib>(`/ribs/${ribId}`),
      api<FeedResponse>(`/ribs/${ribId}/feed`),
    ]);
    setRib(ribData);
    setFeed(feedData.items);
  }, [ribId]);

  useEffect(() => {
    loadFeed().catch(() => router.push("/login"));
  }, [loadFeed, router]);

  useEffect(() => {
    const es = new EventSource(streamUrl());
    es.onmessage = () => loadFeed();
    return () => es.close();
  }, [loadFeed]);

  async function createPost(e: React.FormEvent) {
    e.preventDefault();
    await api(`/ribs/${ribId}/posts`, {
      method: "POST",
      body: JSON.stringify({ title, body }),
    });
    setTitle("");
    setBody("");
    loadFeed();
  }

  return (
    <AppShell>
      <div className="header">
        <h1>{rib?.name || "Rib"}</h1>
      </div>

      <form onSubmit={createPost} className="card" style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ marginBottom: "0.75rem" }}>New post</h3>
        <div className="form-group">
          <input placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} required />
        </div>
        <div className="form-group">
          <textarea placeholder="Body (markdown supported)" value={body} onChange={(e) => setBody(e.target.value)} required />
        </div>
        <button type="submit">Post</button>
      </form>

      {feed.map((post) => (
        <Link key={post.id} href={`/threads/${post.id}`} className="card feed-item">
          <div className="feed-meta">
            <span className={`badge ${post.author.type}`}>{post.author.type}</span>
            <span className={`badge status-${post.status}`}>{post.status}</span>
            <span>{new Date(post.created_at).toLocaleString()}</span>
          </div>
          <h3>{post.title}</h3>
          <p style={{ color: "var(--muted)" }}>{post.body.slice(0, 200)}</p>
        </Link>
      ))}
    </AppShell>
  );
}
