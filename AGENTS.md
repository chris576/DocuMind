# AGENTS.md — paperless-ai / DMS-RAG

Konventionen für KI-Agenten (Copilot, Claude Code, Codex, Hermes u. a.) bei der Arbeit an diesem Projekt.

## Wissensdatenbank (Knowledge Base)

Wichtige Projektdokumentation und Key-Aspekte werden **zusätzlich** in der Obsidian-Wissensdatenbank abgelegt:

- **Pfad:** `/mnt/c/Users/chris/Documents/Obsidian/DMS-RAG/AI-Knowledge/`
- **Natives Memory:** Kurzfristige Build-/Toolchain-Fakten liegen unter `/memories/repo/`.

## Trennung zwischen Nutzer und KI

- Der Bereich `AI-Knowledge/` ist **ausschließlich KI-verwaltet** (Frontmatter `created_by: "GitHub Copilot"`).
- Nutzer-Notizen außerhalb von `AI-Knowledge/` werden **niemals** verändert.

## Was wo abgelegt wird

| Thema | Ablageort im Vault |
|---|---|
| Architektur-Übersichten | `AI-Knowledge/architecture/` |
| Architektur-Entscheidungen (ADR) | `AI-Knowledge/decisions/YYYY-MM-DD-titel.md` |
| Connector-Doku (DMS/ERP) | `AI-Knowledge/connectors/` |
| Pipeline-Doku (Ingestion/Retrieval/Generation) | `AI-Knowledge/pipelines/` |
| Projektüberblick | `AI-Knowledge/project-overview.md` |

## Konventionen

- Format: Markdown, Obsidian-Wikilinks `[[...]]` wo sinnvoll.
- Jede KI-Notiz beginnt mit `created_by: "GitHub Copilot"` im YAML-Frontmatter.
- Vor dem Ablegen: vorhandenen Vault-Inhalt prüfen, um Duplikate zu vermeiden.
