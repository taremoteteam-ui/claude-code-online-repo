"""Contract tests for off-policy estimators.

Uses a tiny hand-computable environment so every assertion is exact (no
tolerance): one context, two actions, q = {a0: 0.2, a1: 0.8}, uniform behavior
policy (propensity 0.5 each), target = always a1. True value V(target) = 0.8.

Two noiseless logged samples (reward == q, still partial feedback: each row
observes only its own action):
    (x, a1, 0.8, 0.5)   and   (x, a0, 0.2, 0.5)
"""

import unittest

from primitives.off_policy_estimators import (dm_value, dr_value,
                                              fit_reward_model, ips_value,
                                              snips_value, true_value)

ACTIONS = ["a0", "a1"]
Q = {"x": {"a0": 0.2, "a1": 0.8}}
CTX_W = {"x": 1.0}
LOGS = [
    {"context": "x", "action": "a1", "reward": 0.8, "propensity": 0.5},
    {"context": "x", "action": "a0", "reward": 0.2, "propensity": 0.5},
]


def target_a1(context):
    return {"a1": 1.0}


def perfect_model(context, action):
    return Q[context][action]


def constant_half(context, action):
    return 0.5


def zero_model(context, action):
    return 0.0


class OffPolicyEstimatorTests(unittest.TestCase):
    def test_true_value(self):
        self.assertAlmostEqual(true_value(CTX_W, Q, target_a1, ACTIONS), 0.8)

    def test_ips_recovers_true_value_exactly(self):
        self.assertAlmostEqual(ips_value(LOGS, target_a1), 0.8)

    def test_snips_recovers_true_value_exactly(self):
        self.assertAlmostEqual(snips_value(LOGS, target_a1), 0.8)

    def test_dm_with_perfect_model_is_exact(self):
        self.assertAlmostEqual(dm_value(LOGS, target_a1, perfect_model, ACTIONS), 0.8)

    def test_dr_with_perfect_model_is_exact(self):
        self.assertAlmostEqual(dr_value(LOGS, target_a1, perfect_model, ACTIONS), 0.8)

    def test_dr_with_zero_model_reduces_to_ips(self):
        # zero reward model -> DR's baseline vanishes, correction == IPS
        self.assertAlmostEqual(dr_value(LOGS, target_a1, zero_model, ACTIONS), 0.8)

    def test_dm_is_biased_under_misspecification_but_dr_is_not(self):
        # constant-0.5 model: DM believes 0.5, DR corrects back to 0.8
        self.assertAlmostEqual(dm_value(LOGS, target_a1, constant_half, ACTIONS), 0.5)
        self.assertAlmostEqual(dr_value(LOGS, target_a1, constant_half, ACTIONS), 0.8)

    def test_full_support_guard(self):
        bad = [{"context": "x", "action": "a1", "reward": 0.8, "propensity": 0.0}]
        with self.assertRaises(ValueError):
            ips_value(bad, target_a1)

    def test_fit_reward_model_recovers_means(self):
        logs = [
            {"context": "x", "action": "a0", "reward": 0.0, "propensity": 0.5},
            {"context": "x", "action": "a0", "reward": 1.0, "propensity": 0.5},
            {"context": "x", "action": "a1", "reward": 1.0, "propensity": 0.5},
        ]
        model = fit_reward_model(logs, ACTIONS)
        self.assertAlmostEqual(model("x", "a0"), 0.5)
        self.assertAlmostEqual(model("x", "a1"), 1.0)
        self.assertAlmostEqual(model("x", "unseen"), 0.5)  # fallback


if __name__ == "__main__":
    unittest.main()
