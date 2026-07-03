# Compiled AI, at Atlas scale

Last updated: 2026-07-03. How the Primitive Atlas relates to and extends
"Compiled AI: Deterministic Code Generation for LLM-Based Workflow Automation"
(arXiv:2604.05150, Trooskens et al.), and what "so much bigger" means concretely.

## The shared thesis

Compiled AI: an LLM generates executable artifacts during a COMPILE phase, after
which workflows execute deterministically with **no further model invocation** —
trading runtime flexibility for predictability, auditability, cost, and security.
The paper measures token amortization, determinism, reliability, and security on
function-calling (BFCL) and document intelligence (DocILE).

That is precisely the law this repo is built on:

```text
Search first. Reuse first. Remix deterministically. Generate ONLY the missing
edge. Prove every route. Promote only after receipts.
```

## The mapping (paper -> this repo)

| Compiled AI concept | Primitive Atlas realization |
| --- | --- |
| Compile phase produces a code artifact | The route compiler emits a **PlanLock** (`primitives/route_compiler.py`) — a hashable, replayable ordered plan, assembled with **zero model calls** |
| Deterministic runtime, no model at execution | **A4 replay** measures `runtime_llm_tokens = 0`; `primitives/route_runtime.py` executes a PlanLock step-by-step, emitting an ExecutionReceipt per step |
| Constrain generation to narrow business-logic functions | "Generate only the missing edge": the deterministic compiler/adapters cover the wiring; a model is bounded to the single unfilled contract, and its output is gated by `route_validator` (propose freely, run only if it type-checks) |
| Validated templates | **Solution frameworks** (`solution_framework`) and **decision frameworks** — typed wiring scaffolds validated to fill+compose against the real graph |
| Four-stage generate-and-validate pipeline | The foundry lifecycle **acquire -> form -> verify -> store -> use** + the ordering portfolio **propose -> validate -> repair** |
| Auditability | Every execution goes through `primitives/core.py` and emits a receipt (input/output hash, effects, proofs, timing); every row is `candidate=true / serves_truth=false` until receipts + review promote it |
| Security (prompt-injection, static safety) | The foundry's **secret-scan** + **license** gates; static-safety/injection lanes are a named next slice (below) |
| Token amortization / break-even / Nx | `scripts/eval/savings_formulas.py` (`compiled_break_even_transactions`, `amortized_tokens_per_transaction`, `token_reduction_factor_at`) + `scripts/run_amortization_model.py` |

## What "so much bigger" means here

The paper compiles **within narrow, per-task templates**. The Atlas generalizes
the same paradigm along several axes:

1. **A universal, cross-lane primitive bank, composed by typed edges** — not one
   template per task, but ~2.8k typed capability-graph nodes across every domain
   (auth, data, warehouse, docs, media, coding-agent, geospatial, …) that the
   compiler orders by contract compatibility. A new capability joins as a data
   row, not a new template.
2. **Composition, not just filling** — Compiled AI fills a chosen template; the
   Atlas *discovers and orders* the primitives (route compiler + adapters), and
   only then fills the residual edge. The compiler is measured **98% shortest-
   optimal, 100% valid** over random graphs.
3. **The non-commitment law over everything** — the decision-portfolio engine +
   planner generalize "compile once, run deterministically" to *every* decision
   (retrieval plane, remix ladder, ordering strategy, execution target),
   choosing the cheapest sufficient path from receipts and finding the best
   *combination* of gates/checkpoints.
4. **A self-growing supply side** — the primitive foundry mines new primitives
   from sources (offline/fixture here) and registers verified ones into the
   graph, so the compilable bank grows without rewrites.

## Token amortization: honest framing

The paper's headline is token economics (break-even ~17 transactions, ~57x at
1000). The Atlas implements the **exact formulas** and a model
(`run_amortization_model.py`) that reproduces that curve's *shape* for
illustrative inputs. But per this repo's non-negotiable honesty rules:

- `compile_phase_tokens` and `baseline_runtime_tokens_per_transaction` for THIS
  system require measured **baseline arms (A1/A2) that have not run**.
- Only `compiled_runtime_tokens_per_transaction = 0` is measured (A4 fixture
  replay).
- Therefore **no measured Nx/break-even is claimed for this repo**; the paper's
  numbers are attributed to the paper. The formula is exact given inputs; the
  inputs await the baseline arms. `savings_formulas.py:MEASUREMENT_STATUS`
  records exactly which inputs exist and which do not.

This is the honest version of the paper's central claim: the machinery and the
arithmetic are here and verified; the specific reduction for this system is a
measurement we have set up but not yet taken.

## Next build slices (to close the paper's evaluation axes)

1. **Baseline arms A1/A2** (model-in-the-loop) so `compile_phase_tokens` and
   `baseline_runtime_tokens_per_transaction` become measured — then the
   amortization model reports a real break-even/Nx for this system.
2. **Security lane** — a prompt-injection detector family + a static code-safety
   gate on mined/generated primitives (the paper's 135-case security eval),
   measured over synthetic fixtures like the foundry's secret-scan gate.
3. **Function-calling + DocILE parity** — the coding-agent lane already models
   function-calling solve loops; the document-extraction lane already enforces
   span-grounding (the DocILE anti-hallucination invariant). Wire model-in-the-
   loop arms to produce the paper's task-completion / KILE / LIR style numbers.
