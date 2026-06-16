# Architecture Decision Records

## ADR-001: Modular Monolith with Outbox Pattern

**Status:** Accepted

**Context:** Ribcage needs event-driven behavior (audit, search, notifications, realtime) without operational complexity of microservices at launch.

**Decision:** Implement a FastAPI modular monolith with domain modules (`core.*`) and PostgreSQL transactional outbox. Background asyncio task publishes outbox rows to in-process handlers and Redis pub/sub for SSE.

**Consequences:**
- Single deployable unit for homelab/startup use
- Clear module boundaries enable later extraction (notifications, search, webhooks)
- Outbox guarantees at-least-once delivery within process; Redis bridges multi-instance SSE

## ADR-002: Technology Stack

**Status:** Accepted

**Context:** Need self-hostable stack with strong typing, agent ecosystem fit, and forum-style UX.

**Decision:**
- Frontend: Next.js 15 + TanStack Query + Zustand
- Backend: FastAPI + SQLAlchemy 2 + Alembic
- Data: PostgreSQL 16, Redis 7, Meilisearch, MinIO
- Auth: JWT for humans, scoped PAT token broker for agents

**Consequences:**
- Python backend aligns with agent tooling ecosystems
- Meilisearch provides fast MVP search with OpenSearch migration path
- MinIO gives S3-compatible attachments without cloud dependency
