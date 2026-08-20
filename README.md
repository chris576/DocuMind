# 📄 DMS-RAG

[![License](https://img.shields.io/github/license/chris576/paperless-rag?cacheSeconds=1)](LICENSE)

**DMS-RAG** is an open-source RAG (Retrieval-Augmented Generation) backend for companies whose documents live in non-standardized DMS, ERP, or industry solutions. It brings automatic document classification, smart tagging, and semantic search using OpenAI-compatible APIs and Ollama.

It enables **fully automated document workflows**, **contextual chat**, and **powerful customization** — all via an intuitive web interface.

> 💡 Just ask:  
> “When did I sign my rental agreement?”  
> “What was the amount of the last electricity bill?”  
> “Which documents mention my health insurance?”  

Powered by **Retrieval-Augmented Generation (RAG)**, you can now search semantically across your full archive and get precise, natural language answers.

---

## ✨ Features

### 🔌 DMS-Agnostic Connector Layer
- Connector interface for any DMS/ERP source — Paperless-ngx is the reference connector
- Normalized document model (`DocumentRecord`, `DocumentContent`) keeps the rest of the app source-agnostic
- Registry + factory pattern: new connectors are added without touching selection logic

### 🔄 Automated Document Processing
- Detects new documents in your DMS automatically
- Analyzes content using OpenAI API, Ollama, and other compatible backends
- Assigns title, tags, document type, and correspondent
- Built-in support for:
  - Ollama (Mistral, Llama, Phi-3, Gemma-2)
  - OpenAI
  - DeepSeek.ai
  - OpenRouter.ai
  - Perplexity.ai
  - Together.ai
  - LiteLLM
  - VLLM
  - Fastchat
  - Gemini (Google)
  - ...and more!

### 🧠 RAG-Based AI Chat
- Natural language document search and Q&A
- Understands full document context (not just keywords)
- Semantic memory powered by your own data
- Fast, intelligent, privacy-friendly document queries

### 🏗️ Modern Monorepo Architecture
- pnpm + Turbo workspace (`apps/*` + `packages/*`)
- NestJS 10 backend (`apps/backend`, port 3001)
- Vite 6 + React 18 frontend (`apps/frontend`, port 3000)
- Python pipelines (FastAPI): Ingestion (8001), Retrieval (8002), Generation (8003)
- Direct HTTP REST communication between backend and pipelines (FastAPI)
- Vector-DB factory: Chroma / Qdrant / PGVector
- TypeScript 7 (native Go compiler) across the monorepo — the backend stays on TS 5.9 for NestJS toolchain compatibility

---

## 🚀 Installation

### 🐳 Docker Compose (recommended)

```bash
git clone https://github.com/chris576/paperless-rag.git
cd paperless-rag
cp .env.example .env
# Fill in PAPERLESS_API_URL, PAPERLESS_API_TOKEN, JWT_SECRET, ...
docker compose -f infrastructure/docker-compose.yml up -d
```

Services:

| Service | URL / Port |
|---|---|
| Frontend | http://localhost:3000 |
| Backend (NestJS) | http://localhost:3001 |
| Ingestion pipeline | http://localhost:8001 |
| Retrieval pipeline | http://localhost:8002 |
| Generation pipeline | http://localhost:8003 |
| PostgreSQL | 5432 |
| ChromaDB | 8000 |

### 🔧 Local Development

```bash
# Install dependencies
pnpm install

# Start all services in watch mode
pnpm dev

# Build all packages
pnpm build

# Type-check all packages
pnpm typecheck
```

---

## 🧭 Roadmap Highlights

- ✅ DMS-agnostic connector layer (Paperless-ngx reference connector)
- ✅ Multi-AI model support
- ✅ Multilingual document analysis
- ✅ Integrated document chat with RAG
- ✅ Vector-DB factory (Chroma / Qdrant / PGVector)
- 🚧 MCP server for agent access (Hermes, OpenClaw, …)
- 🚧 Additional connectors (generic REST/OData, Nextcloud/WebDAV, ELO, d.velop, windream, DATEV)

---

## 🤝 Contributing

We welcome PRs and contributions!

```bash
# Fork, clone, then:
git checkout -b feature/YourFeature
# After changes:
git commit -m "Add YourFeature"
git push origin feature/YourFeature
```

Then open a Pull Request via GitHub.

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
