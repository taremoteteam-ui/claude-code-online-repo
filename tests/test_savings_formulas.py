"""Unit tests for the savings/impact formula single source.

Run from the repo root:
    python3 -m unittest tests.test_savings_formulas -v

All inputs in this file are SYNTHETIC values chosen to verify algebra and
error paths. They are not measurements and must never be quoted as results.
"""

from __future__ import annotations

import unittest

from scripts.eval.savings_formulas import (
    FORMULAS,
    MEASUREMENT_STATUS,
    _self_test,
    break_even_tasks,
    cost_savings_pct,
    per_100k_developers,
    promotion_value,
    proof_coverage,
    reuse_ratio,
    route_reuse_value,
    source_context_avoidance_pct,
    speedup_factor,
    token_savings_pct,
    weekly_cost_saved_per_developer,
    weekly_hours_saved_per_developer,
    weekly_tokens_saved_per_developer,
)


class TestTokenSavingsPct(unittest.TestCase):
    def test_algebra(self):
        self.assertAlmostEqual(token_savings_pct(50, 100), 0.5)
        self.assertAlmostEqual(token_savings_pct(0, 100), 1.0)
        self.assertAlmostEqual(token_savings_pct(100, 100), 0.0)

    def test_measured_regression_is_negative_not_error(self):
        self.assertAlmostEqual(token_savings_pct(150, 100), -0.5)

    def test_zero_baseline_raises(self):
        with self.assertRaises(ValueError):
            token_savings_pct(50, 0)

    def test_negative_inputs_raise(self):
        with self.assertRaises(ValueError):
            token_savings_pct(-1, 100)
        with self.assertRaises(ValueError):
            token_savings_pct(50, -100)

    def test_non_numeric_and_nan_raise(self):
        with self.assertRaises(ValueError):
            token_savings_pct("50", 100)
        with self.assertRaises(ValueError):
            token_savings_pct(float("nan"), 100)
        with self.assertRaises(ValueError):
            token_savings_pct(50, float("inf"))
        with self.assertRaises(ValueError):
            token_savings_pct(True, 100)


class TestSourceContextAvoidancePct(unittest.TestCase):
    def test_algebra(self):
        self.assertAlmostEqual(source_context_avoidance_pct(25, 100), 0.75)
        self.assertAlmostEqual(source_context_avoidance_pct(0, 10), 1.0)

    def test_zero_baseline_raises(self):
        with self.assertRaises(ValueError):
            source_context_avoidance_pct(25, 0)

    def test_negative_raises(self):
        with self.assertRaises(ValueError):
            source_context_avoidance_pct(-5, 100)


class TestCostSavingsPct(unittest.TestCase):
    def test_algebra(self):
        self.assertAlmostEqual(cost_savings_pct(1.0, 4.0), 0.75)
        self.assertAlmostEqual(cost_savings_pct(0.0, 2.0), 1.0)

    def test_zero_baseline_raises(self):
        with self.assertRaises(ValueError):
            cost_savings_pct(1.0, 0.0)

    def test_negative_cost_raises(self):
        with self.assertRaises(ValueError):
            cost_savings_pct(-0.5, 4.0)
        with self.assertRaises(ValueError):
            cost_savings_pct(1.0, -4.0)


class TestSpeedupFactor(unittest.TestCase):
    def test_algebra(self):
        self.assertAlmostEqual(speedup_factor(10, 2), 5.0)
        self.assertAlmostEqual(speedup_factor(2, 10), 0.2)
        self.assertAlmostEqual(speedup_factor(3.0, 3.0), 1.0)

    def test_zero_denominator_raises(self):
        with self.assertRaises(ValueError):
            speedup_factor(10, 0)

    def test_zero_baseline_raises(self):
        with self.assertRaises(ValueError):
            speedup_factor(0, 2)

    def test_negative_raises(self):
        with self.assertRaises(ValueError):
            speedup_factor(-10, 2)
        with self.assertRaises(ValueError):
            speedup_factor(10, -2)


class TestProofCoverage(unittest.TestCase):
    def test_algebra(self):
        self.assertAlmostEqual(proof_coverage(3, 4), 0.75)
        self.assertAlmostEqual(proof_coverage(0, 5), 0.0)
        self.assertAlmostEqual(proof_coverage(5, 5), 1.0)

    def test_zero_total_raises(self):
        with self.assertRaises(ValueError):
            proof_coverage(0, 0)
        with self.assertRaises(ValueError):
            proof_coverage(1, 0)

    def test_passed_exceeding_total_raises(self):
        with self.assertRaises(ValueError):
            proof_coverage(5, 4)

    def test_negative_counts_raise(self):
        with self.assertRaises(ValueError):
            proof_coverage(-1, 4)
        with self.assertRaises(ValueError):
            proof_coverage(1, -4)

    def test_non_integer_counts_raise(self):
        with self.assertRaises(ValueError):
            proof_coverage(1.5, 4)
        with self.assertRaises(ValueError):
            proof_coverage(1, 4.0)
        with self.assertRaises(ValueError):
            proof_coverage(True, 4)


class TestReuseRatio(unittest.TestCase):
    def test_algebra(self):
        self.assertAlmostEqual(reuse_ratio(2, 8), 0.25)
        self.assertAlmostEqual(reuse_ratio(0, 3), 0.0)
        self.assertAlmostEqual(reuse_ratio(3, 3), 1.0)

    def test_zero_total_raises(self):
        with self.assertRaises(ValueError):
            reuse_ratio(0, 0)

    def test_reused_exceeding_total_raises(self):
        with self.assertRaises(ValueError):
            reuse_ratio(9, 8)

    def test_negative_counts_raise(self):
        with self.assertRaises(ValueError):
            reuse_ratio(-1, 8)
        with self.assertRaises(ValueError):
            reuse_ratio(1, -8)

    def test_non_integer_counts_raise(self):
        with self.assertRaises(ValueError):
            reuse_ratio(0.5, 8)


class TestWeeklyTokensSavedPerDeveloper(unittest.TestCase):
    def test_algebra(self):
        self.assertAlmostEqual(weekly_tokens_saved_per_developer(10, 500), 5000.0)
        self.assertAlmostEqual(weekly_tokens_saved_per_developer(0, 500), 0.0)

    def test_measured_regression_allowed(self):
        self.assertAlmostEqual(weekly_tokens_saved_per_developer(10, -50), -500.0)

    def test_negative_tasks_per_week_raises(self):
        with self.assertRaises(ValueError):
            weekly_tokens_saved_per_developer(-1, 500)

    def test_nan_raises(self):
        with self.assertRaises(ValueError):
            weekly_tokens_saved_per_developer(10, float("nan"))


class TestWeeklyCostSavedPerDeveloper(unittest.TestCase):
    def test_algebra(self):
        self.assertAlmostEqual(weekly_cost_saved_per_developer(10, 0.25), 2.5)

    def test_measured_regression_allowed(self):
        self.assertAlmostEqual(weekly_cost_saved_per_developer(4, -0.5), -2.0)

    def test_negative_tasks_per_week_raises(self):
        with self.assertRaises(ValueError):
            weekly_cost_saved_per_developer(-2, 0.25)


class TestWeeklyHoursSavedPerDeveloper(unittest.TestCase):
    def test_algebra(self):
        self.assertAlmostEqual(weekly_hours_saved_per_developer(10, 360), 1.0)
        self.assertAlmostEqual(weekly_hours_saved_per_developer(10, 7200), 20.0)

    def test_negative_tasks_per_week_raises(self):
        with self.assertRaises(ValueError):
            weekly_hours_saved_per_developer(-1, 360)

    def test_infinite_seconds_raises(self):
        with self.assertRaises(ValueError):
            weekly_hours_saved_per_developer(10, float("inf"))


class TestPer100kDevelopers(unittest.TestCase):
    def test_algebra(self):
        self.assertAlmostEqual(per_100k_developers(2.0), 200000.0)
        self.assertAlmostEqual(per_100k_developers(0.0), 0.0)

    def test_measured_regression_allowed(self):
        self.assertAlmostEqual(per_100k_developers(-1.0), -100000.0)

    def test_nan_raises(self):
        with self.assertRaises(ValueError):
            per_100k_developers(float("nan"))

    def test_non_numeric_raises(self):
        with self.assertRaises(ValueError):
            per_100k_developers(None)


class TestBreakEvenTasks(unittest.TestCase):
    def test_algebra(self):
        self.assertAlmostEqual(break_even_tasks(100.0, 4.0), 25.0)
        self.assertAlmostEqual(break_even_tasks(0.0, 4.0), 0.0)

    def test_zero_savings_denominator_raises(self):
        with self.assertRaises(ValueError):
            break_even_tasks(100.0, 0.0)

    def test_negative_savings_raises(self):
        with self.assertRaises(ValueError):
            break_even_tasks(100.0, -4.0)

    def test_negative_creation_cost_raises(self):
        with self.assertRaises(ValueError):
            break_even_tasks(-100.0, 4.0)


class TestRouteReuseValue(unittest.TestCase):
    def test_algebra(self):
        self.assertAlmostEqual(route_reuse_value(10, 500, 0.9), 4500.0)
        self.assertAlmostEqual(route_reuse_value(0, 500, 0.9), 0.0)
        self.assertAlmostEqual(route_reuse_value(10, 500, 0.0), 0.0)
        self.assertAlmostEqual(route_reuse_value(10, 500, 1.0), 5000.0)

    def test_negative_count_raises(self):
        with self.assertRaises(ValueError):
            route_reuse_value(-1, 500, 0.9)

    def test_non_integer_count_raises(self):
        with self.assertRaises(ValueError):
            route_reuse_value(1.5, 500, 0.9)

    def test_probability_outside_unit_interval_raises(self):
        with self.assertRaises(ValueError):
            route_reuse_value(10, 500, 1.5)
        with self.assertRaises(ValueError):
            route_reuse_value(10, 500, -0.1)


class TestPromotionValue(unittest.TestCase):
    def test_algebra(self):
        self.assertAlmostEqual(promotion_value(10000, 0.9, 0.5), 4500.0)
        self.assertAlmostEqual(promotion_value(0, 0.9, 0.5), 0.0)
        self.assertAlmostEqual(promotion_value(10000, 1.0, 1.0), 10000.0)

    def test_negative_estimate_raises(self):
        with self.assertRaises(ValueError):
            promotion_value(-1, 0.9, 0.5)

    def test_probabilities_outside_unit_interval_raise(self):
        with self.assertRaises(ValueError):
            promotion_value(10000, 1.1, 0.5)
        with self.assertRaises(ValueError):
            promotion_value(10000, 0.9, -0.5)
        with self.assertRaises(ValueError):
            promotion_value(10000, 0.9, 2.0)


class TestModuleContracts(unittest.TestCase):
    def test_measurement_status_covers_every_formula(self):
        self.assertEqual(set(MEASUREMENT_STATUS), set(FORMULAS))
        for name, sources in MEASUREMENT_STATUS.items():
            self.assertIsInstance(sources, list, name)
            self.assertGreater(len(sources), 0, name)
            for source in sources:
                self.assertIsInstance(source, str, name)
                self.assertTrue(source, name)

    def test_registry_entries_are_the_module_functions(self):
        self.assertEqual(FORMULAS["token_savings_pct"], token_savings_pct)
        self.assertEqual(FORMULAS["promotion_value"], promotion_value)
        self.assertEqual(len(FORMULAS), 16)

    def test_docstring_declares_formulas_only(self):
        import scripts.eval.savings_formulas as mod
        self.assertIn(
            "Formulas only. This module computes nothing until fed MEASURED "
            "inputs from\nreceipts and scorecards. No default values, no "
            "example numbers, no\nprojections live here.",
            mod.__doc__,
        )

    def test_self_test_passes_and_labels_inputs_synthetic(self):
        result = _self_test()
        self.assertTrue(result["ok"], result["failures"])
        self.assertEqual(result["self_test_inputs"], "synthetic")
        self.assertEqual(result["formulas_checked"], len(FORMULAS))
        self.assertEqual(result["failures"], [])


if __name__ == "__main__":
    unittest.main()
