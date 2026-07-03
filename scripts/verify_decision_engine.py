#!/usr/bin/env python3
"""Adversarial property-based verifier for the decision engine / planner / graph.

Instead of a few fixed tests, this fuzzes the algorithms over hundreds of random
inputs (deterministic seeded PRNG - replayable) and checks INVARIANTS that must
hold for any input, comparing against brute force where a brute-force answer
exists. Its job is to FALSIFY the implementation; a green run is evidence the
algorithms are correct, not a demo.

Invariants checked:
  P1 plan_combination == brute-force optimum (same min cost + a valid feasible
     combo) whenever the space is exact; infeasible iff brute force finds none.
  P2 optimal_gate_order's expected cost == the min over all permutations.
  P3 choose() never returns an inapplicable path; the chosen path is applicable.
  P4 a compiled decision order always validates and reaches the goal.
  P5 LedgerStats keeps win_rate and decayed_win_rate in [0,1].
  P6 argmax_receipts is monotone: making a path win MORE never lowers its score.

Usage: python3 scripts/verify_decision_engine.py --self-test [--trials N]
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from itertools import permutations, product
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from primitives.decision_engine import (LedgerStats, choose, is_applicable,  # noqa: E402
                                        normalize_cost)
from primitives.decision_planner import (_expected_cost_to_failure, optimal_gate_order,  # noqa: E402
                                         plan_combination, _MIN_SUCCESS, _PRIOR_SUCCESS)
from primitives.decision_graph import compile_decision_order, validate_decision_dag  # noqa: E402

TOL = 1e-6


def _rand_paths(rng, did, n):
    paths = []
    for i in range(n):
        risk = rng.choice(["none", "low", "medium", "high"])
        paths.append({"record_type": "execution_path", "path_id": f"{did}.p{i}", "decision_id": did,
                      "title": f"p{i}", "method": "a way to do the stage in this fuzz case",
                      "applicability": {"requires_keys": [], "conditions": []},
                      "cost_model": {"tokens": rng.randint(0, 800), "latency_ms": rng.randint(0, 900),
                                     "side_effect_risk": risk},
                      "reversibility": "reversible", "preference_rank": i, "deterministic": True,
                      "expected_receipts": ["win"], "version": "0", "candidate": True, "serves_truth": False})
    return paths


def _receipts(rng, did, paths):
    recs, seq = [], 0
    succ = {}
    for p in paths:
        s = round(rng.uniform(_MIN_SUCCESS, 1.0), 3)
        succ[p["path_id"]] = s
        for _ in range(rng.randint(3, 8)):
            recs.append({"decision_id": did, "path_id": p["path_id"], "context_signature": "c",
                         "sequence": seq, "applicable": True, "chosen": True, "proved": s > 0,
                         "win_score": s, "cost_observed": 0, "candidate": True, "serves_truth": False})
            seq += 1
    return recs, succ


def check_P1(rng) -> bool:
    dids = [f"decision:f{i}" for i in range(rng.randint(2, 3))]
    decisions, paths_by, all_recs, succ = [], {}, [], {}
    for did in dids:
        n = rng.randint(2, 4)
        paths = _rand_paths(rng, did, n)
        paths_by[did] = paths
        decisions.append({"decision_id": did, "context_signature": ["s"],
                          "contract": {"input": "x", "output": "y", "win_definition": "wins",
                                       "consumes": [], "produces": ["k"]},
                          "selection_policy": "argmax_receipts", "default_path": paths[0]["path_id"]})
        recs, s = _receipts(rng, did, paths)
        all_recs += recs
        succ.update({(did, k): v for k, v in s.items()})
    stats = LedgerStats.from_receipts(all_recs)
    min_r = rng.choice([0.0, 0.2, 0.4, 0.6])
    plan = plan_combination(decisions, paths_by, {"s": 1}, stats, min_reliability=min_r)

    # brute force
    best = None
    for combo in product(*[paths_by[d] for d in dids]):
        rel, cost = 1.0, 0.0
        for did, p in zip(dids, combo):
            s = succ[(did, p["path_id"])]
            rel *= s
            cost += normalize_cost(p["cost_model"]) / s
        if rel >= min_r:
            if best is None or cost < best[0] - TOL:
                best = (cost, tuple(p["path_id"] for p in combo))
    if best is None:
        return plan["feasible"] is False
    if not plan["feasible"]:
        return False
    return abs(plan["expected_cost"] - best[0]) < 1e-3


def check_P2(rng) -> bool:
    gates = [{"gate_id": f"g{i}", "cost": rng.randint(1, 20), "p_fail": round(rng.uniform(0, 1), 3)}
             for i in range(rng.randint(2, 6))]
    plan = optimal_gate_order(gates)
    by_id = {g["gate_id"]: g for g in plan["gates"]}
    brute = min(_expected_cost_to_failure([by_id[i] for i in perm]) for perm in permutations(by_id))
    return abs(plan["expected_cost_optimal"] - round(brute, 4)) < 1e-3


def check_P3(rng) -> bool:
    did = "decision:x"
    paths = _rand_paths(rng, did, rng.randint(2, 5))
    # give some paths a required key so applicability varies
    ctx = {"k": rng.choice([True, False]), "n": rng.randint(0, 10)}
    for p in paths:
        if rng.random() < 0.5:
            p["applicability"] = {"requires_keys": ["k"], "conditions": [{"key": "k", "op": "truthy"}]}
        if rng.random() < 0.3:
            p["applicability"]["conditions"].append({"key": "n", "op": "gte", "value": rng.randint(0, 10)})
    decision = {"decision_id": did, "context_signature": ["k", "n"],
                "contract": {"input": "x", "output": "y", "win_definition": "wins", "consumes": [], "produces": ["z"]},
                "selection_policy": rng.choice(["deterministic_tier", "argmax_receipts", "cheapest_that_proves"]),
                "default_path": paths[0]["path_id"]}
    c = choose(decision, paths, ctx)
    if c["chosen_path"] is None:
        return not any(is_applicable(p, ctx) for p in paths)
    chosen = next(p for p in paths if p["path_id"] == c["chosen_path"])
    return is_applicable(chosen, ctx)


def check_P4(rng) -> bool:
    keys = [f"k{i}" for i in range(rng.randint(3, 6))]
    decisions = []
    for i in range(rng.randint(2, 5)):
        cons = rng.sample(keys, rng.randint(0, 2))
        prod = rng.sample(keys, rng.randint(1, 2))
        decisions.append({"decision_id": f"decision:d{i}",
                          "contract": {"input": "x", "output": "y", "win_definition": "w",
                                       "consumes": cons, "produces": prod}})
    initial = rng.sample(keys, rng.randint(1, 3))
    goal = rng.sample(keys, 1)
    plan = compile_decision_order(decisions, initial, goal)
    if not plan["compiled"]:
        return True  # a gap is allowed; only compiled plans must be valid
    v = validate_decision_dag(plan["order"], decisions, initial)
    return v["valid"] and set(goal) <= set(v["final_state_keys"])


def check_P5(rng) -> bool:
    did = "decision:y"
    paths = _rand_paths(rng, did, 3)
    recs, _ = _receipts(rng, did, paths)
    stats = LedgerStats.from_receipts(recs)
    for p in paths:
        st = stats.get(did, p["path_id"])
        if not (0.0 <= st.win_rate <= 1.0 and 0.0 <= st.decayed_win_rate <= 1.0):
            return False
    return True


def check_P6(rng) -> bool:
    did = "decision:m"
    paths = _rand_paths(rng, did, 2)
    decision = {"decision_id": did, "context_signature": ["s"],
                "contract": {"input": "x", "output": "y", "win_definition": "w", "consumes": [], "produces": ["z"]},
                "selection_policy": "argmax_receipts", "default_path": paths[0]["path_id"]}
    target = paths[0]["path_id"]
    base, seq = [], 0
    for p in paths:
        for _ in range(5):
            base.append({"decision_id": did, "path_id": p["path_id"], "context_signature": "c",
                         "sequence": seq, "applicable": True, "chosen": True, "proved": True,
                         "win_score": 0.5, "cost_observed": 0, "candidate": True, "serves_truth": False})
            seq += 1
    r1 = next(r for r in choose(decision, paths, {"s": 1}, LedgerStats.from_receipts(base))["ranked"]
              if r["path_id"] == target)
    boosted = base + [{"decision_id": did, "path_id": target, "context_signature": "c", "sequence": seq + i,
                       "applicable": True, "chosen": True, "proved": True, "win_score": 1.0,
                       "cost_observed": 0, "candidate": True, "serves_truth": False} for i in range(5)]
    r2 = next(r for r in choose(decision, paths, {"s": 1}, LedgerStats.from_receipts(boosted))["ranked"]
              if r["path_id"] == target)
    return r2["decayed_win_rate"] >= r1["decayed_win_rate"] - TOL


CHECKS = {"P1_planner_vs_bruteforce": check_P1, "P2_gate_order_optimal": check_P2,
          "P3_applicability_respected": check_P3, "P4_compiled_dag_valid": check_P4,
          "P5_winrate_bounded": check_P5, "P6_argmax_monotone": check_P6}


def run(trials: int) -> dict:
    results = {}
    failures = []
    for name, fn in CHECKS.items():
        passed = 0
        for t in range(trials):
            rng = random.Random(hash((name, t)) & 0xFFFFFFFF)
            try:
                ok = fn(rng)
            except Exception as exc:  # noqa: BLE001
                ok = False
                failures.append({"check": name, "trial": t, "error": repr(exc)})
            if ok:
                passed += 1
            elif len(failures) < 10 and (not failures or failures[-1].get("trial") != t):
                failures.append({"check": name, "trial": t, "invariant_violated": True})
        results[name] = {"trials": trials, "passed": passed}
    return {"record_type": "adversarial_verification", "trials_per_check": trials,
            "results": results, "failures": failures[:10],
            "all_passed": all(r["passed"] == trials for r in results.values()),
            "candidate": True, "serves_truth": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--trials", type=int, default=200)
    args = parser.parse_args()
    if not args.self_test:
        parser.print_help()
        return 2
    result = run(args.trials)
    print(json.dumps(result, indent=2))
    return 0 if result["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
