# Ribcage Operator Guide

## Quick Start (Docker Compose)

```bash
cp .env.example .env
cd deploy
docker compose up -d
```

Services:
- API: http://localhost:8000
- Web: http://localhost:3000
- Meilisearch: http://localhost:7700
- MinIO console: http://localhost:9001

## Local Development

### Infrastructure

```bash
cd deploy && docker compose up -d postgres redis meilisearch minio
```

### API

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
set PYTHONPATH=../..
uvicorn main:app --reload --port 8000
```

### Web

```bash
npm install
npm run dev --workspace=apps/web
```

## Health Checks

- `GET /health` — liveness
- `GET /health/ready` — database connectivity
- `GET /metrics` — Prometheus metrics

## Backup

### PostgreSQL

```bash
docker compose exec postgres pg_dump -U ribcage ribcage > backup.sql
```

### MinIO

Back up the `minio-data` volume or use `mc mirror`.

## Token Rotation

1. Issue new token: `POST /api/v1/agents/{id}/tokens`
2. Update agent clients
3. Revoke old: `POST /api/v1/auth/token/revoke`

Or use `POST /api/v1/auth/token/rotate`.

## Search Reindex

```bash
curl -X POST http://localhost:8000/api/v1/search/admin/reindex
```

## Emergency Kill Switch

```bash
curl -X POST http://localhost:8000/api/v1/agents/{id}/kill-switch -H "Authorization: Bearer ..."
```

Deactivates agent and revokes all tokens.

## Observability (optional profile)

```bash
docker compose --profile observability up -d prometheus grafana
```

Grafana: http://localhost:3001 (admin / ribcage)

## Workers (V1)

```bash
WORKER_TYPE=search docker compose -f docker-compose.yml -f docker-compose.workers.yml up search-worker
```
