#!/usr/bin/env python3
"""Counterfactual risk minimization benchmark: LEARN a policy from logs, and
report honestly what the variance penalty does and does not buy.

Synthetic contextual bandit with KNOWN reward means q and a behavior policy with
full support but POOR OVERLAP on the good actions (it mostly plays a mediocre arm).
From partial-feedback logs alone we learn policies by maximizing an off-policy
objective over the deterministic context->action policy class:

  naive_ips  - maximize the raw IPS value estimate (unregularized ERM)
  naive_snips- maximize the SNIPS value estimate (lambda = 0)
  crm        - maximize SNIPS minus lambda * confidence-radius (POEM)

and compare each learned policy's TRUE value (knowable, since the env is known)
against the behavior and optimal policies, averaged over seeds.

GATED verdicts (robustly true, nothing tuned to manufacture them):
  1. CRM learns a policy far better than the behavior policy that produced the logs.
  2. So does the naive learner - off-policy LEARNING works; the penalty is a knob.
  3. With a large log CRM approaches the optimal policy's value (consistency).

REPORTED honestly, not gated: the variance penalty's effect on mean true value in
this regime. Finding: with SNIPS already self-normalizing and the good actions only
mildly under-covered, the extra empirical-Bernstein penalty does NOT reliably
improve mean true value here - it trades value-chasing for conservatism. The
penalty earns its keep when the logs poorly cover the good actions; we DISCLOSE
this rather than tune lambda until a win appears (that would be exactly the kind of
curated claim this repo forbids).

Honesty: synthetic so the learned policy's true value is knowable and used only to
score; valid only with genuine full-support propensities; seeded -> deterministic;
zero model calls. candidate / serves_truth=false.

Usage: python3 scripts/run_policy_learning_benchmark.py --self-test
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from primitives.off_policy_estimators import true_value  # noqa: E402
from primitives.policy_learning import (learn_naive_ips_policy,  # noqa: E402
                                        learn_naive_policy, learn_policy)

CONTEXTS = ["A", "B"]
ACTIONS = ["a0", "a1", "a2"]
CONTEXT_WEIGHTS = {"A": 0.5, "B": 0.5}
Q = {
    "A": {"a0": 0.20, "a1": 0.50, "a2": 0.80},   # best: a2
    "B": {"a0": 0.75, "a1": 0.50, "a2": 0.20},   # best: a0
}
BEHAVIOR = {"a0": 0.10, "a1": 0.80, "a2": 0.10}   # mostly the mediocre arm
LAMBDA = 0.30
SEEDS = list(range(1, 21))
N_LEARN = 600
N_LARGE = 4000


def _optimal_policy():
    return {x: max(Q[x], key=lambda a: Q[x][a]) for x in CONTEXTS}


def _policy_true_value(policy_map):
    return true_value(CONTEXT_WEIGHTS, Q, lambda x: {policy_map[x]: 1.0}, ACTIONS)


def _generate_log(seed: int, n: int) -> list[dict]:
    rng = random.Random(seed)
    ctxs, cw = list(CONTEXT_WEIGHTS), [CONTEXT_WEIGHTS[c] for c in CONTEXT_WEIGHTS]
    acts, ap = list(BEHAVIOR), [BEHAVIOR[a] for a in BEHAVIOR]
    log = []
    for _ in range(n):
        x = rng.choices(ctxs, weights=cw, k=1)[0]
        a = rng.choices(acts, weights=ap, k=1)[0]
        r = 1.0 if rng.random() < Q[x][a] else 0.0
        log.append({"context": x, "action": a, "reward": r, "propensity": BEHAVIOR[a]})
    return log


def _mean_true_value(n: int, learner) -> float:
    return statistics.fmean(
        _policy_true_value(learner(_generate_log(s, n), CONTEXTS, ACTIONS)["policy"])
        for s in SEEDS)


def run() -> dict:
    v_opt = _policy_true_value(_optimal_policy())
    v_behavior = true_value(CONTEXT_WEIGHTS, Q, lambda x: BEHAVIOR, ACTIONS)

    crm = lambda log, c, a: learn_policy(log, c, a, lam=LAMBDA)  # noqa: E731
    naive_ips_mean = _mean_true_value(N_LEARN, learn_naive_ips_policy)
    naive_snips_mean = _mean_true_value(N_LEARN, learn_naive_policy)
    crm_mean = _mean_true_value(N_LEARN, crm)
    crm_large = _mean_true_value(N_LARGE, crm)

    verdict = {
        "crm_beats_behavior": crm_mean > v_behavior + 0.05,
        "naive_also_beats_behavior": naive_ips_mean > v_behavior + 0.05,
        "crm_approaches_optimal_with_data": abs(crm_large - v_opt) < 0.03,
    }
    return {
        "run_id": "crmbench", "contexts": len(CONTEXTS), "actions": len(ACTIONS),
        "lambda": LAMBDA, "seeds": len(SEEDS), "n_learn": N_LEARN,
        "behavior_policy": BEHAVIOR, "optimal_policy": _optimal_policy(),
        "true_values": {
            "optimal": round(v_opt, 4), "behavior": round(v_behavior, 4),
            "naive_ips_learned_mean": round(naive_ips_mean, 4),
            "naive_snips_learned_mean": round(naive_snips_mean, 4),
            "crm_learned_mean": round(crm_mean, 4),
            "crm_learned_mean_large_n": round(crm_large, 4),
        },
        "penalty_effect_on_mean_true_value": round(crm_mean - naive_snips_mean, 4),
        "verdict": verdict,
        "candidate": True, "serves_truth": False,
        "honesty_notes": [
            "the learned policy's TRUE value is knowable (synthetic) and used only to score; "
            "the learner sees logs + propensities only",
            "GATED claims are the robustly-true ones (learning beats the logging policy; "
            "CRM -> optimal with data); the penalty's effect is REPORTED, not gated",
            "FINDING: here the variance penalty did not reliably raise mean true value - with "
            "SNIPS already self-normalizing and only mild under-coverage, it adds conservatism. "
            "lambda was NOT tuned to force a win; the penalty helps when the logs poorly cover "
            "the good actions",
            "valid only with genuine full-support propensities; seeded -> deterministic; zero model calls",
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
        (out / "policy_learning_benchmark.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0 if all(result["verdict"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
