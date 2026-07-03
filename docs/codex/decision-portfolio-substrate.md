# The decision-portfolio substrate: store all paths, let data choose

Last updated: 2026-07-03. The domain-agnostic engine that generalizes the
non-commitment law to EVERY decision in the codebase — runtime or development.
Companion to `docs/codex/multi-path-flexible-primitive-architecture.md` (the
vision) and `docs/codex/retrieval-architecture-red-team.md` (the critique that
motivated proving things with numbers).

## What it is

A `DecisionPoint` is a stable, globally-unique decision that owns a portfolio of
contract-substitutable `ExecutionPath`s, a selection policy over an append-only
receipt ledger, and a cold-start default. The rule:

> Store the SPACE of paths as data; keep SELECTION as a policy over receipts.
> Adding a path is a data row; changing how you choose is a policy swap. Neither
> is a rewrite.

Nothing in the engine is primitive-specific. Three data layers (portfolio,
ledger, policy) + one thin call-site hook. The same engine drives a retrieval
choice, a remix ladder, and a CI decision.

## The pieces (all built, tested, proven)

- **Contracts**: `schemas/decision_point.schema.json`,
  `schemas/execution_path.schema.json`, `schemas/decision_receipt.schema.json`.
- **Engine** `primitives/decision_engine.py`: `is_applicable` (declarative
  predicate over context), `normalize_cost`, `LedgerStats.from_receipts`
  (recency-decayed win-rates, optionally CONTEXT-CONDITIONED — the contextual-
  bandit seam), and `choose` — which returns a FULLY DISCLOSED ranking (every
  applicable path's cost, decayed win-rate, and why the winner won). Never a
  silent pick.
- **Policies**: `deterministic_tier` (cheapest applicable tier, receipts
  ignored — models the route-compiler exact→typed→adapter ladder),
  `cheapest_that_proves`, `argmax_receipts`, `epsilon_greedy` (deterministic
  exploration by context hash — reproducible).
- **Supervisor** `primitives/decision_supervisor.py`: the self-aware / self-
  tuning layer. Reads the ledger and emits candidate recommendations —
  `promote_default` (a challenger beats the default by a margin with enough
  samples), `retire_dominated` (worse on win-rate AND cost — kept as data for
  revival), `reopen_exploration` (drift: recent window fell below lifetime).
  It never rewrites a policy; a human applies a recommendation by editing the
  seed (a data change), keeping the non-commitment law honest.
- **Pack**: `scripts/build_decision_portfolio_pack.py` +
  `scripts/check_decision_portfolio_pack.py`. The checker enforces the
  invariants: a portfolio has ≥2 paths; `default_path` is a member AND
  cold-start-eligible (its `applicability.requires_keys` is empty, so there is
  always a valid fallback before any receipts); every `handler_ref` resolves.
- **Demo** `scripts/run_decision_engine_demo.py`: the measured generality proof.

## The generality proof (measured, zero model calls)

One engine drives three structurally-dissimilar decisions from data alone
(`scripts/run_decision_engine_demo.py --self-test`):

1. **`decision:retrieval.plane_selection`** (runtime, execute-all-when-cheap,
   `argmax_receipts`). All applicable planes run over the honest 15-probe
   cross-lane set; receipts (reciprocal rank) accumulate; the engine picks the
   plane the DATA prefers. Context-conditioned win-rates (want-known bucket, so
   applicability differences compare fairly):

   ```text
   lexical_only        0.62
   lexical_plus_typed  0.70
   typed_edge          0.90   <- data-preferred when a wanted type is known
   when no type known  -> only lexical_only is applicable (fallback)
   ```

   The supervisor then recommends `promote_default: lexical_only -> typed_edge`.
   Honest caveat: typed-edge leads because a specific wanted type has few
   producers; on this small probe set that dominates fused — a floor signal, not
   a tuned verdict (fused likely wins on ambiguous queries not probed).

2. **`decision:remix.escalation`** (runtime, `deterministic_tier`). The ladder
   picks the cheapest APPLICABLE tier by contract-diff context:
   `rename -> deterministic_mutator`, `envelope -> type_adapter`,
   `novel_semantic -> bounded_model`.

3. **`decision:dev.proof_stage_order`** (development, `cheapest_that_proves`).
   The same engine drives a build/CI decision — evidence the substrate spans
   runtime AND development choices.

Ledger + supervision report persist under `benchmarks/decision_runs/`. Wired as
three `run_proofs.py` stages (build self-test, checker, engine demo); 25 stages
green. Unit tests in `tests/test_decision_engine.py` (11).

## The honest boundary (where "all paths" stops being literal)

Typed by **cost × reversibility**:
- **Reversible + cheap + observable** (retrieval, remix, most runtime): execute
  the portfolio and let receipts choose — the mode demonstrated here.
- **One-way + expensive + unobservable** (architecture picks): store the
  decision RECORD + the losing branches as revivable specs with revival
  triggers; run only cheap challengers as shadow. `ExecutionPath` carries
  `reversibility` and `revival_trigger` for exactly this.

Known limits (see the red-team doc): cold-start needs a prior; dominated paths
must be pruned by applicability+cost before spending; non-stationarity is why
receipts decay and demoted paths stay as data; decision COUPLING (the best path
for A depends on B) is the sharpest limit — independent per-site portfolios
assume a separability that does not always hold; and most lines of code are NOT
decisions worth portfolio-izing.

## Adopting it for a new decision

1. Add a `DecisionPoint` row (question, context keys, contract, policy, default).
2. Add ≥2 `ExecutionPath` rows (applicability, cost, reversibility, optional
   `handler_ref`).
3. At the call site: `choose(decision, paths, context, stats)` → run the chosen
   path → append a `DecisionReceipt`. The ledger does the rest.

No engine change. A fifth decision costs data rows, not code — which is the whole
point.
