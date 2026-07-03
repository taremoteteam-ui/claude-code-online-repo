"""Contract tests for Multiple-Path Development."""

import unittest

from primitives.multipath import (benchmark_paths, choose, run_with_fallback,
                                  select_portfolio)


def _narrow(s):
    return [int(x) for x in s.split(",")]


def _wide(s):
    import re
    parts = [p for p in re.split(r"[,\s]+", s.strip()) if p]
    try:
        return [int(p) for p in parts]
    except ValueError:
        return None


def _widest(s):
    import re
    return [int(x) for x in re.findall(r"-?\d+", s)]


PATHS = [
    {"path_id": "p.narrow", "impl": _narrow, "produces": "x.int_list", "cost_hint": 1.0},
    {"path_id": "p.wide", "impl": _wide, "produces": "x.int_list", "cost_hint": 1.5},
    {"path_id": "p.widest", "impl": _widest, "produces": "x.int_list", "cost_hint": 2.0},
]
CASES = [
    {"input": "1,2,3", "expected": [1, 2, 3]},
    {"input": "4 5 6", "expected": [4, 5, 6]},
    {"input": "x1y2", "expected": [1, 2]},
]


class BenchmarkTests(unittest.TestCase):
    def test_correctness_measured(self):
        cards = {c["path_id"]: c for c in benchmark_paths(PATHS, CASES)}
        self.assertAlmostEqual(cards["p.widest"]["correctness"], 1.0)
        self.assertAlmostEqual(cards["p.narrow"]["correctness"], 1 / 3, places=3)
        self.assertEqual(cards["p.narrow"]["errors"], 2)   # crashes on the two non-comma cases

    def test_score_fn_path(self):
        # score by fraction-of-expected-recovered instead of exact match
        def score(out, case):
            exp = case["expected"]
            got = out or []
            return len(set(got) & set(exp)) / len(exp)
        cards = {c["path_id"]: c for c in benchmark_paths(PATHS, CASES, score_fn=score)}
        self.assertGreater(cards["p.widest"]["mean_score"], cards["p.narrow"]["mean_score"])


class ChooseTests(unittest.TestCase):
    def test_ranks_by_correctness(self):
        decision = choose(benchmark_paths(PATHS, CASES))
        self.assertEqual(decision["chosen"], "p.widest")
        self.assertEqual(decision["fallback_chain"], ["p.wide", "p.narrow"])

    def test_tie_break_prefers_lower_cost_then_id(self):
        cards = [
            {"path_id": "p.b", "correctness": 1.0, "mean_score": 1.0, "cost_hint": 2.0},
            {"path_id": "p.a", "correctness": 1.0, "mean_score": 1.0, "cost_hint": 1.0},
        ]
        self.assertEqual(choose(cards)["chosen"], "p.a")   # lower cost wins the tie


class FallbackTests(unittest.TestCase):
    def _impls(self):
        return {p["path_id"]: p["impl"] for p in PATHS}

    def test_fires_on_none(self):
        r = run_with_fallback(self._impls(), ["p.wide", "p.widest"], "x1y2")
        self.assertEqual(r["served_by"], "p.widest")
        self.assertEqual(r["value"], [1, 2])
        self.assertFalse(r["attempts"][0]["ok"])   # p.wide returned None

    def test_fires_on_exception(self):
        r = run_with_fallback(self._impls(), ["p.narrow", "p.widest"], "x1y2")
        self.assertEqual(r["served_by"], "p.widest")   # p.narrow raised

    def test_all_fail_returns_none(self):
        r = run_with_fallback({"p.narrow": _narrow}, ["p.narrow"], "no ints here!")
        self.assertIsNone(r["served_by"])


class PortfolioTests(unittest.TestCase):
    def test_select_portfolio_bundles_everything(self):
        rec = select_portfolio(PATHS, CASES)
        self.assertEqual(rec["path_count"], 3)
        self.assertEqual(rec["decision"]["chosen"], "p.widest")
        self.assertEqual(len(rec["scorecards"]), 3)


if __name__ == "__main__":
    unittest.main()
