# The primitive-foundry pipeline: scrape → form → store → use, engine-driven

Last updated: 2026-07-03. The implemented ingestion lifecycle that turns a source
into edge-typed, verified, composable primitives — the working first slice of
`docs/codex/repo-mining-factory-spec.md` and `docs/codex/primitive-foundry-
operating-manual.md`, wired to the flexible decision engine.

## What it covers (the full lifecycle, in code)

| Stage | Code | What it does |
| --- | --- | --- |
| **Acquire (scrape)** | `primitives/foundry.py:acquire` + `decision:ingest.acquire_strategy` | the decision engine picks an acquisition path from a portfolio (`cached_snapshot → structured_api → ast_parse → …`); `acquire()` reads the source and emits a snapshot + receipt disclosing `retrieved_mode` |
| **Form (ingest)** | `primitives/foundry.py:form` | edge-types each mined signature to the shared port vocabulary (`primitives/edges.py`) → a `mined_primitive` card; runs the **license gate** (non-permissive → `license_blocked` promotion blocker) |
| **Verify** | `primitives/foundry.py:verify` | use-readiness gate: edges parse to real ports, effects valid, license permissive → flips `verification_status` to `fixture_verified` |
| **Store** | `scripts/build_foundry_pack.py` + `schemas/mined_primitive.schema.json` | writes the `foundry-mined-primitives/` pack (manifest + content hash); the checker re-derives every verification status so none can be hand-tuned |
| **Use** | `scripts/build_capability_graph.py` (foundry source) + route compiler | only `fixture_verified` mined primitives enter the capability graph; the compiler then chains them like any other node |

## The measured proof (offline, zero model calls)

`scripts/run_foundry_pipeline.py --self-test` runs all five stages over the
synthetic fixture sources:

```text
ACQUIRE  engine chose path:ingest.cached_snapshot; retrieved_mode=fixture_synthetic
FORM     5 mined primitives across 2 sources
VERIFY   4 fixture_verified (MIT source) + 1 license_blocked (GPL source)
STORE    only the 4 verified enter the composable graph
USE      GeoJsonDocument -> RowSet compiles in 3 MINED steps:
           mined:geoutils_fixture.parse_geojson      -> PointFeatureCollection
           mined:geoutils_fixture.features_to_records -> EntityRecordSet
           mined:geoutils_fixture.records_to_rows     -> RowSet
```

A mined primitive composes with the seeded bank purely from its typed edges — no
one read its body. That is the whole thesis, demonstrated on freshly-formed
primitives.

## Honesty & boundaries

- **Offline / synthetic.** This workspace has restricted outbound network, so
  acquisition runs against `fixtures/foundry/*.json` (labeled
  `fixture_synthetic`). Live mining runs where the network policy allows; the
  acquisition portfolio just swaps `cached_snapshot` for a live rung and the
  receipt flips `retrieved_mode` to `live_network`.
- **Candidate only.** Every mined primitive is `candidate=true /
  serves_truth=false`. It becomes source-backed when a live source ref + import-
  smoke/behavior receipts attach — the operating manual's L4→L7 path.
- **License gate is never bypassed.** A non-permissive source's primitives are
  stored as `license_blocked` with a promotion blocker and are excluded from the
  composable graph. The checker enforces the gate is coherent and recomputable.
- **Engine-driven, not hardcoded.** The acquisition strategy is a
  `DecisionPoint` (portfolio + policy), so adding a new acquisition rung is a
  data row — the non-commitment law applied to ingestion.

## Commands

```bash
python3 scripts/build_foundry_pack.py --write        # acquire->form->verify->store
python3 scripts/check_foundry_pack.py --self-test    # license gate + verification recompute
python3 scripts/run_foundry_pipeline.py --self-test  # full lifecycle, engine-driven
```

## Next build slices

1. A real AST miner (`ast`/tree-sitter) behind the `ast_parse` acquisition path,
   runnable in a network-enabled environment, feeding real signatures into
   `form()`.
2. Import-smoke + fixture-behavior verification that earns real receipts (moving
   a mined primitive from `fixture_verified` to source-backed).
3. A per-source compose-rate lift metric (how many new routes a mined source
   unlocks) — the signal that says a source was worth mining.
