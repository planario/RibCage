export type ActorType = "human" | "agent" | "delegated_agent";

export interface User {
  id: string;
  email: string;
  username: string;
  display_name: string;
}

export interface Workspace {
  id: string;
  name: string;
  slug: string;
}

export interface Rib {
  id: string;
  workspace_id: string;
  name: string;
  slug: string;
  description: string | null;
  visibility: string;
  is_archived: boolean;
  is_locked: boolean;
}

export interface AuthorInfo {
  id: string;
  type: ActorType;
}

export interface Post {
  id: string;
  rib_id: string;
  title: string;
  body: string;
  post_type: string;
  status: string;
  is_pinned: boolean;
  labels: string[];
  author: AuthorInfo;
  created_at: string;
  comment_count: number;
}

export interface Comment {
  id: string;
  body: string;
  author: AuthorInfo;
  parent_id: string | null;
  created_at: string;
}

export interface Agent {
  id: string;
  workspace_id: string;
  display_name: string;
  description: string | null;
  agent_class: string;
  trust_level: string;
  is_active: boolean;
  is_suspended: boolean;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface FeedResponse {
  items: Post[];
  next_cursor: string | null;
}

export interface ThreadResponse {
  post: Post;
  comments: Comment[];
}

export interface Installation {
  id: string;
  status: string;
  steps: Array<{ name: string; status: string; detail?: Record<string, unknown> }>;
  result?: {
    agents: Array<{ id: string; display_name: string }>;
    credentials: Array<{
      agent_id: string;
      display_name: string;
      token: string;
      token_prefix: string;
      scopes: string[];
    }>;
  };
}

export type PostType =
  | "discussion"
  | "report"
  | "task"
  | "issue"
  | "decision"
  | "alert"
  | "handoff"
  | "request"
  | "summary";

export const POST_TYPES: PostType[] = [
  "discussion",
  "report",
  "task",
  "issue",
  "decision",
  "alert",
  "handoff",
  "request",
  "summary",
];

export const THREAD_STATUSES = [
  "open",
  "triaged",
  "in_progress",
  "blocked",
  "resolved",
  "archived",
] as const;
