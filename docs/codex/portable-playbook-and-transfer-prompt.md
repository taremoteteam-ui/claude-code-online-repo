# Portable playbook & transfer prompt

This distills the transferable ideas from the Primitive Atlas + flexible path &
runtime engine work into a form another project can adopt — and a ready-to-paste
prompt to hand another Claude session. Nothing here is geospatial-specific; the
place-discovery lane was only the first instance.

The through-line: **store every viable path, commit to none, and let measured
receipts — not an engineer's guess — choose which one runs. Then verify the
verifier.**

---

## Part 1 — The ten transferable ideas

### 1. Compile by typed edges, not by prose
Give every unit (function, tool, service, decision) a **typed input port and
output port**. A chain is valid iff each step's outputs satisfy the next step's
required inputs. Then "how do I get from what I have to what I want" becomes
forward-chaining graph search with **zero model calls** — a deterministic
compiler, not a prompt. The compiled artifact (call it a *PlanLock*) is a hash of
the exact steps; runtime replays it. The model is only needed to *generate the
one missing edge*, never to re-plan what already type-checks.

### 2. The non-commitment law
Never hardwire a single strategy where several are viable. Embeddings, ingestion,
matching, retrieval, ordering, CI gating — each is a **portfolio of paths behind
one decision point**, not an `if` in the code. Adding a new strategy is *data*
(a new path row), never a rewrite. This is the difference between a system that
ossifies and one that keeps absorbing better ideas.

### 3. Let data choose, and make the choice auditable
A decision point owns contract-substitutable paths. A **selection policy** scores
them by fusing cost with accumulated, **recency-decayed** receipts. Every choice
returns a *fully disclosed ranking* — each path's score, cost, win-rate, and the
reason the winner won — never a silent pick. Recency decay is what lets it
**re-adapt** when the environment shifts (a path that was best last month but
collapsed recently loses its lead automatically).

### 4. The candidate / truth boundary
Every generated row is born `candidate: true, serves_truth: false`. **Nothing
promotes itself to truth.** Promotion requires source review + proof receipts +
explicit gates. This single invariant is what lets you generate aggressively
without ever lying — the output is always labeled as unproven until something
external earns the label.

### 5. No unmeasured claims, anywhere
No performance, savings, or accuracy number appears unless a run produced it.
Fixture/synthetic runs measure *machinery*, not real-world accuracy, and every
scorecard says so. A component that *cannot* run emits a **gap record**, never a
simulated success. "We reduced tokens 10x" is forbidden until a baseline arm
actually ran. This is the most important cultural rule; it makes every other
number trustworthy.

### 6. Schemas before data; builders, not hand-edits
Define the JSON schema (the contract) *before* changing any row shape. Generated
data comes from **builder scripts** reading pure-data seed modules — never
hand-edit generated files (a content-hash gate catches it). Counts come from a
computed `manifest.json`, never typed by hand. IDs are stable and version-free;
versions live in a metadata field. Result: the whole corpus rebuilds
byte-identically from source.

### 7. Receipts are the only memory
Every execution emits an **ExecutionReceipt** (input/output hashes, effects,
proofs, timing). Every decision emits a **DecisionReceipt** into a ledger. The
policy and the self-tuning supervisor learn *only* from receipts — there is no
hidden state. This makes the system replayable, auditable, and honest about what
it has and hasn't observed.

### 8. Effects are typed and gated
Each primitive declares its effects (`none`, `file_write`, `network_read`,
`model_call`, …) and each effect carries a **proof obligation** (a write needs a
roundtrip/idempotency test; a model call needs human review). A license/secret
scan gates ingestion. Nothing with an unmet obligation becomes use-ready.

### 9. Adapters over bucket-widening
When two ports *almost* match, don't widen the type buckets (that silently merges
distinct artifacts). Insert a **reviewed deterministic adapter** as an explicit,
auditable graph node. An adapter-mediated route *discloses* the bridge as a step.
Curated code with a proof beats a heuristic that blurs your type system.

### 10. Verify the verifier (the lesson that pays for itself)
A green test suite proves nothing if the tests are toothless or the harness is
buggy. Add three cheap meta-gates:
- **Mutation testing** — inject a real defect into a core module, confirm the
  gate that *should* catch it goes red. A surviving mutant is a reported hole.
- **Determinism gate** — build twice, assert byte-identical output. Catches
  hidden dict/set-order and timestamp nondeterminism before it flakes a hash gate.
- **Quality ratchet** — record each measured headline metric as a candidate
  floor; fail if a later run silently regresses below it. Demos that *print*
  numbers and pass regardless are a regression blind spot.

---

## Part 2 — Two bugs the meta-verification caught (cautionary tales)

Adding the gates in idea #10 immediately exposed two real bugs *in the
verification harness itself* — proof that "the tests pass" was weaker than it
looked:

1. **`hash()`-seeded randomness is non-deterministic across processes.** A
   property verifier seeded its trials with `hash((name, t))`. `PYTHONHASHSEED`
   salts `hash()` per process, so "thousands of trials, zero failures" was one
   process's luck, not a proof. **Fix:** seed with a *string* (`random.Random(f"{name}:{t}")`),
   which is stable across processes. Rule: never seed a reproducible harness with
   `hash()`; use an explicit stable seed.

2. **Mutation testing can poison the bytecode cache.** A catcher imports the
   mutated module; Python compiles a `.pyc` from mutated source; restoring the
   `.py` within the same mtime tick leaves Python loading the *stale mutated
   bytecode* on later runs — silently corrupting every subsequent stage. **Fix:**
   run catchers with `PYTHONDONTWRITEBYTECODE=1` and purge `__pycache__` around
   the run. Rule: any harness that edits-then-restores source on disk must defeat
   the bytecode cache.

---

## Part 3 — Ready-to-paste transfer prompt

Paste the following into a fresh session on the target project. Trim the parts
that don't apply; the ideas are language-agnostic.

> **Adopt a "store all paths, commit to none, let receipts choose, then verify
> the verifier" architecture in this project.**
>
> Work in small, proven increments. For each of the following, propose the
> smallest change that fits THIS codebase's conventions, implement it, and prove
> it with a runnable check before moving on. Do not invent metrics — measure or
> say "unmeasured".
>
> 1. **Find a hardcoded strategy choice** (embedding model, retrieval method,
>    ordering heuristic, cache policy, CI gate order — anything where >1 approach
>    is viable and one is baked in). Refactor it into a *decision point*: a
>    portfolio of substitutable paths behind one selector, so adding a strategy
>    is data, not a code change.
> 2. **Give the selector a disclosed ranking.** It must score paths by cost fused
>    with recency-decayed outcome history and return *why* it picked what it
>    picked — never a silent choice. Persist an outcome receipt per decision;
>    that ledger is the only memory it learns from.
> 3. **Type the seams.** Where units connect (functions/tools/services), give
>    them explicit input/output "ports" and a compatibility check, so a chain can
>    be *compiled* (validated deterministically) instead of hoped-for. Where two
>    seams almost match, add a reviewed adapter as an explicit step, not a silent
>    coercion.
> 4. **Draw a candidate/truth boundary.** Label generated/derived artifacts as
>    unproven by default; require an explicit, gated promotion (review + proof)
>    to trust them. Make "no unmeasured performance/accuracy/savings claim" a
>    hard rule in the repo.
> 5. **Make it rebuild from source.** Generated data comes from builder scripts
>    over pure-data seeds; never hand-edit generated files; counts come from a
>    computed manifest. Add a determinism gate: build twice, assert identical.
> 6. **Verify the verifier.** Add (a) mutation testing — inject a real defect and
>    confirm the relevant gate goes red; a surviving mutant is a reported hole;
>    (b) a quality ratchet — record each measured headline metric as a floor and
>    fail on silent regression. Watch for two traps: never seed a reproducible
>    harness with `hash()` (it's salted per process — use a stable string seed);
>    and any harness that edits-then-restores source must run with
>    `PYTHONDONTWRITEBYTECODE=1` and purge bytecode caches, or a stale `.pyc` will
>    poison later runs.
> 7. **Wire it into CI** so every push runs the full proof suite, and keep an
>    umbrella `run_proofs` entrypoint that exits non-zero if any gate fails.
>
> Deliver each step as its own commit with a message that states what was proven
> and how. If a step can't be proven yet, say so and emit a gap record rather
> than a fake success.

---

*Candidate material. This playbook describes machinery and practices measured in
fixture mode on the source project; it makes no real-world accuracy or savings
claim. `candidate: true, serves_truth: false`.*
