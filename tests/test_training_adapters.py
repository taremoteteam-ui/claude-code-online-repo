"""Tests for the workforce-training source adapters (training_provider_discovery).

Run from the repo root:

    python3 -m unittest tests.test_training_adapters -v

Both adapters run through FixtureTransport (mode "fixture_offline"); no
network access happens in this suite. Fixtures are SYNTHETIC data shaped
like the real APIs and every fixture file carries "fixture_synthetic": true.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from primitives.adapters.careeronestop import (
    ELIGIBILITY_NOTE,
    careeronestop_training_provider_adapter,
)
from primitives.adapters.college_scorecard import (
    college_scorecard_ipeds_program_adapter,
)
from primitives.adapters.transport import FixtureTransport
from primitives.core import PrimitiveOutcome

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_ROOT = REPO_ROOT / "fixtures" / "place-discovery"

HARRIS_CENTROID = (29.86, -95.39)
GLACIER_CENTROID = (48.70, -112.99)
COORD_DELTA = 0.35

COS_HARRIS_PAYLOAD = {
    "aoi_id": "aoi:harris_county_tx",
    "state": "TX",
    "program_keyword": "skilled trades",
    "fixture_name": "careeronestop_providers_harris_tx.json",
}
COS_GLACIER_PAYLOAD = {
    "aoi_id": "aoi:glacier_county_mt",
    "state": "MT",
    "program_keyword": "skilled trades",
    "fixture_name": "careeronestop_providers_glacier_mt.json",
}
CSC_HARRIS_PAYLOAD = {
    "aoi_id": "aoi:harris_county_tx",
    "state": "TX",
    "program_cip_prefix": "5138",
    "fixture_name": "college_scorecard_harris_tx.json",
}
CSC_GLACIER_PAYLOAD = {
    "aoi_id": "aoi:glacier_county_mt",
    "state": "MT",
    "program_cip_prefix": "5138",
    "fixture_name": "college_scorecard_glacier_mt.json",
}

ALL_ADAPTER_RUNS = [
    ("cos_harris", careeronestop_training_provider_adapter, COS_HARRIS_PAYLOAD),
    ("cos_glacier", careeronestop_training_provider_adapter, COS_GLACIER_PAYLOAD),
    ("csc_harris", college_scorecard_ipeds_program_adapter, CSC_HARRIS_PAYLOAD),
    ("csc_glacier", college_scorecard_ipeds_program_adapter, CSC_GLACIER_PAYLOAD),
]

FACILITY_RECORD_KEYS = {
    "record_id",
    "source_id",
    "name",
    "address",
    "city",
    "state",
    "zip",
    "phone",
    "lat",
    "lon",
}
COS_RECORD_KEYS = FACILITY_RECORD_KEYS | {"program_name", "wioa_eligible"}
CSC_RECORD_KEYS = FACILITY_RECORD_KEYS | {"programs"}


def make_transport() -> FixtureTransport:
    return FixtureTransport(fixture_root=FIXTURE_ROOT)


class TestFixtureHonesty(unittest.TestCase):
    def test_every_training_fixture_declares_synthetic_and_shape(self):
        names = sorted({run[2]["fixture_name"] for run in ALL_ADAPTER_RUNS})
        self.assertEqual(len(names), 4)
        for name in names:
            payload = json.loads(
                (FIXTURE_ROOT / name).read_text(encoding="utf-8")
            )
            self.assertIs(
                payload.get("fixture_synthetic"),
                True,
                f"{name} must carry fixture_synthetic: true",
            )
            self.assertIn("recorded_shape", payload, name)
            self.assertIn("request", payload, name)
            self.assertIn("response", payload, name)


class TestCommonAdapterContract(unittest.TestCase):
    """Contract shared by both adapters when run offline against fixtures."""

    def test_outcome_shape_effects_and_retrieved_mode(self):
        for label, fn, payload in ALL_ADAPTER_RUNS:
            with self.subTest(adapter=label):
                outcome = fn(payload, make_transport())
                self.assertIsInstance(outcome, PrimitiveOutcome)
                self.assertEqual(outcome.effects_observed, ["file_read"])
                meta = outcome.output["snapshot_meta"]
                for key in (
                    "snapshot_id",
                    "source_id",
                    "license_family",
                    "attribution",
                    "retrieved_mode",
                ):
                    self.assertIn(key, meta)
                self.assertEqual(meta["retrieved_mode"], "fixture_offline")
                self.assertEqual(meta["license_family"], "public_domain_us_gov")
                self.assertIn("synthetic", meta["attribution"])
                self.assertEqual(
                    outcome.source_snapshot_ids, [meta["snapshot_id"]]
                )
                self.assertTrue(meta["snapshot_id"].startswith("snap:"))
                self.assertEqual(
                    outcome.output["record_count"],
                    len(outcome.output["records"]),
                )

    def test_all_proofs_pass(self):
        for label, fn, payload in ALL_ADAPTER_RUNS:
            with self.subTest(adapter=label):
                outcome = fn(payload, make_transport())
                self.assertTrue(outcome.proof_results)
                failed = [p.proof for p in outcome.proof_results if not p.passed]
                self.assertEqual(failed, [], f"{label} failed proofs: {failed}")

    def test_snapshot_ids_stable_across_two_loads(self):
        for label, fn, payload in ALL_ADAPTER_RUNS:
            with self.subTest(adapter=label):
                first = fn(payload, make_transport())
                second = fn(payload, make_transport())
                self.assertEqual(
                    first.source_snapshot_ids, second.source_snapshot_ids
                )
                self.assertEqual(
                    first.output["snapshot_meta"]["snapshot_id"],
                    second.output["snapshot_meta"]["snapshot_id"],
                )

    def test_coordinates_near_aoi_centroids(self):
        expectations = [
            ("cos_harris", careeronestop_training_provider_adapter,
             COS_HARRIS_PAYLOAD, HARRIS_CENTROID),
            ("cos_glacier", careeronestop_training_provider_adapter,
             COS_GLACIER_PAYLOAD, GLACIER_CENTROID),
            ("csc_harris", college_scorecard_ipeds_program_adapter,
             CSC_HARRIS_PAYLOAD, HARRIS_CENTROID),
            ("csc_glacier", college_scorecard_ipeds_program_adapter,
             CSC_GLACIER_PAYLOAD, GLACIER_CENTROID),
        ]
        for label, fn, payload, (clat, clon) in expectations:
            with self.subTest(adapter=label):
                outcome = fn(payload, make_transport())
                for rec in outcome.output["records"]:
                    self.assertAlmostEqual(
                        rec["lat"], clat, delta=COORD_DELTA, msg=rec["record_id"]
                    )
                    self.assertAlmostEqual(
                        rec["lon"], clon, delta=COORD_DELTA, msg=rec["record_id"]
                    )
                    self.assertGreaterEqual(rec["lat"], -90.0)
                    self.assertLessEqual(rec["lat"], 90.0)
                    self.assertGreaterEqual(rec["lon"], -180.0)
                    self.assertLessEqual(rec["lon"], 180.0)


class TestCareerOneStopAdapter(unittest.TestCase):
    def test_harris_records_normalized(self):
        outcome = careeronestop_training_provider_adapter(
            COS_HARRIS_PAYLOAD, make_transport()
        )
        records = outcome.output["records"]
        self.assertGreaterEqual(len(records), 6)
        self.assertLessEqual(len(records), 8)
        for rec in records:
            self.assertEqual(set(rec), COS_RECORD_KEYS)
            self.assertEqual(
                rec["source_id"], "src:careeronestop.training_providers_api"
            )
            self.assertTrue(rec["record_id"].startswith("cos:"))
            self.assertEqual(rec["address"], "")
            self.assertIsNone(rec["phone"])
            self.assertTrue(rec["program_name"])

    def test_etpl_flag_recorded_per_record_and_mixed(self):
        outcome = careeronestop_training_provider_adapter(
            COS_HARRIS_PAYLOAD, make_transport()
        )
        records = outcome.output["records"]
        for rec in records:
            self.assertIsInstance(rec["wioa_eligible"], bool)
        flags = {rec["wioa_eligible"] for rec in records}
        self.assertEqual(flags, {True, False}, "Harris fixture mixes ETPL flags")
        proof = {p.proof: p for p in outcome.proof_results}[
            "wioa_flag_recorded_per_record"
        ]
        self.assertTrue(proof.passed)

    def test_eligibility_note_present_verbatim(self):
        # Freshness honesty: the note travels with every output.
        expected = (
            "ETPL/WIOA eligibility is state-maintained and time-sensitive; "
            "verify against the state list before relying on it"
        )
        self.assertEqual(ELIGIBILITY_NOTE, expected)
        for payload in (COS_HARRIS_PAYLOAD, COS_GLACIER_PAYLOAD):
            outcome = careeronestop_training_provider_adapter(
                payload, make_transport()
            )
            self.assertEqual(outcome.output["eligibility_note"], expected)

    def test_near_duplicate_variants_present_for_dedupe_work(self):
        outcome = careeronestop_training_provider_adapter(
            COS_HARRIS_PAYLOAD, make_transport()
        )
        names = {rec["name"] for rec in outcome.output["records"]}
        self.assertIn("Gulf Coast Technical Institute", names)
        self.assertIn("GULF COAST TECHNICAL INST", names)
        by_name = {rec["name"]: rec for rec in outcome.output["records"]}
        a = by_name["Gulf Coast Technical Institute"]
        b = by_name["GULF COAST TECHNICAL INST"]
        # Same zip and near-identical coordinates: raw material for dedupe.
        self.assertEqual(a["zip"], b["zip"])
        self.assertLess(abs(a["lat"] - b["lat"]), 0.01)
        self.assertLess(abs(a["lon"] - b["lon"]), 0.01)

    def test_glacier_frontier_scarcity(self):
        outcome = careeronestop_training_provider_adapter(
            COS_GLACIER_PAYLOAD, make_transport()
        )
        records = outcome.output["records"]
        self.assertGreaterEqual(len(records), 1)
        self.assertLessEqual(len(records), 2)

    def test_attribution_mentions_careeronestop(self):
        outcome = careeronestop_training_provider_adapter(
            COS_HARRIS_PAYLOAD, make_transport()
        )
        self.assertIn(
            "CareerOneStop", outcome.output["snapshot_meta"]["attribution"]
        )

    def test_proof_names(self):
        outcome = careeronestop_training_provider_adapter(
            COS_HARRIS_PAYLOAD, make_transport()
        )
        self.assertEqual(
            [p.proof for p in outcome.proof_results],
            [
                "schema_validation",
                "row_count_positive",
                "coordinates_in_range",
                "wioa_flag_recorded_per_record",
            ],
        )


class TestCollegeScorecardAdapter(unittest.TestCase):
    def test_harris_cip_5138_returns_only_matching_programs(self):
        outcome = college_scorecard_ipeds_program_adapter(
            CSC_HARRIS_PAYLOAD, make_transport()
        )
        records = outcome.output["records"]
        # Three fixture institutions carry a 5138 program; the two without
        # one are dropped by the filter.
        self.assertEqual(len(records), 3)
        self.assertEqual(outcome.output["institutions_total"], 5)
        names = {rec["name"] for rec in records}
        self.assertEqual(
            names,
            {
                "Houston Gulf Coast College",
                "Northline Community College",
                "Spring Branch College of Health Sciences",
            },
        )
        for rec in records:
            self.assertEqual(set(rec), CSC_RECORD_KEYS)
            self.assertEqual(
                rec["source_id"], "src:college_scorecard.ipeds_programs_api"
            )
            self.assertTrue(rec["record_id"].startswith("csc:"))
            self.assertEqual(rec["address"], "")
            self.assertIsNone(rec["phone"])
            self.assertTrue(rec["programs"])
            for prog in rec["programs"]:
                self.assertEqual(set(prog), {"code", "title"})
                self.assertTrue(str(prog["code"]).startswith("5138"))

    def test_broader_cip_prefix_keeps_more_programs(self):
        payload = dict(CSC_HARRIS_PAYLOAD, program_cip_prefix="51")
        outcome = college_scorecard_ipeds_program_adapter(
            payload, make_transport()
        )
        records = outcome.output["records"]
        self.assertEqual(len(records), 3)
        codes = sorted(
            prog["code"] for rec in records for prog in rec["programs"]
        )
        self.assertEqual(
            codes, ["5100", "5107", "5108", "5138", "5138", "5138", "5139"]
        )
        for code in codes:
            self.assertTrue(code.startswith("51"))
        failed = [p.proof for p in outcome.proof_results if not p.passed]
        self.assertEqual(failed, [])

    def test_record_ids_trace_source_row_index(self):
        outcome = college_scorecard_ipeds_program_adapter(
            CSC_HARRIS_PAYLOAD, make_transport()
        )
        ids = [rec["record_id"] for rec in outcome.output["records"]]
        # Institutions 1, 3, and 5 in the fixture carry a 5138 program.
        self.assertEqual(ids, ["csc:1", "csc:3", "csc:5"])

    def test_glacier_single_institution_single_program(self):
        outcome = college_scorecard_ipeds_program_adapter(
            CSC_GLACIER_PAYLOAD, make_transport()
        )
        records = outcome.output["records"]
        self.assertEqual(len(records), 1)
        rec = records[0]
        self.assertEqual(rec["name"], "Blackfeet Community College")
        self.assertEqual(rec["state"], "MT")
        self.assertEqual(len(rec["programs"]), 1)
        self.assertEqual(rec["programs"][0]["code"], "5138")

    def test_attribution_mentions_college_scorecard(self):
        outcome = college_scorecard_ipeds_program_adapter(
            CSC_HARRIS_PAYLOAD, make_transport()
        )
        self.assertIn(
            "College Scorecard", outcome.output["snapshot_meta"]["attribution"]
        )

    def test_proof_names(self):
        outcome = college_scorecard_ipeds_program_adapter(
            CSC_HARRIS_PAYLOAD, make_transport()
        )
        self.assertEqual(
            [p.proof for p in outcome.proof_results],
            [
                "schema_validation",
                "row_count_positive",
                "coordinates_in_range",
                "cip_filter_applied",
            ],
        )


if __name__ == "__main__":
    unittest.main()
