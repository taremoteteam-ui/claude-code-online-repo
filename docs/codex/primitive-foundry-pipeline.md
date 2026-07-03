# The primitive-foundry pipeline: scrape → form → store → use, engine-driven

Last updated: 2026-07-03. The implemented ingestion lifecycle that turns a source
into edge-typed, verified, composable primitives — the working first slice of
`docs/codex/repo-mining-factory-spec.md` and `docs/codex/primitive-foundry-
operating-manual.md`, wired to the flexible decision engine.

## What it covers (the full lifecycle, in code) — capabilities per stage

| Stage | Code | Capabilities |
| --- | --- | --- |
| **Acquire (scrape)** | `foundry.py:acquire` + `decision:ingest.acquire_strategy` | engine-chosen acquisition path from a portfolio; **secret scan** (AWS/GitHub/private-key/`api_key=` patterns → promotion blocker); **vendored/generated exclusion**; snapshot + receipt disclosing `retrieved_mode`, `symbols_kept`, `excluded_symbols`, `secret_findings` |
| **Form (ingest)** | `foundry.py:form` | edge-types each signature to the shared vocabulary; resolves **port roles** (required-data vs request-config vs outputs) via `primitives/edges.py`; carries a **`handler_ref`** when the source ships one; runs the **license gate**; dedupes by contract+symbol |
| **Verify** | `foundry.py:verify` | a check **ladder** → `unverified` / `fixture_verified` (edges parse, an output *data* port exists, every effect has a proof obligation, license permissive) / **`fixture_executable`** (all that **and** a resolvable handler — proven to actually transform its input edge into its output edge) / `license_blocked` |
| **Store** | `build_foundry_pack.py` + `schemas/mined_primitive.schema.json` | writes the pack (manifest + content hash); the checker re-derives every verification status and the license-gate coherence so nothing is hand-tuned |
| **Use** | `build_capability_graph.py` + `route_compiler.py` + **`route_runtime.py`** + `graph_search.py` | only verified/executable primitives enter the graph; USE then **retrieves** them by intent, measures **compose-lift** (targets that compile only because the source exists), emits a **PlanLock**, and **executes** the route for real — one `ExecutionReceipt` per step |

## The measured proof (offline, zero model calls)

`scripts/run_foundry_pipeline.py --self-test` runs all five stages over the
synthetic fixture sources:

```text
ACQUIRE  engine chose path:ingest.cached_snapshot; retrieved_mode=fixture_synthetic;
         _vendored_shim EXCLUDED; secret scan clean
FORM     5 mined primitives (edge-typed, port-roled, license-gated)
VERIFY   3 fixture_executable (handler-backed) + 1 fixture_verified (fetch_tiles,
         network effect, no handler) + 1 license_blocked (GPL source)
STORE    only the verified/executable enter the composable graph
USE      retrieve: intent "parse a geojson document..." -> mined parse_geojson,
                   features_to_records
         compose-lift: 3/3 targets unlocked ONLY by the foundry lane (measured
                   by compiling WITH vs WITHOUT it)
         planlock: GeoJsonDocument -> RowSet, route_hash sha256:b1bc..., 3 mined steps
         execute:  RAN the route on a fixture GeoJSON -> a real 2-row table
                   {columns: [kind,lat,lon,name]}, 3 ExecutionReceipts, effects={none}
```

A freshly-formed mined primitive is **retrieved, composed, and actually run** —
producing a real artifact with a receipt trail — purely from its typed edges.
That is the whole thesis, end to end, on primitives that did not exist before
this run.

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
