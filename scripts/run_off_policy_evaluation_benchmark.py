#!/usr/bin/env python3
"""Off-policy evaluation benchmark: recover a target policy's KNOWN value from
partial-feedback logs of a different behavior policy, and show WHY doubly-robust.

Setup (contextual bandit, fully synthetic so the truth is known):
  contexts A, B (equal weight); actions a0, a1, a2; known reward means q[x][a].
  behavior policy mu: uniform over actions (full support, propensity 1/3) - it is
  what generated the logs. target policy pi: greedy on q (the policy we want to
  evaluate but never deployed). rewards are Bernoulli(q[x][a]) - partial feedback:
  each log row observes only the action mu happened to take.

We estimate V(pi) four ways (IPS, SNIPS, DM, DR) from the logs alone, and compare
to the exact V(pi) computed from q. Repeated over many seeds to measure bias and
variance. The reward model for DM/DR is fit on an INDEPENDENT pilot log (not the
evaluation log) so DR's correction stays honest.

Three measured claims (each a pass/fail verdict, none hardcoded as the answer):
  1. IPS is ~unbiased (mean estimate ~= true value).
  2. DR is robust to a MISSPECIFIED reward model: with a deliberately wrong model
     (constant 0.5), DM is badly biased but DR still recovers the true value.
  3. DR has <= the variance of IPS (the control-variate payoff), with a good model.

Honesty: the estimate is only as honest as the propensities, which here are
logged at decision time (not reconstructed). Simulated environment measures the
ESTIMATORS' statistics, not any real-world value. Seeded PRNG -> deterministic.
Zero model calls. candidate / serves_truth=false.

Usage: python3 scripts/run_off_policy_evaluation_benchmark.py --self-test
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

from primitives.off_policy_estimators import (dm_value, dr_value,  # noqa: E402
                                              fit_reward_model, ips_value,
                                              snips_value, true_value)

ACTIONS = ["a0", "a1", "a2"]
CONTEXT_WEIGHTS = {"A": 0.5, "B": 0.5}
Q = {
    "A": {"a0": 0.20, "a1": 0.50, "a2": 0.80},   # best: a2
    "B": {"a0": 0.70, "a1": 0.40, "a2": 0.30},   # best: a0
}
N_EVAL = 6000       # samples per evaluation log
N_PILOT = 6000      # samples for the (independent) reward-model fit
SEEDS = list(range(11, 31))   # 20 independent evaluation logs


def greedy_target(context):
    """pi: deterministic greedy on the true q (the policy under evaluation)."""
    best = max(Q[context], key=lambda a: Q[context][a])
    return {best: 1.0}


def _behavior_probs():
    p = 1.0 / len(ACTIONS)
    return {a: p for a in ACTIONS}


def _generate_log(seed: int, n: int) -> list[dict]:
    rng = random.Random(seed)
    contexts = list(CONTEXT_WEIGHTS)
    weights = [CONTEXT_WEIGHTS[c] for c in contexts]
    mu = _behavior_probs()
    acts, probs = list(mu), [mu[a] for a in mu]
    log = []
    for _ in range(n):
        x = rng.choices(contexts, weights=weights, k=1)[0]
        a = rng.choices(acts, weights=probs, k=1)[0]
        r = 1.0 if rng.random() < Q[x][a] else 0.0   # partial feedback: only a
        log.append({"context": x, "action": a, "reward": r, "propensity": mu[a]})
    return log


def _bad_model(context, action):
    return 0.5   # deliberately misspecified (true means span 0.2..0.8)


def run() -> dict:
    v_star = true_value(CONTEXT_WEIGHTS, Q, greedy_target, ACTIONS)
    good_model = fit_reward_model(_generate_log(seed=999, n=N_PILOT), ACTIONS)

    ips, snips, dm_good, dr_good, dm_bad, dr_bad = ([] for _ in range(6))
    for s in SEEDS:
        log = _generate_log(seed=s, n=N_EVAL)
        ips.append(ips_value(log, greedy_target))
        snips.append(snips_value(log, greedy_target))
        dm_good.append(dm_value(log, greedy_target, good_model, ACTIONS))
        dr_good.append(dr_value(log, greedy_target, good_model, ACTIONS))
        dm_bad.append(dm_value(log, greedy_target, _bad_model, ACTIONS))
        dr_bad.append(dr_value(log, greedy_target, _bad_model, ACTIONS))

    def stat(xs):
        return {"mean": round(statistics.fmean(xs), 4),
                "stdev": round(statistics.pstdev(xs), 4),
                "abs_bias": round(abs(statistics.fmean(xs) - v_star), 4)}

    est = {"IPS": stat(ips), "SNIPS": stat(snips),
           "DM_good_model": stat(dm_good), "DR_good_model": stat(dr_good),
           "DM_bad_model": stat(dm_bad), "DR_bad_model": stat(dr_bad)}

    verdict = {
        "ips_unbiased": est["IPS"]["abs_bias"] < 0.02,
        "dr_robust_to_misspecified_model": (
            est["DR_bad_model"]["abs_bias"] < 0.03 and est["DM_bad_model"]["abs_bias"] > 0.10),
        "dr_variance_le_ips": est["DR_good_model"]["stdev"] <= est["IPS"]["stdev"],
    }
    return {
        "run_id": "opebench", "true_value": round(v_star, 4),
        "eval_samples": N_EVAL, "eval_logs": len(SEEDS), "pilot_samples": N_PILOT,
        "behavior_policy": "uniform (propensity 1/3, full support)",
        "target_policy": "greedy on q (never deployed)",
        "estimators": est, "verdict": verdict,
        "candidate": True, "serves_truth": False,
        "honesty_notes": [
            "fully synthetic: the estimators are checked against the KNOWN true value",
            "partial feedback - each log row observes only the action the behavior policy took",
            "propensities are logged at decision time (mu is known), not reconstructed",
            "the reward model is fit on an INDEPENDENT pilot log so DR's correction is honest",
            "DR stays unbiased under a deliberately wrong reward model - that is the "
            "doubly-robust property, measured, not asserted",
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
        (out / "off_policy_evaluation_benchmark.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8")
    v = result["verdict"]
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
