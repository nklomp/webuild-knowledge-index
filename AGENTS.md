# WeBuild knowledge gateway

This is the standalone implementation repository. All upstream WeBuild and VDX-infra repositories are read-only inputs. Do not add or modify files, documents, metadata, workflows, links, comments, issues, or PRs in them. Put this project's source, configuration, annotations, generated content, and deployment workflows here.

Read `docs/PLAN.md`, `docs/MIGRATION.md`, and `docs/RUNBOOK.md` before continuing. The migration recovered source from recorded file writes because the latest cloud workspace had uncommitted changes and its downloadable archive was stale. Recovery is not a verified byte-for-byte filesystem transfer. The migration report identifies missing generated artifacts and required fresh validation.

First release requires the generated wiki, actual hybrid/vector search with real compatible embeddings and PostgreSQL/pgvector, REST retrieval, and a remote read-only MCP server using the same retrieval logic. Do not defer these or substitute mocks/static-only retrieval. No chatbot, collaboration, comments, editing, messaging, or question submission features.

Run implementation and tests in native Codex Cloud. Do not start or resume ChatGPT Work. Keep credentials out of source, logs, and browser bundles. Never reuse source-read credentials to write upstream. User questions are not currently available and are not a prerequisite; use explicitly labeled source-derived and held-out evaluations.

Historical test counts are checkpoint reports, not fresh evidence. Validate restored source, generate reproducible dependencies, run the complete suite against real PostgreSQL/pgvector, exercise HTTP MCP with a client, and report incomplete live ingestion and deployment requirements honestly. No production deployment or paid resources have been authorized.
