#!/usr/bin/env python3
"""Learning + non-stationarity benchmark for the decision engine.

The engine claims it is self-tuning and re-adapts when the world shifts (that is
why receipts DECAY). This benchmark MEASURES both instead of asserting them:
simulate a decision whose paths have TRUE hidden success rates, run the engine's
argmax-over-decayed-receipts selection for T rounds against an epsilon of random
exploration, and track cumulative regret vs an oracle that always plays the true
best. Halfway through, the true rates SHIFT - a non-stationary world - and we
measure how fast each configuration recovers.

The load-bearing comparison: decay=0.9 (the default - forgets stale receipts) vs
decay=1.0 (never forgets). If decay matters, decay=0.9 recovers faster after the
shift. Deterministic seeded PRNG - replayable. Zero model calls.

Usage: python3 scripts/run_decision_bandit_benchmark.py --self-test
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from primitives.decision_engine import LedgerStats, choose  # noqa: E402

ROUNDS = 400
EPSILON = 0.10
# equal cost so the argmax is driven purely by learned win-rate, not the cost term
PATHS = [{"record_type": "execution_path", "path_id": f"path:bandit.arm{i}", "decision_id": "decision:bandit",
          "title": f"arm{i}", "method": "one arm of the bandit in this simulation",
          "applicability": {"requires_keys": [], "conditions": []},
          "cost_model": {"tokens": 0, "latency_ms": 10, "side_effect_risk": "none"},
          "reversibility": "reversible", "preference_rank": i, "deterministic": True,
          "expected_receipts": ["win"], "version": "0", "candidate": True, "serves_truth": False}
         for i in range(3)]
DECISION = {"decision_id": "decision:bandit", "context_signature": ["s"],
            "contract": {"input": "x", "output": "y", "win_definition": "arm succeeds",
                         "consumes": [], "produces": ["z"]},
            "selection_policy": "argmax_receipts", "default_path": "path:bandit.arm0"}

TRUE_BEFORE = {"path:bandit.arm0": 0.30, "path:bandit.arm1": 0.60, "path:bandit.arm2": 0.85}
TRUE_AFTER = {"path:bandit.arm0": 0.85, "path:bandit.arm1": 0.40, "path:bandit.arm2": 0.30}


def simulate(decay: float, seed: int) -> dict:
    rng = random.Random(seed)
    ledger, seq = [], 0
    cum_regret = 0.0
    regret_before = regret_after = 0.0
    correct_after = 0
    shift = ROUNDS // 2
    for t in range(ROUNDS):
        true = TRUE_BEFORE if t < shift else TRUE_AFTER
        best_rate = max(true.values())
        best_arm = max(true, key=true.get)
        stats = LedgerStats.from_receipts(ledger, decay=decay)
        if rng.random() < EPSILON:
            arm = rng.choice(PATHS)["path_id"]           # explore
        else:
            arm = choose(DECISION, PATHS, {"s": 1}, stats)["chosen_path"]  # exploit
        win = 1.0 if rng.random() < true[arm] else 0.0
        ledger.append({"decision_id": "decision:bandit", "path_id": arm, "context_signature": "c",
                       "sequence": seq, "applicable": True, "chosen": True, "proved": win > 0,
                       "win_score": win, "cost_observed": 10, "candidate": True, "serves_truth": False})
        seq += 1
        r = best_rate - true[arm]
        cum_regret += r
        if t < shift:
            regret_before += r
        else:
            regret_after += r
            # after a recovery window, is the greedy choice the new best?
            if t >= shift + 50:
                greedy = choose(DECISION, PATHS, {"s": 1},
                                LedgerStats.from_receipts(ledger, decay=decay))["chosen_path"]
                correct_after += 1 if greedy == best_arm else 0
    final = choose(DECISION, PATHS, {"s": 1}, LedgerStats.from_receipts(ledger, decay=decay))["chosen_path"]
    return {"decay": decay, "cumulative_regret": round(cum_regret, 2),
            "regret_before_shift": round(regret_before, 2), "regret_after_shift": round(regret_after, 2),
            "final_choice": final, "final_is_new_best": final == max(TRUE_AFTER, key=TRUE_AFTER.get),
            "correct_choice_fraction_late": round(correct_after / max(1, ROUNDS - (ROUNDS // 2 + 50)), 3)}


def run() -> dict:
    adaptive = simulate(decay=0.9, seed=7)
    sticky = simulate(decay=1.0, seed=7)
    # random baseline regret (expected)
    rng = random.Random(7)
    rnd_regret = 0.0
    for t in range(ROUNDS):
        true = TRUE_BEFORE if t < ROUNDS // 2 else TRUE_AFTER
        arm = rng.choice(PATHS)["path_id"]
        rnd_regret += max(true.values()) - true[arm]
    return {
        "run_id": "banditbench", "rounds": ROUNDS, "epsilon": EPSILON,
        "shift_at": ROUNDS // 2,
        "adaptive_decay_0_9": adaptive, "sticky_decay_1_0": sticky,
        "random_baseline_regret": round(rnd_regret, 2),
        "verdict": {
            "engine_learns_pre_shift": adaptive["regret_before_shift"] < 0.4 * (rnd_regret / 2),
            "decay_recovers_faster": adaptive["regret_after_shift"] < sticky["regret_after_shift"],
            "adaptive_final_is_new_best": adaptive["final_is_new_best"],
        },
        "candidate": True, "serves_truth": False,
        "honesty_notes": [
            "true success rates are hidden from the engine; it sees only receipts",
            "regret is measured against an oracle that always plays the true best arm",
            "the world shifts at the midpoint; decay=0.9 forgets stale receipts, decay=1.0 does not",
            "seeded PRNG - the run is deterministic and replayable",
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
        (out / "bandit_benchmark.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    v = result["verdict"]
    return 0 if (v["engine_learns_pre_shift"] and v["decay_recovers_faster"]
                 and v["adaptive_final_is_new_best"]) else 1


if __name__ == "__main__":
    sys.exit(main())
