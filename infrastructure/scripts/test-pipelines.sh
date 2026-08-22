#!/usr/bin/env bash
#
# test-pipelines.sh — Qualitäts-Gates für die drei Python-Pipelines
# (ingestion, retrieval, generation) des DMS-RAG Monorepos.
#
# Führt je Pipeline folgende Gates aus:
#   lint      ruff    (Clean-Code-Regelsatz aus pyproject.toml)
#   typecheck mypy    (strenge Typ-Prüfung der eigenen Apps)
#   security  bandit  (Sicherheits-Scan; liest pyproject.toml via -c)
#   test      pytest  (Unit-Tests inkl. Coverage-Gate >= 75 %)
#
# Usage:
#   test-pipelines.sh [lint|typecheck|security|test|coverage|all] [pipeline ...]
#
# Beispiele:
#   ./infrastructure/scripts/test-pipelines.sh all
#   ./infrastructure/scripts/test-pipelines.sh lint retrieval
#   ./infrastructure/scripts/test-pipelines.sh test ingestion generation
#
# Exit-Code != 0 bricht bei der ersten fehlgeschlagenen Stufe ab.
set -euo pipefail

# --- Lokalisierung -----------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"

PYTHON="${VENV_DIR}/bin/python"
RUFF="${VENV_DIR}/bin/ruff"
MYPY="${VENV_DIR}/bin/mypy"
BANDIT="${VENV_DIR}/bin/bandit"

PIPELINES=( "ingestion-pipeline" "retrieval-pipeline" "generation-pipeline" )
ALL_STEPS=( "lint" "typecheck" "security" "test" )

# --- Argumente ---------------------------------------------------------------
STEP="${1:-all}"
shift || true
SELECTED=("$@")

if [[ ${#SELECTED[@]} -gt 0 ]]; then
  PIPELINES=("${SELECTED[@]}")
fi

# --- Hilfsfunktionen ---------------------------------------------------------
fail() { echo "  ✗ $*" >&2; exit 1; }
ok()   { echo "  ✓ $*"; }

run_for_pipeline() {
  local pipeline="$1" step="$2" dir="${ROOT_DIR}/apps/${pipeline}"
  [[ -d "${dir}" ]] || fail "Pipeline-Verzeichnis fehlt: ${dir}"
  echo "── ${pipeline} ──"

  ( cd "${dir}" && case "${step}" in
    lint)
      "${RUFF}" check . || fail "ruff check (${pipeline})"
      "${RUFF}" format --check . || fail "ruff format --check (${pipeline})"
      ;;
    typecheck)
      "${MYPY}" main.py src || fail "mypy (${pipeline})"
      ;;
    security)
      "${BANDIT}" -c pyproject.toml -r main.py src -q || fail "bandit (${pipeline})"
      ;;
    test)
      "${PYTHON}" -m pytest -q || fail "pytest/cov (${pipeline})"
      ;;
  esac )
  ok "${step} ${pipeline}"
}

# --- Ausführung --------------------------------------------------------------
echo "=== DMS-RAG Python-Pipeline Quality Gates ==="
steps_to_run=()
if [[ "${STEP}" == "all" ]]; then
  steps_to_run=( "${ALL_STEPS[@]}" )
elif [[ " ${ALL_STEPS[*]} " =~ " ${STEP} " ]]; then
  steps_to_run=( "${STEP}" )
else
  fail "Unbekannte Stufe '${STEP}'. Erlaubt: ${ALL_STEPS[*]} | all"
fi

for step in "${steps_to_run[@]}"; do
  echo "── Stufe: ${step} ──"
  for pipeline in "${PIPELINES[@]}"; do
    run_for_pipeline "${pipeline}" "${step}"
  done
done

echo "=== Alle Qualitäts-Gates bestanden! ==="