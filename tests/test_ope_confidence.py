"""Contract tests for OPE confidence intervals + the overlap diagnostic."""

import math
import unittest

from primitives.off_policy_estimators import dr_value
from primitives.ope_confidence import (bootstrap_ci, dr_confidence,
                                        dr_per_sample, effective_sample_size,
                                        empirical_bernstein_radius,
                                        importance_weights)

ACTIONS = ["a0", "a1"]
LOGS = [
    {"context": "x", "action": "a1", "reward": 0.8, "propensity": 0.5},
    {"context": "x", "action": "a0", "reward": 0.2, "propensity": 0.5},
]


def target_a1(context):
    return {"a1": 1.0}


def zero_model(context, action):
    return 0.0


class EssTests(unittest.TestCase):
    def test_equal_weights_give_full_ess(self):
        self.assertEqual(effective_sample_size([2, 2, 2, 2])["ess"], 4)

    def test_one_hot_weights_give_ess_one(self):
        self.assertEqual(effective_sample_size([0, 0, 5, 0])["ess"], 1)

    def test_importance_weights_match_hand_calc(self):
        self.assertEqual(importance_weights(LOGS, target_a1), [2.0, 0.0])


class PerSampleTests(unittest.TestCase):
    def test_dr_per_sample_mean_equals_dr_value(self):
        terms = dr_per_sample(LOGS, target_a1, zero_model, ACTIONS)
        self.assertAlmostEqual(sum(terms) / len(terms),
                               dr_value(LOGS, target_a1, zero_model, ACTIONS))


class CiTests(unittest.TestCase):
    def test_bootstrap_ci_brackets_the_mean_and_is_deterministic(self):
        vals = [0.1 * i for i in range(50)]
        a = bootstrap_ci(vals, seed=1)
        b = bootstrap_ci(vals, seed=1)
        self.assertEqual(a, b)                    # deterministic
        self.assertLessEqual(a["lo"], a["mean"])
        self.assertLessEqual(a["mean"], a["hi"])

    def test_empirical_bernstein_radius_shrinks_with_n(self):
        small = [float(i % 2) for i in range(40)]
        large = [float(i % 2) for i in range(4000)]
        self.assertGreater(empirical_bernstein_radius(small),
                           empirical_bernstein_radius(large))

    def test_radius_is_infinite_for_singleton(self):
        self.assertTrue(math.isinf(empirical_bernstein_radius([1.0])))


class TrustTests(unittest.TestCase):
    def _logs(self, n_match, w_match_propensity, n_miss):
        match = [{"context": "x", "action": "a1", "reward": 1.0,
                  "propensity": w_match_propensity}] * n_match
        miss = [{"context": "x", "action": "a0", "reward": 0.0, "propensity": 0.5}] * n_miss
        return match + miss

    def test_high_overlap_is_trustworthy(self):
        rep = dr_confidence(self._logs(250, 0.5, 250), target_a1, zero_model, ACTIONS,
                            n_boot=100, seed=2)
        self.assertGreaterEqual(rep["overlap"]["ess"], 200)
        self.assertTrue(rep["trustworthy"])

    def test_low_overlap_is_flagged_untrustworthy(self):
        # only 10 matching samples, each with a huge weight -> ESS collapses
        rep = dr_confidence(self._logs(10, 0.02, 490), target_a1, zero_model, ACTIONS,
                            n_boot=100, seed=3)
        self.assertLess(rep["overlap"]["ess"], 200)
        self.assertFalse(rep["trustworthy"])


if __name__ == "__main__":
    unittest.main()
