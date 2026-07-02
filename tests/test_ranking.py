"""Tests for the coverage_gap_ranker primitive (stdlib unittest, offline).

Run from the repo root:
    python3 -m unittest tests.test_ranking -v

All coordinates, populations, and distances here are SYNTHETIC hand-built
values; nothing asserts real-world coverage or siting facts.

Hand-computed base scenario (ranking_policy.max_km = 10.0):

  point  pop   nearest distance  candidate?  excess
  d1     1000  25.0              yes         15.0
  d2      500  40.0              yes         30.0
  d3     2000  12.0              yes          2.0
  d4      800   8.0              no (covered)
  d5      100  10.0              no (exactly at threshold, strict >)

  max candidate pop = 2000, max excess = 30.0
  weights {uncovered_population: 0.7, distance_beyond_threshold: 0.3}:
    d1: 0.7*(1000/2000) + 0.3*(15/30) = 0.35  + 0.15 = 0.5
    d2: 0.7*( 500/2000) + 0.3*(30/30) = 0.175 + 0.3  = 0.475
    d3: 0.7*(2000/2000) + 0.3*( 2/30) = 0.7   + 0.02 = 0.72
  expected order: d3, d1, d2

  flipped weights {uncovered_population: 0.3, distance_beyond_threshold: 0.7}:
    d1: 0.3*0.5  + 0.7*0.5     = 0.5
    d2: 0.3*0.25 + 0.7*1.0     = 0.775
    d3: 0.3*1.0  + 0.7*(2/30)  = 0.346666667
  expected order: d2, d1, d3
"""

from __future__ import annotations

import copy
import unittest

from primitives.core import canonical_hash, run_primitive
from primitives.ranking import coverage_gap_ranker

MAX_KM = 10.0
BASE_WEIGHTS = {"uncovered_population": 0.7, "distance_beyond_threshold": 0.3}
BASE_DISTANCES = {"d1": 25.0, "d2": 40.0, "d3": 12.0, "d4": 8.0, "d5": 10.0}

DEMAND_POINTS = [
    {"id": "d1", "lat": 29.0, "lon": -95.0, "population": 1000},
    {"id": "d2", "lat": 29.1, "lon": -95.1, "population": 500},
    {"id": "d3", "lat": 29.2, "lon": -95.2, "population": 2000},
    {"id": "d4", "lat": 29.3, "lon": -95.3, "population": 800},
    {"id": "d5", "lat": 29.4, "lon": -95.4, "population": 100},
]
FACILITIES = [
    {"id": "fac:a", "lat": 29.05, "lon": -95.05},
    {"id": "fac:b", "lat": 29.45, "lon": -95.45},
]
FACILITY_FOR = {"d1": "fac:a", "d2": "fac:b", "d3": "fac:a", "d4": "fac:a", "d5": "fac:b"}


def build_payload(weights=None, top_n=5, distances=None) -> dict:
    """Assemble a full payload; the coverage_report is derived from the
    distances so it always conserves population."""
    weights = dict(weights or BASE_WEIGHTS)
    distances = dict(distances or BASE_DISTANCES)
    demand = copy.deepcopy(DEMAND_POINTS)
    assignments = [
        {"demand_id": d["id"], "facility_id": FACILITY_FOR[d["id"]],
         "distance_km": distances[d["id"]]}
        for d in demand
    ]
    total = sum(d["population"] for d in demand)
    covered = sum(d["population"] for d in demand if distances[d["id"]] <= MAX_KM)
    return {
        "coverage_report": {
            "total_population": total,
            "covered_population": covered,
            "uncovered_population": total - covered,
            "coverage_ratio": round(covered / total, 6),
            "max_km": MAX_KM,
        },
        "assignments": assignments,
        "demand_points": demand,
        "facilities": copy.deepcopy(FACILITIES),
        "ranking_policy": {"max_km": MAX_KM, "top_n": top_n, "weights": weights},
    }


def proofs_by_name(outcome) -> dict:
    return {p.proof: p for p in outcome.proof_results}


class TestCoverageGapRankerKnownScenario(unittest.TestCase):
    def setUp(self):
        self.outcome = coverage_gap_ranker(build_payload())
        self.ranked = self.outcome.output["ranked_gap_areas"]

    def test_known_scenario_rank_order(self):
        self.assertEqual([r["demand_id"] for r in self.ranked], ["d3", "d1", "d2"])
        self.assertEqual([r["rank"] for r in self.ranked], [1, 2, 3])

    def test_known_scenario_scores_hand_computed(self):
        by_id = {r["demand_id"]: r for r in self.ranked}
        self.assertAlmostEqual(by_id["d3"]["score"], 0.72, places=9)
        self.assertAlmostEqual(by_id["d1"]["score"], 0.5, places=9)
        self.assertAlmostEqual(by_id["d2"]["score"], 0.475, places=9)
        comps = by_id["d3"]["score_components"]
        self.assertAlmostEqual(comps["uncovered_population"], 0.7, places=9)
        self.assertAlmostEqual(comps["distance_beyond_threshold"], 0.02, places=9)

    def test_score_components_sum_to_score(self):
        for row in self.ranked:
            comps = row["score_components"]
            self.assertAlmostEqual(
                row["score"],
                comps["uncovered_population"] + comps["distance_beyond_threshold"],
                places=8,
                msg=row["demand_id"],
            )
            self.assertAlmostEqual(
                comps["excess_km"], row["distance_km"] - MAX_KM, places=6
            )

    def test_ranked_rows_carry_expected_fields(self):
        expected_keys = {
            "rank", "demand_id", "lat", "lon", "population",
            "nearest_facility_id", "distance_km", "score", "score_components",
        }
        demand_by_id = {d["id"]: d for d in DEMAND_POINTS}
        for row in self.ranked:
            self.assertEqual(set(row), expected_keys)
            src = demand_by_id[row["demand_id"]]
            self.assertEqual(row["lat"], src["lat"])
            self.assertEqual(row["lon"], src["lon"])
            self.assertEqual(row["population"], src["population"])
            self.assertEqual(
                row["nearest_facility_id"], FACILITY_FOR[row["demand_id"]]
            )
            self.assertEqual(
                row["distance_km"], BASE_DISTANCES[row["demand_id"]]
            )

    def test_threshold_exactly_at_max_km_is_covered(self):
        # d5 sits at exactly max_km; candidates require strictly greater.
        ids = {r["demand_id"] for r in self.ranked}
        self.assertNotIn("d5", ids)
        self.assertNotIn("d4", ids)

    def test_tradeoff_report_accounting(self):
        report = self.outcome.output["tradeoff_report"]
        self.assertEqual(report["candidates_considered"], 3)
        self.assertEqual(report["population_in_gaps"], 3500)
        self.assertAlmostEqual(
            report["share_of_total_population"], round(3500 / 4400, 6), places=6
        )
        self.assertEqual(report["weights_used"], BASE_WEIGHTS)


class TestCoverageGapRankerDeterminism(unittest.TestCase):
    def test_tiebreak_is_deterministic_by_id(self):
        # tie_b and tie_a have identical population and distance -> identical
        # scores; ascending id breaks the tie, whatever the input order.
        payload = build_payload()
        for suffix in ("b", "a"):
            payload["demand_points"].append(
                {"id": f"tie_{suffix}", "lat": 29.6, "lon": -95.6, "population": 500}
            )
            payload["assignments"].append(
                {"demand_id": f"tie_{suffix}", "facility_id": "fac:a",
                 "distance_km": 40.0}
            )
        payload["coverage_report"]["total_population"] += 1000
        payload["coverage_report"]["uncovered_population"] += 1000
        ranked = coverage_gap_ranker(payload).output["ranked_gap_areas"]
        by_id = {r["demand_id"]: r for r in ranked}
        # ties with d2 as well (same pop 500, same distance 40.0)
        self.assertEqual(by_id["tie_a"]["score"], by_id["tie_b"]["score"])
        self.assertEqual(by_id["d2"]["score"], by_id["tie_a"]["score"])
        tied_order = [r["demand_id"] for r in ranked if r["score"] == by_id["d2"]["score"]]
        self.assertEqual(tied_order, ["d2", "tie_a", "tie_b"])

    def test_input_order_invariance(self):
        payload = build_payload()
        shuffled = copy.deepcopy(payload)
        shuffled["assignments"].reverse()
        shuffled["demand_points"].reverse()
        shuffled["facilities"].reverse()
        first = coverage_gap_ranker(payload).output
        second = coverage_gap_ranker(shuffled).output
        self.assertEqual(canonical_hash(first), canonical_hash(second))

    def test_repeat_run_identical(self):
        first = coverage_gap_ranker(build_payload()).output
        second = coverage_gap_ranker(build_payload()).output
        self.assertEqual(canonical_hash(first), canonical_hash(second))


class TestCoverageGapRankerPolicy(unittest.TestCase):
    def test_top_n_truncation(self):
        outcome = coverage_gap_ranker(build_payload(top_n=2))
        ranked = outcome.output["ranked_gap_areas"]
        self.assertEqual([r["demand_id"] for r in ranked], ["d3", "d1"])
        self.assertEqual([r["rank"] for r in ranked], [1, 2])
        # truncation hides rows from the output but not from the accounting
        report = outcome.output["tradeoff_report"]
        self.assertEqual(report["candidates_considered"], 3)
        self.assertEqual(report["population_in_gaps"], 3500)

    def test_weights_sensitivity_flip(self):
        flipped = {"uncovered_population": 0.3, "distance_beyond_threshold": 0.7}
        outcome = coverage_gap_ranker(build_payload(weights=flipped))
        ranked = outcome.output["ranked_gap_areas"]
        self.assertEqual([r["demand_id"] for r in ranked], ["d2", "d1", "d3"])
        by_id = {r["demand_id"]: r for r in ranked}
        self.assertAlmostEqual(by_id["d2"]["score"], 0.775, places=9)
        self.assertAlmostEqual(by_id["d1"]["score"], 0.5, places=9)
        self.assertAlmostEqual(by_id["d3"]["score"], 0.3 + 0.7 * (2.0 / 30.0), places=8)
        self.assertEqual(outcome.output["tradeoff_report"]["weights_used"], flipped)

    def test_empty_gap_case(self):
        # every demand point within max_km -> no candidates, empty ranking,
        # tradeoff report reflects it, proofs still pass
        covered = {"d1": 5.0, "d2": 9.9, "d3": 2.0, "d4": 8.0, "d5": 10.0}
        outcome = coverage_gap_ranker(build_payload(distances=covered))
        self.assertEqual(outcome.output["ranked_gap_areas"], [])
        report = outcome.output["tradeoff_report"]
        self.assertEqual(report["candidates_considered"], 0)
        self.assertEqual(report["population_in_gaps"], 0)
        self.assertEqual(report["share_of_total_population"], 0.0)
        proofs = proofs_by_name(outcome)
        for name in (
            "schema_validation",
            "deterministic_ranking",
            "score_monotonicity",
            "population_accounting",
            "method_receipt_honest",
        ):
            self.assertTrue(proofs[name].passed, name)
        self.assertEqual(outcome.effects_observed, ["none"])


class TestCoverageGapRankerHonesty(unittest.TestCase):
    def test_method_honesty_fields(self):
        outcome = coverage_gap_ranker(build_payload())
        method = outcome.output["method"]
        self.assertEqual(method["scoring"], "weighted_linear_normalized")
        self.assertEqual(
            method["distance_basis"], "straight_line_haversine_proxy_from_upstream"
        )
        self.assertIn("proxy", method["caveat"])
        self.assertIn("NOT modeled", method["caveat"])
        self.assertIn("zoning", method["caveat"])
        self.assertEqual(outcome.effects_observed, ["none"])

    def test_all_proofs_pass(self):
        outcome = coverage_gap_ranker(build_payload())
        proofs = proofs_by_name(outcome)
        expected = {
            "schema_validation",
            "deterministic_ranking",
            "score_monotonicity",
            "population_accounting",
            "method_receipt_honest",
        }
        self.assertEqual(set(proofs), expected)
        for name, proof in proofs.items():
            self.assertTrue(proof.passed, name)

    def test_receipt_through_core_runner(self):
        output, receipt = run_primitive(
            "prim:place_discovery.coverage_gap_ranker",
            coverage_gap_ranker,
            build_payload(),
            run_id="test:ranking",
            declared_effects=["none"],
        )
        self.assertEqual(
            [r["demand_id"] for r in output["ranked_gap_areas"]], ["d3", "d1", "d2"]
        )
        self.assertIsNone(receipt["error"])
        self.assertTrue(receipt["candidate"])
        self.assertFalse(receipt["serves_truth"])
        self.assertEqual(receipt["effects_declared"], ["none"])
        self.assertEqual(receipt["effects_observed"], ["none"])
        self.assertEqual(
            {p["proof"] for p in receipt["proof_results"]},
            {
                "schema_validation",
                "deterministic_ranking",
                "score_monotonicity",
                "population_accounting",
                "method_receipt_honest",
            },
        )


class TestCoverageGapRankerValidation(unittest.TestCase):
    def test_invalid_payloads_raise(self):
        cases = {
            "missing coverage_report": lambda p: p.pop("coverage_report"),
            "demand_points not a list": lambda p: p.update(demand_points="nope"),
            "empty facilities": lambda p: p.update(facilities=[]),
            "assignment unknown demand": lambda p: p["assignments"].append(
                {"demand_id": "ghost", "facility_id": "fac:a", "distance_km": 1.0}
            ),
            "assignment unknown facility": lambda p: p["assignments"][0].update(
                facility_id="fac:ghost"
            ),
            "demand point missing assignment": lambda p: p["assignments"].pop(),
            "negative distance": lambda p: p["assignments"][0].update(
                distance_km=-1.0
            ),
            "top_n zero": lambda p: p["ranking_policy"].update(top_n=0),
            "max_km nonpositive": lambda p: p["ranking_policy"].update(max_km=0),
            "missing weight key": lambda p: p["ranking_policy"]["weights"].pop(
                "uncovered_population"
            ),
            "negative weight": lambda p: p["ranking_policy"]["weights"].update(
                uncovered_population=-0.5
            ),
            "unknown weight factor": lambda p: p["ranking_policy"]["weights"].update(
                equity=1.0
            ),
            "population not int": lambda p: p["demand_points"][0].update(
                population=10.5
            ),
            "nonconserving coverage_report": lambda p: p["coverage_report"].update(
                covered_population=1
            ),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                payload = build_payload()
                mutate(payload)
                with self.assertRaises(ValueError, msg=name):
                    coverage_gap_ranker(payload)

    def test_zero_weight_pair_rejected(self):
        payload = build_payload(
            weights={"uncovered_population": 0.0, "distance_beyond_threshold": 0.0}
        )
        with self.assertRaises(ValueError):
            coverage_gap_ranker(payload)

    def test_single_positive_weight_allowed(self):
        payload = build_payload(
            weights={"uncovered_population": 1.0, "distance_beyond_threshold": 0.0}
        )
        ranked = coverage_gap_ranker(payload).output["ranked_gap_areas"]
        # population-only ranking: d3 (2000), d1 (1000), d2 (500)
        self.assertEqual([r["demand_id"] for r in ranked], ["d3", "d1", "d2"])


if __name__ == "__main__":
    unittest.main()
