# @chrid235/documind-mcp-server

Lokaler MCP-Server (stdio) für DocuMind. Er übersetzt MCP-Tools in REST-Aufrufe
an den DocuMind-Gateway (das Backend).

## Installation (npm)

```bash
# global installieren
npm install -g @chrid235/documind-mcp-server

# oder direkt per npx, ohne Installation
npx -y @chrid235/documind-mcp-server
```

## Konfiguration

| Env | Default | Beschreibung |
|---|---|---|
| `GATEWAY_URL` | `http://localhost:3001` | Basis-URL des Gateways |
| `GATEWAY_API_TOKEN` | – | Optionales Bearer-Token (wird als `Authorization` Header gesendet) |

## Einbindung in Agenten (stdio)

```json
{
  "mcpServers": {
    "documind": {
      "command": "npx",
      "args": ["-y", "@chrid235/documind-mcp-server"],
      "env": {
        "GATEWAY_URL": "http://localhost:3001",
        "GATEWAY_API_TOKEN": "dein-token"
      }
    }
  }
}
```

## Lokal bauen

```bash
pnpm --filter @chrid235/documind-mcp-server build
node apps/mcp-server/dist/server.js
```

## Tools

- `documind.ingest` — Hintergrund-Indexierung starten (liefert `jobId`)
- `documind.ingest_status` — Job-Status pollen
- `documind.search` — semantische/hybride Suche
- `documind.get_context` — Retrieval-Kontext für eine Frage
- `documind.ask` — Frage über das Archiv beantworten (voller Text)
- `documind.pipeline_status` — Status aller Pipelines/Namespaces

Alle Tools akzeptieren optional `namespace` (Dokumentquelle, Default `paperless`).
