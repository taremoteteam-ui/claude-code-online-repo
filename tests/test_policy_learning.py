"""Contract tests for counterfactual risk minimization (policy learning)."""

import random
import unittest

from primitives.policy_learning import (crm_score, learn_naive_ips_policy,
                                        learn_policy)

ACTIONS = ["a0", "a1"]
CONTEXTS = ["_"]
Q = {"_": {"a0": 0.0, "a1": 1.0}}   # a1 always rewards, a0 never
BEHAVIOR = {"a0": 0.5, "a1": 0.5}


def _clean_log(seed, n):
    rng = random.Random(seed)
    acts, ap = list(BEHAVIOR), [BEHAVIOR[a] for a in BEHAVIOR]
    log = []
    for _ in range(n):
        a = rng.choices(acts, weights=ap, k=1)[0]
        r = 1.0 if rng.random() < Q["_"][a] else 0.0
        log.append({"context": "_", "action": a, "reward": r, "propensity": BEHAVIOR[a]})
    return log


class PolicyLearningTests(unittest.TestCase):
    def test_recovers_optimal_on_clean_data(self):
        log = _clean_log(seed=1, n=300)
        learned = learn_policy(log, CONTEXTS, ACTIONS, lam=0.0)
        self.assertEqual(learned["policy"], {"_": "a1"})

    def test_penalty_never_increases_score(self):
        # crm_score = value - lambda * radius, radius >= 0, so a positive lambda
        # can only lower (or equal) the score of a fixed policy. Pins the sign.
        log = _clean_log(seed=2, n=300)
        base = crm_score(log, {"_": "a1"}, lam=0.0)
        penalized = crm_score(log, {"_": "a1"}, lam=0.5)
        self.assertLessEqual(penalized, base)

    def test_learning_is_deterministic(self):
        log = _clean_log(seed=3, n=200)
        a = learn_policy(log, CONTEXTS, ACTIONS, lam=0.3)
        b = learn_policy(log, CONTEXTS, ACTIONS, lam=0.3)
        self.assertEqual(a, b)

    def test_naive_ips_returns_valid_policy(self):
        log = _clean_log(seed=4, n=200)
        learned = learn_naive_ips_policy(log, CONTEXTS, ACTIONS)
        self.assertIn(learned["policy"]["_"], ACTIONS)
        self.assertEqual(learned["policy"], {"_": "a1"})


if __name__ == "__main__":
    unittest.main()
