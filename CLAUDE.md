# CLAUDE.md

Repo: Primitive Atlas — place-discovery-geospatial lane (first build slice of
the proof-aware primitive route market).

## Read first

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
```

Run both self-tests before claiming success or committing pack changes.

## Layout

```text
docs/codex/           mission briefs and lane handoffs
schemas/              JSON schemas (contracts for all pack rows)
scripts/              builder + checker (generated-pack pattern)
scripts/seeds/        pure-data seed modules (the only place to edit content)
catalog/knowledge-packs/data/place-discovery-geospatial-seeds/
                      generated pack: source surfaces, primitive cards,
                      groups, overlays, benchmark task demands, manifest
```
