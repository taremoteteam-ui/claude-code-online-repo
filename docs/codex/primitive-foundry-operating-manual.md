# Claude Code Web Operating Manual: Primitive Foundry, Remixers, Route Compiler, and AIDevObserver Consumption

Last updated: 2026-07-02

Status: canonical operating manual, memorialized verbatim. Some sections
reference wider-portfolio assets (`src/teleon/observer/`,
`.agent/primitive-registry/`, `dist/`, `data/dev-intel/`) that live in the
broader AI Done Right codebase, not in this place-discovery + document-
extraction lane workspace. Treat those paths as future build slices, not
errors. Appendix A maps every section to what already exists HERE.

The job is not to invent random rows. The job is to grow a useful,
source-backed, proof-aware primitive bank that AIDevObserver can search and
consume, then use telemetry and benchmarks to decide which generation, search,
remix, and compile paths are best.

## 0. First Principles

The system should not commit to one way of generating primitives, one way of
searching primitives, one compiler, one model, or one proof method. Build a
strategy tournament:

```text
source adapters + deterministic miners + LLM generators + local models/LoRAs/
rankers + search methods + remixers/mutators + compilers + proof systems +
benchmark arms + telemetry receipts
= promoted primitive routes, reusable primitive groups, and negative memory
```

The core question for every task: **what is the cheapest route that compiles,
proves, and reuses the most existing capability?**

Never treat plausible generated content as truth. New rows remain
`candidate: true, serves_truth: false`. Promotion requires source refs,
contract checks, effect declaration, proof receipts, and benchmark or fixture
evidence.

## 3. Primitive Record Types

Do not store only functions. Store capability records, route records, proof
records, source records, and strategy records:

```text
PrimitiveCandidate · ImplementedCodePrimitiveCandidate · CapabilityCard ·
ProblemSolutionCard · PrimitiveGroup · RouteCandidate · RoutePortfolio ·
PrimitiveOverlay · RuntimeWrapper · SourceAdapter · ProofAdapter ·
BenchmarkAdapter · Mutator · PlanDelta · PlanLock · ExecutionReceipt ·
ProofReceipt · PromotionEvidence · NegativeMemory · StrategyGenome · RunTrace ·
Scorecard · CoOccurrenceEdge · DecompositionMemory · CacheReceipt ·
RegretRecord · ModelComponent · LoRAAdapter · RankerComponent
```

## 4. Compact Primitive Card Format

The LLM should first see the smallest useful contract: input edge + output
edge + blackbox behavior + effects + runtime targets + proof status +
source/provenance summary. Problem-solution details are first-class, not
optional prose: a primitive should say which repeated problem it solves, which
naive failure it prevents, which core components form the solution, and how
success is measured.

## 6. Primitive Groups

Primitive groups hide a repeated route behind one compact visible contract
(visible input/output edge; hidden member edges behind drill-down). Group
promotion should come from repeated successful routes, not an LLM naming
plausible chains.

## 7. Specialization Overlays

Do not physically generate every Cartesian product. Store base primitive +
overlays (algorithm/schema/storage/source/industry/region/role/proof) +
resolver rules, and materialize hot/high-value/benchmarked combinations only.

## 9. Mutators and Remixers

Deterministic mutators make near-matches usable without unbounded glue:
field_rename, field_project, schema_validator_inserter, type_cast,
map_sequence, pagination_expander, retry_wrapper, idempotency_wrapper,
audit_receipt_wrapper, route_to_group_card, and the format mutators. The
deterministic remix path: RequestedEdge -> CandidateBundle -> ContractDiff ->
MutatorPlan -> RouteCandidate -> PlanLock -> ProofReceipt. Hybrid remix:
CandidateBundle + cards + allowed mutators + proof policy -> LLM PlanDelta ->
deterministic compiler validates -> PlanLock. The LLM proposes; the compiler
decides. LLM remix rule: 1 model call = 1 primitive/route/repair; output
remains candidate; validate deterministically after every call; checkpoint.
Genetic sprouts run in experiment mode with budgets and reproducible seeds.

## 10. Search Portfolio

Do not use one retrieval method. Support exact edge, type-compatible, schema
similarity, BM25/lexical, dense vector, hybrid, graph route, known-chain,
benchmark-demand, receipt-boosted, negative-memory-suppressed, source-authority,
cost-aware, and context-depth-aware search. Search returns a CandidateBundle,
never one answer.

## 11. Route Compiler

TaskIntent -> PrimitiveDemand -> CandidateBundle -> RouteCandidate -> PlanDelta
-> PlanLock -> DeterministicExecution -> ExecutionReceipt -> ProofReceipt.
PlanDelta is model-proposed and untrusted; PlanLock is deterministic compiler
output (stable, hashable, replayable). Execution runs from PlanLock, not
free-form model text.

## 12. Proof and Promotion

Proof types span schema/type/unit/contract/fixture/golden/property/metamorphic/
differential/sandbox/static-analysis/effect-audit/state-diff/idempotency/
security/privacy/cloud-dry-run/observability/human-review/benchmark. Lifecycle
L0..L10 (discovered -> source-backed -> contract -> effects -> proof obligations
-> route compiled -> PlanLock -> execution tested -> receipt -> benchmark score
-> promoted/deprecated/negative-memory). Promotion rule: no source refs, no
I/O edge, no effect declaration, no proof receipt, or no privacy/license review
where relevant => no promotion.

## 13. Ranking and Impact Scoring

Rank by evidence and usefulness, not plausibility: primitive_score,
route_score, generator_score, and search_score are all evidence-weighted
(source authority + proof strength + reuse + benchmark lift + token savings
minus false-positive/security/license/stale/hidden-effect risk). Do not
optimize for row count.

## 14. Benchmarks and Experiment Arms

Arms A0 (reference) through A8 (source-level fallback): A1 baseline agent,
A2 repo search, A3 exact route, A4 deterministic mutators, A5 LLM PlanDelta,
A6 deterministic remix repair, A7 LLM micro-repair, A8 source fallback.
Metrics: task_success, tokens_to_plan, tokens_to_pass, runtime_llm_tokens,
source_files_read, source_context_tokens, depth_to_solution, compile_success,
proof_success, route_reuse, new_group_created, negative_memory_created,
cost_per_success, human_review_needed. Benchmark source families: BFCL,
DocILE (document extraction + source-span proof), SWE-bench Verified,
Terminal-Bench, AppWorld, MLE-bench/Kaggle, WebArena/Mind2Web, OpenAPI/AsyncAPI,
MCP Registry, Terraform/GitHub Actions/Kubernetes.

## 15-16. Telemetry Ledger and Strategy Genome

Every run emits traceable events and a RunTrace; every path is a versioned,
replayable StrategyGenome (decomposer/retriever/reranker/planner/compiler/
proof_policy/cache_policy + parameters). Run modes: champion, challenger,
shadow, race, quorum, canary, replay, sprout, benchmark_batch.

## 17. Models, LoRAs, Rankers, Mini-Agents

Intelligence components are records too (ModelComponent/LoRAAdapter/
RankerComponent). Do not hardcode credentials; use env vars or a broker. Prefer
one-call-one-primitive / one-call-one-repair for high-volume LLM generation to
avoid truncation corruption.

## 18. Cache and Co-Occurrence

Cache at every layer (source_surface, edge_card, candidate_bundle,
decomposition, route, PlanLock, proof, artifact, negative_memory, model_decision)
with hash invalidation keys (source/schema/card/route/PlanLock/policy/model/
LoRA/proof/runtime). Strong co-occurrence -> route_to_group_card -> hidden
member edges -> proof requirements -> benchmark task set -> candidate group.

## 19. Negative Memory

Every failure creates structured memory (failure pattern, reason, recommended
fix, suppression policy) that influences search and route ranking.

## 20-21. High-Priority Domains and Source Adapters

Prioritize recurring domains (auth, CRUD, trackers, entity resolution,
document extraction, geospatial, guardrails, deployment, ...). High-value
factories: OpenAPI/AsyncAPI/GraphQL/gRPC/MCP -> contract cards; package
registries -> API surface cards; workflow platforms -> group cards; benchmarks
-> demand cards; runtime traces + AI sessions -> observed routes and negative
memory.

## 24. Safety and Privacy

Never commit or print keys, tokens, cookies, passwords, or real PII. Use env
vars. Public-demo surfaces must not expose local filesystem primitive rows;
private/internal search may.

## 26. Final Operating Rule

The primitive bank improves through evidence: more tasks -> more receipts ->
better rankers -> better route reuse -> fewer tokens -> more proof -> more
promoted primitives -> better future tasks. The durable asset is not the LLM
output; it is the primitive contract + route + proof + wrapper + receipt +
benchmark score + negative memory + promotion evidence.

---

## Appendix A. Local implementation mapping (this repo, 2026-07-02)

This lane workspace already implements most of the manual's architecture.
Recompute every count from the named manifest; verify with
`python3 scripts/run_proofs.py` (13 stages green).

| Manual section | Implemented here |
| --- | --- |
| 0 First principles / candidate boundary | Enforced by every checker; `candidate=true`/`serves_truth=false` on all rows, gated in `scripts/check_*_pack.py` |
| 3 Record types | Schemas: `primitive_card`, `primitive_group`, `primitive_template`, `variation_overlay`, `candidate_bundle`, `plan_delta`, `plan_lock`, `execution_receipt`, `promotion_evidence`, `negative_memory`, `strategy_genome`, `benchmark_scorecard`, plus the document-extraction and source-surface schemas |
| 4 Compact card | `schemas/primitive_card.schema.json` (visible edges + blackbox + effects + proof status); place-discovery + document-extraction cards |
| 6 Primitive groups | `schemas/primitive_group.schema.json` + 12 place-discovery groups (hidden member edges) |
| 7 Overlays | `schemas/variation_overlay.schema.json` (34 overlays); the document lattice materializes `doc_type x field` on demand, not blindly |
| 9 Mutators | `primitives/mutators.py` - 8 deterministic mutators with roundtrip/lossiness proofs (`tests/test_mutators.py`) |
| 10 Search portfolio | `primitives/search.py` - CandidateBundle over the pack (lexical IDF, group-first boost, negative-memory warnings); measured recall via `scripts/evaluate_candidate_search.py` |
| 11 Route compiler | `plan_delta`/`plan_lock` schemas + PlanLock compilation & replay proof in `scripts/run_place_discovery_benchmark.py` (arm A4 executes from the lock; every success replay-verified) |
| 12 Proof & promotion | L0-L10 lifecycle in the north-star docs; `schemas/promotion_evidence.schema.json` + an honestly-BLOCKED example (`examples/core_objects/promotion_evidence.json`) |
| 13 Ranking | `scripts/eval/savings_formulas.py` single source (formulas only; measured inputs marked NOT YET RUN) |
| 14 Benchmarks / arms / DocILE | Two harnesses with arm A4 + depth ladder; DocILE source-span grounding is the document-extraction lane invariant |
| 15-16 Telemetry & genome | `schemas/strategy_genome.schema.json` + example; execution receipts on every primitive run |
| 18 Co-occurrence | `scripts/build_cooccurrence_edges.py` mines edges from run scorecards (boost-only) |
| 19 Negative memory | `schemas/negative_memory.schema.json` + the real zip-blocking incident; the place-discovery harness auto-emits negmem on task failure |
| 24 Safety | No secrets in-repo; all fixtures synthetic and labeled |

Not present here (wider portfolio): the `src/teleon/observer/*` consumption
path, `.agent/primitive-registry/*`, `dist/primitive-registry-operational-load/`,
`data/dev-intel/*`, and the AIDevObserver consumption checks. In this workspace,
the registry-consumption analog is `primitives/search.py` over the generated
pack manifests, and the operational-state analog is `docs/OPERATIONS-BIBLE.md`
Appendix A. When those ecosystem paths exist, wire this lane's packs into them
per this manual's sections 2 and 5.

## Appendix B. Next build slices this manual points at (bounded, in order)

1. `RouteCandidate` + `RoutePortfolio` schemas and a
   `scripts/build_route_portfolios_from_primitives.py` that emits the A3/A4/A5
   candidate paths per benchmark task family (manual section 11).
2. `ModelComponent` schema + a bounded one-call-one-primitive LLM generation
   lane (`scripts/run_single_primitive_llm_compile.py`) with the section-22
   prompt contract - the first non-deterministic generation arm, gated by the
   promotion pipeline (manual sections 17, 22).
3. Baseline arms A1/A2 for both lanes - the first measured `tokens_to_pass`
   comparison that lights up `savings_formulas.py` (manual section 14).
4. `implemented_code_primitive` schema + an AST source-miner over `primitives/`
   itself - this repo's own code becomes source-backed candidates (manual
   section 5).
5. Strategy sprout replay (`scripts/run_strategy_sprout_replay.py`) over the
   `strategy_genome` records, champion/challenger on the search ranker (manual
   sections 9, 16).
