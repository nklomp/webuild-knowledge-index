# Migration to native Codex Cloud

15 October 2026. Destination: private `nklomp/webuild-knowledge-index` repository.

## Stopped source session

ChatGPT Work conversation `6ac63582-3e68-83ed-8b5a-13aeec8e20bd` and its underlying executor `01a11641-11f2-77d6-bd93-8508f595f053` were stopped. Last checkpoint reported 84 passing tests, original expected-source retrieval 6/6, and additional held-out retrieval 2/3. The final validation was interrupted; newer changes remained uncommitted and unpackaged. These are historical reports, not newly verified results.

## Recovery method and boundaries

The downloadable ZIP was the previous 7 October delivery. Source was therefore reconstructed from the original and resumed executor's recorded file-writing commands, in chronological order. The recovery did not run recorded shell commands, package installations, network calls, project modules, test harnesses, or service commands. Only explicit file bodies and constrained text-edit operations were restored into this new project. A recovery log is retained with the migration evidence.

This is not a byte-for-byte archive of the stopped filesystem. Two over-redacted transcript expressions were repaired from their unambiguous source context: reading `SOURCE_READ_TOKEN` from `os.environ` in `gateway/discussions.py`, and escaping a JSON Pointer key in `gateway/extraction.py`. Fresh validation must check both paths.

Generated files that were not fully present in recorded commands have not been invented: the downloaded live corpus, previous/current database contents, model caches, historical dependency lock, source-evidence fixtures, calibration measurements, generated site, screenshots, and full test/validation artifacts must be recovered or regenerated. A new `uv.lock` was resolved from the restored `pyproject.toml`; it is not claimed to match the old environment's lock. Python source syntax compilation passed. Missing files must not be taken as successful fresh validation. Refer to `recovery/source-recovery-events.json` for the exact text-recovery exceptions and `recovery/recorded-source-writes.json` for the source-writing blocks. The legacy `/tmp` UID compatibility shim was not copied into this repository.

## Next native Codex Cloud work

1. Read the agreed plan and inspect the recovered code. Restore/regenerate dependency locks and configuration fixtures from pinned source evidence. Keep any historical extraction separate from the current baseline.
2. Reproduce the database/schema and complete test suite with real PostgreSQL/pgvector and genuine model embeddings. Verify read-only credentials and actual remote HTTP MCP initialization, discovery, tool calls, and REST parity.
3. Re-run original retrieval questions and held-out formulations independently. Preserve the remaining held-out failure until fixed and verified; do not change expected sources to improve the score.
4. Validate resumable/paginated ingestion, review threads/specification adapters, source removals/visibility, source-attributed notes, snapshot consistency, and generated wiki search.
5. Update validation/runbook/requirement mapping and deliver a fresh source archive. Report exact live corpus coverage and remaining credentials, hosting, Pages, and monitoring setup.

All existing repositories remain read-only. The new repository is the only source-write destination. Do not resume the Work task or create another Work conversation. No production deployment is part of this migration.

## Native continuation audit — 15 October 2026

The checkout began clean at imported commit `97898bb2a9f9bd3b7c22f972b9c5f483f220a5a6`.
Recovery exceptions were inspected as source data, never executed:

- Block 63: the missing historical requirements.lock is not recoverable. Its code
  changes (rename reconciliation) are present; current execution uses committed
  uv.lock. Do not invent the old dependency environment.
- Block 74: historical evaluation/coverage artifacts are absent. The generated-site
  ownership marker is implemented in site.py; fresh file evidence is separate.
- Blocks 92/94: generated historical validation prose and archive cannot be trusted
  as fresh evidence. Replaced by the current validation report and a new archive.
- Block 119: both descriptive source-evidence fixture copies were regenerated from
  authoritative public reads, pinned revisions, hashes and exact excerpts. The
  regenerator records its limitations; ETSI reports remain attributed concerns.
- The repaired SOURCE_READ_TOKEN lookup and JSON Pointer escaping both have fresh
  controlled checks. No UID/runtime compatibility shim was restored.

Original six evaluation questions and expected locators were recovered using
literal AST data extraction from block 34, without executing the recorded program.
`config/evaluation-original.json` is now the runner input; additional held-out
questions remain unchanged. Historical file pins beyond the recorded architecture
revision were unavailable, so fresh 12-repository pins are explicitly separate.

The audit found REST/MCP history/filter parity, old SDK test field names and
context-insensitive section-vector cache reuse defects. Fixes and integration
regressions are included, but model-dependent verification remains blocked. See
VALIDATION.md for actual commands, counts and remaining network gates.
