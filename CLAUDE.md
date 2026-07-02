# CLAUDE.md

Repo: Primitive Atlas — place-discovery-geospatial lane (first build slice of
the proof-aware primitive route market).

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
