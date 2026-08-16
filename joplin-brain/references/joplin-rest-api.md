# Joplin REST API — Agent Integration Cheat Sheet

Verified against a live Joplin setup + official docs, August 2026. The REST API is the **supported** surface for agents/scripts to read/write Joplin — direct SQLite writes are not a public contract (schema changes between versions).

## Enable

```bash
joplin server start    # local web-clipper API server (terminal app 3.6.2+)
```
- Config in `settings.json`: `api.token`, `api.port` (default 41184). Token passed as query param: `?token=...`
- Ping check: `GET /ping` → `JoplinClipperServer`. No rate limits on loopback.
- ⚠️ **Profile trap (verified 2026-08-08):** the server serves the ACTIVE profile's DB. Under a redirected `$HOME` (common in agent sandboxes), `~/.config/joplin/database.sqlite` may be an **EMPTY profile DB** (0 notes). The real corpus lives at the real user home. Always verify with a `GET /notes` count before wiring anything.

## Endpoints

| Resource | Endpoints |
|---|---|
| Notes | `GET/POST /notes`, `GET/PUT/DELETE /notes/:id`, `GET /notes/:id/tags`, `GET /notes/:id/resources` |
| Folders | `GET/POST /folders`, `GET/PUT/DELETE /folders/:id`, `GET /folders/:id/notes` |
| Tags | `GET/POST /tags`, `GET/PUT/DELETE /tags/:id`, `POST /tags/:id/notes`, `DELETE /tags/:id/notes/:note_id` |
| Resources | `GET/POST /resources`, `GET/PUT/DELETE /resources/:id`, `GET /resources/:id/file`, `GET /resources/:id/notes` |
| Search | `GET /search?query=...` (full-text; `type=folder|tag`, `field` param) |
| Revisions/Events | `GET /revisions`, `GET /events` (delta-sync friendly) |

Pagination: `limit` (max 100), `page`, `order_by`, `order_dir`; responses `{items: [], has_more}`. Slim payloads with `fields=id,title`. Timestamps are Unix ms. Trash/conflicts excluded by default (`include_deleted=1&include_conflicts=1` to override). PUT merges only provided fields.

> ⚠️ **Token hygiene:** the curl examples below put the token on the shell command line (`?token=$TOKEN`), where it is visible in `ps`/`/proc/<pid>/cmdline` and lands in shell history. For agent use, prefer the bundled client (`python3 scripts/joplin_client.py ping`), which reads the token in-process. The curl forms are fine for one-off interactive debugging on a single-user machine.

```bash
TOKEN=<api.token>
curl "http://localhost:41184/notes?token=$TOKEN&fields=id,title&limit=100"
curl "http://localhost:41184/search?token=$TOKEN&query=medium&fields=id,title"
curl -X POST "http://localhost:41184/notes?token=$TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"Test","body":"Hello **world**","parent_id":"<folder-id>"}'
curl -X PUT "http://localhost:41184/notes/$ID?token=$TOKEN" -d '{"body":"new body"}'
```

## Local DB facts (fallback, read-only)

- `notes_fts` / `items_fts` are **FTS4** (not FTS5) — keyword search only, no BM25/trigram. `SELECT * FROM notes_fts WHERE notes_fts MATCH 'medium'`.
- `joplin sync` running in parallel with SQL queries can cause database-locked errors; avoid API calls during sync windows.
- E2EE must stay OFF for agent/API access (encrypted bodies break both API and raw DB retrieval).

## Joplin 3.7.x — semantic search (the unlock)

3.7.x (prerelease as of 2026-07-28, latest tagged v3.7.10) ships native AI: local ONNX embedding indexer, `joplin.ai.search({query, relevance: strict|normal|loose, scope})`, `joplin.ai.getEmbeddings()` / `getIndexStatus()`, a built-in **MCP server**, and new REST item type `note_embedding` (17). Offline-capable. **Test on a throwaway profile first** — it's prerelease and touches the DB.

## Community tooling (verified star counts Aug 2026)

- **Jarvis** (`alondmnt/joplin-plugin-jarvis`, 354★, active) — the canonical in-app AI assistant (chat, summarize, transform; OpenAI/Claude/Gemini/Ollama/local).
- **NoteLLM** (`HorseSword/joplin-plugin-notellm`, 46★) — OSS LLM chat + note actions.
- Official AI plugins: `joplin/plugin-note-categorization` (semantic clustering), `joplin/plugin-ai-summarisation`, `joplin/plugin-email` (IMAP→notes, 40★).
- RAG bridges: `luisriverag/joplin_weaviate_ollama`, `robbiemu/vault-mcp` (MCP across Obsidian/Joplin/markdown), `madhan112007/joplin-rag---poc`.
- ⚠️ There is NO "Copilot" or "Text Generator" plugin for Joplin (those are Obsidian-only); `joplin-ai` standalone does not exist.
