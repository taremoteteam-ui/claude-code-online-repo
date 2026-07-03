# AIDoneRight Standard 001 — Globally Unique Variable Names & deterministic tracing

Status: **candidate standard** · Reference impl: `primitives/guvn.py` ·
Tracer: `scripts/build_code_map.py` · Tests: `tests/test_guvn.py`

## Why

If every meaningful data artifact has a **globally unique name (GUN)**, the
data-flow map of the whole system is just **name matching** — the artifact
produced under name `N` and the artifact consumed under name `N` are the same
thing, everywhere, in any file or language. No type inference, no call-graph
reconstruction, no heuristics. The names *are* the edges. That makes a
whole-repo **code map** cheap to build, stable to diff, and deterministic — which
is exactly what an AI-driven codebase needs to reason about itself.

This standard generalizes the typed-port model (`primitives/edges.py`, where
primitives connect by port name) from primitive boundaries to **every named
artifact**.

## The law

1. **Global uniqueness.** A GUN denotes exactly one artifact *semantics*
   system-wide. If two things mean different things, they get different names.
2. **Grammar.** `<lane>.<component>.<artifact>[.<qualifier>...]` — lowercase
   snake segments, dot-separated, **at least two segments**. Version-free; the
   version lives in metadata, never in the name (so references never rot).
   Regex: `^[a-z][a-z0-9]*(_[a-z0-9]+)*(\.[a-z][a-z0-9]*(_[a-z0-9]+)*){1,}$`.
3. **A name is a unit or an artifact, never both.** A unit (function/step/
   service) has its own GUN; the artifacts it consumes/produces have theirs.
4. **Same name ⇒ same contract.** Two units may *produce* the same GUN only when
   they emit the same substitutable artifact. That is not a collision — it is a
   **multi-path artifact** (Standard 002), and the tracer flags it for review that
   the producers really are interchangeable.

## Declaring units

A unit declares its wiring with GUNs; the tracer never reads the body:

```python
from primitives.guvn import unit

@unit("geo.transform.features_to_records",
      consumes=["geo.features.point_feature_collection"],
      produces=["geo.records.entity_record_set"],
      effects=["none"])
def features_to_records(fc): ...
```

## The tracer

`build_code_map(units)` produces a deterministic map:

- **nodes** = every unit GUN + every artifact GUN;
- **edges** = `artifact → unit` (consume) and `unit → artifact` (produce);
- **classification** of each artifact: `source` (external input, never produced),
  `sink` (terminal output, never consumed), `internal` (both), `multi_path`
  (produced by >1 unit);
- a **content hash** so the map diffs cleanly and can gate a content-hash check.

`lint(units)` reports law violations — invalid grammar, a name used as both a
unit and an artifact, a duplicate unit GUN — and surfaces multi-path artifacts as
review items. `render_mermaid(code_map)` emits a diagram.

Run it: `python3 scripts/build_code_map.py --self-test` traces the annotated
fixture (`fixtures/guvn/sample_pipeline.py`) — 5 units, 7 artifacts, 3 sources, 1
sink, and correctly flags `geo.records.entity_record_set` as multi-path (a GeoJSON
path and a CSV path emit the same contract). `--write` persists the JSON map and
the Mermaid rendering under `benchmarks/code_maps/`.

## Adoption (incremental, non-invasive)

1. Name the artifacts at your subsystem boundaries first (they become GUNs); the
   internals can follow.
2. Decorate the boundary units with `@unit(...)`.
3. Add `build_code_map --self-test` to your proof suite so the map is regenerated
   and linted on every push; the content hash catches an un-declared rewire.
4. Extend inward one component at a time. A partially-annotated repo still yields
   a valid (partial) map — sources are just the not-yet-annotated inputs.

## Determinism & honesty

The map is a pure function of the declarations: sorted nodes/edges, a content
hash, no wall-clock or hash-seed nondeterminism. The map is `candidate` structural
truth about the code, not a claim about behavior; it says how artifacts are wired,
not that any unit is correct.
