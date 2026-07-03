"""Contract tests for off-policy / counterfactual policy evaluation."""

import unittest

from primitives.policy_evaluation import (POLICY_PORTFOLIO, evaluate, make_log,
                                          replay, select_best)

ARMS = ["path:t.a0", "path:t.a1", "path:t.a2"]
PATHS = [{"record_type": "execution_path", "path_id": a, "decision_id": "decision:t",
          "title": a, "method": "arm", "applicability": {"requires_keys": [], "conditions": []},
          "cost_model": {"tokens": 0, "latency_ms": 10, "side_effect_risk": "none"},
          "reversibility": "reversible", "preference_rank": i, "deterministic": True,
          "expected_receipts": ["win"], "version": "0", "candidate": True, "serves_truth": False}
         for i, a in enumerate(ARMS)]
DECISION = {"decision_id": "decision:t", "learn_keys": ["c"],
            "contract": {"input": "x", "output": "y", "win_definition": "wins"},
            "selection_policy": "argmax_receipts", "default_path": "path:t.a0"}


def _fixed_ctx(t, rng):
    return {"c": "S"}


def _arm2_dominates(t, ctx):
    return {"path:t.a0": 0.2, "path:t.a1": 0.4, "path:t.a2": 0.9}


def _context_dependent(t, ctx):
    if ctx["c"] == "A":
        return {"path:t.a0": 0.9, "path:t.a1": 0.4, "path:t.a2": 0.2}
    return {"path:t.a0": 0.2, "path:t.a1": 0.4, "path:t.a2": 0.9}


def _alt_ctx(t, rng):
    return {"c": "A" if rng.random() < 0.5 else "B"}


class PolicyEvaluationTests(unittest.TestCase):
    def test_regret_is_nonnegative_for_every_policy(self):
        log = make_log(120, ARMS, _arm2_dominates, _fixed_ctx, seed=1)
        results = evaluate(DECISION, PATHS, log)
        for name, m in results.items():
            self.assertGreaterEqual(m["cumulative_regret"], 0.0, name)

    def test_replay_is_deterministic(self):
        log = make_log(120, ARMS, _arm2_dominates, _fixed_ctx, seed=1)
        a = replay(POLICY_PORTFOLIO[2], DECISION, PATHS, log)   # argmax_receipts
        b = replay(POLICY_PORTFOLIO[2], DECISION, PATHS, log)
        self.assertEqual(a, b)

    def test_make_log_is_deterministic_per_seed(self):
        self.assertEqual(make_log(50, ARMS, _arm2_dominates, _fixed_ctx, seed=5),
                         make_log(50, ARMS, _arm2_dominates, _fixed_ctx, seed=5))

    def test_learner_beats_non_learning_tier(self):
        # arm2 dominates; a receipt-driven learner must converge to it and accrue
        # far less regret than the tier baseline that is stuck on arm0.
        log = make_log(300, ARMS, _arm2_dominates, _fixed_ctx, seed=3)
        results = evaluate(DECISION, PATHS, log)
        self.assertLess(results["argmax_receipts"]["cumulative_regret"],
                        results["deterministic_tier"]["cumulative_regret"])

    def test_context_conditioning_beats_global_when_best_arm_flips_by_context(self):
        log = make_log(400, ARMS, _context_dependent, _alt_ctx, seed=7)
        results = evaluate(DECISION, PATHS, log)
        self.assertLess(results["argmax_contextual"]["cumulative_regret"],
                        results["argmax_receipts"]["cumulative_regret"])

    def test_select_best_returns_min_regret_policy(self):
        results = {"p_hi": {"cumulative_regret": 10.0}, "p_lo": {"cumulative_regret": 2.0},
                   "p_mid": {"cumulative_regret": 5.0}}
        self.assertEqual(select_best(results), "p_lo")


if __name__ == "__main__":
    unittest.main()
