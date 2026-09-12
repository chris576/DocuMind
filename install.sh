#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# DocuMind Installer
#
#   wget -qO- https://raw.githubusercontent.com/chris576/documind/main/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/chris576/documind/main/install.sh | bash
#
# Interaktiver Installer: fragt die exakten Stack-Typen ab (DMS, VectorDB
# neu/bestehend, LLM), schreibt eine vollständige .env und startet den
# kompletten Stack über reguläre docker-Befehle (KEIN docker compose).
# App-Images werden aus der GitHub Container Registry (GHCR) gepullt.
#
# Optionen:
#   --dry-run   docker-Befehle nur ausgeben, nicht ausführen
# ============================================================================

# --- Konfiguration ----------------------------------------------------------
REPO_URL="https://github.com/chris576/documind.git"
REPO_NAME="documind"
NETWORK_NAME="documind"
DATA_VOLUME="documind-data"
DEFAULT_REGISTRY="ghcr.io/chris576/documind"
DEFAULT_TAG="latest"

# --- Farben ----------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

DRY_RUN=0
QUICKSTART=0
REPO_DIR=""

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }

# --- VARS (assoziatives Array) ---------------------------------------------
declare -A VARS

# Alle möglichen Schlüssel initialisieren (verhindert "unbound variable" bei set -u)
for _k in IMAGE_REGISTRY IMAGE_TAG DOCUMENT_PROVIDER DOCUMENT_PROVIDER_URL \
          DOCUMENT_PROVIDER_TOKEN PAPERLESS_API_URL PAPERLESS_API_TOKEN \
          PAPERLESS_USERNAME VECTOR_DB_TYPE VECTOR_DB_MODE CHROMA_URL QDRANT_URL \
          QDRANT_API_KEY PGVECTOR_URL KEYWORD_METHOD KEYWORD_WEIGHT SEMANTIC_WEIGHT \
          FTS_LANGUAGE KEYWORD_INDEX_FILE LLM_PROVIDER LLM_MODEL OPENAI_API_KEY \
          OLLAMA_BASE_URL ANTHROPIC_API_KEY CUSTOM_BASE_URL CUSTOM_API_KEY \
          CUSTOM_MODEL OPENCODE_BASE_URL OPENCODE_USERNAME OPENCODE_PASSWORD \
          OPENCODE_MODEL BACKEND_PORT DATABASE_URL BACKEND_DB_MODE JWT_SECRET API_KEY \
          INGESTION_PORT INGESTION_HOST_PORT RETRIEVAL_PORT RETRIEVAL_HOST_PORT \
          GENERATION_PORT GENERATION_HOST_PORT \
          EXTERNAL_API_ENABLED PAPERLESS_AI_INITIAL_SETUP SCAN_INTERVAL \
          PROCESS_PREDEFINED_DOCUMENTS TAGS ADD_AI_PROCESSED_TAG AI_PROCESSED_TAG_NAME \
          USE_PROMPT_TAGS PROMPT_TAGS USE_EXISTING_DATA SYSTEM_PROMPT \
          GATEWAY_API_TOKEN GATEWAY_URL PIPELINE_CONTAINER_MAP \
          PIPELINE_REGISTRY_JSON CONFIG_FILE; do
  VARS["$_k"]="${VARS[$_k]:-}"
done
unset _k

# --- Argumente -------------------------------------------------------------
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --quickstart) QUICKSTART=1 ;;
    -h|--help)
      echo "Usage: install.sh [--dry-run] [--quickstart]"
      echo "  --dry-run     docker-Befehle nur ausgeben, nicht ausführen"
      echo "  --quickstart  non-interaktiv mit sinnvollen Defaults"
      exit 0
      ;;
    *) warn "Unbekanntes Argument: $arg" ;;
  esac
done

# --- Prompt-Helfer ----------------------------------------------------------
prompt() {
  local varname="$1" message="$2" default="${VARS[$1]:-}" input
  if [ -n "$default" ]; then
    read -rp "$(echo -e "${CYAN}?${NC} $message [${YELLOW}$default${NC}]: ")" input
  else
    read -rp "$(echo -e "${CYAN}?${NC} $message: ")" input
  fi
  VARS["$varname"]="${input:-$default}"
}

prompt_secret() {
  local varname="$1" message="$2" default="${VARS[$1]:-}" input
  if [ -n "$default" ]; then
    read -rsp "$(echo -e "${CYAN}?${NC} $message [${YELLOW}********${NC}]: ")" input
  else
    read -rsp "$(echo -e "${CYAN}?${NC} $message: ")" input
  fi
  echo ""
  VARS["$varname"]="${input:-$default}"
}

prompt_required() {
  local varname="$1" message="$2"
  while true; do
    prompt "$varname" "$message"
    if [ -n "${VARS[$varname]:-}" ]; then
      break
    else
      error "Dieser Wert ist erforderlich."
    fi
  done
}

prompt_yesno() {
  local varname="$1" message="$2" default="${VARS[$1]:-}" input
  if [ -n "$default" ]; then
    read -rp "$(echo -e "${CYAN}?${NC} $message [y/N] [${YELLOW}$default${NC}]: ")" input
  else
    read -rp "$(echo -e "${CYAN}?${NC} $message [y/N]: ")" input
  fi
  input="${input:-$default}"
  case "$input" in
    [Yy]|[Yy][Ee][Ss]) VARS["$varname"]="yes" ;;
    *) VARS["$varname"]="no" ;;
  esac
}

validate_url() {
  local url="$1"
  [[ "$url" =~ ^https?://[^[:space:]]+$ ]]
}

prompt_url() {
  local varname="$1" message="$2"
  while true; do
    prompt "$varname" "$message"
    if validate_url "${VARS[$varname]}"; then
      break
    else
      error "Bitte eine gültige http:// oder https:// URL angeben."
    fi
  done
}

select_option() {
  local varname="$1" message="$2" current="${VARS[$1]:-}" default_idx=1 choice
  shift 2
  local options=("$@")
  echo -e "${CYAN}?${NC} $message"
  for i in "${!options[@]}"; do
    if [ "${options[$i]}" = "$current" ]; then
      default_idx=$((i+1))
    fi
    echo "  $((i+1))) ${options[$i]}"
  done
  read -rp "Auswahl [1-${#options[@]}] [${YELLOW}$default_idx${NC}]: " choice
  choice="${choice:-$default_idx}"
  if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "${#options[@]}" ]; then
    VARS["$varname"]="${options[$((choice-1))]}"
  else
    error "Ungültige Auswahl, nutze Default."
    VARS["$varname"]="${options[$((default_idx-1))]}"
  fi
}

generate_secret() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32
  else
    tr -d '-' < /proc/sys/kernel/random/uuid || date +%s%N | sha256sum | cut -d' ' -f1
  fi
}

# --- Voraussetzungen --------------------------------------------------------
check_prereqs() {
  echo ""
  echo -e "${CYAN}=== Voraussetzungen prüfen ===${NC}"
  local missing=()
  command -v docker >/dev/null 2>&1 || missing+=("docker")
  command -v git >/dev/null 2>&1 || missing+=("git")
  command -v curl >/dev/null 2>&1 || command -v wget >/dev/null 2>&1 || missing+=("curl oder wget")
  if [ ${#missing[@]} -gt 0 ]; then
    error "Fehlende Werkzeuge: ${missing[*]}"
    exit 1
  fi
  if ! docker info >/dev/null 2>&1; then
    error "Docker-Daemon läuft nicht oder keine Berechtigung."
    exit 1
  fi
  ok "Alle Voraussetzungen erfüllt."
}

# --- Repo sicherstellen -----------------------------------------------------
ensure_repo() {
  if [ -d infrastructure ] && [ -d apps ] && [ -f package.json ]; then
    REPO_DIR="$(pwd)"
    info "Bereits im Repo: ${REPO_DIR}"
    return 0
  fi
  local target="./${REPO_NAME}" input
  if [ -d "$target" ]; then
    REPO_DIR="$(cd "$target" && pwd)"
    info "Repo-Verzeichnis existiert bereits: ${REPO_DIR}"
    return 0
  fi
  echo ""
  echo -e "${CYAN}?${NC} Installationsverzeichnis [${YELLOW}$target${NC}]: "
  read -r input
  target="${input:-$target}"
  info "Klone ${REPO_URL} nach $target ..."
  git clone "$REPO_URL" "$target"
  REPO_DIR="$(cd "$target" && pwd)"
}

# --- Bestehende .env laden --------------------------------------------------
load_existing_env() {
  if [ -f "$ENV_FILE" ]; then
    warn "Bestehende .env gefunden. Werte werden als Defaults verwendet."
    while IFS='=' read -r key val; do
      [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
      key=$(echo "$key" | tr -d '[:space:]')
      val=$(echo "$val" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
      val=$(echo "$val" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
      VARS["$key"]="$val"
    done < "$ENV_FILE"
  fi
}

# --- Fragebogen -------------------------------------------------------------
configure_registry() {
  echo ""
  echo -e "${CYAN}=== 1/7 Image-Registry (GHCR) ===${NC}"
  VARS["IMAGE_REGISTRY"]="${VARS[IMAGE_REGISTRY]:-$DEFAULT_REGISTRY}"
  prompt "IMAGE_REGISTRY" "Registry-Prefix"
  VARS["IMAGE_TAG"]="${VARS[IMAGE_TAG]:-$DEFAULT_TAG}"
  prompt "IMAGE_TAG" "Image-Tag"
}

configure_dms() {
  echo ""
  echo -e "${CYAN}=== 2/7 Dokumentenquelle (DMS) ===${NC}"
  select_option DOCUMENT_PROVIDER "Dokumentenquelle" paperless docspell
  case "${VARS[DOCUMENT_PROVIDER]}" in
    paperless)
      prompt_url "PAPERLESS_API_URL" "Paperless API URL"
      prompt_required "PAPERLESS_API_TOKEN" "Paperless API Token"
      prompt "PAPERLESS_USERNAME" "Paperless Benutzername (optional)"
      VARS["DOCUMENT_PROVIDER_URL"]="${VARS[PAPERLESS_API_URL]}"
      VARS["DOCUMENT_PROVIDER_TOKEN"]="${VARS[PAPERLESS_API_TOKEN]}"
      ;;
    docspell)
      warn "Docspell ist als Platzhalter registriert, aber noch NICHT implementiert (NotImplementedError)."
      prompt_url "DOCUMENT_PROVIDER_URL" "Docspell API URL"
      prompt_required "DOCUMENT_PROVIDER_TOKEN" "Docspell API Token"
      ;;
  esac
}

configure_vector_db() {
  echo ""
  echo -e "${CYAN}=== 3/7 Vektor-Datenbank ===${NC}"
  select_option VECTOR_DB_TYPE "Vektor-Datenbank" chroma qdrant pgvector
  select_option VECTOR_DB_MODE "Modus" new existing
  case "${VARS[VECTOR_DB_TYPE]}" in
    chroma)
      if [ "${VARS[VECTOR_DB_MODE]}" = "new" ]; then
        VARS["CHROMA_URL"]="http://chromadb:8000"
        info "Chroma wird als Container 'chromadb' gestartet (URL: ${VARS[CHROMA_URL]})."
      else
        prompt_url "CHROMA_URL" "Bestehende Chroma-URL"
      fi
      ;;
    qdrant)
      if [ "${VARS[VECTOR_DB_MODE]}" = "new" ]; then
        VARS["QDRANT_URL"]="http://qdrant:6333"
        info "Qdrant wird als Container 'qdrant' gestartet (URL: ${VARS[QDRANT_URL]})."
        VARS["QDRANT_API_KEY"]="${VARS[QDRANT_API_KEY]:-}"
        prompt "QDRANT_API_KEY" "Qdrant API-Key (optional)"
      else
        prompt_url "QDRANT_URL" "Bestehende Qdrant-URL"
        prompt "QDRANT_API_KEY" "Qdrant API-Key (optional)"
      fi
      ;;
    pgvector)
      if [ "${VARS[VECTOR_DB_MODE]}" = "new" ]; then
        VARS["PGVECTOR_URL"]="postgresql://paperless:paperless@pgvector:5432/paperless_ai"
        info "PGVector wird als Container 'pgvector' gestartet."
      else
        warn "Bestehende Postgres/PGVector-Verbindung (z.B. Paperless-Postgres)."
        warn "Hinweis: Die 'vector'-Extension muss installiert sein: CREATE EXTENSION vector;"
        prompt_required "PGVECTOR_URL" "PGVector-Verbindungs-URL (postgresql://...)"
      fi
      ;;
  esac
}

configure_keyword() {
  echo ""
  echo -e "${CYAN}=== 4/7 Hybrid-Suche / Keyword (BM25) ===${NC}"
  local kw_options=()
  case "${VARS[VECTOR_DB_TYPE]}" in
    qdrant)   kw_options=(auto native) ;;
    pgvector) kw_options=(auto fts) ;;
    chroma)   kw_options=(auto local) ;;
  esac
  VARS["KEYWORD_METHOD"]="${VARS[KEYWORD_METHOD]:-auto}"
  select_option KEYWORD_METHOD "Keyword-Methode" "${kw_options[@]}"
  VARS["KEYWORD_WEIGHT"]="${VARS[KEYWORD_WEIGHT]:-0.3}"
  prompt "KEYWORD_WEIGHT" "Keyword-Gewicht (0-1)"
  VARS["SEMANTIC_WEIGHT"]="${VARS[SEMANTIC_WEIGHT]:-0.7}"
  prompt "SEMANTIC_WEIGHT" "Semantik-Gewicht (0-1)"
  VARS["FTS_LANGUAGE"]="${VARS[FTS_LANGUAGE]:-german}"
  prompt "FTS_LANGUAGE" "FTS-Sprache (pgvector)"
  VARS["KEYWORD_INDEX_FILE"]="${VARS[KEYWORD_INDEX_FILE]:-/app/data/bm25_index.pkl}"
  prompt "KEYWORD_INDEX_FILE" "BM25-Index-Datei (im Container)"
}

configure_llm() {
  echo ""
  echo -e "${CYAN}=== 5/7 LLM-Provider ===${NC}"
  select_option LLM_PROVIDER "LLM-Provider" openai ollama anthropic custom opencode
  case "${VARS[LLM_PROVIDER]}" in
    openai)
      prompt_secret "OPENAI_API_KEY" "OpenAI API-Key"
      VARS["LLM_MODEL"]="${VARS[LLM_MODEL]:-gpt-4o-mini}"
      prompt "LLM_MODEL" "OpenAI-Modell"
      ;;
    ollama)
      VARS["OLLAMA_BASE_URL"]="${VARS[OLLAMA_BASE_URL]:-http://localhost:11434}"
      prompt_url "OLLAMA_BASE_URL" "Ollama Base-URL"
      VARS["LLM_MODEL"]="${VARS[LLM_MODEL]:-llama3.2}"
      prompt "LLM_MODEL" "Ollama-Modell"
      ;;
    anthropic)
      prompt_secret "ANTHROPIC_API_KEY" "Anthropic API-Key"
      VARS["LLM_MODEL"]="${VARS[LLM_MODEL]:-claude-3-5-sonnet-20240620}"
      prompt "LLM_MODEL" "Anthropic-Modell"
      ;;
    custom)
      prompt_url "CUSTOM_BASE_URL" "Custom Base-URL"
      prompt_secret "CUSTOM_API_KEY" "Custom API-Key"
      VARS["CUSTOM_MODEL"]="${VARS[CUSTOM_MODEL]:-deepseek-chat}"
      prompt "CUSTOM_MODEL" "Custom-Modell"
      VARS["LLM_MODEL"]="${VARS[CUSTOM_MODEL]}"
      ;;
    opencode)
      VARS["OPENCODE_BASE_URL"]="${VARS[OPENCODE_BASE_URL]:-http://127.0.0.1:4096}"
      prompt_url "OPENCODE_BASE_URL" "OpenCode Base-URL"
      VARS["OPENCODE_USERNAME"]="${VARS[OPENCODE_USERNAME]:-opencode}"
      prompt "OPENCODE_USERNAME" "OpenCode Benutzername"
      prompt_secret "OPENCODE_PASSWORD" "OpenCode Passwort (optional)"
      prompt "OPENCODE_MODEL" "OpenCode Modell (provider/model, optional)"
      ;;
  esac
}

configure_backend() {
  echo ""
  echo -e "${CYAN}=== 6/7 Backend ===${NC}"
  select_option BACKEND_DB_MODE "Backend-Datenbank (Postgres)" new existing
  if [ "${VARS[BACKEND_DB_MODE]}" = "new" ]; then
    VARS["DATABASE_URL"]="postgresql://paperless:paperless@postgres:5432/paperless_ai"
    info "Postgres wird als Container 'postgres' gestartet."
  else
    prompt_required "DATABASE_URL" "Bestehende Postgres-URL (postgresql://...)"
  fi
  VARS["BACKEND_PORT"]="${VARS[BACKEND_PORT]:-3001}"
  prompt "BACKEND_PORT" "Backend-Port (Host)"
  VARS["INGESTION_PORT"]="${VARS[INGESTION_PORT]:-8001}"
  prompt "INGESTION_PORT" "Ingestion-Pipeline-Port (Container/Netzwerk)"
  VARS["INGESTION_HOST_PORT"]="${VARS[INGESTION_HOST_PORT]:-${VARS[INGESTION_PORT]}}"
  prompt "INGESTION_HOST_PORT" "Ingestion-Pipeline-Port (Host)"
  VARS["RETRIEVAL_PORT"]="${VARS[RETRIEVAL_PORT]:-8002}"
  prompt "RETRIEVAL_PORT" "Retrieval-Pipeline-Port (Container/Netzwerk)"
  VARS["RETRIEVAL_HOST_PORT"]="${VARS[RETRIEVAL_HOST_PORT]:-${VARS[RETRIEVAL_PORT]}}"
  prompt "RETRIEVAL_HOST_PORT" "Retrieval-Pipeline-Port (Host)"
  VARS["GENERATION_PORT"]="${VARS[GENERATION_PORT]:-8003}"
  prompt "GENERATION_PORT" "Generation-Pipeline-Port (Container/Netzwerk)"
  VARS["GENERATION_HOST_PORT"]="${VARS[GENERATION_HOST_PORT]:-${VARS[GENERATION_PORT]}}"
  prompt "GENERATION_HOST_PORT" "Generation-Pipeline-Port (Host)"
  VARS["EXTERNAL_API_ENABLED"]="${VARS[EXTERNAL_API_ENABLED]:-no}"
  prompt_yesno "EXTERNAL_API_ENABLED" "Externe API aktivieren?"
  if [ -z "${VARS[JWT_SECRET]:-}" ]; then
    VARS["JWT_SECRET"]="$(generate_secret)"
    info "JWT_SECRET generiert."
  fi
  if [ -z "${VARS[API_KEY]:-}" ]; then
    VARS["API_KEY"]="$(generate_secret)"
    info "API_KEY generiert."
  fi
}

configure_legacy() {
  echo ""
  echo -e "${CYAN}=== 7/7 Sonstiges (optional) ===${NC}"
  VARS["PAPERLESS_AI_INITIAL_SETUP"]="${VARS[PAPERLESS_AI_INITIAL_SETUP]:-yes}"
  prompt_yesno "PAPERLESS_AI_INITIAL_SETUP" "Initiales Setup?"
  VARS["SCAN_INTERVAL"]="${VARS[SCAN_INTERVAL]:-*/30 * * * *}"
  prompt "SCAN_INTERVAL" "Scan-Intervall (Cron)"
  VARS["PROCESS_PREDEFINED_DOCUMENTS"]="${VARS[PROCESS_PREDEFINED_DOCUMENTS]:-no}"
  prompt_yesno "PROCESS_PREDEFINED_DOCUMENTS" "Vordefinierte Dokumente verarbeiten?"
  VARS["TAGS"]="${VARS[TAGS]:-}"
  prompt "TAGS" "Tags (kommagetrennt, optional)"
  VARS["ADD_AI_PROCESSED_TAG"]="${VARS[ADD_AI_PROCESSED_TAG]:-no}"
  prompt_yesno "ADD_AI_PROCESSED_TAG" "AI-verarbeitet-Tag hinzufügen?"
  VARS["AI_PROCESSED_TAG_NAME"]="${VARS[AI_PROCESSED_TAG_NAME]:-ai-processed}"
  prompt "AI_PROCESSED_TAG_NAME" "AI-verarbeitet-Tag-Name"
  VARS["USE_PROMPT_TAGS"]="${VARS[USE_PROMPT_TAGS]:-no}"
  prompt_yesno "USE_PROMPT_TAGS" "Prompt-Tags verwenden?"
  VARS["PROMPT_TAGS"]="${VARS[PROMPT_TAGS]:-}"
  prompt "PROMPT_TAGS" "Prompt-Tags (kommagetrennt, optional)"
  VARS["USE_EXISTING_DATA"]="${VARS[USE_EXISTING_DATA]:-no}"
  prompt_yesno "USE_EXISTING_DATA" "Bestehende Daten verwenden?"
  VARS["SYSTEM_PROMPT"]="${VARS[SYSTEM_PROMPT]:-You are a helpful document assistant. Analyze the following document and extract relevant metadata, tags, and a concise summary.}"
  prompt "SYSTEM_PROMPT" "System-Prompt (optional)"
}

# --- Quickstart-Defaults (non-interaktiv) -----------------------------------
apply_quickstart_defaults() {
  echo ""
  info "Quickstart: verwende vorkonfigurierte Defaults (non-interaktiv)."

  VARS["IMAGE_REGISTRY"]="${VARS[IMAGE_REGISTRY]:-$DEFAULT_REGISTRY}"
  VARS["IMAGE_TAG"]="${VARS[IMAGE_TAG]:-$DEFAULT_TAG}"

  # DMS: Paperless (Werte via Env/Flags überschreibbar)
  VARS["DOCUMENT_PROVIDER"]="${VARS[DOCUMENT_PROVIDER]:-paperless}"
  VARS["PAPERLESS_API_URL"]="${VARS[PAPERLESS_API_URL]:-http://localhost:8000}"
  VARS["PAPERLESS_API_TOKEN"]="${VARS[PAPERLESS_API_TOKEN]:-}"
  VARS["DOCUMENT_PROVIDER_URL"]="${VARS[DOCUMENT_PROVIDER_URL]:-${VARS[PAPERLESS_API_URL]}}"
  VARS["DOCUMENT_PROVIDER_TOKEN"]="${VARS[DOCUMENT_PROVIDER_TOKEN]:-${VARS[PAPERLESS_API_TOKEN]}}"

  # VectorDB: Chroma neu
  VARS["VECTOR_DB_TYPE"]="${VARS[VECTOR_DB_TYPE]:-chroma}"
  VARS["VECTOR_DB_MODE"]="${VARS[VECTOR_DB_MODE]:-new}"
  VARS["CHROMA_URL"]="${VARS[CHROMA_URL]:-http://chromadb:8000}"

  # Hybrid-Suche
  VARS["KEYWORD_METHOD"]="${VARS[KEYWORD_METHOD]:-auto}"
  VARS["KEYWORD_WEIGHT"]="${VARS[KEYWORD_WEIGHT]:-0.3}"
  VARS["SEMANTIC_WEIGHT"]="${VARS[SEMANTIC_WEIGHT]:-0.7}"
  VARS["FTS_LANGUAGE"]="${VARS[FTS_LANGUAGE]:-german}"
  VARS["KEYWORD_INDEX_FILE"]="${VARS[KEYWORD_INDEX_FILE]:-/app/data/bm25_index.pkl}"

  # LLM: Ollama
  VARS["LLM_PROVIDER"]="${VARS[LLM_PROVIDER]:-ollama}"
  VARS["LLM_MODEL"]="${VARS[LLM_MODEL]:-llama3.2}"
  VARS["OLLAMA_BASE_URL"]="${VARS[OLLAMA_BASE_URL]:-http://localhost:11434}"

  # Backend
  VARS["BACKEND_DB_MODE"]="${VARS[BACKEND_DB_MODE]:-new}"
  VARS["DATABASE_URL"]="${VARS[DATABASE_URL]:-postgresql://paperless:paperless@postgres:5432/paperless_ai}"
  VARS["BACKEND_PORT"]="${VARS[BACKEND_PORT]:-3001}"
  VARS["INGESTION_PORT"]="${VARS[INGESTION_PORT]:-8001}"
  VARS["INGESTION_HOST_PORT"]="${VARS[INGESTION_HOST_PORT]:-${VARS[INGESTION_PORT]}}"
  VARS["RETRIEVAL_PORT"]="${VARS[RETRIEVAL_PORT]:-8002}"
  VARS["RETRIEVAL_HOST_PORT"]="${VARS[RETRIEVAL_HOST_PORT]:-${VARS[RETRIEVAL_PORT]}}"
  VARS["GENERATION_PORT"]="${VARS[GENERATION_PORT]:-8003}"
  VARS["GENERATION_HOST_PORT"]="${VARS[GENERATION_HOST_PORT]:-${VARS[GENERATION_PORT]}}"
  VARS["EXTERNAL_API_ENABLED"]="${VARS[EXTERNAL_API_ENABLED]:-no}"

  # Secrets
  if [ -z "${VARS[JWT_SECRET]:-}" ]; then VARS["JWT_SECRET"]="$(generate_secret)"; fi
  if [ -z "${VARS[API_KEY]:-}" ]; then VARS["API_KEY"]="$(generate_secret)"; fi
}

# --- config.json (Admin-Panel Base-Config) ---------------------------------
write_config() {
  echo ""
  info "Schreibe config/config.json (Admin-Panel Base-Config) ..."
  mkdir -p "$REPO_DIR/config"
  local cfg="$REPO_DIR/config/config.json"
  {
    echo '{'
    echo '  "version": 1,'
    echo '  "llm": {'
    echo "    \"provider\": \"${VARS[LLM_PROVIDER]}\","
    echo "    \"model\": \"${VARS[LLM_MODEL]}\""
    if [ -n "${VARS[OLLAMA_BASE_URL]:-}" ]; then
      echo ",    \"baseUrl\": \"${VARS[OLLAMA_BASE_URL]}\""
    fi
    echo '  },'
    echo '  "connectors": ['
    echo '    {'
    echo "      \"id\": \"${VARS[DOCUMENT_PROVIDER]}\","
    echo "      \"type\": \"${VARS[DOCUMENT_PROVIDER]}\","
    echo '      "enabled": true,'
    if [ -n "${VARS[DOCUMENT_PROVIDER_URL]:-}" ]; then
      echo "      \"url\": \"${VARS[DOCUMENT_PROVIDER_URL]}\","
    fi
    echo '      "tokenEnv": "DOCUMENT_PROVIDER_TOKEN"'
    echo '    }'
    echo '  ],'
    echo '  "vectorDb": {'
    echo "    \"type\": \"${VARS[VECTOR_DB_TYPE]}\","
    echo '    "collection": "documents",'
    echo '    "embeddingProvider": "sentence_transformer",'
    echo '    "embeddingModel": "paraphrase-multilingual-MiniLM-L12-v2",'
    echo '    "rerankerProvider": "cross_encoder",'
    echo '    "crossEncoderModel": "cross-encoder/ms-marco-MiniLM-L-6-v2",'
    echo '    "similarityMetric": "cosine"'
    case "${VARS[VECTOR_DB_TYPE]}" in
      chroma)   [ -n "${VARS[CHROMA_URL]:-}" ]   && echo ",    \"chromaUrl\": \"${VARS[CHROMA_URL]}\"" ;;
      qdrant)   [ -n "${VARS[QDRANT_URL]:-}" ]   && echo ",    \"qdrantUrl\": \"${VARS[QDRANT_URL]}\"" ;;
      pgvector) [ -n "${VARS[PGVECTOR_URL]:-}" ] && echo ",    \"pgvectorUrl\": \"${VARS[PGVECTOR_URL]}\"" ;;
    esac
    echo '  },'
    echo '  "hybridSearch": {'
    echo "    \"keywordMethod\": \"${VARS[KEYWORD_METHOD]}\","
    echo "    \"keywordWeight\": ${VARS[KEYWORD_WEIGHT]},"
    echo "    \"semanticWeight\": ${VARS[SEMANTIC_WEIGHT]},"
    echo "    \"ftsLanguage\": \"${VARS[FTS_LANGUAGE]}\","
    echo "    \"keywordIndexFile\": \"${VARS[KEYWORD_INDEX_FILE]}\""
    echo '  },'
    echo '  "retrieval": { "maxResults": 20 }'
    echo '}'
  } > "$cfg"
  ok "config.json geschrieben."
}

# --- .env schreiben ---------------------------------------------------------
write_env() {
  echo ""
  info "Schreibe ${ENV_FILE} ..."
  mkdir -p "$(dirname "$ENV_FILE")"
  if [ -f "$ENV_FILE" ]; then
    cp "$ENV_FILE" "${ENV_FILE}.bak.$(date '+%Y%m%d_%H%M%S')"
    ok "Backup erstellt."
  fi

  cat > "$ENV_FILE" <<EOF
# ============================================================
# DocuMind Umgebungskonfiguration
# Generiert von install.sh am $(date '+%Y-%m-%d %H:%M:%S')
# Hinweis: URLs sind In-Netzwerk-Adressen (docker network $NETWORK_NAME).
# Achtung: Keine Backticks oder \$(...) in Werten verwenden (wird beim
# Sourcen der .env durch start.sh ausgeführt).
# ============================================================

# --- 1. Image-Registry (GHCR) ---
IMAGE_REGISTRY="${VARS[IMAGE_REGISTRY]}"
IMAGE_TAG="${VARS[IMAGE_TAG]}"
NETWORK_NAME="$NETWORK_NAME"
DATA_VOLUME="$DATA_VOLUME"

# --- 2. Dokumentenquelle (DMS) ---
DOCUMENT_PROVIDER="${VARS[DOCUMENT_PROVIDER]}"
DOCUMENT_PROVIDER_URL="${VARS[DOCUMENT_PROVIDER_URL]}"
DOCUMENT_PROVIDER_TOKEN="${VARS[DOCUMENT_PROVIDER_TOKEN]}"
PAPERLESS_API_URL="${VARS[PAPERLESS_API_URL]}"
PAPERLESS_API_TOKEN="${VARS[PAPERLESS_API_TOKEN]}"
PAPERLESS_USERNAME="${VARS[PAPERLESS_USERNAME]}"

# --- 3. Vektor-DB / Embeddings / Reranker ---
VECTOR_DB_TYPE="${VARS[VECTOR_DB_TYPE]}"
VECTOR_DB_MODE="${VARS[VECTOR_DB_MODE]}"
EMBEDDING_PROVIDER=sentence_transformer
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
RERANKER_PROVIDER=cross_encoder
CROSS_ENCODER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
COLLECTION_NAME=documents
SIMILARITY_METRIC=cosine
CHROMA_URL="${VARS[CHROMA_URL]}"
QDRANT_URL="${VARS[QDRANT_URL]}"
QDRANT_API_KEY="${VARS[QDRANT_API_KEY]}"
PGVECTOR_URL="${VARS[PGVECTOR_URL]}"

# --- 4. Hybrid-Suche / Keyword (BM25) ---
KEYWORD_METHOD="${VARS[KEYWORD_METHOD]}"
KEYWORD_WEIGHT="${VARS[KEYWORD_WEIGHT]}"
SEMANTIC_WEIGHT="${VARS[SEMANTIC_WEIGHT]}"
FTS_LANGUAGE="${VARS[FTS_LANGUAGE]}"
KEYWORD_INDEX_FILE="${VARS[KEYWORD_INDEX_FILE]}"

# --- 5. LLM ---
LLM_PROVIDER="${VARS[LLM_PROVIDER]}"
LLM_MODEL="${VARS[LLM_MODEL]}"
OPENAI_API_KEY="${VARS[OPENAI_API_KEY]}"
OLLAMA_BASE_URL="${VARS[OLLAMA_BASE_URL]}"
ANTHROPIC_API_KEY="${VARS[ANTHROPIC_API_KEY]}"
CUSTOM_BASE_URL="${VARS[CUSTOM_BASE_URL]}"
CUSTOM_API_KEY="${VARS[CUSTOM_API_KEY]}"
CUSTOM_MODEL="${VARS[CUSTOM_MODEL]}"
OPENCODE_BASE_URL="${VARS[OPENCODE_BASE_URL]}"
OPENCODE_USERNAME="${VARS[OPENCODE_USERNAME]}"
OPENCODE_PASSWORD="${VARS[OPENCODE_PASSWORD]}"
OPENCODE_MODEL="${VARS[OPENCODE_MODEL]}"

# --- 6. Backend ---
NODE_ENV=production
BACKEND_PORT="${VARS[BACKEND_PORT]}"
DATABASE_URL="${VARS[DATABASE_URL]}"
BACKEND_DB_MODE="${VARS[BACKEND_DB_MODE]}"
JWT_SECRET="${VARS[JWT_SECRET]}"
API_KEY="${VARS[API_KEY]}"
EXTERNAL_API_ENABLED="${VARS[EXTERNAL_API_ENABLED]}"

# --- 7. Inter-Service-URLs & Pipeline-Ports ---
INGESTION_PORT="${VARS[INGESTION_PORT]}"
INGESTION_HOST_PORT="${VARS[INGESTION_HOST_PORT]}"
RETRIEVAL_PORT="${VARS[RETRIEVAL_PORT]}"
RETRIEVAL_HOST_PORT="${VARS[RETRIEVAL_HOST_PORT]}"
GENERATION_PORT="${VARS[GENERATION_PORT]}"
GENERATION_HOST_PORT="${VARS[GENERATION_HOST_PORT]}"
INGESTION_PIPELINE_URL=http://ingestion-pipeline:${VARS[INGESTION_PORT]}
RETRIEVAL_PIPELINE_URL=http://retrieval-pipeline:${VARS[RETRIEVAL_PORT]}
GENERATION_PIPELINE_URL=http://generation-pipeline:${VARS[GENERATION_PORT]}
MAX_RESULTS=20
VITE_API_URL=http://localhost:${VARS[BACKEND_PORT]}

# --- 8. Sonstiges (optional) ---
PAPERLESS_AI_INITIAL_SETUP="${VARS[PAPERLESS_AI_INITIAL_SETUP]}"
SCAN_INTERVAL="${VARS[SCAN_INTERVAL]}"
PROCESS_PREDEFINED_DOCUMENTS="${VARS[PROCESS_PREDEFINED_DOCUMENTS]}"
TAGS="${VARS[TAGS]}"
ADD_AI_PROCESSED_TAG="${VARS[ADD_AI_PROCESSED_TAG]}"
AI_PROCESSED_TAG_NAME="${VARS[AI_PROCESSED_TAG_NAME]}"
USE_PROMPT_TAGS="${VARS[USE_PROMPT_TAGS]}"
PROMPT_TAGS="${VARS[PROMPT_TAGS]}"
USE_EXISTING_DATA="${VARS[USE_EXISTING_DATA]}"
SYSTEM_PROMPT="${VARS[SYSTEM_PROMPT]}"

# --- 9. Gateway / MCP / Admin-Panel Config ---
CONFIG_FILE="${VARS[CONFIG_FILE]}"
GATEWAY_API_TOKEN="${VARS[GATEWAY_API_TOKEN]}"
GATEWAY_URL="${VARS[GATEWAY_URL]}"
PIPELINE_CONTAINER_MAP="${VARS[PIPELINE_CONTAINER_MAP]}"
EOF
  ok ".env geschrieben."
}

# --- Helper-Skripte generieren ----------------------------------------------
generate_scripts() {
  echo ""
  info "Generiere start.sh / stop.sh / update.sh ..."

  # start.sh
  cat > "$REPO_DIR/start.sh" <<'STARTEOF'
#!/usr/bin/env bash
set -euo pipefail
# DocuMind Stack starten (docker run, kein Compose)
# Generiert von install.sh — bei Bedarf anpassen.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f .env ]; then
  echo "Keine .env gefunden. Führe zuerst install.sh aus." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1091
source .env
set +a

NETWORK="${NETWORK_NAME:-documind}"
REGISTRY="${IMAGE_REGISTRY:-ghcr.io/chris576/documind}"
TAG="${IMAGE_TAG:-latest}"
DATA_VOLUME="${DATA_VOLUME:-documind-data}"

container_running() { docker inspect -f '{{.State.Running}}' "$1" 2>/dev/null | grep -q true; }
container_exists() { docker inspect "$1" >/dev/null 2>&1; }

ensure_container() {
  local name="$1"
  shift
  if container_running "$name"; then
    echo "[OK] $name läuft bereits."
    return 0
  fi
  if container_exists "$name"; then
    echo "[INFO] Starte vorhandenen Container $name ..."
    docker start "$name"
    return 0
  fi
  echo "[INFO] Starte Container $name ..."
  docker run -d --name "$name" "$@"
}

ensure_image() {
  local image="$1" service="$2" ans
  if docker image inspect "$image" >/dev/null 2>&1; then
    return 0
  fi
  echo "[INFO] Pull $image ..."
  if docker pull "$image" >/dev/null 2>&1; then
    return 0
  fi
  echo "[WARN] Pull fehlgeschlagen: $image" >&2
  if [ -d "apps/$service" ]; then
    read -rp "Image lokal bauen (docker build)? [y/N]: " ans
    if [[ "$ans" =~ ^[Yy] ]]; then
      docker build -t "$image" "apps/$service" \
        || echo "[WARN] Build fehlgeschlagen (Build-Kontext packages/ prüfen)." >&2
    fi
  fi
}

# Netzwerk
docker network inspect "$NETWORK" >/dev/null 2>&1 || docker network create "$NETWORK"

# --- Datenbanken ---
if [ "${BACKEND_DB_MODE:-new}" = "new" ]; then
  ensure_container documind-postgres \
    --network "$NETWORK" \
    -e POSTGRES_USER=paperless \
    -e POSTGRES_PASSWORD=paperless \
    -e POSTGRES_DB=paperless_ai \
    -p 5432:5432 \
    -v postgres_data:/var/lib/postgresql/data \
    --restart unless-stopped \
    postgres:16-alpine
fi

if [ "${VECTOR_DB_MODE:-new}" = "new" ]; then
  case "${VECTOR_DB_TYPE}" in
    chroma)
      ensure_container documind-chromadb \
        --network "$NETWORK" \
        -e IS_PERSISTENT=TRUE \
        -e ANONYMIZED_TELEMETRY=FALSE \
        -p 8000:8000 \
        -v chroma_data:/chroma/chroma \
        --restart unless-stopped \
        chromadb/chroma:latest
      ;;
    qdrant)
      ensure_container documind-qdrant \
        --network "$NETWORK" \
        -p 6333:6333 \
        -v qdrant_data:/qdrant/storage \
        --restart unless-stopped \
        qdrant/qdrant:latest
      ;;
    pgvector)
      ensure_container documind-pgvector \
        --network "$NETWORK" \
        -e POSTGRES_USER=paperless \
        -e POSTGRES_PASSWORD=paperless \
        -e POSTGRES_DB=paperless_ai \
        -p 5433:5432 \
        -v pgvector_data:/var/lib/postgresql/data \
        --restart unless-stopped \
        pgvector/pgvector:pg16
      ;;
  esac
fi

# --- App-Container (Images aus GHCR) ---
ensure_image "$REGISTRY/backend:$TAG" backend
ensure_container documind-backend \
  --network "$NETWORK" \
  -e NODE_ENV=production \
  -e BACKEND_PORT=3001 \
  -e DATABASE_URL="${DATABASE_URL}" \
  -e JWT_SECRET="${JWT_SECRET}" \
  -e API_KEY="${API_KEY}" \
  -e PAPERLESS_API_URL="${PAPERLESS_API_URL}" \
  -e PAPERLESS_API_TOKEN="${PAPERLESS_API_TOKEN}" \
  -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
  -e OLLAMA_API_URL="${OLLAMA_BASE_URL}" \
  -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}" \
  -e CUSTOM_BASE_URL="${CUSTOM_BASE_URL}" \
  -e CUSTOM_API_KEY="${CUSTOM_API_KEY}" \
  -e VECTOR_DB_TYPE="${VECTOR_DB_TYPE}" \
  -e CHROMA_URL="${CHROMA_URL}" \
  -e QDRANT_URL="${QDRANT_URL}" \
  -e QDRANT_API_KEY="${QDRANT_API_KEY}" \
  -e PGVECTOR_URL="${PGVECTOR_URL}" \
  -e INGESTION_PIPELINE_URL="${INGESTION_PIPELINE_URL}" \
  -e RETRIEVAL_PIPELINE_URL="${RETRIEVAL_PIPELINE_URL}" \
  -e GENERATION_PIPELINE_URL="${GENERATION_PIPELINE_URL}" \
  -e EXTERNAL_API_ENABLED="${EXTERNAL_API_ENABLED}" \
  -e CONFIG_FILE="/data/config.json" \
  -e GATEWAY_API_TOKEN="${GATEWAY_API_TOKEN:-}" \
  -v ./config:/data \
  -p "${BACKEND_PORT:-3001}:3001" \
  --restart unless-stopped \
  "$REGISTRY/backend:$TAG"

ensure_image "$REGISTRY/frontend:$TAG" frontend
ensure_container documind-frontend \
  --network "$NETWORK" \
  -e VITE_API_URL="${VITE_API_URL:-http://localhost:3001}" \
  -p 3000:80 \
  --restart unless-stopped \
  "$REGISTRY/frontend:$TAG"

ensure_image "$REGISTRY/ingestion-pipeline:$TAG" ingestion-pipeline
ensure_container documind-ingestion \
  --network "$NETWORK" \
  -e PYTHONUNBUFFERED=1 \
  -e PORT="${INGESTION_PORT:-8001}" \
  -e GATEWAY_URL="http://backend:3001" \
  -e DOCUMENT_PROVIDER="${DOCUMENT_PROVIDER}" \
  -e DOCUMENT_PROVIDER_URL="${DOCUMENT_PROVIDER_URL}" \
  -e DOCUMENT_PROVIDER_TOKEN="${DOCUMENT_PROVIDER_TOKEN}" \
  -e PAPERLESS_API_URL="${PAPERLESS_API_URL}" \
  -e PAPERLESS_API_TOKEN="${PAPERLESS_API_TOKEN}" \
  -e VECTOR_DB_TYPE="${VECTOR_DB_TYPE}" \
  -e EMBEDDING_PROVIDER="${EMBEDDING_PROVIDER}" \
  -e EMBEDDING_MODEL="${EMBEDDING_MODEL}" \
  -e COLLECTION_NAME="${COLLECTION_NAME}" \
  -e SIMILARITY_METRIC="${SIMILARITY_METRIC}" \
  -e CHROMA_URL="${CHROMA_URL}" \
  -e QDRANT_URL="${QDRANT_URL}" \
  -e QDRANT_API_KEY="${QDRANT_API_KEY}" \
  -e PGVECTOR_URL="${PGVECTOR_URL}" \
  -e KEYWORD_METHOD="${KEYWORD_METHOD}" \
  -e KEYWORD_WEIGHT="${KEYWORD_WEIGHT}" \
  -e SEMANTIC_WEIGHT="${SEMANTIC_WEIGHT}" \
  -e FTS_LANGUAGE="${FTS_LANGUAGE}" \
  -e KEYWORD_INDEX_FILE="${KEYWORD_INDEX_FILE}" \
  -p "${INGESTION_HOST_PORT:-8001}:${INGESTION_PORT:-8001}" \
  -v "${DATA_VOLUME}:/app/data" \
  --restart unless-stopped \
  "$REGISTRY/ingestion-pipeline:$TAG"

ensure_image "$REGISTRY/retrieval-pipeline:$TAG" retrieval-pipeline
ensure_container documind-retrieval \
  --network "$NETWORK" \
  -e PYTHONUNBUFFERED=1 \
  -e PORT="${RETRIEVAL_PORT:-8002}" \
  -e GATEWAY_URL="http://backend:3001" \
  -e MAX_RESULTS="${MAX_RESULTS:-20}" \
  -e VECTOR_DB_TYPE="${VECTOR_DB_TYPE}" \
  -e EMBEDDING_PROVIDER="${EMBEDDING_PROVIDER}" \
  -e EMBEDDING_MODEL="${EMBEDDING_MODEL}" \
  -e RERANKER_PROVIDER="${RERANKER_PROVIDER}" \
  -e CROSS_ENCODER_MODEL="${CROSS_ENCODER_MODEL}" \
  -e COLLECTION_NAME="${COLLECTION_NAME}" \
  -e SIMILARITY_METRIC="${SIMILARITY_METRIC}" \
  -e CHROMA_URL="${CHROMA_URL}" \
  -e QDRANT_URL="${QDRANT_URL}" \
  -e QDRANT_API_KEY="${QDRANT_API_KEY}" \
  -e PGVECTOR_URL="${PGVECTOR_URL}" \
  -e KEYWORD_METHOD="${KEYWORD_METHOD}" \
  -e KEYWORD_WEIGHT="${KEYWORD_WEIGHT}" \
  -e SEMANTIC_WEIGHT="${SEMANTIC_WEIGHT}" \
  -e FTS_LANGUAGE="${FTS_LANGUAGE}" \
  -e KEYWORD_INDEX_FILE="${KEYWORD_INDEX_FILE}" \
  -p "${RETRIEVAL_HOST_PORT:-8002}:${RETRIEVAL_PORT:-8002}" \
  -v "${DATA_VOLUME}:/app/data" \
  --restart unless-stopped \
  "$REGISTRY/retrieval-pipeline:$TAG"

ensure_image "$REGISTRY/generation-pipeline:$TAG" generation-pipeline
ensure_container documind-generation \
  --network "$NETWORK" \
  -e PYTHONUNBUFFERED=1 \
  -e PORT="${GENERATION_PORT:-8003}" \
  -e GATEWAY_URL="http://backend:3001" \
  -e LLM_PROVIDER="${LLM_PROVIDER}" \
  -e LLM_MODEL="${LLM_MODEL}" \
  -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
  -e OLLAMA_BASE_URL="${OLLAMA_BASE_URL}" \
  -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}" \
  -e CUSTOM_BASE_URL="${CUSTOM_BASE_URL}" \
  -e CUSTOM_API_KEY="${CUSTOM_API_KEY}" \
  -e CUSTOM_MODEL="${CUSTOM_MODEL}" \
  -e OPENCODE_BASE_URL="${OPENCODE_BASE_URL}" \
  -e OPENCODE_USERNAME="${OPENCODE_USERNAME}" \
  -e OPENCODE_PASSWORD="${OPENCODE_PASSWORD}" \
  -e OPENCODE_MODEL="${OPENCODE_MODEL}" \
  -e RETRIEVAL_PIPELINE_URL="${RETRIEVAL_PIPELINE_URL}" \
  -p "${GENERATION_HOST_PORT:-8003}:${GENERATION_PORT:-8003}" \
  --restart unless-stopped \
  "$REGISTRY/generation-pipeline:$TAG"

echo ""
echo "[OK] Stack gestartet."
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:${BACKEND_PORT:-3001}"
  echo "  Ingestion: http://localhost:${INGESTION_HOST_PORT:-8001}"
  echo "  Retrieval: http://localhost:${RETRIEVAL_HOST_PORT:-8002}"
  echo "  Generation:http://localhost:${GENERATION_HOST_PORT:-8003}"
STARTEOF

  # stop.sh
  cat > "$REPO_DIR/stop.sh" <<'STOPEOF'
#!/usr/bin/env bash
set -euo pipefail
# DocuMind Stack stoppen (Container werden entfernt, Volumes bleiben).
# Generiert von install.sh.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi
NETWORK="${NETWORK_NAME:-documind}"

for c in documind-generation documind-retrieval documind-ingestion \
         documind-frontend documind-backend \
         documind-pgvector documind-qdrant documind-chromadb documind-postgres; do
  if docker inspect "$c" >/dev/null 2>&1; then
    echo "[INFO] Stoppe $c ..."
    docker rm -f "$c"
  fi
done

docker network rm "$NETWORK" 2>/dev/null || true
echo "[OK] Stack gestoppt."
STOPEOF

  # update.sh
  cat > "$REPO_DIR/update.sh" <<'UPDATEEOF'
#!/usr/bin/env bash
set -euo pipefail
# DocuMind Update: neue Images pullen und App-Container neu erstellen.
# Generiert von install.sh.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f .env ]; then
  echo "Keine .env gefunden. Führe zuerst install.sh aus." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1091
source .env
set +a

REGISTRY="${IMAGE_REGISTRY:-ghcr.io/chris576/documind}"
TAG="${IMAGE_TAG:-latest}"

for svc in backend frontend ingestion-pipeline retrieval-pipeline generation-pipeline; do
  echo "[INFO] Pull $REGISTRY/$svc:$TAG ..."
  docker pull "$REGISTRY/$svc:$TAG" || true
done

# App-Container neu erstellen (DB-Container bleiben unangetastet)
for c in documind-generation documind-retrieval documind-ingestion \
         documind-frontend documind-backend; do
  docker rm -f "$c" 2>/dev/null || true
done

exec "$SCRIPT_DIR/start.sh"
UPDATEEOF

  chmod +x "$REPO_DIR/start.sh" "$REPO_DIR/stop.sh" "$REPO_DIR/update.sh"
  ok "Helper-Skripte generiert (start.sh, stop.sh, update.sh)."
}

# --- Zusammenfassung --------------------------------------------------------
print_summary() {
  echo ""
  echo -e "${CYAN}=== Zusammenfassung ===${NC}"
  echo "  Repo:           ${REPO_DIR}"
  echo "  DMS:            ${VARS[DOCUMENT_PROVIDER]}"
  echo "  VectorDB:       ${VARS[VECTOR_DB_TYPE]} (${VARS[VECTOR_DB_MODE]})"
  echo "  LLM:            ${VARS[LLM_PROVIDER]}"
  echo "  Registry:       ${VARS[IMAGE_REGISTRY]}:${VARS[IMAGE_TAG]}"
  echo "  Backend-DB:     ${VARS[BACKEND_DB_MODE]}"
}

# --- Main -------------------------------------------------------------------
main() {
  echo -e "${CYAN}========================================${NC}"
  echo -e "${CYAN}  DocuMind Installer${NC}"
  echo -e "${CYAN}========================================${NC}"
  echo ""

  check_prereqs
  ensure_repo
  cd "$REPO_DIR"
  ENV_FILE="$REPO_DIR/.env"

  load_existing_env

  if [ "$QUICKSTART" = "1" ]; then
    apply_quickstart_defaults
  else
    configure_registry
    configure_dms
    configure_vector_db
    configure_keyword
    configure_llm
    configure_backend
    configure_legacy
  fi

  # Gateway-Konfiguration (gilt für beide Modi)
  VARS["CONFIG_FILE"]="${VARS[CONFIG_FILE]:-/data/config.json}"
  VARS["GATEWAY_URL"]="${VARS[GATEWAY_URL]:-http://localhost:${VARS[BACKEND_PORT]:-3001}}"
  VARS["GATEWAY_API_TOKEN"]="${VARS[GATEWAY_API_TOKEN]:-}"

  write_env
  write_config
  generate_scripts
  print_summary

  if [ "$DRY_RUN" = "1" ]; then
    info "Dry-Run: Keine Container werden gestartet. start.sh wurde generiert."
    info "Starte später mit: bash start.sh"
    return 0
  fi

  echo ""
  prompt_yesno START_NOW "Stack jetzt starten?"
  if [ "${VARS[START_NOW]}" = "yes" ]; then
    bash "$REPO_DIR/start.sh"
  else
    info "Starte später mit: bash start.sh"
  fi
}

main "$@"