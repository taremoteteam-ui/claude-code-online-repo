# CLAUDE.md — agent instructions (project template)

Repo: <one-line description of this project>. Built to the AIDoneRight standards
(`STANDARDS.md`): a catalog of typed primitives plus a flexible path/runtime engine
that stores every viable path, commits to none, and lets measured receipts choose.

## Read first

- `STANDARDS.md` — the non-negotiable rules (Invariants, GUVN, MPD, verify-the-verifier).
- `CONTEXT.md` — the operating manual + the living status ledger (edit every session).

## Non-negotiable conventions

1. Generated packs come from builder scripts. NEVER hand-edit generated files; edit
   the seed modules in `scripts/seeds/` or the builder, then regenerate. A
   content-hash gate goes red on hand-edits.
2. Every generated row is `candidate: true, serves_truth: false`. Nothing promotes
   truth without source review + proof receipts.
3. Counts come from `manifest.json` only — recompute, never type them.
4. Schemas before data: update `schemas/*.schema.json` before changing row shapes.
5. No unmeasured performance/savings/accuracy claims anywhere.
6. IDs are stable and version-free; versions live in the `version` field.
7. Names are Globally Unique (Standard 001); where >1 reasonable path exists, use a
   Multiple-Path Development portfolio (Standard 002), not an `if`.

## Commands

```bash
# Everything at once (CI runs this on every push)
python3 scripts/run_proofs.py

# Build the code map from GUVN declarations (once you have annotated units)
python3 scripts/build_code_map.py --self-test

# Verify-the-verifier gates (add modules/metrics as the project grows)
python3 scripts/check_determinism.py --self-test
python3 scripts/mutation_test.py --self-test
python3 scripts/check_quality_ratchet.py --self-test
```

Run `scripts/run_proofs.py` before claiming success or committing.

## Layout

```text
schemas/        JSON schemas (contracts)
scripts/        builders + checkers + proof runner
scripts/seeds/  pure-data seed modules (the only place to edit content)
primitives/     implementations; every run emits a receipt
tests/          contract tests
```
