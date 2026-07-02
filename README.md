# Primitive Atlas — Place Discovery / Geospatial Lane

First build slice of the **proof-aware primitive route market** described in
[`docs/codex/primitive-atlas-northstar.md`](docs/codex/primitive-atlas-northstar.md):
a generated, schema-validated seed pack for the place / facility / open-data /
geospatial primitive lane — clinic and training-provider discovery, open-map
enrichment, open-government portal harvesting, and spatial analysis.

Core sentence:

```text
Search first. Reuse first. Remix deterministically. Generate only the missing
edge. Prove every route. Promote only after receipts. Remember failures as
negative memory.
```

## Status

Everything in this repo is **candidate seed material**:

```json
{ "candidate": true, "serves_truth": false }
```

No primitive here is implemented, promoted, or benchmarked yet. No metric in
this repo is measured. Benchmark task demands are generated candidate tasks —
no arm has been run and no scorecard value exists.

## What is here

| Area | Contents |
| --- | --- |
| `docs/codex/` | North-star mission brief, compiled-primitive-routes handoff, lane playbook, compliance/policy pack |
| `schemas/` | JSON schemas for source surfaces, primitive cards, primitive groups, variation overlays, benchmark task demands, and the pack manifest |
| `scripts/seeds/` | Pure-data seed modules — the only place lane content is edited |
| `scripts/` | Builder and checker for the generated pack |
| `catalog/knowledge-packs/data/place-discovery-geospatial-seeds/` | The generated pack (JSONL + `manifest.json`) |

The lane's canonical visible edge:

```text
AreaOfInterest+DirectedQuestion+SourcePolicy+ExtractionSchema
  -> EvidenceBackedAnswer+SourceBundle+SpatialArtifacts+UncertaintyReport
```

The pack covers five source lanes (health facilities, workforce/training, open
maps, open-data portals, geospatial analysis tooling), the 18-primitive P0
build order, primitive groups, variation overlays, and generated benchmark
task demands (8 task families x 40 areas of interest). Row counts and hashes
live in the pack `manifest.json` — recompute from it, never type them.

## Commands

```bash
python3 scripts/build_place_discovery_geospatial_pack.py --self-test
python3 scripts/build_place_discovery_geospatial_pack.py --write
python3 scripts/check_place_discovery_geospatial_pack.py --self-test
```

The builder is the single source for every pack file. Never hand-edit files
under `catalog/knowledge-packs/data/` — the checker's content-hash gate fails
on hand-edited generated files.

## Hard boundaries for this lane

- Directory / access / planning outputs only — never patient-level data, never
  diagnosis or treatment advice, never final legal or compliance conclusions.
- Respect source usage policies (e.g. public Nominatim/Overpass endpoints) and
  attribution requirements (e.g. OSM ODbL). Scaled use must self-host or use
  bulk extracts.
- Every ingest records license status, attribution, and a source snapshot
  receipt; every spatial analysis records a method receipt.

See [`docs/codex/place-discovery-compliance-and-policy.md`](docs/codex/place-discovery-compliance-and-policy.md)
for the full promotion gates.

## Next build slices

1. Live source capture: run the adapters through `LiveTransport` in a
   network-enabled environment to replace synthetic fixtures with real source
   snapshots (receipts flip from `fixture_offline` to `live_network`).
2. Baseline arms: wire A1/A2 model-in-the-loop runs so the first measured
   `tokens_to_pass` comparison exists — until then no savings claim is made.
3. Promotion pipeline: first held-out promotion gate run over the implemented
   primitives (L9 -> L10 with receipts), per the compliance doc.
4. PDU/packaging slice: runtime wrappers + package factories for the
   highest-reuse groups (Operations Bible section 9).
