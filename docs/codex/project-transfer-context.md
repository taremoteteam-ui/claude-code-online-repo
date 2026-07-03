# CONTEXT.md — migrating a large project onto the Primitive Atlas architecture

> **How to use this file.** Copy it to the ROOT of the project you are migrating,
> as `CONTEXT.md`. It is the operating manual for the migration — for humans and
> for coding agents. It is a *living* document: the Status Ledger (§7) is meant to
> be edited every working session. `CLAUDE.md` tells an agent *how to behave in
> this repo*; `CONTEXT.md` tells everyone *what we are building toward and where we
> are on the path*. Keep them both short enough to be read in full.

---

## 1. The thesis in 60 seconds

You are moving a codebase from **"one hardwired way to do each thing"** to **"store
every viable way as data, commit to none, and let measured receipts choose at
runtime."** Two pillars:

- **The catalog** — every reusable capability is a *primitive* with **typed input
  and output ports**, so capabilities compose by type-compatibility instead of by
  prose or tribal knowledge.
- **The engine** — a *route compiler* chains primitives by their ports (zero model
  calls), a *decision portfolio* stores competing strategies behind each choice, and
  a *receipt ledger* is the only memory the system learns from.

Three laws sit over all of it: **the non-commitment law** (never hardwire a choice
where several are viable), **the candidate/truth boundary** (nothing is trusted
until proven), and **verify the verifier** (a green suite proves nothing unless the
suite itself is shown to have teeth).

Migration is **strangler-fig, never rewrite**: you *wrap* existing code as
primitives and route around it, replacing internals later. The app keeps working
the whole way.

---

## 2. Non-negotiable invariants (the laws)

| # | Invariant | Why | How to enforce |
|---|-----------|-----|----------------|
| 1 | **Candidate by default.** Every generated/derived row is `candidate: true, serves_truth: false`. Nothing promotes itself. | Lets you generate aggressively without ever lying. | A checker gate rejects any row missing the boundary; promotion needs review + proof receipts. |
| 2 | **No unmeasured claims.** No performance/accuracy/savings number appears unless a run produced it. | Every other number stays trustworthy. | A claim-language regex gate over all generated text; fixture runs disclose "measures machinery, not real-world accuracy". |
| 3 | **Schemas before data.** Change the JSON Schema before changing any row shape. | Contracts lead; data follows. | Rows validate against `schemas/*.schema.json` in the checker. |
| 4 | **Builders, not hand-edits.** Generated files come from builder scripts over pure-data seeds; never hand-edit generated output. | The corpus rebuilds byte-identically from source. | Content-hash gate goes red on hand-edits; counts come from a computed `manifest.json` only. |
| 5 | **Stable, version-free IDs.** Versions live in a `version` field, not in the id. | References never rot across versions. | ID pattern in schema; referential-integrity checks. |
| 6 | **Receipts are the only memory.** Every execution/decision emits a receipt; the system learns only from receipts. | Replayable, auditable, honest about what it has observed. | Every run goes through one execution wrapper that emits a receipt. |
| 7 | **Effects are typed and gated.** Each primitive declares its effects; each effect carries a proof obligation. | No unsafe/unproven side effects sneak in. | Verify step refuses to mark use-ready if an obligation is unmet. |

If any doc, comment, or row disagrees with these, the invariant wins — fix or
archive the offender.

---

## 3. Map your project's concepts onto the abstractions

Do this mapping FIRST, on paper, before touching code. Fill the right column with
your project's real names.

| Atlas abstraction | What it is | Your project's version |
|-------------------|-----------|------------------------|
| **Primitive** | a reusable capability with typed ports + a proof | functions, service endpoints, tools, jobs |
| **Typed port / edge** | the named type on a primitive's input/output | your DTOs, schemas, message shapes |
| **Config port** | request-supplied settings (suffix `Policy/Spec/Config/Options/Settings`) | flags, options objects, tuning params |
| **Receipt port** | an evidence artifact (suffix `Receipt/Report/Verdict/Digest`) | logs, audit records, run metadata |
| **Adapter** | a reviewed deterministic `FromPort→ToPort` bridge, as its own node | your glue/mapper/coercion functions |
| **Route / PlanLock** | a compiled, hash-pinned chain of primitives | a hardcoded pipeline or call sequence |
| **Decision point** | a portfolio of substitutable strategies behind one choice | every `if strategy == ...` / feature flag / A-B branch |
| **Execution path** | one strategy in a decision point's portfolio | each branch of that `if` |
| **Selection policy** | how the data picks a path (cost + decayed receipts) | your heuristic / hardcoded default |
| **Gap record** | an honest "cannot do this yet", never a fake success | swallowed exceptions, silent fallbacks |

The single most valuable move is finding your **hardcoded strategy choices**
(embedding model, retrieval method, ranking heuristic, cache policy, retry policy,
CI gate order) and turning each into a decision point. That is where the
non-commitment law pays off.

---

## 4. Repo layout to adopt

```text
schemas/            JSON schemas — the contracts; edited before any row shape
scripts/            builders + checkers + benchmark harness + proof runner
scripts/seeds/      pure-data seed modules — the ONLY place to edit content
primitives/         working primitive implementations; every run emits a receipt
primitives/adapters/ source/transport adapters (fixture offline / live when allowed)
fixtures/           synthetic fixtures shaped like real sources, labeled synthetic
catalog/.../data/   GENERATED packs (never hand-edited): cards, groups, manifest
tests/              contract tests for every implementation
benchmarks/runs/    measured runs (scorecards, receipts, gap records, manifest)
docs/codex/         mission briefs + lane handoffs (this file lives here or at root)
```

---

## 5. The migration playbook (phased — each phase ships value)

Run these in order. Each has an **exit gate**; do not start the next phase until the
current one's gate is green in CI. A "lane" = one subsystem you migrate end-to-end.

**Phase 0 — Inventory & baseline.**
Enumerate subsystems, their public entry points, and every hardcoded strategy
choice. Capture current behavior as characterization tests (golden outputs) so you
can prove you did not change behavior while wrapping. *Exit:* a Status Ledger (§7)
listing every subsystem with an owner and a "current behavior pinned" checkbox.

**Phase 1 — Schemas & the candidate/truth boundary.**
Write schemas for your core row/record types. Stamp every generated/derived record
with `candidate/serves_truth`. Stand up an empty `run_proofs` umbrella that runs the
schema checker. *Exit:* `run_proofs` green on an empty catalog; boundary enforced.

**Phase 2 — Wrap, don't rewrite (strangler-fig).**
Pick one subsystem. Wrap its existing entry points as primitives that emit receipts —
*call the old code inside*. Nothing is reimplemented yet. Characterization tests
still pass. *Exit:* the subsystem's public behavior is unchanged but now flows
through the receipt-emitting wrapper.

**Phase 3 — Type the seams.**
Give those primitives explicit input/output ports; register them on a capability
graph; compile a route for a real request instead of calling a hardcoded sequence.
Where two seams almost match, insert a reviewed **adapter** node (never widen types
to force a match). *Exit:* at least one real request is served by a compiled
PlanLock; the compose rate is measured.

**Phase 4 — De-hardcode (the non-commitment law).**
Take one hardcoded strategy choice and make it a decision point with ≥2 paths and a
selection policy that returns a *disclosed ranking*. Default to the old behavior so
nothing changes until receipts say otherwise. *Exit:* the choice is data; adding a
strategy is a new row, not a code change.

**Phase 5 — Receipts & telemetry.**
Persist decision receipts to a ledger (in-memory → JSONL → DB as you scale). Add a
supervisor that reads the ledger and recommends promote/retire/reopen. *Exit:* the
system can answer "which path is winning, and why" from data alone.

**Phase 6 — Verify the verifier.**
Add the three meta-gates (§6). *Exit:* mutation testing kills injected defects; the
determinism gate is green; the quality ratchet has a recorded floor.

**Phase 7 — Measure & ratchet, then repeat.**
Record headline metrics (compose rate, win-rate, coverage) as ratchet floors and
move to the next subsystem. *Exit:* a new lane cannot silently regress a shipped
one.

---

## 6. Verification discipline (the proof suite)

One umbrella command runs everything and exits non-zero if any stage fails:
`python3 scripts/run_proofs.py`. Wire it into CI on every push. Beyond ordinary
tests, three meta-gates keep the suite honest:

- **Determinism gate** — build each pack twice, assert byte-identical output.
  Catches hidden dict/set-order and timestamp nondeterminism before it flakes a
  hash gate.
- **Mutation testing** — inject a real defect into a core module and confirm the
  gate that *should* catch it goes red. A surviving mutant is a reported hole. Add
  a mutant for every load-bearing module.
- **Quality ratchet** — record each measured headline metric as a floor; fail on
  silent regression. The baseline is a candidate artifact, updated deliberately.

**Required reading — two traps these gates exposed here (do not repeat them):**
1. **Never seed a reproducible harness with `hash()`** — `PYTHONHASHSEED` salts it
   per process, so "thousands of trials, zero failures" can be one process's luck.
   Use an explicit stable (e.g. string) seed.
2. **Any harness that edits-then-restores source on disk must defeat the bytecode
   cache** — run children with `PYTHONDONTWRITEBYTECODE=1` and purge `__pycache__`,
   or a stale `.pyc` from mutated source will poison later runs.

---

## 7. Status ledger (living — edit this every session)

### 7.1 Subsystem inventory
| Subsystem | Owner | Behavior pinned | Wrapped (P2) | Typed (P3) | De-hardcoded (P4) | Receipts (P5) | Notes |
|-----------|-------|-----------------|--------------|------------|-------------------|---------------|-------|
| _example: search_ | | ☐ | ☐ | ☐ | ☐ | ☐ | |

### 7.2 Hardcoded-choice backlog (Phase 4 targets)
| Choice | Current default | Candidate paths | Decision point id | Status |
|--------|-----------------|-----------------|-------------------|--------|
| _example: ranking_ | bm25 | bm25 / embedding / hybrid | `decision:ranking` | not started |

### 7.3 Decision log (why we chose what we chose)
| Date | Decision | Rationale | Reversible? |
|------|----------|-----------|-------------|

---

## 8. Traps & anti-patterns (hard-won on this codebase)

- **Port-role suffix trap.** A data product accidentally named `...Spec`/`...Policy`
  gets read as request config and won't chain as a required input. Name data ports
  as nouns (`ParsedIssue`, `RowSet`); reserve config/receipt suffixes deliberately.
- **Bucket-widening vs adapters.** Merging two distinct types into one "canonical"
  bucket to force a match silently loses information. Insert an explicit adapter
  node instead — it discloses the bridge as a step.
- **Hand-editing generated packs.** Always red on the content-hash gate. Edit the
  seed or builder and regenerate.
- **Async builder races.** If a builder can run in the background, it may overwrite a
  hand-authored seed. Rebuild deterministically from source and treat the builder as
  the single source of truth.
- **Unmeasured-claim creep.** "~10x faster" in a comment or card is a violation until
  a baseline actually ran. Say "unmeasured" or emit a gap record.
- **Over-promotion.** Do not flip `serves_truth` to true to make a demo look better.
  Promotion is a gated, reviewed, receipt-backed event.
- **Silent caps.** If a step samples/top-N/truncates, `log()` what was dropped —
  silent truncation reads as "covered everything" when it didn't.

---

## 9. Definition of done

**A migrated subsystem is done when:** its behavior is pinned by tests; it flows
through a receipt-emitting primitive; its seams are typed and a real request
compiles a PlanLock; at least one former hardcoded choice is a decision point with a
disclosed ranking; a mutant in its core logic is caught by the suite; and its
headline metric has a ratchet floor.

**A PR is ready when:** `run_proofs` is green; new row shapes have schemas; generated
files were regenerated (not hand-edited); no unmeasured claim was added; every new
row carries the candidate/truth boundary; and the Status Ledger was updated.

---

## 10. Glossary

- **Primitive** — a reusable capability with typed ports and a proof obligation.
- **Port / edge** — the named type on a primitive's input or output.
- **Adapter** — a reviewed deterministic bridge between two nearly-matching ports,
  registered as its own graph node.
- **Route / PlanLock** — a compiled, hash-pinned chain of primitives; runtime replays
  it with zero model calls.
- **Decision point** — a portfolio of substitutable strategies behind one choice.
- **Execution path** — one strategy in that portfolio.
- **Selection policy** — how logged receipts pick a path (cost fused with decayed
  win-rate), always returning a disclosed ranking.
- **Receipt** — the immutable record an execution or decision emits; the only memory.
- **Gap record** — an honest "cannot do this yet", emitted instead of a fake result.
- **Candidate / serves_truth** — the trust boundary; candidate until reviewed and
  proven.

---

*This file is candidate guidance describing an architecture and a migration method;
it makes no measured claim about your project until your own proof suite runs.
`candidate: true, serves_truth: false`.*
