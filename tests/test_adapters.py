"""Tests for source-adapter P0 primitives against synthetic offline fixtures.

Run from the repo root:

    python3 -m unittest tests.test_adapters -v

Every adapter runs through FixtureTransport (mode "fixture_offline"); no
network access happens in this suite. Fixtures are SYNTHETIC data shaped
like the real APIs and every fixture file carries "fixture_synthetic": true.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from primitives.adapters.arcgis import arcgis_featureserver_layer_ingester
from primitives.adapters.ckan import ckan_package_resource_harvester
from primitives.adapters.hrsa import hrsa_health_center_ingester
from primitives.adapters.nppes import nppes_provider_identity_resolver
from primitives.adapters.overpass import osm_overpass_bounded_poi_query
from primitives.adapters.socrata import socrata_soql_dataset_ingester
from primitives.adapters.transport import FixtureTransport, TransportError
from primitives.core import PrimitiveOutcome

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_ROOT = REPO_ROOT / "fixtures" / "place-discovery"

HARRIS_BBOX = [29.5, -95.8, 30.2, -95.0]
GLACIER_BBOX = [48.4, -113.4, 49.0, -112.6]

HRSA_HARRIS_PAYLOAD = {
    "aoi_id": "aoi:harris_county_tx",
    "state": "TX",
    "fixture_name": "hrsa_sites_harris_tx.json",
}
HRSA_GLACIER_PAYLOAD = {
    "aoi_id": "aoi:glacier_county_mt",
    "state": "MT",
    "fixture_name": "hrsa_sites_glacier_mt.json",
}
NPPES_HARRIS_PAYLOAD = {
    "aoi_id": "aoi:harris_county_tx",
    "state": "TX",
    "candidate_names": [
        "Gulf Coast Community Health Center",
        "Bayou City Family Clinic",
        "Northline Neighborhood Health Services",
        "Totally Unknown Facility Zz",
    ],
    "fixture_name": "nppes_orgs_harris_tx.json",
}
NPPES_GLACIER_PAYLOAD = {
    "aoi_id": "aoi:glacier_county_mt",
    "state": "MT",
    "candidate_names": ["Browning Community Health Station"],
    "fixture_name": "nppes_orgs_glacier_mt.json",
}
CKAN_PAYLOAD = {
    "query": "health facilities",
    "fixture_name": "ckan_package_search_health.json",
}
SOCRATA_PAYLOAD = {
    "domain": "data.example-city.gov",
    "dataset_id": "hlth-insp",
    "soql": "SELECT * WHERE result IS NOT NULL LIMIT 8",
    "fixture_name": "socrata_health_inspections.json",
}
ARCGIS_PAYLOAD = {
    "layer_url_family": (
        "https://services.example.org/arcgis/rest/services/"
        "health_facilities/FeatureServer/0"
    ),
    "where": "FACILITY_TYPE='clinic'",
    "fixture_name": "arcgis_facilities_harris_tx.json",
}
OVERPASS_HARRIS_PAYLOAD = {
    "bbox": HARRIS_BBOX,
    "tags": {"amenity": "clinic"},
    "fixture_name": "overpass_clinics_harris_tx.json",
}
OVERPASS_GLACIER_PAYLOAD = {
    "bbox": GLACIER_BBOX,
    "tags": {"amenity": "clinic"},
    "fixture_name": "overpass_clinics_glacier_mt.json",
}

ALL_ADAPTER_RUNS = [
    ("hrsa_harris", hrsa_health_center_ingester, HRSA_HARRIS_PAYLOAD),
    ("hrsa_glacier", hrsa_health_center_ingester, HRSA_GLACIER_PAYLOAD),
    ("nppes_harris", nppes_provider_identity_resolver, NPPES_HARRIS_PAYLOAD),
    ("nppes_glacier", nppes_provider_identity_resolver, NPPES_GLACIER_PAYLOAD),
    ("ckan", ckan_package_resource_harvester, CKAN_PAYLOAD),
    ("socrata", socrata_soql_dataset_ingester, SOCRATA_PAYLOAD),
    ("arcgis", arcgis_featureserver_layer_ingester, ARCGIS_PAYLOAD),
    ("overpass_harris", osm_overpass_bounded_poi_query, OVERPASS_HARRIS_PAYLOAD),
    ("overpass_glacier", osm_overpass_bounded_poi_query, OVERPASS_GLACIER_PAYLOAD),
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


def make_transport() -> FixtureTransport:
    return FixtureTransport(fixture_root=FIXTURE_ROOT)


class TestFixtureTransport(unittest.TestCase):
    def test_snapshot_id_shape_and_stability(self):
        transport = make_transport()
        response_a, snap_a = transport.get_json(
            "", {}, "hrsa_sites_harris_tx.json"
        )
        response_b, snap_b = transport.get_json(
            "", {}, "hrsa_sites_harris_tx.json"
        )
        self.assertEqual(snap_a, snap_b)
        self.assertTrue(snap_a.startswith("snap:"))
        self.assertEqual(len(snap_a), len("snap:") + 16)
        self.assertEqual(response_a, response_b)

    def test_missing_fixture_raises(self):
        transport = make_transport()
        with self.assertRaises(TransportError):
            transport.get_json("", {}, "does_not_exist.json")

    def test_every_fixture_declares_synthetic(self):
        # Honesty rule: everything under fixtures/place-discovery is
        # synthetic and must say so.
        fixture_files = sorted(FIXTURE_ROOT.glob("*.json"))
        self.assertGreaterEqual(len(fixture_files), 9)
        for path in fixture_files:
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertIs(
                payload.get("fixture_synthetic"),
                True,
                f"{path.name} must carry fixture_synthetic: true",
            )
        # The adapter fixtures additionally carry the transport shape.
        adapter_fixtures = {run[2]["fixture_name"] for run in ALL_ADAPTER_RUNS}
        self.assertEqual(len(adapter_fixtures), 9)
        for name in sorted(adapter_fixtures):
            payload = json.loads(
                (FIXTURE_ROOT / name).read_text(encoding="utf-8")
            )
            self.assertIn("recorded_shape", payload, name)
            self.assertIn("request", payload, name)
            self.assertIn("response", payload, name)


class TestAllAdaptersCommonContract(unittest.TestCase):
    """Contract shared by every adapter when run offline against fixtures."""

    def test_outcome_shape_effects_and_snapshot_meta(self):
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
                self.assertEqual(
                    outcome.source_snapshot_ids, [meta["snapshot_id"]]
                )
                self.assertTrue(meta["snapshot_id"].startswith("snap:"))

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


class TestHrsaAdapter(unittest.TestCase):
    def test_harris_records_normalized(self):
        outcome = hrsa_health_center_ingester(HRSA_HARRIS_PAYLOAD, make_transport())
        records = outcome.output["records"]
        self.assertGreaterEqual(len(records), 8)
        self.assertLessEqual(len(records), 12)
        for rec in records:
            self.assertEqual(set(rec), FACILITY_RECORD_KEYS)
            self.assertEqual(rec["source_id"], "src:hrsa.health_center_sites")
            self.assertTrue(rec["record_id"].startswith("hrsa:"))
            self.assertIsNone(rec["phone"])
            self.assertAlmostEqual(rec["lat"], 29.86, delta=0.35)
            self.assertAlmostEqual(rec["lon"], -95.39, delta=0.35)
        self.assertEqual(
            outcome.output["snapshot_meta"]["license_family"],
            "public_domain_us_gov",
        )

    def test_glacier_frontier_scarcity(self):
        outcome = hrsa_health_center_ingester(HRSA_GLACIER_PAYLOAD, make_transport())
        records = outcome.output["records"]
        self.assertGreaterEqual(len(records), 2)
        self.assertLessEqual(len(records), 3)
        for rec in records:
            self.assertAlmostEqual(rec["lat"], 48.70, delta=0.35)
            self.assertAlmostEqual(rec["lon"], -112.99, delta=0.35)

    def test_proof_names(self):
        outcome = hrsa_health_center_ingester(HRSA_HARRIS_PAYLOAD, make_transport())
        self.assertEqual(
            [p.proof for p in outcome.proof_results],
            ["schema_validation", "row_count_positive", "coordinates_in_range"],
        )


class TestNppesAdapter(unittest.TestCase):
    def test_harris_matching_produces_matched_decisions(self):
        outcome = nppes_provider_identity_resolver(
            NPPES_HARRIS_PAYLOAD, make_transport()
        )
        decisions = outcome.output["match_decisions"]
        matched = [d for d in decisions if d["matched"]]
        self.assertGreaterEqual(len(matched), 1)
        by_candidate = {}
        for d in decisions:
            by_candidate.setdefault(d["candidate"], []).append(d)
        # Every candidate got at least one decision receipt.
        for name in NPPES_HARRIS_PAYLOAD["candidate_names"]:
            self.assertIn(name, by_candidate)
        # The near-duplicate variants resolve despite abbreviation noise.
        gulf = by_candidate["Gulf Coast Community Health Center"]
        self.assertTrue(any(d["matched"] and d["npi"] == "1990000101" for d in gulf))
        # The unknown candidate is honestly unmatched.
        unknown = by_candidate["Totally Unknown Facility Zz"]
        self.assertEqual(len(unknown), 1)
        self.assertFalse(unknown[0]["matched"])
        self.assertIsNone(unknown[0]["npi"])
        for d in decisions:
            self.assertEqual(set(d), {"candidate", "npi", "matched", "reason"})

    def test_npi_format_and_proofs(self):
        outcome = nppes_provider_identity_resolver(
            NPPES_HARRIS_PAYLOAD, make_transport()
        )
        proof_names = [p.proof for p in outcome.proof_results]
        self.assertEqual(
            proof_names,
            [
                "schema_validation",
                "npi_format_check",
                "match_decision_receipt_present",
            ],
        )
        for rec in outcome.output["records"]:
            self.assertRegex(rec["npi"], r"^199\d{7}$")

    def test_glacier_matching(self):
        outcome = nppes_provider_identity_resolver(
            NPPES_GLACIER_PAYLOAD, make_transport()
        )
        matched = [d for d in outcome.output["match_decisions"] if d["matched"]]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["npi"], "1990001111")


class TestCkanAdapter(unittest.TestCase):
    def test_datasets_and_license_flags(self):
        outcome = ckan_package_resource_harvester(CKAN_PAYLOAD, make_transport())
        datasets = {d["name"]: d for d in outcome.output["datasets"]}
        self.assertEqual(len(datasets), 5)
        # The dataset with no license_id is flagged for review.
        unlicensed = datasets["community-care-sites"]
        self.assertIsNone(unlicensed["license_id"])
        self.assertEqual(
            unlicensed["license_family"], "unspecified_requires_review"
        )
        self.assertTrue(unlicensed["requires_license_review"])
        # Stated licenses are recorded per dataset.
        self.assertEqual(
            datasets["harris-county-health-facilities"]["license_family"], "cc_by"
        )
        self.assertEqual(datasets["texas-clinic-locations"]["license_family"], "cc0")
        self.assertEqual(
            datasets["regional-health-inspections"]["license_family"], "odbl"
        )
        for ds in datasets.values():
            self.assertTrue(ds["resources"])
            for res in ds["resources"]:
                self.assertTrue(res["url"])

    def test_proof_names(self):
        outcome = ckan_package_resource_harvester(CKAN_PAYLOAD, make_transport())
        self.assertEqual(
            [p.proof for p in outcome.proof_results],
            [
                "schema_validation",
                "license_recorded_per_dataset",
                "resource_url_present",
            ],
        )


class TestSocrataAdapter(unittest.TestCase):
    def test_typed_rows_and_field_inference(self):
        outcome = socrata_soql_dataset_ingester(SOCRATA_PAYLOAD, make_transport())
        self.assertEqual(outcome.output["row_count"], 8)
        types = outcome.output["field_types"]
        self.assertEqual(types["score"], "integer")
        self.assertEqual(types["violation_count"], "integer")
        self.assertEqual(types["latitude"], "float")
        self.assertEqual(types["longitude"], "float")
        self.assertEqual(types["inspection_date"], "datetime")
        self.assertEqual(types["facility_name"], "text")
        self.assertEqual(types["result"], "text")
        first = outcome.output["records"][0]
        self.assertEqual(first["record_id"], "socrata:hlth-insp:1")
        self.assertEqual(
            first["source_id"], "src:socrata.data.example-city.gov.hlth-insp"
        )
        self.assertIsInstance(first["fields"]["score"], int)
        self.assertIsInstance(first["fields"]["latitude"], float)
        self.assertIsInstance(first["fields"]["inspection_date"], str)

    def test_proof_names(self):
        outcome = socrata_soql_dataset_ingester(SOCRATA_PAYLOAD, make_transport())
        self.assertEqual(
            [p.proof for p in outcome.proof_results],
            ["schema_validation", "row_count_positive", "field_types_inferred"],
        )


class TestArcgisAdapter(unittest.TestCase):
    def test_features_normalized_to_point_records(self):
        outcome = arcgis_featureserver_layer_ingester(
            ARCGIS_PAYLOAD, make_transport()
        )
        records = outcome.output["records"]
        self.assertEqual(len(records), 6)
        for rec in records:
            self.assertEqual(rec["source_id"], "src:arcgis.featureserver")
            self.assertTrue(rec["record_id"].startswith("arcgis:"))
            self.assertTrue(rec["name"])
            # geometry.y is lat, geometry.x is lon
            self.assertAlmostEqual(rec["lat"], 29.86, delta=0.35)
            self.assertAlmostEqual(rec["lon"], -95.39, delta=0.35)

    def test_proof_names(self):
        outcome = arcgis_featureserver_layer_ingester(
            ARCGIS_PAYLOAD, make_transport()
        )
        self.assertEqual(
            [p.proof for p in outcome.proof_results],
            ["schema_validation", "geometry_present", "coordinates_in_range"],
        )


class TestOverpassAdapter(unittest.TestCase):
    def test_harris_bbox_containment_and_attribution(self):
        outcome = osm_overpass_bounded_poi_query(
            OVERPASS_HARRIS_PAYLOAD, make_transport()
        )
        records = outcome.output["records"]
        self.assertEqual(len(records), 6)
        south, west, north, east = HARRIS_BBOX
        for rec in records:
            self.assertTrue(south <= rec["lat"] <= north, rec["record_id"])
            self.assertTrue(west <= rec["lon"] <= east, rec["record_id"])
            self.assertEqual(rec["license_family"], "odbl")
            self.assertIs(rec["attribution_required"], True)
        meta = outcome.output["snapshot_meta"]
        self.assertEqual(meta["license_family"], "odbl")
        self.assertIn("OpenStreetMap contributors", meta["attribution"])
        self.assertIn("synthetic", meta["attribution"])

    def test_glacier_bbox_containment(self):
        outcome = osm_overpass_bounded_poi_query(
            OVERPASS_GLACIER_PAYLOAD, make_transport()
        )
        records = outcome.output["records"]
        self.assertGreaterEqual(len(records), 1)
        self.assertLessEqual(len(records), 2)
        south, west, north, east = GLACIER_BBOX
        for rec in records:
            self.assertTrue(south <= rec["lat"] <= north)
            self.assertTrue(west <= rec["lon"] <= east)

    def test_proof_names(self):
        outcome = osm_overpass_bounded_poi_query(
            OVERPASS_HARRIS_PAYLOAD, make_transport()
        )
        self.assertEqual(
            [p.proof for p in outcome.proof_results],
            ["schema_validation", "attribution_flag_set", "bbox_containment"],
        )


class TestEntityResolutionRawMaterial(unittest.TestCase):
    """The fixtures deliberately contain near-duplicate facility variants
    across HRSA, NPPES, and Overpass so entity resolution has real work."""

    def test_near_duplicate_variants_align_at_nearby_coords(self):
        transport = make_transport()
        hrsa = hrsa_health_center_ingester(HRSA_HARRIS_PAYLOAD, transport)
        osm = osm_overpass_bounded_poi_query(OVERPASS_HARRIS_PAYLOAD, transport)
        hrsa_by_name = {r["name"]: r for r in hrsa.output["records"]}
        osm_by_name = {r["name"]: r for r in osm.output["records"]}
        pairs = [
            ("Gulf Coast Community Health Center", "Gulf Coast Community Health Center"),
            ("Bayou City Family Clinic", "Bayou City Family Clinic"),
            ("Northline Neighborhood Health Services", "Northline Neighborhood Health Svcs"),
        ]
        for hrsa_name, osm_name in pairs:
            with self.subTest(facility=hrsa_name):
                a = hrsa_by_name[hrsa_name]
                b = osm_by_name[osm_name]
                self.assertLess(abs(a["lat"] - b["lat"]), 0.01)
                self.assertLess(abs(a["lon"] - b["lon"]), 0.01)


if __name__ == "__main__":
    unittest.main()
