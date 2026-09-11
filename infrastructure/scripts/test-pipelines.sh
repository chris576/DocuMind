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
#   coverage  pytest  (Coverage-Report; identisch zum test-Gate)
#
# Abgedeckt werden die drei Pipeline-Apps (apps/*-pipeline) mit allen Gates sowie
# die vier Python-Packages (packages/python-*) mit test/coverage.
#
# Usage:
#   test-pipelines.sh [lint|typecheck|security|test|coverage|all] [ziel ...]
#
# Beispiele:
#   ./infrastructure/scripts/test-pipelines.sh all
#   ./infrastructure/scripts/test-pipelines.sh lint retrieval-pipeline
#   ./infrastructure/scripts/test-pipelines.sh test ingestion-pipeline python-llm
#
# Exit-Code != 0 bricht bei der ersten fehlgeschlagenen Stufe ab.
set -euo pipefail

# --- Lokalisierung -----------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"

PYTHON="${VENV_DIR}/bin/python"
RUFF="${VENV_DIR}/bin/ruff"

PIPELINES=( "ingestion-pipeline" "retrieval-pipeline" "generation-pipeline" )
PACKAGES=( "python-common" "python-dms" "python-llm" "python-vectordb" )
# `all` führt nur die vier echten Gates aus; `coverage` ist als einzelne Stufe
# erlaubt, aber redundant zu `test` (pytest erzwingt via addopts bereits --cov).
ALL_STEPS=( "lint" "typecheck" "security" "test" )
VALID_STEPS=( "lint" "typecheck" "security" "test" "coverage" )

# --- Argumente ---------------------------------------------------------------
STEP="${1:-all}"
shift || true
SELECTED=("$@")

if [[ ${#SELECTED[@]} -gt 0 ]]; then
  PIPELINES=()
  PACKAGES=()
  for target in "${SELECTED[@]}"; do
    if [[ -d "${ROOT_DIR}/apps/${target}" ]]; then
      PIPELINES+=( "${target}" )
    elif [[ -d "${ROOT_DIR}/packages/${target}" ]]; then
      PACKAGES+=( "${target}" )
    else
      fail "Unbekanntes Ziel '${target}' (weder apps/ noch packages/)"
    fi
  done
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
      "${PYTHON}" -m mypy main.py src || fail "mypy (${pipeline})"
      ;;
    security)
      "${PYTHON}" -m bandit -c pyproject.toml -r main.py src -q || fail "bandit (${pipeline})"
      ;;
    test|coverage)
      "${PYTHON}" -m pytest -q || fail "pytest/cov (${pipeline})"
      ;;
  esac )
  ok "${step} ${pipeline}"
}

run_for_package() {
  local package="$1" step="$2" dir="${ROOT_DIR}/packages/${package}"
  [[ -d "${dir}" ]] || fail "Package-Verzeichnis fehlt: ${dir}"
  echo "── ${package} ──"

  ( cd "${dir}" && case "${step}" in
    test|coverage)
      "${PYTHON}" -m pytest -q || fail "pytest/cov (${package})"
      ;;
  esac )
  ok "${step} ${package}"
}

# --- Ausführung --------------------------------------------------------------
echo "=== DMS-RAG Python-Pipeline Quality Gates ==="
steps_to_run=()
if [[ "${STEP}" == "all" ]]; then
  steps_to_run=( "${ALL_STEPS[@]}" )
elif [[ " ${VALID_STEPS[*]} " =~ " ${STEP} " ]]; then
  steps_to_run=( "${STEP}" )
else
  fail "Unbekannte Stufe '${STEP}'. Erlaubt: ${VALID_STEPS[*]} | all"
fi

for step in "${steps_to_run[@]}"; do
  echo "── Stufe: ${step} ──"
  for pipeline in "${PIPELINES[@]}"; do
    run_for_pipeline "${pipeline}" "${step}"
  done
  # Python-Packages: Unit-Tests/Coverage als Quality-Gate (kein eigenes main.py).
  case "${step}" in
    test|coverage)
      for package in "${PACKAGES[@]}"; do
        run_for_package "${package}" "${step}"
      done
      ;;
  esac
done

echo "=== Alle Qualitäts-Gates bestanden! ==="