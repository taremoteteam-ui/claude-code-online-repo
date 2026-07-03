"""Tests for the decision planner: gate ordering and combination search are
verified against brute force, so 'optimal' is checked, not asserted."""

import unittest
from itertools import permutations, product

from primitives.decision_engine import LedgerStats
from primitives.decision_planner import (_expected_cost_to_failure, optimal_gate_order,
                                         plan_combination)


def _paths(did, specs):
    # specs: [(path_id, cost_units)]
    return [{"record_type": "execution_path", "path_id": pid, "decision_id": did, "title": pid,
             "method": "one way to do the stage here",
             "applicability": {"requires_keys": [], "conditions": []},
             "cost_model": {"tokens": 0, "latency_ms": c * 1000, "side_effect_risk": "none"},
             "reversibility": "reversible", "preference_rank": 0, "deterministic": True,
             "expected_receipts": ["win"], "version": "0", "candidate": True, "serves_truth": False}
            for pid, c in specs]


def _decision(did):
    return {"decision_id": did, "title": did, "question": "which path for this stage",
            "regime": "runtime", "context_signature": ["s"],
            "contract": {"input": "x", "output": "y", "win_definition": "path succeeds"},
            "selection_policy": "argmax_receipts", "default_path": None,
            "candidate": True, "serves_truth": False}


def _stats(success_by_path):
    recs = []
    seq = 0
    for (did, pid), s in success_by_path.items():
        for _ in range(5):
            recs.append({"decision_id": did, "path_id": pid, "context_signature": "c",
                         "sequence": seq, "applicable": True, "chosen": True, "proved": s > 0,
                         "win_score": s, "cost_observed": 0, "candidate": True, "serves_truth": False})
            seq += 1
    return LedgerStats.from_receipts(recs)


class GateOrderTests(unittest.TestCase):
    def test_matches_bruteforce_minimum(self):
        gates = [{"gate_id": "a", "cost": 1, "p_fail": 0.5},
                 {"gate_id": "b", "cost": 10, "p_fail": 0.9},
                 {"gate_id": "c", "cost": 2, "p_fail": 0.1},
                 {"gate_id": "d", "cost": 3, "p_fail": 0.3}]
        plan = optimal_gate_order(gates)
        by_id = {g["gate_id"]: g for g in plan["gates"]}
        best = min(_expected_cost_to_failure([by_id[i] for i in perm])
                   for perm in permutations(by_id))
        self.assertAlmostEqual(plan["expected_cost_optimal"], round(best, 4), places=4)

    def test_cheapest_most_likely_to_fail_first(self):
        gates = [{"gate_id": "expensive", "cost": 20, "p_fail": 0.2},
                 {"gate_id": "cheap_flaky", "cost": 1, "p_fail": 0.6}]
        self.assertEqual(optimal_gate_order(gates)["order"][0], "cheap_flaky")


class CombinationTests(unittest.TestCase):
    def setUp(self):
        self.decisions = [_decision("d:f"), _decision("d:p")]
        self.paths = {"d:f": _paths("d:f", [("d:f.cheap", 1), ("d:f.reliable", 4)]),
                      "d:p": _paths("d:p", [("d:p.cheap", 1), ("d:p.reliable", 5)])}
        self.stats = _stats({("d:f", "d:f.cheap"): 0.6, ("d:f", "d:f.reliable"): 0.95,
                             ("d:p", "d:p.cheap"): 0.7, ("d:p", "d:p.reliable"): 0.98})

    def _brute(self, min_r, budget=None):
        from primitives.decision_engine import normalize_cost
        succ = {("d:f", "d:f.cheap"): 0.6, ("d:f", "d:f.reliable"): 0.95,
                ("d:p", "d:p.cheap"): 0.7, ("d:p", "d:p.reliable"): 0.98}
        best = None
        for fp in self.paths["d:f"]:
            for pp in self.paths["d:p"]:
                s = succ[("d:f", fp["path_id"])] * succ[("d:p", pp["path_id"])]
                cost = (normalize_cost(fp["cost_model"]) / succ[("d:f", fp["path_id"])]
                        + normalize_cost(pp["cost_model"]) / succ[("d:p", pp["path_id"])])
                if s >= min_r and (budget is None or cost <= budget):
                    if best is None or cost < best[0]:
                        best = (cost, fp["path_id"], pp["path_id"])
        return best

    def test_combination_matches_bruteforce(self):
        plan = plan_combination(self.decisions, self.paths, {"s": 1}, self.stats, min_reliability=0.6)
        brute = self._brute(0.6)
        self.assertTrue(plan["feasible"])
        self.assertAlmostEqual(plan["expected_cost"], round(brute[0], 4), places=3)
        self.assertEqual(plan["chosen"]["d:f"], brute[1])
        self.assertEqual(plan["chosen"]["d:p"], brute[2])

    def test_reliability_gate_can_be_infeasible(self):
        plan = plan_combination(self.decisions, self.paths, {"s": 1}, self.stats, min_reliability=0.999)
        self.assertFalse(plan["feasible"])

    def test_compatibility_constraint_respected(self):
        def incompatible(combo):
            return not (combo.get("d:f") == "d:f.cheap")  # forbid the cheapest fetch
        plan = plan_combination(self.decisions, self.paths, {"s": 1}, self.stats,
                                min_reliability=0.0, compatible=incompatible)
        self.assertEqual(plan["chosen"]["d:f"], "d:f.reliable")


if __name__ == "__main__":
    unittest.main()
