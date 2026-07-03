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

## The planner: the most efficient COMBINATION of gates/checkpoints/paths

The engine picks one path for one decision. Real pipelines couple decisions, so
`primitives/decision_planner.py` adds joint optimization — the piece that lets a
project "drop in an engine that finds the most efficient combination of
gates/paths" instead of an engineer hand-ordering them:

- **`optimal_gate_order`** — order independent checkpoints to minimise expected
  cost until the first failure. Provably optimal (adjacent-exchange): run gates
  by descending `p_fail / cost` (cheapest-most-likely-to-fail first). Measured in
  the demo: expected cost `11.09 → 6.10` for the same gate set, just by ordering.
- **`plan_combination`** — branch-and-bound over the product of applicable paths
  across several decisions to find the min-expected-cost combination that clears
  a whole-plan reliability checkpoint (∏ success ≥ R) and an optional budget,
  honouring a compatibility predicate (the coupling). Exact for the small
  portfolios real pipelines have; greedy fallback (disclosed) above a size cap.
  Demo: the cheapest per-decision picks give reliability `0.42 < 0.6` and fail
  the gate; the planner upgrades the least-cost stages to `0.698` under the
  constraint — a combination the local optimum never finds. Verified against
  brute force in `tests/test_decision_planner.py`.

Both are receipt-driven (win-rates → success/failure probabilities, cost models →
cost) and disclose their arithmetic. The engineer declares only the path space,
the cost model, and what a win is; the planner derives ordering, selection, and
combination from data — no further engineering decision.

## Contracts, edges, and frameworks BETWEEN forks (the decision graph)

Primitives compose by typed edges; so should decisions. `primitives/
decision_graph.py` makes the control-flow tree edge-typed, so forks compose the
same way primitives do:

- **Contract per fork.** Each decision's `contract` now declares `consumes` and
  `produces` — the state keys it needs and yields. A fork is a typed node.
- **Edges derived, not hand-wired.** Fork A → fork B whenever B consumes a key A
  produces (`build_decision_edges`). The demo derives
  `retrieval → ordering` (on `candidate_set`) and `ordering → execution` (on
  `validated_order`) with no wiring by hand.
- **Compile the fork order.** `compile_decision_order(decisions, initial_keys,
  goal_keys)` forward-chains over state keys to order the forks that reach the
  goal — the *route compiler, for decisions* — or returns a gap with the first
  unmet key.
- **Decision frameworks.** A `decision_framework` (own schema/pack) is a reusable
  typed DAG of forks solving a meta-problem; the checker validates it composes by
  the same wave rule the warehouse multi-wave pipelines use (every consumed key
  produced by the initial state or an earlier fork) and reaches the goal.

`scripts/run_decision_dag_demo.py` ties it together: for `dframework:solve` it
derives the fork edges, compiles the order (matching the declared framework),
then resolves each fork to a path and threads the produced state forward — a
fully wired decision plan from `{problem_intent, want_type, have, want,
effect_profile}` to `execution_result`. The capability graph (runtime) and the
decision graph (control flow) are now the same kind of object, composed by the
same machinery.

## Drop-in for any project: `primitives/decision_kit.py`

`DecisionKit` wires the engine + planner to any codebase in ~3 lines with a
pluggable ledger sink (in-memory / JSONL / any callable — the storage seam):

```python
kit = DecisionKit(ledger=JsonlLedger("ledger.jsonl")).load_pack()
choice = kit.decide("decision:retry.policy", {"idempotent": True})   # engine picks
# ... run choice["chosen_path"] ...
kit.record("decision:retry.policy", choice["chosen_path"], ctx, win=1.0, cost=12)
plan = kit.plan(["d:fetch", "d:parse", "d:verify"], ctx, min_reliability=0.6)   # planner combines
```

Because selection/ordering/combination are pure functions over (portfolio,
context, ledger), the same kit runs on files today and a database tomorrow
without touching a single call site.

## Adversarial verification, benchmarks, and developer simulations

The algorithms are not just unit-tested on fixed cases — they are fuzzed and
measured:

- **Adversarial verifier** (`scripts/verify_decision_engine.py`): a seeded
  property-based harness that tries to FALSIFY the implementation over hundreds
  of random inputs per invariant, comparing against brute force. Six invariants —
  P1 planner == brute-force optimum, P2 gate order == min over all permutations,
  P3 no inapplicable path is ever chosen, P4 a compiled decision DAG always
  validates and reaches its goal, P5 win-rates stay in [0,1], P6 argmax is
  monotone in receipts. **6,000 random trials (1,000 × 6), zero failures.**
- **Learning + non-stationarity benchmark**
  (`scripts/run_decision_bandit_benchmark.py`): simulates a decision whose paths
  have TRUE hidden success rates, runs the engine's argmax-over-decayed-receipts
  selection for 400 rounds with ε-exploration, and measures cumulative regret vs
  an oracle — then SHIFTS the world at the midpoint. Measured (not asserted):
  the engine learns (pre-shift regret ≈ 12 vs random ≈ 57), and **decay drives
  re-adaptation** — post-shift regret 14.7 with decay=0.9 vs 66.9 with decay=1.0,
  and the greedy choice tracks the new best 99% vs 54% of late rounds. The honest
  tradeoff is disclosed: decay=1.0 is slightly better before the shift, far worse
  after.
- **Developer simulations** (`scripts/run_dev_decision_sims.py`): the same engine
  driving everyday engineering decisions — retry policy (non-idempotent forbids
  retry, settled structurally by applicability), serialization
  (protobuf for large/stable, json for small/evolving — learned), concurrency
  (async for IO-bound, multiprocess for CPU-bound — learned). 5/5 picks correct
  per context.

All three run as `run_proofs.py` stages (38 green). Every artifact
`candidate=true / serves_truth=false`; every number is computed by the script.

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
