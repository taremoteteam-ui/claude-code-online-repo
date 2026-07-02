# THE OPERATIONS BIBLE — the single consolidated state + operations reference

> **Purpose.** One file that holds ALL load-bearing information about what this system is, what exists, what is
> measured, how to operate every lane, and where every number lives — so agents and humans stop reading 300+
> scattered, dated markdown files. **Precedence:** `docs/BIBLE.md` wins on vision/laws; `docs/DESIGN-BIBLE.md` on
> design; `docs/INTEGRATION-BIBLE.md` on frontend↔backend wiring; **this file wins on current state + operations.**
> If a dated handoff disagrees with this file, this file wins — fix or archive the handoff (see §12).
>
> **Number discipline (the No-Magic-Values law applies):** structural facts are prose; every count/measurement is a
> DATED SNAPSHOT that cites its computed source (manifest/report/receipt path) and the command to recompute it.
> Snapshots are superseded in place. All generated rows everywhere are `candidate=true` / `serves_truth=false` until
> a promotion gate says otherwise. Last reconciled: **2026-07-02**.

---

## 1. The system in one page

We are building a **proof-aware primitive route market** — a systems layer for executable capability. A massive
searchable primitive database + deterministic remixing + bounded generation means AI development systems stop
re-creating capabilities that already exist.

The loop (every stage receipted):

```text
user intent -> compact edge search -> CandidateBundle (primitives / groups / templates / routes)
-> deterministic remix or bounded generation ONLY for the missing edge -> PlanLock / executable route
-> deterministic execution or bounded runtime -> proof receipt -> telemetry
-> promotion | demotion | negative memory | gap queue -> registry memory (compounds)
```

The invariant: **compact context at the model boundary, proofed deterministic capability at the runtime boundary.**

Never forget: *Metrics decide. Proof decides. Receipts decide. Candidate remains candidate until promoted.
Search first. Reuse first. Remix deterministically. Generate only the missing edge.*

Products (brand law): **AI Done Right** (parent, `aidoneright.dev`) · **Teleon** (capability compiler + deterministic
runtime + receipts) · **Baltor** (verified context / truth-serving packs, powered by Teleon) · **OpenHubForAI** (open
registry substrate) · **AIDevObserver** (AI-usage/session review + reuse recommendations). Dependency law:
Baltor → Teleon → OpenHubForAI, never the reverse (`scripts/check_portfolio_dependency_law.py`).

## 2. Surfaces

The 5 product surfaces are FULL apps in `web/{context-is-everything, teleon, baltor, openhubforai, aidevobserver}`
served by the showcase (`OH_PRODUCT=<brand> python3 -m scripts.showcase --port N`) over the shared kit, wired
through same-origin seams (`/api/identity/`, `/registry/`, `/api/teleon/`, `/api/observer/`, + live-ops fan-out).
Never build skinny replacement servers. Seam ports single-source from `architecture/local_service_registry.json`.
Extras: Global Operations Console (`scripts/ops_console_service.py`, self-contained realtime SPA); observer service
(`scripts/observer_local_service.py`); showcase-native `/api/primitives` + `/api/components` endpoints — the mount
points for future Primitive Explorer / Gap Queue / Savings Dashboard screens (none built yet). Surface family counts
are computed by `scripts/check_ai_done_right_surface_family.py` — never hand-counted.

## 3. Primitive Atlas: goalposts vs measured state

Goalposts (NOT facts): 1M+ candidates · 50k+ templates · 10k+ groups · 1k+ promoted groups · 100k+ source surfaces ·
10k+ benchmark tasks wired · 250+ variation dimensions · 100+ model/adapter component slots.

Measured state (snapshot **2026-07-02**, recompute via the named sources):

```text
verified primitive candidates, grand total: 30,524
  source: sum over data/dev-intel/primitive_factory/verified_candidates/*/manifest.json
  recompute: jq verified_count over that glob | awk sum
2026-07-02 day: 1,516 verified across 770 distinct areas, 0 saturated
  labels: uc02=702/0dup/0rej · uc03=811/0/0 · slowtier-glm=3 · slowtier-kimi=0
  sources: data/dev-intel/primitive_factory/multilane_generation_report_2026-07-02.md,
           data/dev-intel/primitive_saturation/2026-07-02_saturation.md
2026-07-01 reference day (fast Ollama tier): 14,307 verified in one 20k-fleet label
variation dimensions: 250 (catalog/knowledge-packs/data/primitive-variation-dimension-atlas/manifest.json)
benchmark tracks: 240, arms A0..A8, depth L1..L7 (catalog/knowledge-packs/data/benchmark-lab-adapter-catalog/manifest.json)
path portfolio rows: 294 across 26 files (catalog/knowledge-packs/data/compiled-primitive-route-benchmark-seeds/manifest.json)
knowledge packs on disk: 299 dirs under catalog/knowledge-packs/data/ (ls | wc -l)
observer edge cards: 74,278 (data/dev-intel/aidevobserver_edge_foundry manifest)
foundry lifecycle: 5,200 selected rows in state existing_source_ref_candidate (primitive_source_lifecycle/summary.md)
templates with slot constraints: NO dedicated pack yet (uc01 emitted primitive_template_candidate rows as precedent)
```

## 4. Core objects + lifecycle (canonical shapes)

Objects: **Primitive** (compact contract: input_edge/output_edge/blackbox/effects/proof status) · **Primitive Group**
(hidden member route behind one visible edge; verifier requires `group_contract.hidden_member_edges >= 3` and visible
edges exactly matching) · **Primitive Template** (slot constraints + overlay hooks) · **Variation Overlay** (never
materialize blind cartesians) · **CandidateBundle** (search returns a bundle, never one answer) · **PlanDelta**
(proposed, not truth) · **PlanLock** (canonical locked route = execution truth) · **ExecutionReceipt** ·
**PromotionEvidence** · **NegativeMemory** (failed paths remembered, suppress repeated waste) · **StrategyGenome**
(every search/model/proof/cache choice explicit + mutable).

Lifecycle: `L0 discovered → L1 source-backed → L2 contract → L3 effects → L4 proof obligations → L5 route compiled →
L6 PlanLock → L7 deterministic-execution tested → L8 receipt → L9 benchmark score → L10 promoted|deprecated|retired|
negative-memory-only`. No model, adapter, agent, or benchmark row promotes truth by itself.

The REAL machine-enforced schema is `scripts/verify_primitive_candidates.py`: REQUIRED_FIELDS (primitive_id, kind,
title, input_edge, output_edge, contract, blackbox, effects, source_refs, mutators, proof_requirements,
promotion_blockers, dedupe_key, candidate, serves_truth), ALLOWED_KINDS = {primitive, primitive_group} ONLY
(family strings go in `primitive_kind`), ≥1 public https source_ref, ≥2 proof_requirements, ≥1 mutator/effect,
input_edge ≠ output_edge, in-run dedupe by `kind::input_edge::output_edge::dedupe_key`. Rich-lane quality adds:
≥300-char edge descriptions, edge_contract, reuse_profile, `candidate_boundary_gate` in proofs.

## 5. Factory operations manual (the exact commands)

**Generation lanes** (all stage JSONL to `data/dev-intel/primitive_factory/batch_runs/<label>/**/extracted/
extracted_candidates.jsonl`; verification picks up that glob):

- **Deterministic intake** (zero model tokens): `python3 scripts/build_primitive_pipeline_catalog_intake.py
  --date-prefix <day> --write` (8k owner catalog → deduped family cards; 2026-07-01-c8kdet went 200/200 verified).
- **Ollama GLM/Kimi**: `PYTHONPATH=. python3 scripts/run_primitive_factory_batch_loop.py --date <label>
  --shards <shards.jsonl> --target-profile 20k --provider ollama --model glm-5.2|kimi-k2.7-code --mode direct
  --workers N --timeout T --max-tokens M --prompt-raw-candidate-target R`. **Slow-tier recipe (current key tier,
  measured 2026-07-02: GLM 4.3 tok/s, Kimi 6.5):** R=2-3, M≥6000, T≥900 (GLM) / 700 (Kimi), workers=1 per model
  (account concurrency cap is small — "too many concurrent requests" observed at ~4-6 in flight). On the fast tier
  (2026-07-01) the defaults worked as-is.
- **Gemma 4 via OpenWebUI/CDP**: gated by `GEMMA_PAUSE.json` (running loops honor it PER CALL) + the SEVERE
  cross-process rate limiter in `scripts/_llm_client.py` (fcntl lock, max concurrency 1, spacing from call end,
  owner-tunable `data/dev-intel/primitive_factory/GEMMA_RATE_LIMIT.json`, labeled `gemma_rate_limited` fail-fast,
  Cloudflare origin-5xx session-down breaker). New lanes pick the limiter up at process start.
- **Fable ultracode waves** (Claude Code Workflow tool): briefs → parallel lane agents → one JSONL shard each,
  self-checked → one-shot verification. Wave labels: uc01 (1,382 verified) · uc02 (702) · uc03 (811) · uc04
  (14 new lanes: PDU/package factories, IaC, K8s/Helm/Operator, serverless, CI/CD, SBOM, Postgres + analytics SQL,
  streaming, API→MCP, observability, doc-span grounding, format mutators, SLM harness — pending relaunch).
  ALWAYS relaunch dead waves via Workflow resumeFromRunId — completed agents replay from cache free.

**Model-lane prompt contract (single source — 2026-07-02):** every shard writer prompt is prefixed by
`PRIMITIVE_CANDIDATE_OUTPUT_CONTRACT` and suffixed by `PRIMITIVE_CANDIDATE_PROMPT_EXAMPLE_ROW` from
`scripts/_config.py` (imported by `build_primitive_factory_5k_shards.py` + `build_primitive_pipeline_catalog_intake.py`,
never retyped): JSONL-only, one COMPLETE object per line, no fences/prose/reasoning in the body, and the truncation
rule — stop after the last complete line, fewer complete rows always beat one truncated row (the fix for the
json_decode_error reject class). Retry discipline: in-place worker retries stay OFF for timeouts/breaker labels;
"try again later" is `scripts/run_primitive_failed_shard_retry_loop.py` (per-label `--once`, or periodic
`--interval-seconds 1800 --max-ticks N` — the repo-native cron with backoff + fallback routing).

**Verification (one-shot per label):** `PYTHONPATH=. python3 scripts/run_primitive_verification_loop.py
--source-root data/dev-intel/primitive_factory/batch_runs/<label> --out-dir
data/dev-intel/primitive_factory/verified_candidates/<label> --max-ticks 1` → manifest with
verified/duplicate/rejected. Stop file for ALL verification loops: `data/dev-intel/primitive_factory/VERIFY_STOP`.

**Reporting:** `python3 scripts/report_multilane_primitive_generation.py --date-prefix <day> --write` (lane
comparison from manifests) · `python3 scripts/track_primitive_saturation_and_savings.py` (saturation bands +
measured savings from `scripts/primitive_lift_benchmark.py` receipts).

**Autonomous loops running on this machine:** 2M-goal loop (`run_primitive_2m_goal_loop.py --target-verified
2000000`, stop file `2M_STOP`, self-mints labels + spawns lanes) · flywheel orchestrator (`--forever`, stop via
`.agent/STOP_REQUESTED` — do NOT create it casually) · AIDevObserver foundry daemon (hourly). Six Jun-25
`.agent/*_STOP_REQUESTED` markers intentionally park OLDER loops — do not delete them.

**Model-lane credentials + breakers:** keys live ONLY in `.env` (`OLLAMA_API_KEY`, `OH_LLM_API_KEY`,
`AIDEVOBSERVER_OLLAMA_API_KEY`); `scripts/_llm_client.py _env()` falls back to `.env` PER CALL, so a key swap needs
NO restarts. Breakers: `OLLAMA_PAUSE.json` (session-cap 429 → 1h pause; concurrency 429 → 3 min;
`ollama_usage_pause_active` labels), `GEMMA_PAUSE.json`, `GEMMA_RATE_LIMIT.json`. Self-tests:
`PYTHONPATH=. python3 scripts/_llm_client.py --self-test`.

## 6. Diagnosis playbook (negative memory — do not re-derive)

```text
Ollama lane produces 0 rows across all shards
  -> QUOTA/CREDITS/TIER EVENT until proven otherwise. Order: read call_events.jsonl for 429/402 bodies ->
     probe tokens/sec with ONE bounded chat() call -> only then suspect extraction code.
  -> 429 "reached your session usage limit" = cap exhausted (1h breaker). 402 = no credits (owner action).
     Held-then-timeout requests are logged as misleading TimeoutError.
json_decode_error rejects on model lanes = OUTPUT TRUNCATION (max_tokens < cards x tokens-per-card), not model failure.
Timeout at exactly the lane timeout with tiny probes succeeding = throughput tier or concurrency queueing.
Claude wave agents die mid-wave = Fable-5 usage or 5h session limit; resume the workflow (cache replays), reduce
     effort on retries; never re-run completed shards.
Gemma GPU overload = pause file first (instant, per-call), rate limiter for steady state, restart lane to adopt it.
Kind-mismatch rejections = family string placed in `kind` instead of `primitive_kind` (the historical 690-card bug).
A memory/doc naming a file or flag is a claim about a PAST state — re-verify before relying on it.
```

## 7. Matching engine, search + embedding infrastructure

- **Hybrid matcher**: `src/teleon/registry/primitive_match.py` (1,059 lines, contract-locked by
  `scripts/check_primitive_hybrid_search.py`) — blocking lanes (keyword/label/contract-signature/graph-neighbor/
  semantic bucket LSH), fit classes `FIT_EXACT_MATCH / FIT_DETERMINISTIC_EDIT_MATCH / FIT_NONDETERMINISTIC_EDIT_MATCH`,
  mutation hints, graph assembly status. Extend by adding LANES here — never a second matcher.
- **Co-occurrence learning**: `src/teleon/registry/composition_affinity.py` — pairwise edge affinity from group-card
  seeds + run outcomes + triage negative memory; log-scaled, 30-day half-life, BOOST-ONLY (capped 0.12, never
  outweighs a fit class).
- **Embeddings**: `src/teleon/retrieval/embedding_port.py` (LexicalEmbedder deterministic floor + LocalOllamaEmbedder
  nomic-embed-text 768-dim, policy-selected); RRF fusion (`src/teleon/retrieval/hybrid.py`, RRF_K=60); storage
  `src/teleon/retrieval/pgvector_index.py` (honest local fallback). CAUTION: `primitive_vector_export.jsonl` carries
  64-dim deterministic-lexical vectors (staging, not promotion-ready) — never mix dims in one index. Named
  multi-profile embeddings (edge_io/problem_statement/failure_mode/...) exist only as schema vocabulary — the
  embedding-profile registry pack is a pending build slice.
- **Efficacy**: context-reduction receipts (edge cards vs full source) come ONLY from
  `scripts/primitive_lift_benchmark.py` (the 486x figure lives there), surfaced by the saturation tracker.

## 8. Benchmarks + the SLM-uplift experiment

- **Benchmark Lab adapter catalog**: 240 tracks, 5 families (coding/function-calling/web-os/data-science/security),
  arms A0..A8, depth ladder L1..L7 — IMPORT these ids, never re-type (`scripts/build_benchmark_lab_adapter_catalog.py`).
  Track names are unverified intake until adapter receipts exist.
- **Compiled-primitive-route benchmark seeds**: 26 files/294 rows — generation/search/planning/compilation/proof/
  repair path portfolios, model slot lanes, adapter lanes, micro-agent envelopes, trial/exploration/sprout policies,
  telemetry signals, cache policies, strategy genomes, champion/challenger, route economics. Regenerate ONLY via
  `scripts/build_compiled_primitive_route_benchmark_seeds.py --write` (hand-edits go RED).
- **Pending build slices**: offline paired 100-task plan (paired-arm protocol over adapter-catalog tracks) ·
  AIDevObserver 100-session simulation pack · **SLM-uplift benchmark** (owner hypothesis 2026-07-02: small model +
  primitive-first harness ≈/≥ large SOTA baseline; matrix = model tier × A0..A8 arm × task family; headline
  `uplift_ratio = score(small+harness)/score(large baseline)`; stays HYPOTHESIS until receipts; measured tier speeds
  above feed its model-tier lanes).
- **Prior art anchors** (never presented as local performance): Compiled AI (arXiv:2604.05150; its released suite of
  540 YAML workflow specs = intake source surface; per-stage FirstPassRate metrics adopted into scorecards),
  PlanCompiler, DSPy, LLM+P, LLMCompiler, SWE-agent, Terminal-Bench, AppWorld, MLE-bench.

## 9. Packaging / PDU layer (owner directive 2026-07-02)

Packaging/deployment formats are first-class primitives, not delivery afterthoughts. **PDU (Primitive Distribution
Unit)** = packageable/deployable form of a primitive group: PrimitiveCard → Group → RuntimeWrapper →
DeploymentPackage → MarketplaceListing → DeploymentReceipt → RuntimeTelemetry. Package FACTORIES are records:
`factory:primitive_to_{oci_image, buildpack_image, terraform_module, pulumi_component, cdk_construct, bicep_module,
cloudformation_sam_app, helm_chart, kubernetes_operator, mcp_server, github_action, postman_collection,
pipedream_component, marketplace_listing, sbom_and_attestation, benchmark_task}`. Two loops: marketplaces are BOTH
source (mine Terraform Registry/Artifact Hub/MCP Registry/Kaggle) AND output (publish modules/charts/listings).
Base images (python:3.11-slim, node:22-alpine, distroless, ubi9-minimal…) are TRACKED surfaces: digest pinning,
CVE/EOL rebuild triggers, SBOM + signing receipts. Deployment dimensions on every primitive:
`deployment.{package_kinds[], runtime_targets[], marketplace_targets[], required_artifacts[]}`. Intake law: external
`@N` id suffixes become `version` METADATA — version never lives in ids. Status: uc04 lanes + the
deployment-packaging + marketplace-listing build slices carry this; first worked vertical = agent tool-call
guardrail gateway packaged N ways.

## 10. Proof + guardrail system

`PYTHONPATH=. python3 scripts/run_proofs.py` runs EVERY registered `--self-test` (registration:
`scripts/flywheel_proof_modules.py`; `flywheel_proof_modules.py` alone is a NO-OP false green). Repo-level gates:
surface family · handoff freshness (`check_handoff_docs_freshness.py` — hardcoded expected_counts; update checker +
state JSON + docs in the SAME change) · portfolio dependency law · pyprefix conformance (code names) ·
canonical_id single source (data ids; direct `import hashlib` in `src/**` is the drift signal) · README stats
(`build_readme_stats.py` markers). Laws: change-verification (warrant before change) · lossless distillation
(distillation never replacement; preserve raw + lineage + rollback) · archive-never-delete (§12) · no unbounded
model loops without stop file/ledger/budget/dry-run. Zero-network gate: `check_inference_pipeline_redteam` requires
run_full_pipeline to complete offline — builders/checkers must be offline-deterministic.

## 11. Current work in flight (2026-07-02, see task board)

```text
wave-1 resume (wf_27c21f1e-db6): 20/37 gen shards cached-or-done; 17 gen shards + ALL 12 build slices +
  closer/critic pending relaunch after the 12pm ET limit reset. Build slices = northstar docs trio, schema
  foundation (PrimitiveTemplate/NegativeMemory/CandidateBundle/PlanDelta/PlanLock/StrategyGenome JSON-schemas +
  crosswalk), telemetry+savings single source (scripts/eval/savings_formulas.py), template seeds (>=1k),
  unified source-surface registry (+ packaging/marketplace surfaces + query lattice + scheduler policy),
  deployment packaging pack, paired benchmark plan, observer session sims, marketplace listings,
  embedding-profile registry, product artifacts, negative-memory seed pack.
wave-1.5 (wf_b1d79dc7-931): all 14 uc04 lanes died on the Fable limit — full relaunch pending.
Gemma: rate limiter + breakers LANDED + self-tested; final CDP end-to-end probe + lane restart pending.
Ollama: new key live; slow-tier recipe validation shard (3 cards / 6500 tokens) running; account tier
  decision is the owner's lever for restoring 14k+/day fleet pace.
Integration pass pending: register new self-tests in flywheel_proof_modules.py (_llm_client,
  primitive_factory_model_worker, + all wave build slices), full run_proofs.py, mkdocs nav, memory update.
```

## 12. Documentation map + consolidation law (what lives, what archives)

**The four bibles (live, win their domains):** `docs/BIBLE.md` (vision/laws) · `docs/OPERATIONS-BIBLE.md` (THIS —
state/operations) · `docs/DESIGN-BIBLE.md` · `docs/INTEGRATION-BIBLE.md`. Agent operating rules: `CLAUDE.md` /
`AGENTS.md`. Machine-checked contracts live in `architecture/*.json`.

**Live operational references** (keep): `docs/codex/claude-fable-compiled-primitive-routes-handoff.md` (mission
prompt + dated Factory State Snapshots) · `docs/codex/primitive-registry-operational-schema.md` ·
`docs/benchmarks/edge-first-composition-benchmark-plan.md` · `docs/whitepapers/read-the-edges-not-the-code.md` ·
`docs/strategy/north-stars.md` + `docs/codex/north-star.md` (product north stars — complementary to the Atlas
mission, not superseded) · per-domain contracts in `docs/codex/*-contract.md`.

**Consolidation rule going forward:** dated per-topic handoffs (`*-handoff.md`, `*-2026-MM-DD.md`) are WORKING
DRAFTS. Once their content is reconciled into a bible section, add a header line `Superseded by:
docs/OPERATIONS-BIBLE.md §N` to the old file — `python3 scripts/archive_legacy_docs.py --scan` then picks it up and
`--apply` moves it LOSSLESSLY to `archive/legacy/<original-path>` with a `_manifest.jsonl` entry (171 files already
live there; never delete, never untrack, restore = `git mv` back). Never archive live/generated data (`catalog/`,
`data/dev-intel/`). The conservative scanner only moves files with explicit supersede/deprecate markers — marking is
a deliberate act, done at reconciliation time, never in bulk without reading.

**First reconciliation batch (content now carried by this file — mark + archive on the next hygiene pass after
owner review):** the ~20 `docs/codex/primitive-*-handoff.md` seed-pack handoffs whose packs + checkers are now the
single source; superseded scale docs (`million-object-goal.md`, `billion-component-goal.md`,
`primitive-throughput-scale-plan.md`) once the northstar-docs build slice lands their unified replacement.

## 13. Roadmap (next bounded slices, in order)

1. Relaunch wave-1 resume + wave-1.5 after the limit reset (cached prefixes replay free).
2. Integration pass: proof-module registrations → full `run_proofs.py` green → updated multilane report.
3. Ollama: owner tier decision; adopt the validated slow-tier recipe in the 2M loop's shard minting if staying slow.
4. Gemma: restart the CDP lane with the rate limiter; one bounded end-to-end proof call.
5. Wave 2: PDU schema + package-manifest format + package-factory records pack + PDU matrix + guardrail-gateway
   worked vertical; SLM-uplift pack + pilot runner (dry-run default, budget-gated).
6. Primitive Explorer + Savings Dashboard as new pages on `web/openhubforai` over `/api/primitives` (seam law).
7. Promotion pipeline: first held-out promotion gate run over the 30k verified candidates (L9→L10 with receipts).

---

## Appendix A. Local snapshot for THIS repo (place-discovery-geospatial lane)

> The sections above describe the wider portfolio machine (its `data/dev-intel/`, `src/teleon/`, model lanes, and
> autonomous loops live there, not here). This appendix is the SAME number discipline applied to this repository —
> a dated snapshot citing only locally computed sources. Recompute, never retype.

Snapshot **2026-07-02** (sources: `catalog/knowledge-packs/data/place-discovery-geospatial-seeds/manifest.json`,
`benchmarks/runs/run-20260702T174206Z/{manifest.json,run_summary.json}`; recompute via
`python3 scripts/run_proofs.py` + `python3 scripts/check_benchmark_run.py --self-test`):

```text
seed pack rows: 453 (49 source surfaces · 38 primitive cards · 12 groups · 34 overlays · 320 benchmark task demands)
P0 primitives implemented and receipt-emitting: see primitives/ (registry, fingerprint, entity, gates, evidence,
  spatial join, catchment, map artifact + adapters: HRSA, NPPES, CKAN, Socrata, ArcGIS, Overpass)
first measured run (arm A4, fixture_offline): 12/12 tasks, 58 receipts, 176/176 proofs, 0 runtime LLM tokens,
  2 gap records (training_provider_discovery, site_selection_ranking)
negative memory (fixed): zip-only blocking missed unpostcoded OSM records (run-20260702T174206Z + commit 4ec148f);
  fixed by geo-grid union-of-keys blocking in primitives/entity.py
baselines A1/A2: NOT RUN - no savings claim exists for this lane yet
```
