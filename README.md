# WeBuild read-only knowledge gateway

Independent Python project. Source repositories are fetched through public HTTP GET,
read-only GraphQL queries, and Git fetch only. No source-write API, workflow, issue,
PR, comment, or source-side metadata operation exists in this project.

The generated GitHub Pages wiki provides browse/search/filter/download operations.
FastAPI REST and official MCP SDK Streamable HTTP serve the same `Store` methods.
PostgreSQL full-text search and pgvector cosine search use real revision-pinned
Sentence Transformers embeddings on CPU. Model weights are not mocked. No chatbot
or visitor editing, posting, submission, or collaboration feature is provided.

See [operator runbook](docs/RUNBOOK.md), [requirements/evidence mapping](docs/REQUIREMENTS.md),
and [validation report](docs/VALIDATION.md). Evidence is under `evidence/`.

## Local deployment

1. Copy `.env.example` to an untracked `.env`, replace passwords/origins/URLs.
2. Start the PostgreSQL service: `docker compose up -d db`.
3. Create `gateway_reader` and `gateway_ingest` login roles and apply
   `sql/schema.sql` with a database administrator. `scripts/bootstrap.py` is a
   convenience initializer using `ADMIN_DATABASE_URL`, `READER_DATABASE_PASSWORD` and `INGEST_DATABASE_PASSWORD`.
   Reader and writer passwords must differ. Never give retrieval
   the administrator or ingestion URL.
4. `python -m venv .venv`; install the project: `.venv/bin/pip install '.[test]'`.
5. With ingestion credentials and `PUBLIC_API_URL` set:
   `python -m gateway.cli run --initial`. Full runs omit `--initial`.
6. Start retrieval: `uvicorn gateway.api:factory --factory --host 0.0.0.0 --port 8000`.
   Its environment contains only `RETRIEVAL_DATABASE_URL`, model revision, host,
   and approved origins. Put Caddy or another HTTPS proxy in front of it.
7. Host `site/` on GitHub Pages; configure the new repository's Actions variables
   and protected environment as described in the runbook.

Anonymous GitHub reads work for small runs; the historical four-repository crawl
needs a read-only token to avoid the 60-request anonymous API quota. Partial or
failed captures are explicitly reported and never promoted by the production CLI.
Live file-only integration evidence is deliberately separate from a release run.

## Interfaces

- REST: `GET /v1/search`, `/v1/sources/{id}`, `/v1/relations`,
  `/v1/decisions/{id}/history`, `/v1/changes`, `/v1/manifest`.
- Remote MCP: `/mcp`; `search`, `get_source`, `get_related_sources`,
  `get_related_specs`, `get_decision_history`, `get_changes`.
- Exports: source JSONL, relationship JSON, Markdown topic pack, `llms.txt`.
- Health: `/health`, publication age >36 hours yields HTTP 503.

All retrieval responses identify their snapshot. Search has bounded query length,
page size and offset; REST and MCP share filters, model compatibility checks,
citations, statuses, versions, and restrictions on source content. Lifecycle state
never implies accepted status. Unknown status stays unknown. Link-only external
metadata never silently upgrades a cited baseline to the latest upstream version.

## Tests

Apply the schema to a disposable PostgreSQL/pgvector database, set the three DB
URLs and pinned `EMBEDDING_REVISION`, then run `python -m pytest -q`.
Tests use real embeddings and database queries; HTTP transport tests use an actual
listening service and official MCP client. Only pagination/error-path transport
fixtures use controlled responses. `scripts/live_validation.py` separately indexes
live public file evidence, measures source-derived and held-out formulations,
checks HTTP REST/MCP parity, and optionally runs a Playwright browser check.

## Publication status

This source is independently runnable. It has not been published to a GitHub owner
or deployed to production. Historical capture completeness and production HTTPS,
Pages coordination, notification routing, backups and performance are distinct
release checks; see the validation report. Private-source serving is intentionally
blocked until authenticated access control across every export/cache is implemented.
