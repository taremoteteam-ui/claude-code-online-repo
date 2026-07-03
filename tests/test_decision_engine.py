"""Contract tests for the domain-agnostic decision engine + supervisor."""

import unittest

from primitives.decision_engine import (LedgerStats, choose, context_signature,
                                        is_applicable, normalize_cost)
from primitives.decision_supervisor import supervise


def _decision(policy="argmax_receipts", default="path:d.a", **extra):
    d = {"decision_id": "decision:d", "title": "t", "question": "which one to use here",
         "regime": "runtime", "context_signature": ["k"],
         "contract": {"input": "x", "output": "y", "win_definition": "wins the task"},
         "selection_policy": policy, "default_path": default,
         "candidate": True, "serves_truth": False}
    d.update(extra)
    return d


def _path(pid, rank, requires=None, conds=None, cost=None):
    return {"record_type": "execution_path", "path_id": pid, "decision_id": "decision:d",
            "title": pid, "method": "does the thing in some way",
            "applicability": {"requires_keys": requires or [], "conditions": conds or []},
            "cost_model": cost or {"tokens": 0, "latency_ms": 5, "side_effect_risk": "none"},
            "reversibility": "reversible", "preference_rank": rank, "deterministic": True,
            "expected_receipts": ["win"], "version": "0", "candidate": True, "serves_truth": False}


def _rcpt(pid, seq, win, ctx="ctx:0", cost=5.0):
    return {"decision_id": "decision:d", "path_id": pid, "context_signature": ctx,
            "sequence": seq, "applicable": True, "chosen": False, "proved": win > 0,
            "win_score": win, "cost_observed": cost, "candidate": True, "serves_truth": False}


class DecisionEngineTests(unittest.TestCase):
    def test_applicability_predicate(self):
        p = _path("path:d.a", 0, requires=["k"], conds=[{"key": "k", "op": "gte", "value": 3}])
        self.assertTrue(is_applicable(p, {"k": 5}))
        self.assertFalse(is_applicable(p, {"k": 1}))
        self.assertFalse(is_applicable(p, {}))

    def test_cost_normalization_orders(self):
        cheap = normalize_cost({"tokens": 0, "latency_ms": 5, "side_effect_risk": "none"})
        dear = normalize_cost({"tokens": 600, "latency_ms": 900, "side_effect_risk": "medium"})
        self.assertLess(cheap, dear)

    def test_cold_start_prefers_default(self):
        d = _decision(default="path:d.b")
        paths = [_path("path:d.a", 0), _path("path:d.b", 1)]
        c = choose(d, paths, {"k": 1})
        self.assertEqual(c["chosen_path"], "path:d.b")

    def test_argmax_prefers_higher_winrate_when_warm(self):
        d = _decision(default="path:d.a")
        paths = [_path("path:d.a", 0), _path("path:d.b", 1)]
        recs = [_rcpt("path:d.a", s, 0.4) for s in range(6)] + \
               [_rcpt("path:d.b", s + 6, 0.9) for s in range(6)]
        stats = LedgerStats.from_receipts(recs)
        c = choose(d, paths, {"k": 1}, stats)
        self.assertEqual(c["chosen_path"], "path:d.b")

    def test_deterministic_tier_ignores_receipts(self):
        d = _decision(policy="deterministic_tier", default="path:d.a")
        paths = [_path("path:d.a", 0), _path("path:d.b", 1)]
        recs = [_rcpt("path:d.b", s, 1.0) for s in range(9)]  # b wins every time
        stats = LedgerStats.from_receipts(recs)
        c = choose(d, paths, {"k": 1}, stats)
        self.assertEqual(c["chosen_path"], "path:d.a")  # still cheapest tier

    def test_context_conditioning_filters(self):
        recs = [_rcpt("path:d.a", 0, 0.2, ctx="ctx:A"), _rcpt("path:d.a", 1, 0.9, ctx="ctx:B")]
        only_b = LedgerStats.from_receipts(recs, only_context="ctx:B")
        self.assertEqual(only_b.get("decision:d", "path:d.a").win_rate, 0.9)

    def test_no_applicable_path_returns_none(self):
        d = _decision()
        paths = [_path("path:d.a", 0, requires=["z"]), _path("path:d.b", 1, requires=["z"])]
        c = choose(d, paths, {"k": 1})
        self.assertIsNone(c["chosen_path"])

    def test_ranking_is_disclosed(self):
        d = _decision()
        paths = [_path("path:d.a", 0), _path("path:d.b", 1)]
        c = choose(d, paths, {"k": 1})
        self.assertEqual(len(c["ranked"]), 2)
        self.assertTrue(all("norm_cost" in r and "decayed_win_rate" in r for r in c["ranked"]))


class SupervisorTests(unittest.TestCase):
    def test_promotes_better_challenger(self):
        d = _decision(default="path:d.a")
        paths = [_path("path:d.a", 0), _path("path:d.b", 1)]
        recs = [_rcpt("path:d.a", s, 0.3) for s in range(6)] + \
               [_rcpt("path:d.b", s + 6, 0.9) for s in range(6)]
        rep = supervise([d], paths, recs)
        kinds = [(r["kind"], r["to_path"]) for r in rep["recommendations"]]
        self.assertIn(("promote_default", "path:d.b"), kinds)

    def test_cold_decision_untrusted(self):
        d = _decision()
        paths = [_path("path:d.a", 0), _path("path:d.b", 1)]
        rep = supervise([d], paths, [])
        self.assertEqual(rep["self_awareness"]["decisions_cold"], 1)

    def test_drift_reopens_exploration(self):
        d = _decision(default="path:d.a")
        paths = [_path("path:d.a", 0), _path("path:d.b", 1)]
        # a: strong early, collapses recently -> drift
        recs = [_rcpt("path:d.a", s, 1.0) for s in range(5)] + \
               [_rcpt("path:d.a", s + 5, 0.0) for s in range(5)]
        rep = supervise([d], paths, recs)
        self.assertTrue(any(r["kind"] == "reopen_exploration" for r in rep["recommendations"]))


if __name__ == "__main__":
    unittest.main()
