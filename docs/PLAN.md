# WeBuild read-only knowledge gateway plan

Date: 7 October 2026

Status (15 October 2026): Recovered implementation under native Cloud validation. Real model download remains blocked; no production deployment is authorized or claimed. See VALIDATION.md. The checklists below remain acceptance gates.

## Goal and agreed scope

Provide a public, searchable wiki that helps people and LLMs navigate existing WeBuild information and the external specifications it references. Update the index daily. Start with public sources and provide a path to private sources later.

The first public release includes live hybrid keyword/vector search, a REST retrieval API, and a remote read-only MCP server. GitHub Pages hosts the wiki frontend; its static hosting capabilities do not limit the retrieval capabilities delivered by the separate backend. Live search queries the latest published index; source ingestion remains daily, with per-source freshness shown explicitly.

Real participant questions are not available at this stage and are not a dependency for implementation or release. Initial evaluation uses explicitly labeled source-derived questions and controlled regression fixtures. Participant questions can supplement evaluation later through existing consortium channels; the gateway will not add question-submission or discussion features.

The wiki and search are a read-only information gateway. They will not become an interaction channel between consortium members, partners, beneficiaries, or other visitors. Discussion, contributions, corrections, decisions, and approvals remain in the existing source repositories and consortium channels.

Visitors may browse generated pages, search, filter results, inspect decision history and source relationships, download permitted exports, and follow links to original sources. The gateway has no comments, messages, discussion boards, collaborative editing, submission forms, shared conversations, or partner coordination workflows. A chatbot is outside the initial scope.

Automation may update the derived index and published website. This does not give visitors write access, and the pipeline must not modify the source repositories or post comments, issues, or PRs.

Existing repositories are read-only inputs. This project must not add documents, metadata files, generated summaries, indexes, workflows, configuration, navigation links, or agent instructions to them. It must work with their existing structure and metadata without requiring contributor changes or new source-side conventions. Store all project-owned artifacts in a new, separate repository and associated backend storage. Keep this planning artifact outside existing repositories as well.

## Research basis

The organization inventory observed on 7 October contains 12 public repositories and 703 files across their default branches, including source code and binary assets. Representative documents and selected PR conversations, inline reviews, and issues were inspected. The complete historical discussion corpus has not yet been extracted or evaluated.

The initial corpus covers:

- `wp4-architecture`: ADRs, blueprint, conformance specifications, drafts, issues, and PRs.
- `wp4-trust-group`: trust framework, onboarding, certificate profiles, trust evaluation, APIs, ETSI reference material, and discussions.
- `wp4-semantics-group`: EBWV, semantic intakes, ontology, application profiles, and discussions.
- `webuild-attestation-rulebooks-catalog`: rulebooks, schemas, samples, and discussions.

Subsequent coverage includes `wp4-qtsp-group`, `wp4-wallets-group`, `wp4-pid-ebwoid-group`, `wp4-interop-test-bed`, `SC5`, `BU3`, `webuild-github-policies`, and `.github`. Discover new public repositories during ingestion and admit them through maintained source configuration. Index GitHub Discussions, wiki content, releases, and attachments where present, accessible, relevant, and permitted; mark each source type's coverage explicitly.

Evidence that drives the design:

- ADRs express decisions and rationale; conformance specifications express implementation requirements. Preserve both roles: https://github.com/webuild-consortium/wp4-architecture/blob/main/blueprint/07-governance-and-adr.md
- An overview can lag behind files. The retrieved ADR overview did not list the AuthZEN ADR merged on 6 October. Discover actual content, not only manually maintained navigation: https://github.com/webuild-consortium/wp4-architecture/pull/336
- Accepted decisions may contain unresolved limitations. The AuthZEN ADR leaves historical key-binding queries open: https://github.com/webuild-consortium/wp4-architecture/blob/main/adr/eaa-key-binding-authzen.md
- Conflicting evidence needs attribution. Trust-group issue 104 reports ETSI schema/PDF differences; index the report without automatically treating it as an official correction: https://github.com/webuild-consortium/wp4-trust-group/issues/104
- Reuse the existing EBWV identifiers and SKOS/OWL/JSON-LD assets: https://github.com/webuild-consortium/wp4-semantics-group/blob/main/vocab/README.md

## Reuse the VDX-infra wiki pattern

Adapt the pattern documented in `docs/module-index/README.md` and implemented in `tooling/module-docs/`. Reuse its structured inventory, hierarchy, generated detail and overview pages, relationship data, human navigation, machine exports, source evidence, and drift verification approach.

Replace Gradle-specific extraction with WeBuild document, GitHub discussion, vocabulary, schema, and specification adapters. Replace product/domain/module grouping with working-group/topic/source grouping.

The current VDX query CLI and explorer use term matching. Retain exact identifier matching and add semantic retrieval for natural-language questions. Existing module verification checks establish useful engineering patterns, but new checks must validate citations, decision status, external versions, and discussion attribution. Module-specific checks do not prove semantic correctness for this corpus.

Keep the WeBuild implementation in a new dedicated repository, proposed name `webuild-knowledge-index`. Store ingestion adapters, source configuration, vocabulary mappings, classification corrections, evaluation fixtures, generated wiki content, index manifests, exports, and deployment workflows there or in its associated artifact/database storage. This planning document is stored outside existing repositories; deployment of the gateway is an independent project. VDX-infra provides reference patterns only and requires no changes for the WeBuild gateway.

## Architecture

Approved sources -> ingestion -> immutable source revisions -> parsing and classification -> versioned index -> generated wiki, search, and exports.

The same index supplies the website, REST retrieval API, and MCP retrieval tools. These are consumption interfaces to the same evidence. They must not maintain separate versions of decisions or conclusions.

Use a Python ingestion worker, versioned JSON/Markdown artifacts, a generated wiki frontend hosted on GitHub Pages, and a separately hosted HTTPS retrieval service backed by PostgreSQL full-text search and pgvector. Deliver hybrid search, REST retrieval, and remote read-only MCP in the first public release. Store relationships in PostgreSQL initially; reconsider a separate graph database only after measured query requirements justify it.

The wiki's search interface calls the HTTPS retrieval API. The MCP server uses the same search and source-retrieval implementation, so LLM clients and website visitors receive the same status, version, provenance, and filtering behavior. Query embeddings are computed by the backend with the model/version compatible with the indexed embeddings. Model API keys and database credentials remain outside the browser. Semantic classification and index updates run during ingestion; user queries do not modify source or published knowledge.

Host the retrieval API and MCP endpoint together in one container service initially, with a persistent PostgreSQL database supporting pgvector. Select the hosting provider using consortium infrastructure preferences and measured resource requirements during execution planning. GitHub Actions performs daily ingestion and coordinates backend index promotion with GitHub Pages publication. The browser requires no direct database access. Configure browser cross-origin access for the approved website origins and apply query limits and timeouts at the retrieval service.

Search responses, wiki pages, exports, and the manifest expose their snapshot IDs. Keep the previous complete snapshot available during promotion so the site can retrieve the revision it references. Show newly published live-search results with their source revisions and publication time; never silently combine incompatible snapshots. Service failure must be visible in the search UI; generated wiki pages and source links remain available. A static keyword fallback may supplement availability if clearly labeled, but cannot satisfy the first-release acceptance gate for live/vector search and MCP.

Generated wiki pages cover working groups, topics, decisions, conformance specifications, rulebooks, terminology, and source-backed question-oriented reading paths. Cross-cutting topic pages connect information across repositories. Each page displays citations, status, source revisions, unresolved questions, and freshness. Visitors follow an original-source link to use that source's existing contribution or discussion mechanism. Do not describe derived questions as frequently asked or representative of participant demand without supporting evidence.

## Source records and semantic relationships

Use stable identities distinct from revisions. Track repository identity and path aliases through renames. Index meaningful document sections, schema entities, and discussion contributions; preserve their surrounding context.

Required metadata:

- Stable ID, source kind, repository/working group, revision, original URL, and precise locator.
- GitHub lifecycle state and document decision status as separate fields.
- Topics, actors, credential types, EBWV identifiers, terminology aliases, and document role.
- Referenced specification identity, exact edition/version, clause or requirement identifier, and official URL.
- Scope and limitations, including pilot/production and live/offline/archival cases when evidenced.
- Source update time, retrieval time, content hash, visibility, reuse permissions, and extraction/annotation provenance.

Extract explicit links, identifiers, statuses, and source relationships deterministically where possible. Use constrained LLM annotation for topic suggestions, concise summaries, questions answered, and candidate relationships. Retain evidence spans for substantive annotations and track the annotation model/prompt version.

Relationships include `references`, `changes`, `implements`, `supersedes`, and `raises-concern-about`. Explicit references can be indexed automatically. Semantic similarity alone cannot establish compliance, supersession, consensus, or contradiction. Inferred stronger relationships remain candidates until confirmed by existing source evidence or a documented maintainer review process outside the gateway. Store project-owned review annotations and overrides in the new index repository with evidence and provenance; these are derived index metadata, not changes to consortium decisions. Source documents do not need new metadata or edits to be indexed.

Default search should favor current relevant evidence and expose proposals, historical decisions, and unresolved questions as distinct categories. A closed issue is not automatically answered; a merged document may still describe a draft. Missing status evidence yields an explicit unknown state. A merged decision's limitations remain attached to the decision.

## External specification catalogue

Index the official EUDI ARF repository and tagged releases, EC standards and technical specifications, EUR-Lex references, ETSI publications and associated machine-readable artifacts, and referenced OpenID/IETF specifications.

Useful starting points:

- https://github.com/eu-digital-identity-wallet/eudi-doc-architecture-and-reference-framework
- https://github.com/eu-digital-identity-wallet/eudi-doc-standards-and-technical-specifications
- https://www.etsi.org/
- https://eur-lex.europa.eu/

Evaluate the open-source EUDI Trust & Conformance Atlas as a seed catalogue and mapping source: https://github.com/ForkbombEu/eudi-conformance-atlas. Verify references against official sources; its catalogue is navigation evidence rather than an authoritative legal interpretation.

Keep the version cited by WeBuild separate from the newer upstream version. Changes generate an impact report and candidate links; they do not automatically change the consortium baseline. Distinguish legislative proposals, adopted acts, amendments, technical specifications, drafts, and consultation material.

Preserve external-source attribution and reuse restrictions. Publish full text only where permitted. Otherwise publish permitted metadata, annotations/excerpts, and links. Link-only sources remain searchable by their indexed metadata, with coverage limitations disclosed.

## Read-only interfaces

Website operations: browse, search, filter, inspect sources and relationships, view changes, and download permitted data. Search queries do not create shared conversations or public content.

Proposed REST operations:

- `GET /v1/search`: query, scope, status, version, and pagination filters.
- `GET /v1/sources/{id}`: source metadata and permitted content.
- `GET /v1/relations`: evidence-backed relationships for a source or topic.
- `GET /v1/decisions/{id}/history`: lifecycle and revision evidence.
- `GET /v1/changes`: changes between published snapshots.
- `GET /v1/manifest`: publication time, source coverage, revisions, and schema version.

Proposed MCP tools: `search`, `get_source`, `get_related_sources`, `get_related_specs`, `get_decision_history`, and `get_changes`. All tools perform retrieval only. Read-only annotations document intent; permissions and implementation enforce it. Retrieval processes have no source-write credentials or source mutation operations. Use a database role restricted to reading the published index; ingestion uses a separate role that can update derived data. Public queries remain anonymous initially, with bounded resource usage. Private-source access introduces authenticated retrieval in the later extension.

Publish Markdown topic packs, JSONL source records, relationship exports, and a compact `llms.txt` entry point. Clients without MCP can use REST or exports. Embeddings are derived artifacts with explicit model/version metadata, not the portable source of truth.

Any generated search synopsis must distinguish current decisions, implementation requirements, rationale, reported concerns, and unresolved questions, with source citations and snapshot date. It must abstain from asserting consensus or requirements that its sources do not establish.

## Daily publication and reliability

Run scheduled ingestion daily, proposed at 03:17 UTC, with manual rerun available to operators through the existing CI system. Discover repositories, capture file revisions, and independently ingest updated issues, comments, PRs, reviews, and threads. Follow all pagination. Poll with an overlap window and deduplicate by stable identity/revision.

Use hashes to reprocess changed items and their affected summaries. Preserve source revisions and source-specific checkpoints. Reconcile renames, deletions, visibility changes, and unavailable sources. Run a weekly full reconciliation; repeat initial discovery on every daily run.

Validate citations, classification output, status evidence, version references, and public visibility before promotion. Publish a consistent snapshot atomically, retaining the last successful snapshot for recovery. On partial failures, identify failed sources and their last successful capture times; do not label retained data current. Visibility changes and deletions must propagate to searchable content and exports.

Display the last successful publication time and per-source freshness. Treat a publication age over 36 hours as a freshness failure. GitHub Actions schedules can be delayed or dropped, so use an independent health check to notify designated operators through an existing authorized operational channel. The website does not become a notification or coordination channel.

Treat public source text and LLM annotations as untrusted data: never execute instructions embedded in documents or comments; render content safely; validate output structure; restrict external fetching to approved sources. Isolate untrusted PR processing from ingestion and publishing credentials.

## Delivery stages and acceptance

### Stage 1: Read-only wiki, live hybrid search, and MCP

- [ ] Define source configuration, identities, revisions, permissions, and classification schema.
- [ ] Establish the new index repository and external storage as the only write destinations. Verify ingestion uses public reads or read-only source credentials, and that neither ingestion nor publication requires adding any files or workflows to existing repositories.
- [ ] Extract the four initial repositories, including historical issues, PRs, comments, and reviews.
- [ ] Align core topic aliases with EBWV and capture the external-specification identities, versions, and references explicitly present in the initial corpus.
- [ ] Generate working-group/topic/source pages, Markdown/JSON exports, and `llms.txt`, and publish the frontend on GitHub Pages.
- [ ] Deploy PostgreSQL full-text search and pgvector with separate ingestion and read-only retrieval roles.
- [ ] Implement live hybrid search, relationship/source retrieval, the REST API, and the remote read-only MCP server against the same published index.
- [ ] Connect the wiki search interface to the API and validate cross-origin access, source locators, status filters, model-compatible embeddings, snapshot IDs, timeouts, and service-failure presentation.
- [ ] Add daily publication, source freshness, deletion handling, citation checks, and recovery.
- [ ] Verify that visitors and retrieval interfaces cannot create or modify gateway or source content.
- [ ] Build a provisional evaluation set from indexed ADRs, specifications, rulebooks, and existing issue/PR discussions, with expected source locators, status, versions, limitations, and unanswerable cases verified against the evidence. Include natural-language paraphrases and controlled deletion/status/version regression fixtures.

Acceptance: all configured sources and pagination are accounted for; generated substantive claims have resolvable citations; status distinctions are visible; repeat ingestion is idempotent; published snapshots remain internally consistent; simulated ingestion failures expose stale-source status; the gateway supports browsing/search without interaction features. Exact identifiers and natural-language questions retrieve relevant sources through the website and an actual MCP client. REST and MCP preserve identical source/status/version semantics and expose retrieval operations only. Verify retrieval credentials cannot write to the index or source repositories. Live vector search and MCP must pass this gate before the first public release; a static-only site is not completion of Stage 1.

Use the provisional source-derived set for this gate. Require all deterministic citation/status/version regression cases to pass and no unsupported normative assertions in evaluated generated summaries. Record retrieval results and failures without claiming demonstrated usefulness for real participant questions. Evaluate on held-out sources or question formulations separate from any ranking/alias tuning set. Real participant questions are not a release prerequisite.

### Stage 2: Deeper specification navigation and reviewed relationships

- [ ] Extend EBWV mappings and topic aliases across the initial corpus using measured search gaps.
- [ ] Expand the external-specification catalogue with clause/requirement locators, upstream versions, and version-change impact views.
- [ ] Evaluate inferred relationship candidates against existing source evidence or maintainer review outside the gateway; record derived annotations and overrides in the new index repository without changing existing repositories.

Acceptance: cited and newer specification versions remain separate; draft and historical material cannot silently become current requirements; inferred stronger relationships are labeled as candidates until evidenced or reviewed; specification impact views trace to exact clauses and source revisions.

### Stage 3: Broader coverage and measured answer quality

- [ ] Add remaining public repositories and supported discussion/wiki/release/attachment sources.
- [ ] Publish source-backed topic/question pages and daily change/impact views.
- [ ] Expand the provisional source-derived evaluation set as coverage grows. Add real participant questions when they become available through existing channels, without making their availability a completion gate.

Acceptance: measure retrieval recall, citation correctness, status/version accuracy, unresolved-question recognition, unsupported conclusions, and freshness against the expanded provisional set. Include the AuthZEN archival limitation, a merged ADR omitted from an overview, reported ETSI schema/PDF discrepancies, closed-but-unanswered issues, terminology aliases, and withdrawn/private/deleted sources. Require all deterministic citation/status/version regression cases to pass and no unsupported normative assertions in evaluated generated summaries for this release. Report source-derived and real-question results separately when both exist. Use evaluation results to set semantic retrieval thresholds rather than inventing an unmeasured accuracy claim; synthetic/source-derived results do not establish real participant usefulness.

## Private-source extension

Record visibility from the first release. Before enabling private sources, implement identity-based access checks across retrieval, relationships, summaries, caches, downloads, and exports. Use a separate public publication boundary so private content, titles, links, counts, and derived annotations cannot leak into the public wiki. Keep the private gateway read-only as well.

## Planning boundary

This plan incorporates the public-first, generated-wiki, model-independent, daily-update, and read-only requirements, with live hybrid/vector search and remote MCP included in the first public release. GitHub Pages serves the frontend; a separate backend provides retrieval. It defines architecture and independently assessable delivery stages. Exact implementation files, dependency versions, infrastructure sizing, and operational cost will be established in an execution plan for the dedicated repository after initial full-corpus measurement. No source repositories, deployments, scheduled jobs, or external discussions have been changed by this plan revision.
