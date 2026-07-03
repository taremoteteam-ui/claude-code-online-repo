# CONTEXT.md — operating manual (project template)

The living operating manual for this project. `CLAUDE.md` says how an agent should
behave here; this says what we are building and where we are on the path. Edit the
Status Ledger every working session.

## Thesis

Store every viable path, commit to none, let measured receipts choose, then verify
the verifier. Two pillars: a **catalog** of typed primitives (connected by
Globally Unique Names) and an **engine** that compiles, chooses, runs, and learns
from receipts. Three laws: the non-commitment law, the candidate/truth boundary,
and verify-the-verifier. See `STANDARDS.md`.

## Build order (each phase ships value; keep `run_proofs` green throughout)

1. **Schemas & boundary** — schemas for core records; stamp every row candidate.
2. **Name the seams** — Globally Unique Names for boundary artifacts (Standard 001);
   render the first code map.
3. **Wrap, don't rewrite** — units that emit receipts around existing code.
4. **Type & compile** — register units; serve a real request via a compiled route.
5. **De-hardcode** — turn each multi-answer choice into an MPD portfolio (Standard
   002) or a runtime decision point; default to current behavior.
6. **Receipts & telemetry** — persist decision receipts; add a supervisor.
7. **Verify the verifier** — determinism, mutation, ratchet (Standard 003).

## Status ledger (edit me)

### Subsystems
| Subsystem | Owner | Named (GUN) | Wrapped | Typed/compiles | De-hardcoded | Receipts |
|-----------|-------|-------------|---------|----------------|--------------|----------|
| _example_ | | ☐ | ☐ | ☐ | ☐ | ☐ |

### Multi-answer choices (MPD / decision-point backlog)
| Choice | Current default | Candidate paths | Portfolio / decision id | Status |
|--------|-----------------|-----------------|-------------------------|--------|

### Decision log
| Date | Decision | Rationale | Reversible? |
|------|----------|-----------|-------------|

## Traps (do not repeat)

- Data artifact named like config (`...Spec/...Policy`) won't chain as a required
  input — name data ports as nouns.
- Bucket-widening to force a type match loses information — insert an explicit
  adapter instead.
- Hand-editing generated files — always red on the content-hash gate.
- Seeding a reproducible harness with `hash()` — salted per process; use a stable seed.
- Edit-then-restore harness without `PYTHONDONTWRITEBYTECODE=1` — a stale `.pyc`
  poisons later runs.
