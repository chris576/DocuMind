#!/usr/bin/env bash
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"
COMPOSE_FILE="${REPO_ROOT}/infrastructure/docker-compose.yml"

info() { echo -e "${BLUE}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
ok() { echo -e "${GREEN}[OK]${NC} $*"; }

declare -A VARS

load_env() {
  if [[ ! -f "$ENV_FILE" ]]; then
    error "No .env file found at ${ENV_FILE}."
    error "Run setup.sh first."
    exit 1
  fi

  while IFS='=' read -r key val; do
    [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
    key=$(echo "$key" | tr -d '[:space:]')
    val=$(echo "$val" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
    val=$(echo "$val" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
    VARS["$key"]="$val"
  done < "$ENV_FILE"

  ok "Loaded existing .env values."
}

backup_env() {
  local ts
  ts=$(date '+%Y%m%d_%H%M%S')
  local backup="${ENV_FILE}.bak.${ts}"
  cp "$ENV_FILE" "$backup"
  ok "Backup created: ${backup}"
}

prompt() {
  local varname="$1"
  local message="$2"
  local default="${VARS[$varname]:-}"
  local input
  if [ -n "$default" ]; then
    read -rp "$(echo -e "${CYAN}?${NC} $message [${YELLOW}$default${NC}]: ")" input
  else
    read -rp "$(echo -e "${CYAN}?${NC} $message: ")" input
  fi
  VARS["$varname"]="${input:-$default}"
}

prompt_secret() {
  local varname="$1"
  local message="$2"
  local default="${VARS[$varname]:-}"
  local input
  if [ -n "$default" ]; then
    read -rsp "$(echo -e "${CYAN}?${NC} $message [${YELLOW}********${NC}]: ")" input
  else
    read -rsp "$(echo -e "${CYAN}?${NC} $message: ")" input
  fi
  echo ""
  VARS["$varname"]="${input:-$default}"
}

prompt_required() {
  local varname="$1"
  local message="$2"
  while true; do
    prompt "$varname" "$message"
    if [ -n "${VARS[$varname]:-}" ]; then
      break
    else
      error "This value is required."
    fi
  done
}

prompt_yesno() {
  local varname="$1"
  local message="$2"
  local default="${VARS[$varname]:-}"
  local input
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
  local varname="$1"
  local message="$2"
  while true; do
    prompt "$varname" "$message"
    if validate_url "${VARS[$varname]}"; then
      break
    else
      error "Please enter a valid http:// or https:// URL."
    fi
  done
}

select_option() {
  local varname="$1"
  shift
  local message="$1"
  shift
  local options=("$@")
  local current="${VARS[$varname]:-}"
  echo -e "${CYAN}?${NC} $message"
  local default_idx=1
  for i in "${!options[@]}"; do
    if [ "${options[$i]}" = "$current" ]; then
      default_idx=$((i+1))
    fi
    echo "  $((i+1))) ${options[$i]}"
  done
  local choice
  read -rp "Select [1-${#options[@]}] [${YELLOW}$default_idx${NC}]: " choice
  choice="${choice:-$default_idx}"
  if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "${#options[@]}" ]; then
    VARS["$varname"]="${options[$((choice-1))]}"
  else
    error "Invalid choice, using default."
    VARS["$varname"]="${options[$((default_idx-1))]}"
  fi
}

configure_database() {
  echo ""
  echo -e "${CYAN}=== Database Configuration ===${NC}"
  select_option DATABASE_TYPE "Database type" postgresql mysql sqlite

  case "${VARS[DATABASE_TYPE]}" in
    postgresql|mysql)
      local default_host="postgres"
      [ "${VARS[DATABASE_TYPE]}" = "mysql" ] && default_host="mysql"
      VARS["DATABASE_HOST"]="${VARS[DATABASE_HOST]:-$default_host}"
      prompt "DATABASE_HOST" "Database host"
      prompt "DATABASE_PORT" "Database port"
      prompt "DATABASE_USER" "Database user"
      prompt_secret "DATABASE_PASSWORD" "Database password"
      prompt "DATABASE_NAME" "Database name"

      if [ "${VARS[DATABASE_TYPE]}" = "postgresql" ]; then
        VARS["DATABASE_URL"]="postgresql://${VARS[DATABASE_USER]}:${VARS[DATABASE_PASSWORD]}@${VARS[DATABASE_HOST]}:${VARS[DATABASE_PORT]}/${VARS[DATABASE_NAME]}"
      else
        VARS["DATABASE_URL"]="mysql://${VARS[DATABASE_USER]}:${VARS[DATABASE_PASSWORD]}@${VARS[DATABASE_HOST]}:${VARS[DATABASE_PORT]}/${VARS[DATABASE_NAME]}"
      fi
      ;;
    sqlite)
      prompt "SQLITE_FILE_PATH" "SQLite file path"
      VARS["DATABASE_URL"]="sqlite://${VARS[SQLITE_FILE_PATH]}"
      ;;
  esac
}

configure_connector() {
  echo ""
  echo -e "${CYAN}=== Document Connector Configuration ===${NC}"
  select_option DOCUMENT_CONNECTOR_TYPE "Document connector type" paperless nextcloud filesystem rest_api

  case "${VARS[DOCUMENT_CONNECTOR_TYPE]}" in
    paperless)
      prompt_url "PAPERLESS_API_URL" "Paperless API URL"
      prompt_required "PAPERLESS_API_TOKEN" "Paperless API token"
      prompt_required "PAPERLESS_USERNAME" "Paperless username"
      ;;
    nextcloud)
      prompt_url "NEXTCLOUD_URL" "Nextcloud URL"
      prompt_required "NEXTCLOUD_USERNAME" "Nextcloud username"
      prompt_secret "NEXTCLOUD_PASSWORD" "Nextcloud password"
      prompt "NEXTCLOUD_FOLDER" "Nextcloud folder (optional)"
      ;;
    filesystem)
      prompt_required "FILESYSTEM_DOCUMENTS_PATH" "Path to documents directory"
      ;;
    rest_api)
      prompt_url "REST_API_BASE_URL" "REST API base URL"
      prompt "REST_API_KEY" "REST API key (optional)"
      ;;
  esac
}

configure_llm() {
  echo ""
  echo -e "${CYAN}=== LLM Provider Configuration ===${NC}"
  select_option LLM_PROVIDER "LLM provider" custom ollama openai anthropic opencode

  case "${VARS[LLM_PROVIDER]}" in
    custom)
      prompt_url "CUSTOM_BASE_URL" "Custom LLM base URL"
      prompt_secret "CUSTOM_API_KEY" "Custom API key"
      prompt_required "CUSTOM_MODEL" "Model name"
      ;;
    ollama)
      prompt_url "OLLAMA_API_URL" "Ollama API URL"
      prompt_required "OLLAMA_MODEL" "Ollama model name"
      ;;
    openai)
      prompt_secret "OPENAI_API_KEY" "OpenAI API key"
      prompt_required "OPENAI_MODEL" "OpenAI model name"
      ;;
    anthropic)
      prompt_secret "ANTHROPIC_API_KEY" "Anthropic API key"
      prompt "ANTHROPIC_MODEL" "Anthropic model"
      ;;
    opencode)
      prompt_url "OPENCODE_BASE_URL" "OpenCode base URL"
      prompt "OPENCODE_USERNAME" "OpenCode username"
      prompt_secret "OPENCODE_PASSWORD" "OpenCode password (optional)"
      prompt "OPENCODE_MODEL" "OpenCode model (provider/model, optional)"
      ;;
  esac
}

configure_vector_db() {
  echo ""
  echo -e "${CYAN}=== Vector Database Configuration ===${NC}"
  VARS["VECTOR_DB_TYPE"]="pgvector"
  info "Vector database: PostgreSQL/PGVector (fixed stack)."
  VARS["PGVECTOR_URL"]="${VARS[PGVECTOR_URL]:-}"
  prompt_url "PGVECTOR_URL" "PGVector connection URL"
}

configure_legacy() {
  echo ""
  echo -e "${CYAN}=== Legacy / Other Settings ===${NC}"
  prompt_yesno "PAPERLESS_AI_INITIAL_SETUP" "Initial setup?"
  prompt "SCAN_INTERVAL" "Scan interval (cron expression)"
  prompt_yesno "PROCESS_PREDEFINED_DOCUMENTS" "Process predefined documents?"
  prompt "TAGS" "Tags (comma-separated, optional)"
  prompt_yesno "ADD_AI_PROCESSED_TAG" "Add AI processed tag?"
  prompt "AI_PROCESSED_TAG_NAME" "AI processed tag name"
  prompt_yesno "USE_PROMPT_TAGS" "Use prompt tags?"
  prompt "PROMPT_TAGS" "Prompt tags (comma-separated, optional)"
  prompt_yesno "USE_EXISTING_DATA" "Use existing data?"
  prompt "API_KEY" "API key"
  prompt "JWT_SECRET" "JWT secret"
  prompt "SYSTEM_PROMPT" "System prompt"
}

write_env() {
  echo ""
  info "Writing updated ${ENV_FILE} ..."
  mkdir -p "$(dirname "$ENV_FILE")"

  cat > "$ENV_FILE" <<EOF
# ============================================================
# Paperless AI / DMS-RAG Environment Configuration
# Updated by reconfigure.sh on $(date '+%Y-%m-%d %H:%M:%S')
# ============================================================

# ------------------------------------------------------------
# Database
# ------------------------------------------------------------
DATABASE_TYPE=${VARS[DATABASE_TYPE]}
DATABASE_URL=${VARS[DATABASE_URL]}

EOF

  if [ "${VARS[DATABASE_TYPE]}" != "sqlite" ]; then
    cat >> "$ENV_FILE" <<EOF
DATABASE_HOST=${VARS[DATABASE_HOST]}
DATABASE_PORT=${VARS[DATABASE_PORT]}
DATABASE_USER=${VARS[DATABASE_USER]}
DATABASE_PASSWORD=${VARS[DATABASE_PASSWORD]}
DATABASE_NAME=${VARS[DATABASE_NAME]}

EOF
  else
    cat >> "$ENV_FILE" <<EOF
SQLITE_FILE_PATH=${VARS[SQLITE_FILE_PATH]}

EOF
  fi

  cat >> "$ENV_FILE" <<EOF
# ------------------------------------------------------------
# Document Connector
# ------------------------------------------------------------
DOCUMENT_CONNECTOR_TYPE=${VARS[DOCUMENT_CONNECTOR_TYPE]}

EOF

  case "${VARS[DOCUMENT_CONNECTOR_TYPE]}" in
    paperless)
      cat >> "$ENV_FILE" <<EOF
PAPERLESS_API_URL=${VARS[PAPERLESS_API_URL]}
PAPERLESS_API_TOKEN=${VARS[PAPERLESS_API_TOKEN]}
PAPERLESS_USERNAME=${VARS[PAPERLESS_USERNAME]}

EOF
      ;;
    nextcloud)
      cat >> "$ENV_FILE" <<EOF
NEXTCLOUD_URL=${VARS[NEXTCLOUD_URL]}
NEXTCLOUD_USERNAME=${VARS[NEXTCLOUD_USERNAME]}
NEXTCLOUD_PASSWORD=${VARS[NEXTCLOUD_PASSWORD]}
NEXTCLOUD_FOLDER=${VARS[NEXTCLOUD_FOLDER]}

EOF
      ;;
    filesystem)
      cat >> "$ENV_FILE" <<EOF
FILESYSTEM_DOCUMENTS_PATH=${VARS[FILESYSTEM_DOCUMENTS_PATH]}

EOF
      ;;
    rest_api)
      cat >> "$ENV_FILE" <<EOF
REST_API_BASE_URL=${VARS[REST_API_BASE_URL]}
REST_API_KEY=${VARS[REST_API_KEY]}

EOF
      ;;
  esac

  cat >> "$ENV_FILE" <<EOF
# ------------------------------------------------------------
# LLM Provider
# ------------------------------------------------------------
LLM_PROVIDER=${VARS[LLM_PROVIDER]}

EOF

  case "${VARS[LLM_PROVIDER]}" in
    custom)
      cat >> "$ENV_FILE" <<EOF
CUSTOM_BASE_URL=${VARS[CUSTOM_BASE_URL]}
CUSTOM_API_KEY=${VARS[CUSTOM_API_KEY]}
CUSTOM_MODEL=${VARS[CUSTOM_MODEL]}

EOF
      ;;
    ollama)
      cat >> "$ENV_FILE" <<EOF
OLLAMA_API_URL=${VARS[OLLAMA_API_URL]}
OLLAMA_MODEL=${VARS[OLLAMA_MODEL]}

EOF
      ;;
    openai)
      cat >> "$ENV_FILE" <<EOF
OPENAI_API_KEY=${VARS[OPENAI_API_KEY]}
OPENAI_MODEL=${VARS[OPENAI_MODEL]}

EOF
      ;;
    anthropic)
      cat >> "$ENV_FILE" <<EOF
ANTHROPIC_API_KEY=${VARS[ANTHROPIC_API_KEY]}
ANTHROPIC_MODEL=${VARS[ANTHROPIC_MODEL]}

EOF
      ;;
    opencode)
      cat >> "$ENV_FILE" <<EOF
OPENCODE_BASE_URL=${VARS[OPENCODE_BASE_URL]}
OPENCODE_USERNAME=${VARS[OPENCODE_USERNAME]}
OPENCODE_PASSWORD=${VARS[OPENCODE_PASSWORD]}
OPENCODE_MODEL=${VARS[OPENCODE_MODEL]}

EOF
      ;;
  esac

  cat >> "$ENV_FILE" <<EOF
# ------------------------------------------------------------
# Vector Database
# ------------------------------------------------------------
VECTOR_DB_TYPE=${VARS[VECTOR_DB_TYPE]}
PGVECTOR_URL=${VARS[PGVECTOR_URL]}

EOF

  cat >> "$ENV_FILE" <<EOF
# ------------------------------------------------------------
# Legacy / Other
# ------------------------------------------------------------
PAPERLESS_AI_INITIAL_SETUP=${VARS[PAPERLESS_AI_INITIAL_SETUP]}
SCAN_INTERVAL=${VARS[SCAN_INTERVAL]}
PROCESS_PREDEFINED_DOCUMENTS=${VARS[PROCESS_PREDEFINED_DOCUMENTS]}
TAGS=${VARS[TAGS]}
ADD_AI_PROCESSED_TAG=${VARS[ADD_AI_PROCESSED_TAG]}
AI_PROCESSED_TAG_NAME=${VARS[AI_PROCESSED_TAG_NAME]}
USE_PROMPT_TAGS=${VARS[USE_PROMPT_TAGS]}
PROMPT_TAGS=${VARS[PROMPT_TAGS]}
USE_EXISTING_DATA=${VARS[USE_EXISTING_DATA]}
API_KEY=${VARS[API_KEY]}
JWT_SECRET=${VARS[JWT_SECRET]}
SYSTEM_PROMPT=${VARS[SYSTEM_PROMPT]}

EOF

  ok ".env updated successfully."
}

offer_restart() {
  echo ""
  if docker compose -f "${COMPOSE_FILE}" ps -q 2>/dev/null | grep -q .; then
    ok "A Docker Compose stack appears to be running."
    local choice
    read -rp "$(echo -e "${CYAN}?${NC} Restart the stack now? [y/N]: ")" choice
    if [[ "$choice" =~ ^[Yy]$ ]]; then
      docker compose -f "${COMPOSE_FILE}" restart
      ok "Stack restarted."
    else
      info "Skipped restart."
    fi
  else
    info "No running Docker Compose stack detected."
  fi
}

main_menu() {
  while true; do
    echo ""
    echo -e "${CYAN}=== Reconfiguration Menu ===${NC}"
    echo "  1) Database"
    echo "  2) DMS Connector"
    echo "  3) LLM"
    echo "  4) Vector DB"
    echo "  5) Legacy / Other"
    echo "  6) Finish"
    local choice
    read -rp "$(echo -e "${CYAN}?${NC} Choose a section [1-6]: ")" choice
    case "$choice" in
      1) configure_database ;;
      2) configure_connector ;;
      3) configure_llm ;;
      4) configure_vector_db ;;
      5) configure_legacy ;;
      6) break ;;
      *) warn "Invalid choice." ;;
    esac
  done
}

main() {
  echo -e "${CYAN}========================================${NC}"
  echo -e "${CYAN}  Paperless AI / DMS-RAG Reconfigure${NC}"
  echo -e "${CYAN}========================================${NC}"
  echo ""
  info "Repository root: ${REPO_ROOT}"

  load_env
  backup_env
  main_menu
  write_env
  offer_restart
}

main "$@"
