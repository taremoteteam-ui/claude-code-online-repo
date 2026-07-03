# The Flexible Multi-Path Primitive Architecture

Last updated: 2026-07-03. Why this system commits to NO single architecture, pipeline, model, prompt, scraper, or
search method — and instead builds a portfolio of paths at every step so that **data, metrics, and receipts choose
the most efficient path (or paths) for each situation.** Companion to `docs/OPERATIONS-BIBLE.md`,
`docs/handoff/parallel-paths-and-path-tracking-manual.md`, and `docs/codex/benchmark-solver-primitives-and-slm-uplift.md`.

> **Grounding note (read `docs/BIBLE.md` first).** This is a north-star architecture document. Like THE BIBLE, it
> references ecosystem assets across the wider portfolio (Teleon/Baltor/OpenHubForAI surfaces, `src/teleon/...`
> engines, registries, and packs that are future build slices here). Treat any path or file not present in this repo
> as a planned slice, not an error. **Appendix A at the end maps this vision to what is actually built and proven in
> THIS repo today, with counts recomputed from manifests — nothing in the appendix is aspirational.** The
> non-commitment law and the `candidate=true / serves_truth=false` boundary hold for every path named below.

---

## 0. The one principle

> Never commit to one way of doing anything. Every step is a PORTFOLIO of interchangeable paths; the engine runs a
> baseline plus challengers; the tracking ledger records which path won, which lost (kept as training negatives),
> and why. Adding a path is a data row, not a rewrite. The invariant everywhere: **compact context at the model
> boundary, proofed deterministic capability at the runtime boundary.**

This is the *non-commitment law*. It is why the system can absorb a new scraper, a new model, a new prompt style, a
new search method, or a new compiler without re-architecting — the new path joins the tournament and either earns its
place on receipts or is demoted to negative memory. The canonical machinery already exists and is reused, never
rebuilt: the parallel-path engine `src.teleon.experiments.parallel_paths.run_parallel` (modes
baseline/candidate/shadow/canary/fallback), the promotion gate `src.teleon.experiments.path_promotion`, and the
append-only tracking ledger `src.teleon.evolution.descent_attempt_store.DescentAttempt`.

The machine-readable catalog of paths-per-step is a real pack:
`catalog/knowledge-packs/data/step-path-portfolios/` (builder `scripts/build_step_path_portfolio_pack.py`, checker
`scripts/check_step_path_portfolio_pack.py`) — every path references a real engine mode and declares when it wins,
how it fails, its escalation order, and the receipt fields it emits.

---

## 1. Multiple paths at EVERY step

Each pipeline step is an ordered escalation ladder (cheapest / most-deterministic first). The system climbs only when
the cheaper path fails its receipt gate — the *escalate-before-unavailable* law. A representative slice:

### Generating seed content — many paths
- **deterministic table→row** (`build_raw_pack_primitive_candidates.py`) — structured MD/TSV packs → verifier rows, zero model tokens.
- **prompt-queue from compact seeds** (`build_prompt_queue_from_seeds.py`) — cluster millions of variation seeds into per-family briefs.
- **catalog intake** (`build_primitive_pipeline_catalog_intake.py`) — owner catalog → deduped family cards.
- **source-adapter extraction** — OpenAPI / MCP / PyPI / Terraform / GitHub Actions / schemas → contract cards.
- **model-drafted candidates** — Fable ultracode lanes, Ollama GLM/Kimi, Gemma 4 — bounded, candidate-only.
- **benchmark-demand extraction** — a benchmark task → the primitive demands it implies.
- **trace-to-workflow mining** — a successful agent/tool trace → a route candidate.
- **negative-memory→gap** — repeated failures mint new primitive demands.

### Scraping / acquisition — a ladder, not one scraper
`cached_snapshot → structured_api → html_fetch_parse → headless_browser → stealth_browser → vision_extraction →
human_review`. Each rung has a receipt gate; the system escalates only on failure and records honest-unavailable only
after the ladder is exhausted (already wired in `src/teleon/hub_freshness.py`).

### Preprocessing — many paths
`profile → validate → normalize → dedupe → quarantine`, each realizable deterministically (rules/schema) OR
hybrid (deterministic core + bounded-LLM fallback on the ambiguous field) OR model-assisted, with format mutators
(json↔parquet, wide↔long, csv↔table) carrying roundtrip proofs.

### Submitting to LLMs — many prompts, personas, lanes
The output contract is single-sourced (`scripts/_config.py:PRIMITIVE_CANDIDATE_OUTPUT_CONTRACT` +
`PRIMITIVE_CANDIDATE_PROMPT_EXAMPLE_ROW`) but the LANE is a portfolio: deterministic (no model), small-local
(Gemma 4 variants), large-cloud (GLM 5.2 / Kimi K2.7-code via Ollama), frontier (Claude Fable). Prompt STYLE is a
path too — sharp-atom vs long-pipeline-group vs chain-decomposition vs template-fill — and personas (writer /
reviewer / decomposer / judge) are model-slot paths. Model-slot selection itself is receipted
(`model_route_receipt` in the benchmark-seeds pack) so the cheapest lane that clears quality wins.

### Search / find / review / compile primitives — many paths
- **Search**: exact edge · type-compatible edge · schema/contract · lexical BM25 · dense vector · hybrid RRF · graph
  route · known-chain · negative-memory-suppress · source-fallback. Search returns a **CandidateBundle**, never one
  overconfident answer.
- **Review/plan**: exact route lookup · template slot-fill · deterministic graph search · contract-diff remix ·
  co-occurrence bundle completion · bounded-LLM PlanDelta · MCTS/evolutionary route search · trace replay · human review.
- **Compile**: deterministic template fill · schema-driven codegen · AST transform · typed graph lowering ·
  grammar-constrained generation · bounded model function · manual approval lock.

**Data chooses.** For a given situation the router asks: *which path solves this with the least source escalation,
least runtime model use, strongest proof, lowest side-effect risk, and best reuse value?* — and the answer is decided
by receipts accumulated over the co-occurrence graph, not by a hardcoded pipeline.

---

## 2. The primitive black box + contract edges (why the LLM never reads everything)

A primitive is a **black box with a compact visible contract.** The model sees WHAT it does, never HOW:

```text
visible input edge  +  visible output edge  +  blackbox behavior (one sentence)
+ effects  +  runtime targets  +  proof status  +  source/evidence status
+ ranking explanation  +  negative-memory warnings
```

That is ~150–300 tokens. The model does **not** read implementation, package source, member edges, dependencies, or
hidden workflow steps unless the route escalates to that depth (the L1→L7 context-depth ladder). Matching happens on
the EDGES and KEYS, not on bodies — so a small model can string a route by reading edge cards, exactly the
composition thesis.

**Nesting-doll architecture.** Capability is layered, each layer hiding the one below behind a single visible edge:

```text
Leaf primitive      one atomic contract  (parse, validate, hash, dedupe)
Primitive group     one visible edge hiding >=3 member edges  (import: parse->validate->normalize->dedupe->receipt)
Route portfolio     a chain of groups; group N's output_edge == group N+1's input_edge
Template            a slot-parameterized family of the above  (Raw{Entity}Batch+{Policy} -> Prepared{Entity}+{Receipt})
PDU                 the packaged/deployable form  (group -> runtime wrapper -> deployment artifact -> marketplace listing)
```

You open a doll only when you need to — the group card answers "can this solve my task?" without exposing its seven
internal member edges. The machine-enforced shape lives in `scripts/verify_primitive_candidates.py` (kind ∈
{primitive, primitive_group}; a group's `group_contract.hidden_member_edges` >= 3 with visible edges exactly equal to
its input/output).

---

## 3. The dimensional / columnar architecture (efficient matching without reading)

A primitive is not a blob — it is a wide record with many typed columns, so retrieval resolves by attribute, key,
and embedding rather than by prose. The load-bearing field families:

- **Contract columns**: `input_edge`, `output_edge`, `input_edge_description`, `output_edge_description`,
  `edge_contract{preconditions, postconditions, failure_modes, composition_notes}`, `contract{summary, input, output,
  errors, transformation_logic}`, `blackbox`.
- **Effect / runtime columns**: `effects[]`, `runtime_targets[]`, `mutators[]`, `proof_requirements[]`,
  `promotion_blockers[]`, `promotion_status`.
- **Key blocks (blocking keys)**: `blocking_keys[]` — the LSH-style lexical/semantic buckets that let search prune
  the universe to a small candidate set in one hop (`src/teleon/registry/primitive_match.py` blocking lanes).
- **Search / view columns**: `slug`, `domains[]`, `capability_tags[]`, `source_family`, `source_evidence_status`,
  `quality_score`, `readiness`, `trust`, `surface_visibility`, `card_hash`, `source_digest`.
- **Variation dimensions**: an extensible dimension bank (industry · region · jurisdiction · schema_standard ·
  data_shape · transform · runtime_target · package_target · role · privacy_class · …) —
  `catalog/knowledge-packs/data/primitive-variation-dimension-atlas/` (count from its manifest, never typed). A
  primitive carries a `variation_profile` naming which slices it applies to, so one row covers many variants instead
  of exploding into thousands of near-duplicate rows.
- **Multi-embedding profiles**: not one vector per primitive but NAMED profiles — `edge_io_embedding`,
  `blackbox_embedding`, `problem_statement_embedding`, `failure_mode_embedding`, `negative_memory_embedding`,
  `benchmark_task_embedding`, `deployment_packaging_embedding`, … each stored long-form (primitive_id,
  embedding_profile_id, model_id, dimensions, vector, source_field_hash) so different queries hit the right facet.
  Registry: `catalog/knowledge-packs/data/embedding-profile-registry/` (declarative); infra: `embedding_port.py`
  (LexicalEmbedder floor + LocalOllamaEmbedder nomic-embed-text 768) + RRF fusion.
- **Edge-type vocabulary (the input/output/edge layers)**: `catalog/knowledge-packs/data/canonical-edge-type-vocabulary/`
  — the shared intermediate-type system (RawGraphInput → EdgeList → AdjacencyGraph → DistanceMap → AnswerArtifact,
  …) that makes edges MATCH across primitives. A primitive's `output_edge` type_id reappearing as another's
  `input_edge` type_id is what makes routes COMPOSE — the difference between "relevant" and "chainable."

The payoff: a query prunes by blocking keys (one hop), reranks by the right embedding profile, and confirms by edge
compatibility — all over columns, never over implementation bodies. That is how ~113k+ primitives stay searchable and
composable at the model boundary without the model reading any of them.

---

## 4. Flexible mutations, remixes, and adjustments

A near-match is made usable without asking a model to write unbounded glue. Remix is itself a portfolio:

- **Deterministic mutators** (preferred — zero tokens, provable): `field_rename`, `field_project`, `type_cast`,
  `schema_validator_inserter`, `input_envelope_wrapper`, `output_receipt_wrapper`, `idempotency_wrapper`,
  `retry_wrapper`, `cache_wrapper`, `pagination_expander`, format mutators (`json_to_parquet`, `wide_to_long`, …),
  runtime wrappers (`api_endpoint_wrapper`, `queue_worker_wrapper`, `kubernetes_job_wrapper`, `mcp_tool_wrapper`),
  `route_to_group_card`. Each declares preconditions, postconditions, lossiness policy, proof obligations, and
  telemetry fields. Path: `RequestedEdge → CandidateBundle → ContractDiff → MutatorPlan → RouteCandidate →
  PlanLock → ProofReceipt`.
- **Non-deterministic / model-assisted remix** (bounded roles only): field-alias suggestion, ambiguous schema
  mapping, code micro-repair, proof-case suggestion, error explanation — the model PROPOSES, the deterministic
  compiler DISPOSES. Model output stays candidate=true / serves_truth=false until proven.
- **Tool / system-assisted**: mutators may call a real tool (a formatter, a linter, a validator, a schema compiler,
  a container build) as a bounded, receipted step — the tool result is the mutation, verified by a proof.
- **Genetic / sprout mutators** (experiment mode, budgeted): mutate retriever weights, embedding-profile mix,
  candidate-bundle size, context-depth limit, model-slot assignment, LoRA choice, route-member order, proof-gate
  order, blocking rule, matching threshold. Sprouts stay candidate-isolated and promote only on held-out wins.

Every mutation is a tracked path with a receipt — so the system learns which mutator wins for which contract-diff
shape, and the cheapest sufficient mutation is selected next time.

---

## 5. Globally-unique names → deterministic graphing

Advanced deterministic graphing depends on names being globally unique and meaning-bearing, so **grep-as-graph is
exact** — the code graph, primitive edges, and cross-codebase search resolve by NAME with zero ambiguity. Two planes,
one law (`docs/codex/ai-first-naming-and-graph-spec.md`):

- **Code objects (Python)**: the pyprefix scheme `py_<kind>__<file>__<scope>__<name>` — every defined thing gets a
  location-derived, unique, long name (a name is context the model uses; no name is ever reused; uniqueness lives IN
  the name). Every collision removed increases graph recall (`codegraph.py` drops ambiguous call edges today; unique
  names climb that back).
- **Data objects (records/ids)**: minted only by the single source `src.teleon.experiments.ids` —
  `canonical_id = "{prefix}-{sha256[:16]}"` over canonical bytes. Version lives in `schema_version` METADATA, never
  in a name or id (no `.vN`, no `@N` suffixes).

Because names are unique and edges name their endpoints (`input_edge` / `output_edge` type_ids from the vocabulary),
the whole primitive universe is a deterministic graph: a route composer WALKS it (producer_family → type → consumer_family
edges in the edge-type vocabulary's `family_edges.jsonl`) rather than guessing. Unique names + typed edges are what
let agents compose by reading names + edges, not bodies.

---

## 6. How it all composes (the flexible loop)

```text
user intent
 -> decompose (path portfolio: rule / small-model / frontier decomposer)
 -> multi-path SEARCH -> CandidateBundle (exact + near + template + mutator + fallback, with negative-memory warnings)
 -> multi-path ORDER/COMPOSE (edge-chain the bundle output_edge->input_edge; template fill; PlanDelta; graph search)
 -> multi-path REMIX (deterministic mutators first; bounded model only for the missing edge)
 -> PlanLock (canonical, hashable, replayable)
 -> multi-path EXECUTE (local fn / container / serverless / queue / k8s / human-review — by effect + risk + proof)
 -> proof receipts + telemetry
 -> metrics/receipts PROMOTE the winning path, DEMOTE losers to negative memory, QUEUE gaps
 -> registry memory compounds; next identical situation is cheaper
```

No box in that loop is a single implementation. Each is a portfolio, each choice is receipted, and the winner is
whatever the data says is cheapest-that-still-proves for THIS situation — which may differ next time as the registry,
the models, and the negative memory evolve. That is the whole design: **not one architecture, but a flexible
multi-path system that lets data choose.**

---

## 7. Why this is efficient (the summary)

- The model reads **edges, not bodies** — ~150–300 tokens per candidate, never implementation.
- Matching is **columnar**: blocking keys prune, embedding profiles rerank, edge types confirm composability.
- Remix prefers **deterministic, zero-token** mutators; the model generates only the genuinely missing edge.
- Every step is a **tournament with receipts**, so the system converges on the cheapest sufficient path and remembers
  failures instead of repeating them.
- **Nesting-doll** hiding + **globally-unique names** + **typed edges** make the universe a deterministic graph a
  small model can walk — the substrate for "retrieve capabilities, not code."

---

## Appendix A — grounded in THIS repo today (recomputed from manifests, not aspirational)

Sections 0–7 are the north-star vision spanning the wider portfolio. This appendix records only what is BUILT,
CHECKED, and PROVEN in this repository as of 2026-07-03 — the concrete instances of each principle above. Counts come
from pack manifests and `scripts/run_proofs.py` (21 green stages), never typed by hand. Every row is
`candidate=true / serves_truth=false`.

### The composable universe that exists now
- **Capability graph**: 2,867 typed nodes across all lanes (`catalog/knowledge-packs/data/capability-graph/`), 917
  distinct canonical port types indexed by producer/consumer.
- **Universal catalog**: 335 base families × runtime wrappers → 1,271 resolved primitives
  (`build_universal_primitive_pack.py`).
- **Warehouse/analytics lane**: 221 families → 976 resolved + 54 templates + 28 multi-wave pipelines (the checker
  enforces the wave-by-wave topological contract).
- **Place-discovery lane**: 38 working primitive cards with source adapters; **document-extraction lane**: 8
  span-grounded extraction primitives.
- **Coding-agent + competitive-programming lane**: SWE and CP solve loops that compile end-to-end from edges (see
  `docs/codex/coding-agent-lane-handoff.md` — this is the local instance of the "benchmark-solver-primitives-and-slm-uplift"
  companion referenced up top).
- **27 JSON schemas** (contracts-before-data) and **27 pure-data seed modules** (the only place content is edited).

### Section 2 (black box + nesting doll) — what is real
- The compact contract is the `primitive_card` / `reusable_primitive_family` row: **20 typed columns** including
  `input_edge`, `output_edge`, `blackbox.does`, `effects[]`, `runtime_targets[]`, `proof_requirements[]`,
  `known_failure_modes[]`, `risk_class`, `human_review_required`, plus the 8-field `problem_solution` block on
  families. The model reads these columns, never the implementation.
- The nesting-doll layers that exist as enforced shapes: **leaf family → resolved primitive** (family × runtime
  wrapper), **primitive group** (hidden member route behind one visible edge, in the place-discovery pack),
  **template** (54 slot-parameterized warehouse templates), **pipeline** (28 multi-wave templates whose waves chain
  by produced/consumed ports).

### Section 3 (columnar matching) — what is real
- **Typed port model** in `primitives/edges.py`: every port has a `role` (data / config / receipt) and a
  `canonical_type`. Config ports (suffixes `Policy/Spec/Context/Weights/Preference/Config/Settings`) never block
  composition; receipt ports are evidence outputs. This is the input/output/edge-layer separation, enforced.
- **Search paths that exist**: `primitives/search.py` (`candidate_bundle_search`, `PackSearchIndex` lexical IDF with
  group-first boost) returns a CandidateBundle; `scripts/evaluate_candidate_search.py` measures retrieval against all
  benchmark task demands; `scripts/build_cooccurrence_edges.py` mines the co-occurrence graph from run scorecards.
- **The canonical edge-type vocabulary** exists in-code as the `canonical_type` map + the capability graph's
  `port_type_index.jsonl` (917 types with their producers/consumers) — the "output_edge type reappears as another's
  input_edge" composability substrate.

### Section 4 (flexible mutation/remix) — what is real
- **Deterministic mutators**: `primitives/mutators.py` — 8 pure, roundtrip-proofed transforms (json↔rows,
  wide↔long, field_rename, field_project [lossy, discloses drops], geojson↔records).
- **The type-adapter connector layer** (new): `primitives/type_adapters.py` — 6 reviewed deterministic bridges
  `FromPort→ToPort`, backed by real code + proofs, registered as `kind=type_adapter` capability-graph nodes so the
  route compiler inserts them and **discloses each adapter as an explicit route step** (`is_adapter` on the step),
  never a silent type collapse. Schema `schemas/type_adapter.schema.json`; the checker runs every adapter's fixture
  through its proofs.
- **Runtime wrappers**: 10 wrappers (`runtime_wrappers_seed.py`) cross each family into its deployable forms —
  the deterministic "same capability, different runtime target" remix.
- **Reviewed synonyms**: the curated `_SYNONYM_MAP` in `primitives/edges.py` (e.g. `JsonObject→JsonDocument`,
  `LoginAttempt→LoginCredential`, the `*RecordSet→EntityRecordSet` family) — pure aliases, distinct from adapters.

### Section 5 (deterministic graphing) — what is real
- **Stable, version-free IDs** with version in the `version` metadata field (repo convention #6), and the
  content-hash gate in every checker that goes red on any hand-edit — the "names/ids are deterministic keys" law.
- **The route compiler** `primitives/route_compiler.py` walks the typed graph by forward-chaining saturation over
  canonical types, emitting a hashable, replayable PlanLock (`route_hash`) or an honest gap with the unmet type +
  nearest producers. Zero model calls.

### Section 6–7 (the loop + efficiency) — the measured instance
- The deterministic slice of the loop runs today in `scripts/run_route_compiler_demo.py`: SEARCH-free compile of 35
  curated (have → want) targets over the graph.
- **Measured compose rate: 31/35 = 88.6%** (up from 22/33 = 67% before the adapter layer), with **7 disclosed
  adapter steps across 6 adapter-mediated routes** and connection tiers `exact: 81, typed: 10`. Example
  adapter-mediated routes: `SessionToken` = `login_verify → [adapter] → session_issue → [adapter]`; `LinkGraph` =
  a 5-step entity-resolution chain via the `match_score_to_set` adapter. The remaining 4 gaps are genuine multi-step
  domain chains (map assembly, RAG, doc extraction, flagship evidence answer) that need real intermediate
  primitives, not adapters — and the gap/normalization queue correctly still names them. **No token-savings,
  speed, or accuracy claim is made**: `runtime_llm_tokens = 0` because no model runs in the compile, and that is the
  only quantity asserted.

### What is referenced above but NOT yet in this repo (future build slices)
The `src/teleon/...` parallel-path engine, promotion gate, and descent-attempt ledger; the
`step-path-portfolios`, `primitive-variation-dimension-atlas`, `embedding-profile-registry`, and
`canonical-edge-type-vocabulary` packs as standalone artifacts; the scraping ladder; the pyprefix naming pass; and
the multi-embedding retrieval stack. These are the wider-portfolio surfaces the vision composes; when a slice lands
here it arrives as a builder + checker + seed + proof stage, and this appendix is updated from its manifest.
