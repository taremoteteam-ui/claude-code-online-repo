# THE BIBLE — AI Done Right · the single north-star reference

> **This file is the bible for development + vision.** If any other doc disagrees with it, this wins — fix or archive
> the other. `CLAUDE.md` / `AGENTS.md` are the agent operating rules; this is the *what + why + the laws*; **`docs/DESIGN-BIBLE.md`**
> is the design/UX counterpart (the look · components · color schemes · design decisions). Counts here
> are **computed by the named scripts** (never hand-typed — see the No-Magic-Values law); the prose states structure,
> the scripts state numbers. Last reconciled **2026-07-01**.

---

## 0. North-star vision

We are building a **systems layer for executable capability** — not point products. Teleon indexes/optimizes it,
Baltor governs its truth, OpenHubForAI structures it, AIDevObserver watches its usage. The binding goal is **DEPTH
BEFORE BREADTH**: every layer must serve the ONE vertical being proven to a paying customer. Scale is the ambition
(billions→trillions of components), but breadth without a revenue vertical is the failure mode.

**The five reconciled filters that govern what we build** (single source: `architecture/substrate_layers.json`):
1. **System filter** — does this improve compiler intelligence? If no, don't build it.
2. **Execution filter (descent)** — can intelligence be removed from this execution path? Descend toward that forever
   (make-it-work → make-it-cheap → deterministic-substitution).
3. **Component admission** — must LIFT over the bare model AND the lift must be STRUCTURAL/durable.
4. **Binding constraint** — depth before breadth (gated by `scripts/proposal_backlog.py`).
5. **Recursive improvement** — *nothing is static.* Every object can be challenged, every architecture can mutate,
   every distillation must rehydrate losslessly, every harness can evolve; every failure triggers diagnosis → a
   versioned improvement. The system improves forever — but **governed** by filters 1–4 and the lossless clause (a
   mutation is a new versioned layer, never a silent overwrite), so "improve forever" never becomes churn-forever.

---

## 1. The holding company: AI Done Right (`aidoneright.dev`)

Tagline **"AI, done right."** The parent brand over three product layers + the wedge. (Legacy name: *ContextIsEverything
Group* → AI Done Right, 2026-06-09.) Canonical portfolio architecture:
`docs/strategy/teleon-baltor-openhubforai-portfolio.md`.

---

## 2. The five brand pillars (single source: `architecture/surface_capability_spec.json`)

| Pillar | Domain | Role | Canonical surface | Governs |
|---|---|---|---|---|
| **AI Done Right** | aidoneright.dev | parent / holding brand | `web/context-is-everything` | — |
| **Teleon** | teleon.dev | purpose-driven, eval-gated, self-adaptive compute **runtime** | `web/teleon` | EFFICIENCY |
| **AIDevObserver** | aidevobserver.io | watches AI **usage** — post-session review + intra-session coaching (renamed from *Teleon Observer* 2026-06-25) | `web/aidevobserver` (engine: `src/teleon/observer`) | the WEDGE |
| **Baltor** | baltor.ai | managed, verified, provable **context**, powered by Teleon (a tenant) | `web/baltor` | TRUTH |
| **OpenHubForAI** | **OpenHubForAI.io** (ONE site) | the open **store** both products consume + the open CapabilityTask spec | `web/openhubforai` | the COMMONS |

**Naming law:** product = Teleon; staff dashboard = Teleon Control Tower; customer dashboard = Capability Assurance
Portal; object = **PurposeTask** (formal synonym **CapabilityTask**). Brand doc: `docs/strategy/teleon-naming-and-domain.md`.

---

## 3. Inter-surface connectivity (the laws that bind them)

- **Architectural dependency law** (enforced by `scripts/check_portfolio_dependency_law.py` over
  `architecture/portfolio_dependency_law.json`): **Baltor → Teleon → OpenHubForAI, NEVER the reverse.** Teleon must
  never import Baltor; OpenHubForAI imports neither. PurposeTask is **Teleon**, not a Baltor subsystem.
- **Component flow** (diagram: `dist/sites/aidoneright-design/diagrams/component-flow.html`): components are published
  to the OpenHubForAI store → the Teleon runtime SELECTS + PROVES them on real examples → Baltor SERVES them as verified
  context. Consumption flows up; dependency points down. AIDevObserver watches the usage.
- **Hosting:** Teleon + Baltor deploy same region/private network (low latency) but stay **separable** (separate
  service/data/identity/IaC + a versioned API + graceful local fallback).
- **One canonical renderer — the SHOWCASE** (`scripts/showcase/server.py`, owner-decided 2026-06-26/27,
  superseding the earlier one-template scaffolding): each of the **5 product surfaces** is the full built-out app
  in `web/<brand>/` served via `OH_PRODUCT=<brand> python3 -m scripts.showcase` over the shared kit, wired to the
  service plane through same-origin seams (`/api/identity/`, `/registry/`, `/api/teleon/`, `/api/observer/`, …).
  `scripts/surface_server.py` is **fallback only** — never a replacement for a built-out surface. Contract-locked:
  `scripts/check_surfaces_match_claude_design.py`. Full design reference: `docs/DESIGN-BIBLE.md`;
  wiring: `docs/INTEGRATION-BIBLE.md`.

---

## 4. The OpenHubForAI surfaces + the 103 registries (the named profiles)

**UI/UX CONSOLIDATION (owner 2026-06-25):** all hubs + registries live under **ONE site — `OpenHubForAI.io`**. Each
hub/registry is a **section**, NOT a separate domain — the per-hub `OpenXxxHub.io` domains are retired as live
surfaces (names stay as section labels). The BACKEND keeps per-hub/registry **data separation** (separate
datasets/databases) — only the UI/UX is unified. One storefront, many catalogs. (NOT `OpenAIHub.io` — OpenAI
trademark.) This also retires the old hub-prominence question: with one site, no hub is privileged.

**FLEXIBLE FACETS, not rigid stores (owner 2026-06-25):** the browsable unit is the **RECORD** (a tool, model, prompt,
skill, dataset…). The hubs + registries become **facets** of one faceted catalog — browse/filter by category (the old
hub names, as collections), registry type (the 103), kind (static/discovery/meta), layer, and status, plus full-text
search. A record may sit under **multiple** categories — the rigid one-record-one-hub `maps_to_hub` becomes a PRIMARY
category, not an exclusive home. Backed by the existing federated search (`src/teleon/registry/search.py`) + `RegistryPort`
(`src/teleon/registry/port.py`) — do NOT rebuild the search; build the browse UI over it.

**TWO LAYERS — don't conflate them** (this is the count people get wrong):

**Hub = storefront · registry = catalog behind it.** A hub is a *surface* — a branded open storefront with a domain
(`opentoolshub.io`), a one-liner, and a `substrate` (the registries + code that stock it); it is the *presentation*
layer. A registry is a *typed catalog* — one named index of a single object TYPE (`capability` holds the action
ontology; `model` holds models). Each registry entry carries a **`maps_to_hub`** field, so MANY registries roll up
into ONE hub. You **query registries** (via `RegistryPort`); you **browse hubs**. Registry **kinds** (single-sourced
in the ontology): **static** (curated + indexed), **discovery** (crawls the world for new components), **meta**
(pointer-only — indexes *where* external registries live; pointer ≠ copy, discovery ≠ trust). The `maps_to_hub` link
is the ONLY explicit hub↔registry binding, and nothing yet enforces it stays valid — a candidate contract.

**(a) The OpenHubForAI SURFACES** — the storefronts. ~35 are NAMED across the design + data (sources:
`architecture/hub_profiles.json` = 32 detailed profiles; `architecture/candidate_open_hubs.json` = 9 existing + 20
candidates). Named ≠ registered: the **currently-registered** roster lives in `web/*/kit/products.js`
`OPENHUB_REGISTRIES` (8 live + 13 preview as of 2026-07-01) and is computed — never hand-counted — by
`scripts/check_ai_done_right_surface_family.py`. By name: OpenAgentHub ·
OpenBenchmarkHub · OpenCompressionHub · OpenContextHub · OpenContradictionHub · OpenCurrentContextHub · OpenDatasetHub ·
OpenEndpointHub · OpenEnrichmentHub · OpenEnvHub · OpenEnvironmentHub · OpenEvalHub · OpenGeoHub · OpenGuardrailHub ·
OpenHardeningHub · OpenHubForAI · OpenLinkingHub · OpenMCPHub · OpenOptimizationHub · OpenPolicyHub · OpenProvenanceHub ·
OpenReceiptHub · OpenReconciliationHub · OpenRedactionHub · OpenReviewHub · OpenRoutingHub · OpenSandboxHub · OpenSkillsHub ·
OpenSourceHub · OpenSourcesHub · OpenStateHub · OpenTemplatesHub · OpenToolsHub · OpenToolToSkillHub · OpenVerificationHub.
The **Baltor method spine** (private bench): Reconciliation · Hardening · Enrichment · Optimization · Verification.

**(b) The 103 REGISTRIES** — the named data profiles UNDER the hubs (single source `architecture/registry_ontology.json`;
count computed by `check_registry_ontology` — **103** as of 2026-06-25; this is the "nearly 100 by name"). Each is a
**pointer + shape**; RECORDS come from POPULATION engines (`src/teleon/registry/populate.py`), never hand-building.
All behind one universal `RegistryPort` (`src/teleon/registry/port.py`), across 5 layers (Discovery + Capability /
Execution / Optimization / Verification). By name:

`capability` · `component` · `api_endpoint` · `model` · `provider` · `prompt` · `failure` · `transformation` ·
`constraint` · `optimization_pass` · `equivalence` · `dataset` · `human_heuristic` · `agent_behavior` ·
`cost_prediction` · `authentication` · `rate_limit` · `retry_strategy` · `schema` · `semantic_ontology` ·
`decision_policy` · `sandbox` · `security` · `trust` · `latency` · `cache` · `human_approval` · `compliance` ·
`execution_memory` · `environment` · `data_source` · `scheduler` · `observability` · `capability_relationship_graph` ·
`execution_pattern` · `validation` · `benchmark` · `regression` · `ai_testing` · `ui_testing` · `magic_number_audit` ·
`synthetic_data` · `adversarial` · `explainability` · `drift` · `agent_qa` · `code_audit` · `formal_verification` ·
`experiment` · `human_preference` · `determinism` · `failure_recovery` · `provenance` · `observed_reality` ·
`economic_opportunity` · `dataset_discovery` · `model_discovery` · `package_discovery` · `paper_discovery` ·
`api_discovery` · `benchmark_discovery` · `competitor_intel` · `provider_arbitrage` · `workflow_discovery` ·
`synthetic_capability_discovery` · `repo_discovery` · `infra_discovery` · `agent_marketplace_discovery` ·
`external_registry_index` · `agent_systems` · `external_systems` · `lookup_portals` · `feed_sources` ·
`human_expert_sources` · `community_sources` · `website_navigation` · `geospatial_sources` · `vulnerability_sources` ·
`reverse_engineering_tools` · `industry_classification` · `knowledge_taxonomies` · `information_acquisition` ·
`registry_dependency_graph` · `registry_enrichment` · `vector_database` · `mcp_servers` · `rights_action_portals` ·
`kaggle_population` · `certification_registry` · `record_population` · `rumors` · `scientific_sources` ·
`vertical_playbooks` · `swarm_systems` · `occupations` · `reasoning_strategies` · `standards` · `formulas` ·
`global_repository` · `agent_frameworks` · `package_dependency` · `product_similarity` · `behavioral_heuristics`.

---

## 5. Product vocabulary (canonical — use these, not the legacy terms)

- **Components / subcomponents** (not "artifact"/"manifest"). The seven **primitives**: Input · Knowledge Corpus ·
  If Statement · Action · Loop · Stop/End · Output (`docs/concepts/component-taxonomy-and-stages.md`).
- **Knowledge Corpus** (not "knowledge pack") · **If Statement** (not "rule pack") · **Action** (a persona/tool/
  processor/harness/rubric IS an Action). Version lives in metadata, never in names or IDs.

---

## 6. Assumptions

- **Data is synthetic or public metadata only** — never real PII, secrets, confidential data, or proprietary dumps.
  `_reference/` is never republished.
- **Insurance is out of scope** — target the claims-SHAPE in adjacent verticals; never expand insurance examples.
- The **descent** assumption: the cheapest bounded path that still passes is preferred; the LLM is the last rung.
- **Discovery ≠ trust** — a scraped/found tool is a CANDIDATE until governed + promoted.
- **serves_truth=false** on everything that isn't a governed Baltor truth output.

---

## 7. Guardrails (governance)

- **Promotion boundary** — candidate-table load-readiness is NOT active publication. A candidate stays tenant-invisible
  while it has open/high-risk review tickets, placeholder embeddings, unresolved source/signature questions, or
  volatile public facts without CDC/revocation. Tool: `scripts.db.daily_promotion_readiness_plan`.
- **Access policy** (`architecture/access_policy.json`, deny-by-default): public < authenticated < plan_gated <
  restricted < internal. A BYO key never grants a restricted tool; evasion/social/PII → restricted; private-bench → internal.
- **BYO keys** — demos + runtime accept the user's key via a TRANSIENT scope (`src/teleon/demos/byo_key_demo.py`,
  `src/teleon/runtime/key_holder.py`): used for one call, never stored, never logged, only a redacted status returned.
- **Freshness** — a fragile changing fact is bound to an authoritative source on a volatility-matched cadence; on a
  change the stale answer is HELD OUT (never served) until re-synced.

---

## 8. The laws (rules — every change obeys these)

1. **No Magic Values** — repo counts/totals are computed, never typed into prose (the "172 bug"). A value used twice
   gets one definition. Full: `docs/codex/no-magic-values.md`; audit: `scripts/audit_magic_numbers.py`.
2. **Lossless Distillation** — distillation is never replacement. Every distill/compress/promote creates a versioned
   derived layer while PRESERVING raw + intermediates + lineage + rejected/held-out. `docs/codex/lossless-distillation.md`.
3. **Move, never delete** — outdated docs/code move to `archive/legacy/<path>` (tracked, manifested), never deleted or
   untracked. Mover: `scripts/archive_legacy_docs.py`; index: `archive/legacy/README.md`.
4. **Change Verification (warrant before change)** — every change carries a warrant: clear user intent, ≥2 agreeing
   sources, or an established principle. Design/brand/strategy/pricing → NEVER a unilateral single-agent call.
   `docs/codex/change-verification-contract.md`.
5. **Northstar design** — no placeholders / dummy / orphaned / SIDE designs in any surface; the **five surfaces** are
   the full built-out `web/<brand>/` apps served by the SHOWCASE (`scripts/showcase/server.py`, `OH_PRODUCT=<brand>`)
   over the shared kit — NEVER a skinny replacement server (`scripts/surface_server.py` is fallback only).
   Reference: `docs/DESIGN-BIBLE.md`. Enforced: `scripts/check_surfaces_match_claude_design.py` +
   `scripts/check_northstar_design.py`.
6. **Capability-Gap admission** — build for the NEGATIVE space; a component must lift AND the lift must be structural
   (`scripts/eval/reason_codes.py`, `scripts/eval/durable_gap_harness.py`).
7. **Code-graph change audit** — before/after editing a `.py`, audit its strong neighbors:
   `PYTHONPATH=. python3 scripts/codegraph.py --audit <target>`.
8. **Thin flexible wrappers** — base/universal objects (`ObjectShell`, `RegistryObject`) are a STABLE envelope
   (id/type) with the **version in METADATA, never the name**, around a flexible `payload`/`component`. Domain records
   inherit thin-ness via `src/teleon/io/governed_record.mint_record` (envelope + payload; version in `schema_version`).
   Never put a version in an object/schema NAME — the portfolio-wide `.vN`-suffix elimination (2026-06-25) made
   272 lossless renames; `scripts/check_object_wrapper_hygiene.py` is the oracle (one legacy record-type tag,
   `primitive_record.v0` in `src/teleon/synthesis/pipeline_templates.py`, recorded 2026-07-01 — migrate its version
   into `schema_version` metadata, never silently rename stored-record identity).
9. **Recursive improvement (nothing is static)** — every object can be challenged, every architecture can mutate, every
   distillation must rehydrate losslessly, every harness can evolve; every failure → diagnosis → a versioned improvement,
   never a silent patch. The system improves forever, but **governed** by laws 1–8 (a mutation is a new versioned layer,
   not an overwrite). Engine = candidate views over existing assets: **OpenInterrogationHub** (challenge) /
   **OpenMutationHub** (rewrite) / **OpenRehydrationHub** (prove lossless) / **OpenHarnessEvolutionHub** (evolve the
   evals) — `architecture/candidate_open_hubs.json`. Pinned: `architecture/substrate_layers.json → foundational_law.recursive_improvement`.
10. **Deterministic global object naming (AI-first — owner law 2026-06-27, hardened 2026-07-01)** — every defined
    thing gets a globally unique, location-derived, MEANING-BEARING name; long names are good (a name is context);
    no name is ever reused. CODE objects: pyprefix `py_<kind>__<file>__<scope>__<name>`
    (`docs/codex/ai-first-naming-and-graph-spec.md`; gates `check_pyprefix_conformance.py` +
    `check_pyprefix_methodology.py` over `architecture/pyprefix_migration.json`). DATA objects: minted ONLY by
    `src.teleon.experiments.ids.canonical_id` (`"{prefix}-{sha256[:16]}"` over canonical bytes; version in
    `schema_version` metadata, never names/ids — no `.vN`/`@N`). Gate:
    `scripts/check_canonical_id_single_source.py` over `architecture/canonical_id_migration.json` (legacy
    direct-hash sites ratchet DOWN, never up). Unique names make grep-as-graph exact — the deterministic code
    graph and primitive-edge search resolve by NAME.

---

## 9. Contracts + hooks (anti-regression — how the laws are enforced)

- **The gate** — `PYTHONPATH=. python3 scripts/run_proofs.py` runs every registered `--self-test` (count computed from
  `scripts/flywheel_proof_modules.py`; run the gate for the LIVE green count — never hand-type it here, per the
  No-Magic-Values law this very file declares). Registry of every proof:
  `scripts/flywheel_proof_modules.py`. The NO-OP trap: `flywheel_proof_modules.py` is a LIST, not a runner — always
  run `run_proofs.py`.
- **Surface contracts** — `check_surface_and_dev_contract` (built-out surfaces exist) + `check_northstar_design`
  (no placeholders, shared-kit consistency) + `check_context_freshness` (canonical docs CLAUDE/AGENTS/BIBLE have 0
  broken refs; rot reported).
- **Edit-time hook** — `.claude/settings.json` PostToolUse → `scripts/hooks/hygiene_guard.py`: FAIL-OPEN advisory that
  warns (never blocks) on placeholders in surfaces, magic-number bursts, broken doc refs, the moment you write them.
- **Manual sweep** — the `/hygiene` skill (`.claude/commands/hygiene.md`): freshness + northstar + magic-number audit +
  archive scan, cleaning safe wins losslessly.
- **The codex contracts** (`docs/codex/*.md` — count them with `ls docs/codex/*.md | wc -l`, never trust prose)
  are the long-form law; the `check_*` scripts are their teeth.

---

## 10. Tools (the load-bearing scripts + ports)

| Need | Tool |
|---|---|
| Run the proof gate | `scripts/run_proofs.py` |
| Search the registry records | `./status search <q>` (`scripts/scale_index.py`) |
| Federated search across registries | `src/teleon/registry/search.py` |
| Faceted browse (OpenHubForAI.io — records as the unit, hubs/registries as facets) | `src/teleon/registry/browse.py` + `scripts/openhubforai_browse_server.py` |
| Registry menu / populate / compose | `src/teleon/registry/{port,populate,compose}.py` |
| Run a capability descent | `src/teleon/synthesis/` + `src/teleon/economics/` |
| BYO-key demos (all surfaces) | `scripts/byo_demo_server.py` + `src/teleon/demos/byo_key_demo.py` |
| Durable work queue + flywheel | `scripts/work_queue.py` + `src/teleon/monitoring/flywheel_queue.py` |
| Git-backed records + branch promotion | `src/teleon/storage/git_record_store.py` |
| Multi-location sync (CDC + leaf-shard) | `src/teleon/storage/sync_engine.py` |
| Self-tuning (ledger + contrastive tuner) | `src/teleon/tuning/` |
| Infra scale ports (Temporal/PG/CH/Vespa/Redpanda) | `src/teleon/infra/scale_ports.py` |
| Token-savings benchmark (with/without hubs) | `scripts/bench_token_usage.py` |
| Launch all surfaces (one URL) | `scripts/landing_server.py` |
| Port the design source → web/ | `scripts/port_full_design_to_web.py` |

---

## 11. Goals (what every serious turn should advance)

- Win ONE vertical provably (starter: HealthLynked provider-directory — healthcare-admin, synthetic/public only).
- Generate 1k–5k component candidates/day + 5–25 showcase pipelines/day; reduce duplicate collapse; improve source
  governance / entity linking / dedupe / embeddings / promotion readiness.
- Keep high-volume rows in JSONL staging + Postgres/pgvector load plans, NOT thousands of static pages.
- Every cycle improves at least one factory target; never a no-op (`docs/codex/no-no-op` principle).

---

## 12. What to do when stuck

If one path is blocked, SWITCH paths (don't stop on a slow scraper/API/rebuild): generate showcase pipelines · add
promotion/readiness tooling · improve load audits · add source seeds · add repair planners · add docs that prevent
repeated slow/incorrect paths. ESCALATE before declaring unavailable (try the LLM-driven browser before giving up).

---

## 13. Factory state ledger (where the CURRENT numbers live — never typed here)

Counts and efficacy claims are COMPUTED artifacts; this section only names their single sources. To know the current
state, run/read these (all candidate-only, `serves_truth=false`):

- **Verified primitive counts** — per-lane manifests `data/dev-intel/primitive_factory/verified_candidates/<label>/manifest.json`;
  daily cross-lane comparison: `PYTHONPATH=. python3 scripts/report_multilane_primitive_generation.py --date-prefix <day> --write`
  → `data/dev-intel/primitive_factory/multilane_generation_report_<day>.md`.
- **Saturation + measured savings** — `PYTHONPATH=. python3 scripts/track_primitive_saturation_and_savings.py`
  → `data/dev-intel/primitive_saturation/<day>_saturation.md` (savings numbers flow ONLY from
  `scripts/primitive_lift_benchmark.py` receipts — the edge-cards-vs-full-source context-reduction measurement).
- **Matching engine + path dynamics** — hybrid search + fit classes live in `src/teleon/registry/primitive_match.py`
  (contract-locked by `scripts/check_primitive_hybrid_search.py`); learned pair affinity in
  `src/teleon/registry/composition_affinity.py` (boost-only law). Path portfolios (generation/search/planning/
  compilation/proof/repair) are data: `catalog/knowledge-packs/data/compiled-primitive-route-benchmark-seeds/`.
- **Benchmark surface** — `catalog/knowledge-packs/data/benchmark-lab-adapter-catalog/manifest.json` (arms A0..A8,
  depth L1..L7; track names are unverified intake until adapter receipts exist).
- **Model-lane health** — circuit breakers + rate limiters are state files under `data/dev-intel/primitive_factory/`
  (`OLLAMA_PAUSE.json`, `GEMMA_PAUSE.json`, `GEMMA_RATE_LIMIT.json`); per-call receipts in each lane's
  `model/call_events.jsonl`. Rule: an Ollama-lane zero-row day is a quota/credits/tier event until proven otherwise —
  probe tokens/sec with one bounded `scripts/_llm_client.py` chat call before touching extraction code.
- **Dated operator snapshots** — `docs/codex/claude-fable-compiled-primitive-routes-handoff.md` carries the latest
  "Factory State Snapshot" section (with per-number source paths); older snapshots are superseded in place.
