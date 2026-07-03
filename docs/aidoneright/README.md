# AIDoneRight — standards hub

The single index of the rules every AIDoneRight project and system follows. Each
standard is a **candidate standard** with a working reference implementation and a
proof in this repo; a new project starts from the template
(`templates/aidoneright-project-template/`) and adopts these.

> If any project doc disagrees with a standard, the standard wins — fix or archive
> the offender. If a standard disagrees with `docs/BIBLE.md`, the Bible wins.

## The standards

| # | Standard | Reference impl | Proof |
|---|----------|----------------|-------|
| **000** | **The Invariants** (below) | schemas + checkers | every pack checker |
| **001** | [Globally Unique Variable Names & deterministic tracing](globally-unique-naming-and-tracing.md) | `primitives/guvn.py` | `scripts/build_code_map.py`, `tests/test_guvn.py` |
| **002** | [Multiple-Path Development](multiple-path-development.md) | `primitives/multipath.py` | `scripts/run_multipath_demo.py`, `tests/test_multipath.py` |
| **003** | [Verify the verifier](#standard-003--verify-the-verifier) | determinism + mutation + ratchet gates | `scripts/check_determinism.py`, `scripts/mutation_test.py`, `scripts/check_quality_ratchet.py` |
| **004** | [Project transfer / operating manual](../codex/project-transfer-context.md) | the `CONTEXT.md` template | the migration playbook |

## Standard 000 — The Invariants

The non-negotiable laws. Every generated row, every claim, every file obeys these.

1. **Candidate by default.** Every generated/derived row is
   `candidate: true, serves_truth: false`. Nothing promotes itself; promotion is a
   gated, reviewed, receipt-backed event.
2. **No unmeasured claims.** No performance/accuracy/savings number unless a run
   produced it. Fixture runs disclose that they measure machinery, not real-world
   accuracy. If you can't measure it, say "unmeasured" or emit a gap record.
3. **Schemas before data.** Change the JSON Schema before changing any row shape.
4. **Builders, not hand-edits.** Generated files come from builder scripts over
   pure-data seeds; a content-hash gate catches hand-edits. Counts come from a
   computed `manifest.json` only.
5. **Stable, version-free IDs.** Versions live in a `version` field, never in the id.
6. **Receipts are the only memory.** Every execution/decision emits a receipt; the
   system learns only from receipts.
7. **Typed, gated effects.** Each unit declares its effects; each effect carries a
   proof obligation that must be met before it is use-ready.

## Standard 003 — Verify the verifier

A green suite proves nothing unless the suite has teeth. Three meta-gates, run by
the umbrella `run_proofs`:

- **Determinism gate** — build twice, assert byte-identical output.
- **Mutation testing** — inject a real defect into each load-bearing module and
  confirm the gate that should catch it goes red. A surviving mutant is a reported
  hole.
- **Quality ratchet** — record each measured headline metric as a floor; fail on
  silent regression.

Two traps this org hit and will not repeat:
1. **Never seed a reproducible harness with `hash()`** — it is salted per process;
   use an explicit stable seed.
2. **Any harness that edits-then-restores source must run children with
   `PYTHONDONTWRITEBYTECODE=1` and purge `__pycache__`** — or a stale `.pyc` from
   mutated source poisons later runs.

## Definition of done

**A subsystem is done when** its behavior is pinned by tests; it flows through a
receipt-emitting unit; its seams are GUNs and a real request compiles/serves;
every former hardcoded choice with >1 reasonable path is an MPD portfolio (or a
runtime decision point); a mutant in its core logic is caught; and its headline
metric has a ratchet floor.

**A PR is ready when** `run_proofs` is green; new row shapes have schemas;
generated files were regenerated (not hand-edited); no unmeasured claim was added;
every new row carries the candidate/truth boundary; and the code map + standards
still lint clean.

## Starting a new project

Copy `templates/aidoneright-project-template/` to the new repo root and follow its
`README.md`. Migrating an existing project instead? Use Standard 004 — the phased
`CONTEXT.md` playbook (`docs/codex/project-transfer-context.md`).
