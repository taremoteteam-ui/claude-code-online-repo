#!/usr/bin/env python3
"""Contextual-learning benchmark for the decision engine.

The engine claims its receipts can be CONDITIONED on a context signature so the
selection policy learns a DIFFERENT best path per context - something a single
global (non-contextual) win-rate aggregate provably cannot do when the best arm
flips between contexts. This benchmark MEASURES that instead of asserting it.

Setup: 3 equal-cost arms and two contexts, mode="A" and mode="B". The TRUE
hidden success rates flip the winner across contexts - in A the best arm is
arm0, in B it is arm2 - and the middle arm is mediocre in both. Two policies run
the same alternating stream of contexts under an epsilon of random exploration:

  * CONTEXT-CONDITIONED: exploit uses LedgerStats.from_receipts(ledger,
    only_context=sig) - it scores each arm on the receipts seen IN THIS CONTEXT.
  * GLOBAL control: exploit uses LedgerStats.from_receipts(ledger) with no
    only_context - it mixes both contexts into one aggregate, so arm0 and arm2
    tie globally (~0.575 each) and it plays one of them everywhere, eating the
    other context's regret.

We track cumulative regret vs a PER-CONTEXT oracle (the true best arm in the
mode actually presented that round). The contextual policy should both (1) learn
the correct best arm for A AND B and (2) accrue strictly less total regret than
the global control. Deterministic seeded PRNG - replayable. Zero model calls.

Usage: python3 scripts/run_contextual_bandit_benchmark.py --self-test
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from primitives.decision_engine import (  # noqa: E402
    LedgerStats, choose, context_signature)

DID = "decision:ctxbandit"
ROUNDS = 600
EPSILON = 0.10
SEED = 7
CTX_KEYS = ["mode"]

# equal cost so the argmax is driven purely by learned (per-context) win-rate,
# not the cost term - every arm normalizes to the same cost.
PATHS = [{"record_type": "execution_path", "path_id": f"path:cb.arm{i}",
          "decision_id": DID, "title": f"arm{i}",
          "method": "a bandit arm in this simulation over ten chars",
          "applicability": {"requires_keys": [], "conditions": []},
          "cost_model": {"tokens": 0, "latency_ms": 10, "side_effect_risk": "none"},
          "reversibility": "reversible", "preference_rank": i, "deterministic": True,
          "expected_receipts": ["win"], "version": "0", "candidate": True,
          "serves_truth": False}
         for i in range(3)]

DECISION = {"decision_id": DID, "context_signature": CTX_KEYS,
            "contract": {"input": "x", "output": "y",
                         "win_definition": "arm succeeds in this context",
                         "consumes": [], "produces": ["z"]},
            "selection_policy": "argmax_receipts", "default_path": "path:cb.arm0"}

# TRUE hidden success rates: the best arm DIFFERS by context (A->arm0, B->arm2),
# and the middle arm is mediocre in both. Hidden from the engine.
TRUE = {
    "A": {"path:cb.arm0": 0.85, "path:cb.arm1": 0.50, "path:cb.arm2": 0.30},
    "B": {"path:cb.arm0": 0.30, "path:cb.arm1": 0.50, "path:cb.arm2": 0.85},
}
BEST_ARM = {mode: max(rates, key=rates.get) for mode, rates in TRUE.items()}


def simulate(contextual: bool, seed: int) -> dict:
    """Run ROUNDS of epsilon-greedy selection. When contextual is True the
    exploit step conditions the ledger on the current context signature; when
    False it uses the global (context-blind) aggregate."""
    rng = random.Random(seed)
    ledger: list[dict] = []
    seq = 0
    regret = {"A": 0.0, "B": 0.0}
    total_regret = 0.0
    for t in range(ROUNDS):
        mode = "A" if t % 2 == 0 else "B"
        ctx = {"mode": mode}
        sig = context_signature(DID, ctx, CTX_KEYS)
        true = TRUE[mode]
        best_rate = max(true.values())
        if rng.random() < EPSILON:
            arm = rng.choice(PATHS)["path_id"]                       # explore
        else:
            if contextual:
                stats = LedgerStats.from_receipts(ledger, only_context=sig)
            else:
                stats = LedgerStats.from_receipts(ledger)
            arm = choose(DECISION, PATHS, ctx, stats)["chosen_path"]  # exploit
        rate = true[arm]
        win = 1.0 if rng.random() < rate else 0.0
        ledger.append({"decision_id": DID, "path_id": arm, "context_signature": sig,
                       "sequence": seq, "applicable": True, "chosen": True,
                       "proved": win > 0, "win_score": win, "cost_observed": 10,
                       "candidate": True, "serves_truth": False})
        seq += 1
        r = best_rate - rate                     # regret vs this context's oracle
        regret[mode] += r
        total_regret += r

    # Final greedy choice per context under context-conditioned stats.
    final_choice = {}
    for mode in ("A", "B"):
        sig = context_signature(DID, {"mode": mode}, CTX_KEYS)
        cstats = LedgerStats.from_receipts(ledger, only_context=sig)
        final_choice[mode] = choose(DECISION, PATHS, {"mode": mode}, cstats)["chosen_path"]
    return {"contextual": contextual,
            "regret_A": round(regret["A"], 3), "regret_B": round(regret["B"], 3),
            "total_regret": round(total_regret, 3),
            "final_choice": final_choice, "ledger_size": len(ledger)}


def run() -> dict:
    contextual = simulate(contextual=True, seed=SEED)
    glob = simulate(contextual=False, seed=SEED)

    final = contextual["final_choice"]
    learns_both = (final["A"] == BEST_ARM["A"] and final["B"] == BEST_ARM["B"])
    beats_global = contextual["total_regret"] < glob["total_regret"]

    return {
        "record_type": "contextual_bandit_benchmark",
        "run_id": "ctxbanditbench", "rounds": ROUNDS, "epsilon": EPSILON,
        "seed": SEED, "arms": len(PATHS), "contexts": sorted(TRUE.keys()),
        "true_best_arm_per_context": BEST_ARM,
        "contextual_regret_A": contextual["regret_A"],
        "contextual_regret_B": contextual["regret_B"],
        "contextual_total_regret": contextual["total_regret"],
        "global_total_regret": glob["total_regret"],
        "contextual_final_choice": contextual["final_choice"],
        "global_final_choice_context_conditioned_view": glob["final_choice"],
        "verdict": {
            "contextual_learns_both": learns_both,
            "contextual_beats_global": beats_global,
        },
        "candidate": True, "serves_truth": False,
        "honesty_notes": [
            "true per-context success rates are hidden from the engine; it sees only receipts",
            "regret is measured against a per-context oracle (the true best arm in the mode presented)",
            "the global control uses the same stream and epsilon but a context-blind aggregate",
            "arms are equal-cost so the argmax is driven purely by learned win-rate",
            "seeded PRNG (random.Random) only - no global random; the run is deterministic and replayable",
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
        (out / "contextual_bandit_benchmark.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8")
    v = result["verdict"]
    return 0 if (v["contextual_learns_both"] and v["contextual_beats_global"]) else 1


if __name__ == "__main__":
    sys.exit(main())
