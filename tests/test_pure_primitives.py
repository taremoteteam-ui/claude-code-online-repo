"""Unit tests for the pure P0 primitives.

Run from the repo root:
    python3 -m unittest tests.test_pure_primitives -v

Failure-path assertions call the primitive functions directly and
inspect proof_results; run_primitive is only used on happy paths
(it raises on any failed proof by design).
"""

from __future__ import annotations

import copy
import unittest

from primitives.core import run_primitive
from primitives.entity import entity_normalize_and_dedupe
from primitives.evidence import (
    FIXTURE_OFFLINE_NOTE,
    evidence_bundle_wrapper,
)
from primitives.fingerprint import dataset_schema_fingerprint
from primitives.gates import geocode_policy_gate


def _proofs_by_name(outcome):
    return {p.proof: p for p in outcome.proof_results}


class TestDatasetSchemaFingerprint(unittest.TestCase):
    RECORDS = [
        {"name": "Alpha Clinic", "beds": 12, "rating": 4.5, "closed": None},
        {"name": "Beta Clinic", "beds": 30, "rating": None},
        {"name": "Gamma Clinic", "beds": 12, "tags": ["urgent", "walk-in"]},
    ]

    def _payload(self):
        return {"dataset_id": "ds:test", "records": copy.deepcopy(self.RECORDS)}

    def test_profile_and_null_counting(self):
        outcome = dataset_schema_fingerprint(self._payload())
        out = outcome.output
        self.assertEqual(out["dataset_id"], "ds:test")
        self.assertEqual(out["row_count"], 3)
        self.assertEqual(out["field_count"], 5)
        fields = out["fields"]

        # "closed" is explicit-null once and missing twice.
        self.assertEqual(fields["closed"]["null_or_missing_count"], 3)
        self.assertEqual(fields["closed"]["observed_types"], ["null"])
        # "rating" has one value and one explicit null and one missing.
        self.assertEqual(fields["rating"]["null_or_missing_count"], 2)
        self.assertIn("number", fields["rating"]["observed_types"])
        # "beds" repeats the value 12: distinct 2 of 3 rows.
        self.assertEqual(fields["beds"]["null_or_missing_count"], 0)
        self.assertEqual(fields["beds"]["distinct_count"], 2)
        self.assertEqual(fields["beds"]["observed_types"], ["integer"])
        self.assertEqual(fields["tags"]["observed_types"], ["array"])
        self.assertEqual(fields["name"]["distinct_count"], 3)
        self.assertLessEqual(len(fields["name"]["example"] or ""), 80)
        self.assertEqual(outcome.effects_observed, ["none"])

    def test_fingerprint_determinism_across_key_order(self):
        outcome_a = dataset_schema_fingerprint(self._payload())
        reordered = [
            dict(reversed(list(rec.items()))) for rec in copy.deepcopy(self.RECORDS)
        ]
        outcome_b = dataset_schema_fingerprint(
            {"dataset_id": "ds:test", "records": reordered}
        )
        self.assertEqual(
            outcome_a.output["fingerprint_hash"],
            outcome_b.output["fingerprint_hash"],
        )
        for outcome in (outcome_a, outcome_b):
            proofs = _proofs_by_name(outcome)
            self.assertTrue(proofs["schema_validation"].passed)
            self.assertTrue(proofs["fingerprint_determinism"].passed)

    def test_runs_through_receipt_runner(self):
        output, receipt = run_primitive(
            "prim:dataset_schema_fingerprint",
            dataset_schema_fingerprint,
            self._payload(),
            run_id="run:test:fp",
            declared_effects=["none"],
        )
        self.assertIsNone(receipt["error"])
        self.assertTrue(output["fingerprint_hash"].startswith("sha256:"))
        self.assertTrue(receipt["candidate"])
        self.assertFalse(receipt["serves_truth"])

    def test_schema_validation_fails_on_empty_records(self):
        outcome = dataset_schema_fingerprint({"dataset_id": "ds:x", "records": []})
        proofs = _proofs_by_name(outcome)
        self.assertFalse(proofs["schema_validation"].passed)
        self.assertIsNone(outcome.output["fingerprint_hash"])

    def test_schema_validation_fails_on_non_dict_rows(self):
        outcome = dataset_schema_fingerprint(
            {"dataset_id": "ds:x", "records": [{"a": 1}, "not-a-dict"]}
        )
        proofs = _proofs_by_name(outcome)
        self.assertFalse(proofs["schema_validation"].passed)


class TestEntityNormalizeAndDedupe(unittest.TestCase):
    # r1/r2: same facility, name variants, same zip5, ~50 m apart.
    # r3: different facility in the SAME block (zip 45202, name starts 'S').
    # r4: different block by zip.
    # r5/r6: identical names, same zip, ~5.5 km apart (distance gate).
    RECORDS = [
        {
            "record_id": "r1", "source_id": "src_a",
            "name": "St. Mary's Health Center",
            "address": "123 West Elm Street, Suite 4",
            "city": "Cincinnati", "state": "OH", "zip": "45202-1234",
            "phone": "(513) 555-0142", "lat": 39.10310, "lon": -84.51200,
        },
        {
            "record_id": "r2", "source_id": "src_b",
            "name": "SAINT MARYS HEALTH CTR",
            "address": "123 W Elm St Ste 4",
            "city": "CINCINNATI", "state": "OH", "zip": "45202",
            "phone": "1-513-555-0142", "lat": 39.10355, "lon": -84.51200,
        },
        {
            "record_id": "r3", "source_id": "src_a",
            "name": "St. Anthony Medical Pavilion",
            "address": "500 Race Street",
            "city": "Cincinnati", "state": "OH", "zip": "45202",
            "phone": "(513) 555-0987", "lat": 39.10500, "lon": -84.51000,
        },
        {
            "record_id": "r4", "source_id": "src_c",
            "name": "Oakwood Community Clinic",
            "address": "77 Oak Avenue",
            "city": "Cincinnati", "state": "OH", "zip": "45203",
            "phone": "(513) 555-0333", "lat": 39.09800, "lon": -84.52500,
        },
        {
            "record_id": "r5", "source_id": "src_a",
            "name": "Riverfront Coffee Roasters",
            "address": "9 Water Street",
            "city": "Cincinnati", "state": "OH", "zip": "45211",
            "phone": "(513) 555-0777", "lat": 39.14000, "lon": -84.60000,
        },
        {
            "record_id": "r6", "source_id": "src_b",
            "name": "Riverfront Coffee Roasters",
            "address": "800 Hilltop Road",
            "city": "Cincinnati", "state": "OH", "zip": "45211",
            "phone": "(513) 555-0778", "lat": 39.19000, "lon": -84.60000,
        },
    ]
    POLICY = {
        "name_similarity_threshold": 0.85,
        "max_distance_m": 200.0,
        "require_same_zip5": True,
    }

    def _payload(self):
        return {
            "records": copy.deepcopy(self.RECORDS),
            "match_policy": dict(self.POLICY),
        }

    def _entity_for(self, output, record_id):
        for entity in output["entities"]:
            if record_id in entity["member_record_ids"]:
                return entity
        self.fail(f"no entity contains {record_id}")

    def test_merges_obvious_duplicate_pair(self):
        output, receipt = run_primitive(
            "prim:entity_normalize_and_dedupe",
            entity_normalize_and_dedupe,
            self._payload(),
            run_id="run:test:entity",
            declared_effects=["none"],
        )
        self.assertIsNone(receipt["error"])
        merged = self._entity_for(output, "r1")
        self.assertEqual(merged["member_record_ids"], ["r1", "r2"])
        self.assertEqual(merged["name"], "ST MARYS HEALTH CTR")
        self.assertEqual(merged["zip"], "45202")
        self.assertEqual(merged["phone"], "5135550142")
        self.assertEqual(merged["address"], "123 W ELM ST STE 4")
        self.assertEqual(merged["source_ids"], ["src_a", "src_b"])
        self.assertTrue(merged["entity_id"].startswith("ent:"))
        self.assertEqual(len(merged["entity_id"]), len("ent:") + 12)
        self.assertEqual(output["stats"]["input_records"], 6)
        self.assertEqual(output["stats"]["entities"], 5)
        self.assertEqual(output["stats"]["duplicates_merged"], 1)

    def test_does_not_merge_different_facility_in_same_block(self):
        outcome = entity_normalize_and_dedupe(self._payload())
        other = self._entity_for(outcome.output, "r3")
        self.assertEqual(other["member_record_ids"], ["r3"])
        # r1 vs r3 was actually compared (same block) and rejected on score.
        decisions = {
            (d["a"], d["b"]): d for d in outcome.output["match_decisions"]
        }
        self.assertIn(("r1", "r3"), decisions)
        self.assertFalse(decisions[("r1", "r3")]["matched"])
        self.assertLess(decisions[("r1", "r3")]["score"], 0.85)

    def test_does_not_merge_same_name_beyond_distance_limit(self):
        outcome = entity_normalize_and_dedupe(self._payload())
        decisions = {
            (d["a"], d["b"]): d for d in outcome.output["match_decisions"]
        }
        decision = decisions[("r5", "r6")]
        self.assertEqual(decision["score"], 1.0)
        self.assertGreater(decision["distance_m"], 200.0)
        self.assertFalse(decision["matched"])
        self.assertEqual(
            self._entity_for(outcome.output, "r5")["member_record_ids"], ["r5"]
        )

    def test_duplicate_pair_distance_is_about_50m(self):
        outcome = entity_normalize_and_dedupe(self._payload())
        decisions = {
            (d["a"], d["b"]): d for d in outcome.output["match_decisions"]
        }
        distance = decisions[("r1", "r2")]["distance_m"]
        self.assertGreater(distance, 30.0)
        self.assertLess(distance, 80.0)
        self.assertTrue(decisions[("r1", "r2")]["matched"])

    def test_blocking_reduces_comparisons(self):
        outcome = entity_normalize_and_dedupe(self._payload())
        stats = outcome.output["stats"]
        self.assertEqual(stats["pairs_possible"], 15)  # 6*5/2
        self.assertLess(stats["pairs_compared"], stats["pairs_possible"])
        self.assertLess(stats["blocking_reduction_ratio"], 1.0)
        self.assertGreater(stats["blocking_reduction_ratio"], 0.0)

    def test_idempotency_and_state_proofs_pass(self):
        outcome = entity_normalize_and_dedupe(self._payload())
        proofs = _proofs_by_name(outcome)
        self.assertTrue(proofs["schema_validation"].passed)
        self.assertTrue(proofs["no_cross_state_merge"].passed)
        self.assertTrue(proofs["idempotency_test"].passed)
        self.assertEqual(outcome.effects_observed, ["none"])

    def test_schema_validation_fails_on_bad_threshold(self):
        payload = self._payload()
        payload["match_policy"]["name_similarity_threshold"] = 1.5
        outcome = entity_normalize_and_dedupe(payload)
        proofs = _proofs_by_name(outcome)
        self.assertFalse(proofs["schema_validation"].passed)
        self.assertEqual(outcome.output["entities"], [])

    def test_schema_validation_fails_on_empty_records(self):
        outcome = entity_normalize_and_dedupe(
            {"records": [], "match_policy": dict(self.POLICY)}
        )
        proofs = _proofs_by_name(outcome)
        self.assertFalse(proofs["schema_validation"].passed)


class TestGeocodePolicyGate(unittest.TestCase):
    def _gate(self, **kwargs):
        payload = {
            "provider": "nominatim_public",
            "planned_request_count": 100,
            "bulk_job": False,
            "attribution_planned": True,
        }
        payload.update(kwargs)
        return geocode_policy_gate(payload)

    def test_nominatim_small_job_allowed_with_rate_limit(self):
        output, receipt = run_primitive(
            "prim:geocode_policy_gate",
            geocode_policy_gate,
            {
                "provider": "nominatim_public",
                "planned_request_count": 100,
                "bulk_job": False,
                "attribution_planned": True,
            },
            run_id="run:test:gate",
            declared_effects=["none"],
        )
        self.assertIsNone(receipt["error"])
        self.assertEqual(output["decision"], "allow_with_rate_limit")
        self.assertEqual(output["constraints"]["max_rate_per_sec"], 1)
        self.assertTrue(output["attribution_required"])

    def test_nominatim_large_count_denied(self):
        outcome = self._gate(planned_request_count=5000)
        self.assertEqual(outcome.output["decision"], "self_host_or_bulk_required")

    def test_nominatim_bulk_job_denied(self):
        outcome = self._gate(planned_request_count=10, bulk_job=True)
        self.assertEqual(outcome.output["decision"], "self_host_or_bulk_required")

    def test_overpass_small_job_allowed(self):
        outcome = self._gate(provider="overpass_public", planned_request_count=500)
        self.assertEqual(outcome.output["decision"], "allow_with_rate_limit")
        self.assertTrue(outcome.output["attribution_required"])

    def test_overpass_bulk_redirected_to_planet_extract(self):
        outcome = self._gate(provider="overpass_public", bulk_job=True)
        self.assertEqual(outcome.output["decision"], "use_planet_extract")
        outcome = self._gate(
            provider="overpass_public", planned_request_count=50000
        )
        self.assertEqual(outcome.output["decision"], "use_planet_extract")

    def test_census_geocoder_allowed_without_attribution(self):
        outcome = self._gate(
            provider="census_geocoder",
            planned_request_count=8000,
            attribution_planned=False,
        )
        self.assertEqual(outcome.output["decision"], "allow")
        self.assertFalse(outcome.output["attribution_required"])
        self.assertEqual(
            outcome.output["constraints"]["max_batch_records_per_file"], 10000
        )
        proofs = _proofs_by_name(outcome)
        self.assertTrue(proofs["attribution_consistency"].passed)

    def test_self_hosted_nominatim_allowed_with_odbl_note(self):
        outcome = self._gate(provider="self_hosted_nominatim", bulk_job=True)
        self.assertEqual(outcome.output["decision"], "allow")
        self.assertTrue(outcome.output["attribution_required"])
        self.assertTrue(
            any("ODbL" in reason for reason in outcome.output["reasons"])
        )

    def test_unknown_provider_denied(self):
        outcome = self._gate(provider="google_maps_scrape")
        self.assertEqual(outcome.output["decision"], "deny_unknown_provider")
        proofs = _proofs_by_name(outcome)
        self.assertTrue(proofs["policy_table_coverage"].passed)

    def test_attribution_consistency_proof_fails_without_plan(self):
        # Direct call: the failed proof would make run_primitive raise.
        outcome = self._gate(attribution_planned=False)
        proofs = _proofs_by_name(outcome)
        self.assertFalse(proofs["attribution_consistency"].passed)
        self.assertIn("attribution_planned is false", proofs["attribution_consistency"].detail)

    def test_all_known_providers_covered(self):
        for provider in (
            "nominatim_public",
            "overpass_public",
            "census_geocoder",
            "self_hosted_nominatim",
        ):
            outcome = self._gate(provider=provider)
            proofs = _proofs_by_name(outcome)
            self.assertTrue(proofs["policy_table_coverage"].passed, provider)
            self.assertNotEqual(
                outcome.output["decision"], "deny_unknown_provider", provider
            )


class TestEvidenceBundleWrapper(unittest.TestCase):
    OSM_ATTRIBUTION = "(c) OpenStreetMap contributors, ODbL 1.0"

    def _payload(self, **overrides):
        payload = {
            "answer": {"top_place": "ST MARYS HEALTH CTR", "score": 0.92},
            "source_snapshots": [
                {
                    "snapshot_id": "snap:osm:0001",
                    "source_id": "src:osm_overpass",
                    "license_family": "odbl",
                    "attribution": self.OSM_ATTRIBUTION,
                    "retrieved_mode": "fixture_offline",
                },
                {
                    "snapshot_id": "snap:census:0002",
                    "source_id": "src:census_geocoder",
                    "license_family": "public_domain",
                    "attribution": "",
                    "retrieved_mode": "fixture_offline",
                },
            ],
            "uncertainty_notes": ["coverage limited to the fixture region"],
            "attributions": [self.OSM_ATTRIBUTION],
        }
        payload.update(overrides)
        return payload

    def test_bundle_assembly_happy_path(self):
        output, receipt = run_primitive(
            "prim:evidence_bundle_wrapper",
            evidence_bundle_wrapper,
            self._payload(),
            run_id="run:test:evidence",
            declared_effects=["none"],
        )
        self.assertIsNone(receipt["error"])
        bundle = output["evidence_bundle"]
        self.assertEqual(bundle["answer"]["top_place"], "ST MARYS HEALTH CTR")
        self.assertEqual(len(bundle["source_refs"]), 2)
        self.assertEqual(bundle["attribution_block"], [self.OSM_ATTRIBUTION])
        self.assertIn(FIXTURE_OFFLINE_NOTE, bundle["uncertainty_report"])
        self.assertIn(
            "coverage limited to the fixture region", bundle["uncertainty_report"]
        )
        self.assertTrue(bundle["bundle_hash"].startswith("sha256:"))
        self.assertEqual(
            receipt["source_snapshot_ids"],
            ["snap:osm:0001", "snap:census:0002"],
        )

    def test_attribution_block_sorted_and_unique(self):
        outcome = evidence_bundle_wrapper(
            self._payload(
                attributions=[
                    "zeta data source",
                    self.OSM_ATTRIBUTION,
                    "zeta data source",
                    "  alpha data source  ",
                ]
            )
        )
        # ASCII sort: "(" precedes letters, so the OSM string comes first.
        self.assertEqual(
            outcome.output["evidence_bundle"]["attribution_block"],
            [self.OSM_ATTRIBUTION, "alpha data source", "zeta data source"],
        )

    def test_odbl_snapshot_without_attribution_fails_proof(self):
        # Direct call and proof inspection: through run_primitive this
        # failed proof raises PrimitiveExecutionError by design.
        outcome = evidence_bundle_wrapper(self._payload(attributions=[]))
        proofs = _proofs_by_name(outcome)
        self.assertFalse(proofs["attribution_complete"].passed)
        self.assertIn("snap:osm:0001", proofs["attribution_complete"].detail)
        self.assertTrue(proofs["source_ref_coverage"].passed)

    def test_no_snapshots_fails_source_ref_coverage(self):
        outcome = evidence_bundle_wrapper(self._payload(source_snapshots=[]))
        proofs = _proofs_by_name(outcome)
        self.assertFalse(proofs["source_ref_coverage"].passed)
        self.assertTrue(proofs["attribution_complete"].passed)

    def test_missing_uncertainty_notes_fails_proof_without_fixture_data(self):
        payload = self._payload(uncertainty_notes=[])
        for snapshot in payload["source_snapshots"]:
            snapshot["retrieved_mode"] = "live_api"
        outcome = evidence_bundle_wrapper(payload)
        proofs = _proofs_by_name(outcome)
        self.assertFalse(proofs["uncertainty_report_present"].passed)

    def test_bundle_hash_stability(self):
        hash_a = evidence_bundle_wrapper(self._payload()).output[
            "evidence_bundle"
        ]["bundle_hash"]
        hash_b = evidence_bundle_wrapper(self._payload()).output[
            "evidence_bundle"
        ]["bundle_hash"]
        self.assertEqual(hash_a, hash_b)
        changed = evidence_bundle_wrapper(
            self._payload(answer={"top_place": "OAKWOOD COMMUNITY CLINIC"})
        ).output["evidence_bundle"]["bundle_hash"]
        self.assertNotEqual(hash_a, changed)


if __name__ == "__main__":
    unittest.main()
