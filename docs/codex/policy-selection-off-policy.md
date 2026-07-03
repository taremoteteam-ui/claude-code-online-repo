# Off-policy policy selection — the non-commitment law, one level up

**The idea in one line:** don't hardwire *which selection policy* the decision
engine runs — store every policy, replay logged data through each, and let the
data (not an engineer) pick the winner, then verify the pick on held-out data.

The decision engine already stores all *paths* and lets receipts choose one.
This lifts the same discipline to the **policy** that does the choosing. That is
the self-improvement flywheel made concrete: the system reads its own telemetry
and improves its own control policy — measured, not asserted.

## What runs

- `primitives/policy_evaluation.py` — reusable, domain-agnostic:
  - `make_log(...)` generates a **full-feedback** synthetic log (every arm's
    outcome recorded — this is what makes counterfactual regret valid);
  - `replay(policy, ...)` replays one policy over a log through the **real
    engine's `choose`** (no peeking: round *t* sees only receipts `< t`), and
    returns cumulative regret vs a known oracle;
  - `evaluate(...)` runs every policy over the same log; `select_best(...)` picks
    the lowest-regret policy.
- `scripts/run_policy_selection_benchmark.py` — three synthetic regimes
  (stationary / drift / contextual), each **selected on a train log and
  re-checked on an independently-seeded holdout log**.

## The policy portfolio

`deterministic_tier`, `cheapest_that_proves`, `argmax_receipts`,
`epsilon_greedy`, and a variation added here — `argmax_contextual`, which
conditions the receipt stats on the observable context (the engine's
`only_context` seam). Five policies; none is best everywhere.

## What the measurement shows (fixture-mode, seeded, replayable)

- **stationary** — the receipt-driven learners converge to the best arm; the
  non-learning tier baseline is stuck and racks up regret.
- **drift** — the best arm flips at the midpoint. **`epsilon_greedy` wins**:
  pure decay-greedy learners confidently stay on the stale best arm and can do
  *worse* than the fixed baseline; exploration is what recovers.
- **contextual** — the best arm depends on context. **`argmax_contextual` wins
  by a wide margin** over global argmax; conditioning on context is decisive.

Because the winning policy differs by regime, **no single policy dominates** —
which is exactly why the choice must be data-driven, not baked in. The
data-selected policy generalizes to holdout in every regime (it is never the
worst, and always beats the non-learning baseline).

## Honesty boundary

- Counterfactual regret is valid here **only because the environment is a
  simulated full-feedback log**. On a partial-feedback production log you would
  need propensity weighting (IPS / doubly-robust); that is flagged, never faked.
- Policies still learn from partial feedback (only the pulled arm updates); the
  full-feedback log only reveals the pulled arm's reward and lets regret be
  computed against the oracle.
- Seeded PRNG → deterministic and replayable; zero model calls. Every record is
  `candidate: true, serves_truth: false`. The contextual-regime winner's holdout
  regret is protected by the quality ratchet so a future change can't silently
  erode it.

## Commands

```bash
python3 scripts/run_policy_selection_benchmark.py --self-test   # measured, in-memory
python3 scripts/run_policy_selection_benchmark.py --write       # persist scorecard
python3 -m unittest tests.test_policy_evaluation -v
```
