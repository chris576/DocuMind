# @documind/mcp-server

Lokaler MCP-Server (stdio) für DocuMind. Er übersetzt MCP-Tools in REST-Aufrufe
an den DocuMind-Gateway (das bestehende `@documind/backend`).

## Konfiguration

| Env | Default | Beschreibung |
|---|---|---|
| `GATEWAY_URL` | `http://localhost:3001` | Basis-URL des Gateways |
| `GATEWAY_API_TOKEN` | – | Optionales Bearer-Token (wird als `Authorization` Header gesendet) |

## Build & Start

```bash
pnpm --filter @documind/mcp-server build
node apps/mcp-server/dist/server.js
```

## Einbindung in Agenten (stdio)

```json
{
  "mcpServers": {
    "documind": {
      "command": "node",
      "args": ["/absoluter/pfad/zu/apps/mcp-server/dist/server.js"],
      "env": {
        "GATEWAY_URL": "http://localhost:3001",
        "GATEWAY_API_TOKEN": "dein-token"
      }
    }
  }
}
```

## Tools

- `documind.ingest` — Hintergrund-Indexierung starten (liefert `jobId`)
- `documind.ingest_status` — Job-Status pollen
- `documind.search` — semantische/hybride Suche
- `documind.get_context` — Retrieval-Kontext für eine Frage
- `documind.ask` — Frage über das Archiv beantworten (voller Text)
- `documind.pipeline_status` — Status aller Pipelines/Namespaces

Alle Tools akzeptieren optional `namespace` (Dokumentquelle, Default `paperless`).
