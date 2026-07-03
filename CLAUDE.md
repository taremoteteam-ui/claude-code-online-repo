# CLAUDE.md

Repo: Primitive Atlas — a universal catalog of every type of programming
primitive, plus the fully flexible, unlimited-possibility path & runtime
engine(s) (route compiler, decision-portfolio engine, universal search,
deterministic remix/adapters, receipt-driven execution) that search, compose,
choose, and run them under the non-commitment law. Place-discovery/geospatial
was the first lane; any primitive type or decision joins as data, never a
rewrite.

## Read first

- `docs/BIBLE.md` — THE BIBLE (AI Done Right): the single north-star
  reference. If any other doc disagrees with it, the Bible wins — fix or
  archive the other. It references ecosystem assets (Teleon/Baltor/
  OpenHubForAI surfaces, registries, scripts) that live in the wider
  portfolio; treat missing local paths as future build slices, not errors.
- `docs/codex/primitive-atlas-northstar.md` — canonical mission brief and
  operating loop (schemas before data, builders + checkers, manifests,
  candidate/truth boundary).
- `docs/codex/compiled-primitive-routes-handoff.md` — compiled primitive route
  architecture, non-commitment principle, lane branches.
- `docs/codex/place-discovery-geospatial-lane-handoff.md` — this lane's
  playbook.
- `docs/codex/place-discovery-compliance-and-policy.md` — promotion gates,
  license/attribution/privacy boundaries for this lane.
- `docs/codex/document-extraction-lane-handoff.md` — the contract/document
  schema-extraction lane (source-span grounding).
- `docs/codex/coding-agent-lane-handoff.md` — the coding-agent (SWE-bench /
  Terminal-Bench style) and competitive-programming lane: two solve loops that
  compile from typed edges, plus the SLM-uplift benchmark spec.
- `docs/codex/primitive-foundry-operating-manual.md` — the operating manual
  (search/remix/compile/proof/telemetry paths); Appendix A maps each section
  to what already exists in this repo.
- `docs/codex/compiled-primitive-ai-99pct-handoff.md` — the Compiled Primitive
  AI framing and the 99%-programmatic-development coverage claim language.
- `docs/codex/decision-portfolio-substrate.md` — the domain-agnostic
  "store all paths, let data choose" engine (decision points, execution paths,
  receipt ledger, selection policies, self-tuning supervisor) + its generality
  proof. See also `docs/codex/retrieval-architecture-red-team.md` and
  `docs/codex/multi-path-flexible-primitive-architecture.md`.

## Non-negotiable conventions

1. Generated packs come from builder scripts. NEVER hand-edit files under
   `catalog/knowledge-packs/data/` — edit the seed modules in `scripts/seeds/`
   or the builder, then regenerate. The checker's content-hash gate goes red on
   hand-edited pack files.
2. Every generated row is `candidate: true, serves_truth: false`. Nothing in
   this repo promotes truth. Promotion requires source review, proof receipts,
   and the gates in the compliance doc.
3. Counts come from `manifest.json` only — recompute, never type them.
4. Schemas before data: update `schemas/*.schema.json` before changing row
   shapes.
5. No unmeasured performance, savings, or benchmark claims anywhere. Benchmark
   task demands are candidate material; no task here has been run.
6. IDs are stable and version-free; versions live in the `version` metadata
   field.

## Commands

```bash
# Rebuild the pack (single source for all pack files)
python3 scripts/build_place_discovery_geospatial_pack.py --write

# Builder self-test (in-memory build + invariants)
python3 scripts/build_place_discovery_geospatial_pack.py --self-test

# Full pack validation (schemas, hashes, referential integrity, P0 coverage,
# benchmark shape, claim-language gate)
python3 scripts/check_place_discovery_geospatial_pack.py --self-test

# Unit tests for primitive implementations
python3 -m unittest discover -s tests -t . -v

# Benchmark harness: deterministic route replay (arm A4, fixture_offline)
python3 scripts/run_place_discovery_benchmark.py --self-test   # in-memory
python3 scripts/run_place_discovery_benchmark.py --write       # persist run

# Validate a persisted benchmark run (schemas, hashes, honesty gates,
# PlanLock hash recompute, replay-proof requirement on successful A4 tasks)
python3 scripts/check_benchmark_run.py --self-test

# Measured retrieval evaluation: CandidateBundle search vs all 320 task
# demands (question text only; primitive_demands as ground truth)
python3 scripts/evaluate_candidate_search.py --self-test   # print only
python3 scripts/evaluate_candidate_search.py --write       # persist eval

# HONEST cross-lane retrieval eval over the WHOLE capability graph (all 2867
# nodes as distractors; paraphrased intents; lexical vs lexical+typed-edge).
# See docs/codex/retrieval-architecture-red-team.md for why the pack-scoped
# eval above reports 1.0 and this one reports a real floor.
python3 scripts/evaluate_graph_search.py --self-test
python3 scripts/evaluate_graph_search.py --write

# Mine primitive co-occurrence edges from persisted run scorecards
python3 scripts/build_cooccurrence_edges.py --self-test
python3 scripts/build_cooccurrence_edges.py --write

# Core-object schema + example validation
python3 scripts/check_core_object_schemas.py --self-test

# Document-extraction lane: build the (doc_type x field) target lattice,
# validate it (source-span invariant), and run the span-grounded extraction
# benchmark over synthetic contract fixtures
python3 scripts/build_document_extraction_pack.py --write
python3 scripts/check_document_extraction_pack.py --self-test
python3 scripts/run_document_extraction_benchmark.py --self-test
python3 scripts/repair_document_extraction_benchmark.py --check   # ground-truth is extractable

# Universal reusable-primitive catalog: base families x runtime wrappers ->
# resolved primitives (auth/security, crud/trackers, data, integration, devops,
# intelligence, media/vision, coding-agent + competitive-programming + algorithms).
# Never hand-edit pack files; edit scripts/seeds/.
python3 scripts/build_universal_primitive_pack.py --write
python3 scripts/check_universal_primitive_pack.py --self-test

# Warehouse / analytics lane: dbt, dimensional-modeling, data-engineering,
# analytics-pattern, semantic-layer, and multiset (set-algebra) families ->
# resolved primitives; checker enforces the multi-wave topological contract.
python3 scripts/build_warehouse_analytics_pack.py --write
python3 scripts/check_warehouse_analytics_pack.py --self-test

# Type-adapter connector layer: reviewed deterministic bridges FromPort->ToPort
# (backed by real implementations in primitives/type_adapters.py; the checker
# runs each adapter's fixture through its proofs). Registered as capability-graph
# nodes so the compiler inserts them - disclosed as explicit adapter steps.
python3 scripts/build_type_adapters_pack.py --write
python3 scripts/check_type_adapters_pack.py --self-test

# Edge compiler: build the typed capability graph across all lanes (primitives +
# type adapters), then compile primitive chains by edge/type compatibility (zero
# model calls) and measure the compose rate + adapter usage + gap queue
python3 scripts/build_capability_graph.py --write
python3 scripts/run_route_compiler_demo.py --self-test   # print compose rate
python3 scripts/run_route_compiler_demo.py --write       # persist PlanLocks + gaps

# Primitive foundry: the ingestion lifecycle (acquire/scrape -> form -> verify ->
# store -> use), engine-driven and offline over synthetic fixture sources. Forms
# edge-typed mined primitives, license-gates them, and registers verified ones
# into the capability graph so they compose. Edit fixtures/foundry/ not pack files.
python3 scripts/build_foundry_pack.py --write
python3 scripts/check_foundry_pack.py --self-test
python3 scripts/run_foundry_pipeline.py --self-test   # full lifecycle, zero model calls

# Solution frameworks + ordering portfolio + solve loop: reusable typed wiring
# scaffolds; ordering as a portfolio (deterministic compile / framework fill /
# LLM-propose-then-validate); the solve orchestrator wires primitives to solve a
# problem and executes the validated plan. LLM ordering is gated by the
# deterministic route_validator (propose freely, run only if it type-checks).
python3 scripts/build_solution_frameworks_pack.py --write
python3 scripts/check_solution_frameworks_pack.py --self-test
python3 scripts/run_solve_demo.py --self-test

# Decision-portfolio substrate: the domain-agnostic "store all paths, let data
# choose" engine. Build/check the portfolio pack, then the measured generality
# demo (one engine drives retrieval-plane, remix-ladder, and a CI decision).
python3 scripts/build_decision_portfolio_pack.py --write
python3 scripts/check_decision_portfolio_pack.py --self-test
python3 scripts/run_decision_engine_demo.py --self-test   # measured, zero model calls

# Decision graph + frameworks: forks carry state contracts (consumes/produces),
# so decisions compose by edges like primitives do. Build/check a decision
# framework (a reusable typed DAG of forks) and run the wired-plan demo.
python3 scripts/build_decision_frameworks_pack.py --write
python3 scripts/check_decision_frameworks_pack.py --self-test
python3 scripts/run_decision_dag_demo.py --self-test

# Coding-problem primitive mining: harvest synthetic LeetCode/competitive/
# interview/hackathon problems, SOLVE them with real code composed from working
# algorithmic kernels, decompose + store, and measure reuse (few kernels covering
# many problems). The checker re-runs every kernel self-test and every solution
# against its fixtures. See docs/codex/coding-problem-primitive-mining.md.
python3 scripts/build_coding_primitive_pack.py --write
python3 scripts/check_coding_primitive_pack.py --self-test
python3 scripts/run_coding_primitive_pipeline.py --self-test

# Off-policy policy selection: replay a logged full-feedback history through
# every selection policy (via the real engine), let the data pick the lowest-
# regret one, and verify the pick on a held-out log. The non-commitment law
# applied to the policy itself. See docs/codex/policy-selection-off-policy.md.
python3 scripts/run_policy_selection_benchmark.py --self-test

# Off-policy evaluation: estimate a target policy's value from PARTIAL-feedback
# logs of a different behavior policy (IPS / SNIPS / DM / doubly-robust), checked
# against the known true value. Shows DR stays unbiased under a misspecified
# reward model. Closes the full-feedback caveat above. See
# docs/codex/off-policy-evaluation.md.
python3 scripts/run_off_policy_evaluation_benchmark.py --self-test

# Verify-the-verifier gates: build twice byte-identically (determinism), inject
# real defects and confirm the catching gate goes red (mutation), and fail on
# silent regression of measured headline metrics (quality ratchet). Re-record the
# ratchet floor with --update after an intended improvement.
python3 scripts/check_determinism.py --self-test
python3 scripts/mutation_test.py --self-test
python3 scripts/check_quality_ratchet.py --self-test

# Everything at once (CI runs this on every push)
python3 scripts/run_proofs.py
```

Run `scripts/run_proofs.py` before claiming success or committing changes.

## Layout

```text
docs/codex/           mission briefs and lane handoffs
schemas/              JSON schemas (contracts for pack rows, receipts, scorecards)
scripts/              builders + checkers + benchmark harness + proof runner
scripts/seeds/        pure-data seed modules (the only place to edit content)
primitives/           WORKING P0 primitive implementations (stdlib only);
                      every execution goes through primitives/core.py and
                      emits an ExecutionReceipt
primitives/adapters/  source adapters with injectable transports
                      (FixtureTransport offline / LiveTransport when network
                      policy allows)
fixtures/place-discovery/
                      SYNTHETIC fixtures shaped like the real APIs - every
                      file is labeled fixture_synthetic and adapters propagate
                      retrieved_mode into evidence bundles
tests/                unittest contract tests for all implementations
benchmarks/runs/      measured benchmark runs (scorecards, receipts, gap
                      records, artifacts, computed manifest)
catalog/knowledge-packs/data/place-discovery-geospatial-seeds/
                      generated pack: source surfaces, primitive cards,
                      groups, overlays, benchmark task demands, manifest
```

## Benchmark honesty rules

- Only arms that actually ran get scorecards; baselines are never simulated.
- Fixture-mode runs measure route machinery, not real-world data accuracy -
  every scorecard and evidence bundle discloses this.
- `runtime_llm_tokens` on arm A4 is 0 because no model runs; the run checker
  enforces this. No token-savings claim can be made until baseline arms run.
- Families that cannot run emit GapRecords instead of fake scorecards.
