# AIDoneRight standards (project copy)

The rules this project follows. Keep this file short and current. The canonical,
fuller versions live in the AIDoneRight standards hub; this is the project's copy
of the contract.

## 000 — The Invariants (non-negotiable)

1. **Candidate by default** — every generated/derived row is
   `candidate: true, serves_truth: false`; promotion is gated, reviewed, receipt-backed.
2. **No unmeasured claims** — no performance/accuracy/savings number without a run;
   fixtures disclose they measure machinery, not real-world accuracy.
3. **Schemas before data** — change the schema before any row shape.
4. **Builders, not hand-edits** — generated files come from builders over seeds; a
   content-hash gate catches hand-edits; counts come from `manifest.json`.
5. **Stable, version-free IDs** — versions live in a `version` field.
6. **Receipts are the only memory** — every execution/decision emits a receipt.
7. **Typed, gated effects** — each unit declares effects; each effect has a proof
   obligation met before use.

## 001 — Globally Unique Variable Names (GUVN)

Every meaningful artifact has a globally unique name; the code map is name-matching.
Grammar `<lane>.<component>.<artifact>[.<qualifier>]` (lowercase snake, ≥2 segments,
version-free). A name means one thing; a name is a unit or an artifact, never both;
two producers of the same name must be substitutable (a multi-path artifact).
Declare units with `@unit(...)`; build the map with the tracer; lint on every push.

## 002 — Multiple-Path Development (MPD)

Where >1 reasonable path exists, build them all behind one contract, benchmark,
let the data choose, keep the rest as an ordered fallback. No decision by argument;
decide by scorecard. A crash is a measured failure; a fallback is always visible.
Graduate a portfolio to a runtime decision point when the best path is
context-dependent.

## 003 — Verify the verifier

`run_proofs` runs, beyond ordinary tests: a **determinism gate** (build twice,
byte-identical), **mutation testing** (inject a defect, confirm the gate reddens),
and a **quality ratchet** (measured metrics have floors). Never seed a reproducible
harness with `hash()`; any edit-then-restore harness runs with
`PYTHONDONTWRITEBYTECODE=1` and purges `__pycache__`.

## Definition of done

Subsystem: behavior pinned by tests; flows through a receipt-emitting unit; seams
are GUNs; every multi-answer choice is an MPD portfolio or decision point; a mutant
in core logic is caught; headline metric has a ratchet floor.
PR: `run_proofs` green; new shapes have schemas; generated files regenerated; no
unmeasured claim; every new row carries the candidate/truth boundary.
