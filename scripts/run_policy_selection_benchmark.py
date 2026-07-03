#!/usr/bin/env python3
"""Counterfactual policy-selection benchmark: let logged data choose the engine's
SELECTION POLICY, and verify the choice on held-out data.

The non-commitment law, one level up. Instead of hardwiring a selection policy,
we replay a logged full-feedback history through every policy (via the REAL
engine) and measure the regret each WOULD have accrued. We do this across three
synthetic regimes:

  stationary   - fixed hidden arm means; a learner should converge and beat the
                 non-learning tier baseline.
  drift        - the best arm flips at the midpoint; decay-based learners recover.
  contextual   - the best arm depends on the observable context; the
                 context-conditioned policy should beat the global learner.

For each regime we SELECT the lowest-regret policy on a train log, then re-measure
every policy on an independently-seeded HOLDOUT log from the same distribution and
report whether the selected policy generalizes (isn't the worst on holdout, and
still beats the non-learning baseline). Nothing is hardcoded as "the answer" - the
data picks, and the holdout checks the pick.

Honesty: simulated full-feedback environment; regret is vs a known oracle; this
measures the engine's POLICY machinery, not real-world outcomes. Seeded PRNG ->
deterministic and replayable. Zero model calls. candidate / serves_truth=false.

Usage: python3 scripts/run_policy_selection_benchmark.py --self-test
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from primitives.policy_evaluation import (POLICY_PORTFOLIO, evaluate,  # noqa: E402
                                          make_log, select_best)

ROUNDS = 600
ARMS = ["path:pol.arm0", "path:pol.arm1", "path:pol.arm2"]

PATHS = [{"record_type": "execution_path", "path_id": a, "decision_id": "decision:pol",
          "title": a, "method": "one arm of the policy-selection simulation",
          "applicability": {"requires_keys": [], "conditions": []},
          "cost_model": {"tokens": 0, "latency_ms": 10, "side_effect_risk": "none"},
          "reversibility": "reversible", "preference_rank": i, "deterministic": True,
          "expected_receipts": ["win"], "version": "0", "candidate": True, "serves_truth": False}
         for i, a in enumerate(ARMS)]

BASE_DECISION = {"decision_id": "decision:pol", "learn_keys": ["c"],
                 "contract": {"input": "x", "output": "y", "win_definition": "arm succeeds"},
                 "selection_policy": "argmax_receipts", "default_path": "path:pol.arm0"}

_NON_LEARNING = "deterministic_tier"   # the baseline any learner must beat


# ----- regimes: means_fn(t, context) + context_fn(t, rng) ---------------------

def _stationary_means(t, ctx):
    return {"path:pol.arm0": 0.30, "path:pol.arm1": 0.55, "path:pol.arm2": 0.80}


def _drift_means(t, ctx):
    if t < ROUNDS // 2:
        return {"path:pol.arm0": 0.30, "path:pol.arm1": 0.55, "path:pol.arm2": 0.80}
    return {"path:pol.arm0": 0.80, "path:pol.arm1": 0.45, "path:pol.arm2": 0.25}


def _contextual_means(t, ctx):
    # best arm depends on the observable context 'c'
    if ctx["c"] == "A":
        return {"path:pol.arm0": 0.80, "path:pol.arm1": 0.45, "path:pol.arm2": 0.30}
    return {"path:pol.arm0": 0.30, "path:pol.arm1": 0.45, "path:pol.arm2": 0.80}


def _fixed_context(t, rng):
    return {"c": "S"}


def _alternating_context(t, rng):
    return {"c": "A" if rng.random() < 0.5 else "B"}


REGIMES = {
    "stationary": (_stationary_means, _fixed_context),
    "drift": (_drift_means, _fixed_context),
    "contextual": (_contextual_means, _alternating_context),
}


def _regime_result(name: str, means_fn, context_fn) -> dict:
    train = make_log(ROUNDS, ARMS, means_fn, context_fn, seed=101)
    holdout = make_log(ROUNDS, ARMS, means_fn, context_fn, seed=202)
    train_res = evaluate(BASE_DECISION, PATHS, train)
    holdout_res = evaluate(BASE_DECISION, PATHS, holdout)
    selected = select_best(train_res)

    regrets_holdout = {k: v["cumulative_regret"] for k, v in holdout_res.items()}
    worst = max(regrets_holdout.values())
    baseline = regrets_holdout[_NON_LEARNING]
    sel_holdout = regrets_holdout[selected]
    holdout_best = min(regrets_holdout, key=lambda k: (regrets_holdout[k], k))

    return {
        "regime": name,
        "selected_on_train": selected,
        "train_regret": {k: v["cumulative_regret"] for k, v in train_res.items()},
        "holdout_regret": regrets_holdout,
        "holdout_best_policy": holdout_best,
        "checks": {
            # the selected policy generalizes: not the worst on holdout ...
            "selected_not_worst_on_holdout": sel_holdout < worst,
            # ... and still beats the non-learning baseline on holdout
            "selected_beats_baseline_on_holdout": sel_holdout < baseline,
        },
    }


def run() -> dict:
    regimes = {name: _regime_result(name, mf, cf) for name, (mf, cf) in REGIMES.items()}
    # the point of the whole exercise: no single policy is best in every regime
    winners = {r["holdout_best_policy"] for r in regimes.values()}
    contextual_helps = (
        regimes["contextual"]["holdout_regret"]["argmax_contextual"]
        < regimes["contextual"]["holdout_regret"]["argmax_receipts"])
    all_checks_pass = all(all(r["checks"].values()) for r in regimes.values())
    return {
        "run_id": "policyselect", "rounds": ROUNDS, "arms": len(ARMS),
        "policies_evaluated": [p["name"] for p in POLICY_PORTFOLIO],
        "regimes": regimes,
        "distinct_winning_policies": sorted(winners),
        "verdict": {
            "selection_generalizes_every_regime": all_checks_pass,
            "no_single_policy_dominates": len(winners) > 1,
            "context_conditioning_helps_contextual_regime": contextual_helps,
        },
        "candidate": True, "serves_truth": False,
        "honesty_notes": [
            "simulated FULL-FEEDBACK environment; counterfactual regret is valid here "
            "but would need propensity weighting on a partial-feedback production log",
            "policies learn only from the arm they pull; the log reveals that arm's reward",
            "regret is measured against an oracle that always plays the true-best arm",
            "the best policy is chosen on a train log and re-checked on an independently "
            "seeded holdout log - the pick is not asserted, it is measured and verified",
            "seeded PRNG - deterministic and replayable; zero model calls",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if not (args.self_test or args.write):
        parser.print_help()
        return 2
    result = run()
    print(json.dumps(result, indent=2))
    if args.write:
        out = REPO_ROOT / "benchmarks" / "decision_runs"
        out.mkdir(parents=True, exist_ok=True)
        (out / "policy_selection_benchmark.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8")
    v = result["verdict"]
    return 0 if (v["selection_generalizes_every_regime"]
                 and v["no_single_policy_dominates"]
                 and v["context_conditioning_helps_contextual_regime"]) else 1


if __name__ == "__main__":
    sys.exit(main())
