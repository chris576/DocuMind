#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# install-all.sh — Installiert ALLE Abhängigkeiten des DMS-RAG Monorepos
#   [1] Node.js (pnpm, alle Workspaces)
#   [2] Python (venv + python-shared + Pipeline-Runtime-Deps)
# Ein Durchlauf:  bash infrastructure/scripts/install-all.sh
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VENV_DIR="${REPO_ROOT}/.venv"

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }

echo ""
echo -e "${CYAN}=== DMS-RAG: Installation aller Abhängigkeiten ===${NC}"

# ----------------------------------------------------------------------------
# [1] Node.js / pnpm
# ----------------------------------------------------------------------------
echo ""
info "Node.js / pnpm ..."

# nvm laden, falls vorhanden, und Node 26 aktivieren (engines: >=26)
if [ -s "$HOME/.nvm/nvm.sh" ]; then
  # shellcheck disable=SC1091
  . "$HOME/.nvm/nvm.sh"
  if nvm ls 2>/dev/null | grep -q "v26"; then
    nvm use 26 >/dev/null 2>&1 || true
  else
    warn "Node 26 nicht über nvm gefunden. Nutze aktives Node ($(node --version))."
  fi
fi

if ! command -v pnpm >/dev/null 2>&1; then
  error "pnpm nicht gefunden. Installiere es zuerst: npm install -g pnpm@9.15.0"
  exit 1
fi

info "pnpm $(pnpm --version) | node $(node --version)"
pnpm install
ok "Node-Abhängigkeiten installiert."

# ----------------------------------------------------------------------------
# [2] Python
# ----------------------------------------------------------------------------
echo ""
info "Python ..."

if ! command -v python3 >/dev/null 2>&1; then
  error "python3 nicht gefunden."
  exit 1
fi
info "python3 $(python3 --version)"

# venv anlegen, falls noch nicht vorhanden
if [ ! -d "$VENV_DIR" ]; then
  if ! python3 -m venv "$VENV_DIR" 2>/dev/null; then
    error "Konnte venv nicht anlegen. Installiere ggf.: sudo apt install python3-venv python3.12-venv"
    exit 1
  fi
  ok "Virtuelle Umgebung angelegt: $VENV_DIR"
else
  info "Virtuelle Umgebung vorhanden: $VENV_DIR"
fi

PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

# pip aktualisieren
"$PIP" install -q --upgrade pip

# Fach-Pakete (editable installiert): bringen alle ML-/Runtime-Deps mit
# (sentence-transformers, chromadb, qdrant-client, psycopg2, rank-bm25, nltk,
# openai, anthropic, pydantic, requests, httpx, aio-pika, ...)
info "Installiere Python-Fach-Pakete (python-common, python-dms, python-llm, python-vectordb) ..."
"$PIP" install -q \
  -e "$REPO_ROOT/packages/python-common" \
  -e "$REPO_ROOT/packages/python-dms" \
  -e "$REPO_ROOT/packages/python-llm" \
  -e "$REPO_ROOT/packages/python-vectordb"
ok "Python-Fach-Pakete installiert."

# Pipeline-Runtime-Deps (fastapi/uvicorn/dotenv) — identisch in allen 3 Pipelines
# + Retrieval-Extras (rank-bm25, nltk)
info "Installiere Pipeline-Runtime-Deps (fastapi, uvicorn, python-dotenv, rank-bm25, nltk) ..."
"$PIP" install -q "fastapi>=0.115.0" "uvicorn>=0.32.0" "python-dotenv>=1.0.0" "rank-bm25>=0.2.2" "nltk>=3.9.0"
ok "Pipeline-Runtime-Deps installiert."

# Test-/Analyse-Tools (Test-Harness): pytest-cov, coverage, mypy, bandit, ruff
info "Installiere Test-/Analyse-Tools (pytest-cov, coverage, mypy, bandit) + Testcontainers ..."
"$PIP" install -q "pytest-cov>=5.0.0" "coverage>=7.6.0" "mypy>=1.11.0" "bandit>=1.7.9" "testcontainers>=4.8.0"
ok "Test-/Analyse-Tools installiert."

# ----------------------------------------------------------------------------
# Abschluss
# ----------------------------------------------------------------------------
echo ""
echo -e "${GREEN}=== Fertig. Alle Abhängigkeiten installiert. ===${NC}"
echo ""
echo "Node:  pnpm $(pnpm --version) / node $(node --version)"
echo "Python: $("$PYTHON" --version) in $VENV_DIR"
echo ""
echo "Pipelines starten (jeweils im App-Verzeichnis):"
echo "  cd apps/ingestion-pipeline && ../../.venv/bin/python main.py"
echo "  cd apps/retrieval-pipeline  && ../../.venv/bin/python main.py"
echo "  cd apps/generation-pipeline && ../../.venv/bin/python main.py"
echo ""
echo "Node-Services:  pnpm dev"
echo ""
