# Quazar Assistent — Architecture

See the project plan for full architecture details. This document summarizes the implemented structure.

## Components

- **apps/web** — Next.js UI (QwenChat-like)
- **apps/api** — FastAPI backend
- **packages/llm_providers** — LLM adapters (OpenAI, DeepSeek, GigaChat)
- **packages/ingestion** — Document parsing, chunking, Confluence client
- **workers** — Celery tasks for ingestion and Confluence sync
- **infra** — Docker Compose, Nginx

## Supported file formats (ingestion)

- **XLSX/XLSM** — openpyxl, sheets as markdown tables
- **Images** (jpg, png, gif, webp, bmp, tiff) — Tesseract OCR; optional GPT-4o vision fallback
- **MS Project** — `.mpp` via MPXJ+Java, `.mpx` and MSPDI `.xml` via native parsers
- PDF, DOCX, TXT, HTML — existing parsers

## Data flow

1. User uploads file → MinIO → Celery ingest → chunks + embeddings → pgvector
2. User asks question → RAG retrieval → LLM stream → citations in response
3. Confluence binding → periodic sync → same chunking pipeline

## Security

- JWT auth with `organization_id` in token
- PostgreSQL RLS policies prepared for multi-tenant isolation
- `allow_external_llm` per project blocks LLM calls when disabled
- Audit log for uploads, syncs, chat messages

## Running locally

```bash
cd infra && docker compose up -d
cd ../apps/api && alembic upgrade head && python seed.py
uvicorn main:app --reload
celery -A workers.celery_app.app worker --loglevel=info
cd ../web && npm install && npm run dev
```
