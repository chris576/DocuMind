# DocuMind Documentation

This folder contains the project documentation and marketing/landing assets.

## Contents

| File | Purpose |
|---|---|
| `index.html` | Landing page for the project (features, screenshots, installation) |
| `README.md` | This file — documentation overview |

## Knowledge Base

Architecture decisions, connector/pipeline design, and build/toolchain facts are
maintained in two places:

- **Obsidian Vault** (human-readable, versioned): `/mnt/c/Users/chris/Documents/Obsidian/DocuMind/AI-Knowledge/`
  - `project-overview.md` — tech stack & USP
  - `architecture/` — architecture overviews (e.g. connector layer)
  - `decisions/` — architecture decision records (ADRs)
  - `connectors/` — DMS/ERP connector documentation
  - `pipelines/` — ingestion/retrieval/generation/extraction pipeline documentation
- **Agent memory** (fast, machine-readable): `/memories/repo/` (e.g. `build-facts.md`)

## Project Structure

```
apps/
  backend/              NestJS 10 API (port 3001)
  frontend/             Vite 6 + React 18 SPA (port 3000)
  ingestion-pipeline/   Python FastAPI (port 8001)
  retrieval-pipeline/   Python FastAPI (port 8002)
  generation-pipeline/  Python FastAPI (port 8003)
  extraction-pipeline/  Python FastAPI (port 8004) — strukturierte Fakten
packages/
  shared/               Shared TS types/DTOs/enums
  config/               Zod environment validation
  python-common/        Shared Python utilities (config client, http, env)
  python-dms/           DMS connectors (Paperless, Docspell)
  python-llm/           LLM provider abstraction (OpenAI, Ollama, Anthropic, OpenCode, ...)
  python-vectordb/      PostgreSQL/PGVector adapter (embeddings + facts)
infrastructure/         Docker Compose (prod + dev)

