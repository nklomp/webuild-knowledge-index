# Validation boundary after migration

The stopped Work executor reported 84 passing tests, original retrieval 6/6, and additional held-out retrieval 2/3 on 15 October 2026. Its final validation was interrupted. Those results do not verify this reconstructed checkout.

Fresh migration checks: Python syntax compilation of `gateway`, `tests`, and `scripts` passed; `uv lock` resolved the restored declared dependencies. The full runtime, database, embeddings, HTTP MCP, browser, and live-corpus checks have not yet been repeated in native Codex Cloud. No production deployment is claimed.

Read `MIGRATION.md` for recovery exceptions. In particular, source-evidence fixtures and live corpus/evaluation artifacts were generated in the old workspace and are not present here. Restore them from pinned evidence and revalidate rather than inventing prior measurements. Run the existing complete test selection against real PostgreSQL/pgvector before publishing new release claims.
