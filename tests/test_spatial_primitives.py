"""Tests for the spatial P0 primitives (stdlib unittest, offline fixtures).

Run from the repo root:
    python3 -m unittest tests.test_spatial_primitives -v

All geometry here is SYNTHETIC fixture data; nothing asserts real-world
boundaries or populations.
"""

from __future__ import annotations

import hashlib
import json
import math
import unittest
from pathlib import Path

from primitives.maps import map_artifact_generation
from primitives.spatial import (
    haversine_km,
    nearest_facility_catchment,
    point_to_boundary_spatial_join,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = REPO_ROOT / "fixtures" / "place-discovery"

AOI_CENTROIDS = {
    "aoi:harris_county_tx": (29.86, -95.39),
    "aoi:glacier_county_mt": (48.70, -112.99),
    "aoi:fresno_county_ca": (36.76, -119.65),
    "aoi:mcdowell_county_wv": (37.38, -81.65),
}


def load_boundaries() -> dict:
    with open(FIXTURE_DIR / "aoi_boundaries.geojson", "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_demand_points() -> dict:
    with open(FIXTURE_DIR / "demand_points.json", "r", encoding="utf-8") as fh:
        return json.load(fh)


def proofs_by_name(outcome) -> dict:
    return {p.proof: p for p in outcome.proof_results}


class TestPointToBoundarySpatialJoin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.boundaries = load_boundaries()

    def test_fixture_has_all_four_aois(self):
        ids = {f["properties"]["boundary_id"] for f in self.boundaries["features"]}
        self.assertEqual(ids, set(AOI_CENTROIDS))
        for feat in self.boundaries["features"]:
            self.assertEqual(feat["geometry"]["type"], "Polygon")
            self.assertTrue(feat["properties"]["fixture_synthetic"])
            self.assertEqual(
                feat["properties"]["boundary_vintage"], "synthetic-fixture-2026"
            )

    def test_inside_outside_and_centroid_per_aoi(self):
        points = []
        expected = {}
        for aoi_id, (clat, clon) in AOI_CENTROIDS.items():
            slug = aoi_id.split(":")[1]
            centroid_id = f"c:{slug}"
            inside_id = f"i:{slug}"
            outside_id = f"o:{slug}"
            points.append({"id": centroid_id, "lat": clat, "lon": clon})
            # 0.1 deg offset is well within the 0.35-deg hexagon inradius
            points.append({"id": inside_id, "lat": clat + 0.1, "lon": clon + 0.1})
            # 5 deg offset is far outside every fixture hexagon
            points.append({"id": outside_id, "lat": clat + 5.0, "lon": clon})
            expected[centroid_id] = aoi_id
            expected[inside_id] = aoi_id
            expected[outside_id] = None
        outcome = point_to_boundary_spatial_join(
            {"points": points, "boundaries": self.boundaries}
        )
        got = {row["id"]: row["boundary_id"] for row in outcome.output["joined_points"]}
        self.assertEqual(got, expected)

    def test_join_stats_counts(self):
        points = [
            {"id": f"c:{aoi.split(':')[1]}", "lat": lat, "lon": lon}
            for aoi, (lat, lon) in AOI_CENTROIDS.items()
        ]
        points.append({"id": "ocean", "lat": 0.0, "lon": 0.0})
        outcome = point_to_boundary_spatial_join(
            {"points": points, "boundaries": self.boundaries}
        )
        stats = outcome.output["stats"]
        self.assertEqual(stats, {"points": 5, "matched": 4, "unmatched": 1})

    def test_method_receipt_and_proofs(self):
        outcome = point_to_boundary_spatial_join(
            {"points": [{"id": "p1", "lat": 29.86, "lon": -95.39}],
             "boundaries": self.boundaries}
        )
        method = outcome.output["method"]
        self.assertEqual(method["algorithm"], "ray_casting")
        self.assertEqual(method["crs_assumed"], "EPSG:4326")
        self.assertEqual(method["boundary_vintage"], "synthetic-fixture-2026")
        self.assertEqual(method["boundary_source"], "fixture_synthetic")
        self.assertEqual(outcome.effects_observed, ["none"])
        proofs = proofs_by_name(outcome)
        for name in (
            "schema_validation",
            "crs_receipt_present",
            "boundary_vintage_receipt",
            "containment_sanity",
        ):
            self.assertIn(name, proofs)
            self.assertTrue(proofs[name].passed, name)

    def test_all_fixture_demand_points_join_to_their_aoi(self):
        demand = load_demand_points()
        self.assertTrue(demand["fixture_synthetic"])
        for aoi_id, rows in demand["by_aoi"].items():
            self.assertGreaterEqual(len(rows), 6, aoi_id)
            self.assertLessEqual(len(rows), 12, aoi_id)
            outcome = point_to_boundary_spatial_join(
                {"points": [{"id": r["id"], "lat": r["lat"], "lon": r["lon"]}
                            for r in rows],
                 "boundaries": self.boundaries}
            )
            for row in outcome.output["joined_points"]:
                self.assertEqual(row["boundary_id"], aoi_id, row["id"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            point_to_boundary_spatial_join({"points": "nope", "boundaries": {}})


class TestNearestFacilityCatchment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        demand = load_demand_points()
        cls.harris_points = demand["by_aoi"]["aoi:harris_county_tx"]

    def _payload(self, max_km: float) -> dict:
        return {
            "facilities": [
                {"id": "fac:harris_center", "lat": 29.86, "lon": -95.39},
                {"id": "fac:harris_east", "lat": 29.90, "lon": -95.15},
            ],
            "demand_points": self.harris_points,
            "travel_policy": {
                "max_km": max_km,
                "method": "straight_line_haversine_proxy",
            },
        }

    def test_assignments_pick_true_nearest_facility(self):
        payload = self._payload(25.0)
        outcome = nearest_facility_catchment(payload)
        facs = payload["facilities"]
        for asg in outcome.output["assignments"]:
            dp = next(d for d in self.harris_points if d["id"] == asg["demand_id"])
            dists = {
                f["id"]: haversine_km(dp["lat"], dp["lon"], f["lat"], f["lon"])
                for f in facs
            }
            best = min(dists, key=lambda k: (dists[k], k))
            self.assertEqual(asg["facility_id"], best, asg["demand_id"])
            self.assertAlmostEqual(asg["distance_km"], dists[best], places=5)

    def test_population_conservation_and_ratio(self):
        outcome = nearest_facility_catchment(self._payload(25.0))
        report = outcome.output["coverage_report"]
        total = sum(d["population"] for d in self.harris_points)
        self.assertEqual(report["total_population"], total)
        self.assertEqual(
            report["covered_population"] + report["uncovered_population"], total
        )
        self.assertAlmostEqual(
            report["coverage_ratio"],
            report["covered_population"] / total,
            places=6,
        )
        proofs = proofs_by_name(outcome)
        self.assertTrue(proofs["population_conservation"].passed)

    def test_coverage_extremes(self):
        # A generous radius covers everyone; a tiny radius covers no one
        # unless a demand point sits exactly on a facility.
        full = nearest_facility_catchment(self._payload(10000.0)).output
        self.assertEqual(full["coverage_report"]["uncovered_population"], 0)
        self.assertEqual(full["coverage_report"]["coverage_ratio"], 1.0)
        tiny = nearest_facility_catchment(self._payload(0.001)).output
        self.assertEqual(tiny["coverage_report"]["covered_population"], 0)
        self.assertEqual(tiny["coverage_report"]["coverage_ratio"], 0.0)

    def test_method_honesty_fields(self):
        outcome = nearest_facility_catchment(self._payload(25.0))
        method = outcome.output["method"]
        self.assertEqual(method["distance"], "haversine_great_circle")
        self.assertEqual(method["travel_time"], "NOT_COMPUTED_straight_line_proxy")
        self.assertIn("proxy", method["caveat"])
        self.assertIn("not modeled", method["caveat"])
        self.assertEqual(outcome.effects_observed, ["none"])
        proofs = proofs_by_name(outcome)
        for name in (
            "schema_validation",
            "method_receipt_honest",
            "population_conservation",
            "distance_symmetry_spot_check",
        ):
            self.assertIn(name, proofs)
            self.assertTrue(proofs[name].passed, name)

    def test_rejects_unknown_travel_method(self):
        payload = self._payload(25.0)
        payload["travel_policy"]["method"] = "drive_time_isochrone"
        with self.assertRaises(ValueError):
            nearest_facility_catchment(payload)

    def test_haversine_symmetry_and_scale(self):
        a = (29.86, -95.39)
        b = (48.70, -112.99)
        self.assertAlmostEqual(
            haversine_km(*a, *b), haversine_km(*b, *a), places=9
        )
        self.assertEqual(haversine_km(*a, *a), 0.0)
        # one degree of latitude is ~111.19 km on the sphere used
        d = haversine_km(29.0, -95.0, 30.0, -95.0)
        self.assertAlmostEqual(d, math.pi * 6371.0088 / 180.0, places=3)


class TestMapArtifactGeneration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        boundaries = load_boundaries()
        cls.harris_feature = next(
            f for f in boundaries["features"]
            if f["properties"]["boundary_id"] == "aoi:harris_county_tx"
        )
        demand = load_demand_points()["by_aoi"]["aoi:harris_county_tx"]
        cls.points = [
            {
                "id": row["id"],
                "lat": row["lat"],
                "lon": row["lon"],
                "label_class": "covered" if i % 3 else "uncovered",
            }
            for i, row in enumerate(demand)
        ]
        cls.points.append(
            {"id": "fac:harris_center", "lat": 29.86, "lon": -95.39,
             "label_class": "facility"}
        )
        cls.payload = {
            "title": "Harris County (synthetic) coverage map",
            "boundary": cls.harris_feature,
            "points": cls.points,
            "attribution": "Synthetic fixture geometry; NOT census or survey data.",
        }

    def test_svg_proofs_pass_on_real_render(self):
        outcome = map_artifact_generation(self.payload)
        proofs = proofs_by_name(outcome)
        for name in (
            "nonblank_map_artifact_test",
            "title_labeled",
            "attribution_present",
            "viewbox_valid",
        ):
            self.assertIn(name, proofs)
            self.assertTrue(proofs[name].passed, name)
        self.assertEqual(outcome.effects_observed, ["none"])

    def test_svg_content_and_stats(self):
        outcome = map_artifact_generation(self.payload)
        svg = outcome.output["svg"]
        self.assertIn('<path class="boundary"', svg)
        self.assertIn('<circle class="pt', svg)
        self.assertIn('<rect class="pt pt-facility"', svg)
        self.assertIn("Harris County (synthetic) coverage map", svg)
        self.assertIn("Synthetic fixture geometry; NOT census or survey data.", svg)
        stats = outcome.output["artifact_stats"]
        self.assertEqual(stats["points_rendered"], len(self.points))
        self.assertEqual(stats["width"], 600)
        self.assertEqual(stats["height"], 600)
        # exactly one real mark per point (legend swatches excluded)
        marks = svg.count('class="pt ')
        self.assertEqual(marks, len(self.points))

    def test_artifact_ref_hash_matches_svg_bytes(self):
        outcome = map_artifact_generation(self.payload)
        self.assertEqual(len(outcome.artifacts), 1)
        ref = outcome.artifacts[0]
        self.assertEqual(ref.artifact_type, "svg_map")
        expected = hashlib.sha256(
            outcome.output["svg"].encode("utf-8")
        ).hexdigest()
        self.assertEqual(ref.content_sha256, expected)

    def test_svg_render_is_deterministic(self):
        first = map_artifact_generation(json.loads(json.dumps(self.payload)))
        second = map_artifact_generation(json.loads(json.dumps(self.payload)))
        self.assertEqual(first.output["svg"], second.output["svg"])
        self.assertEqual(
            first.artifacts[0].content_sha256,
            second.artifacts[0].content_sha256,
        )

    def test_rejects_bad_label_class(self):
        payload = dict(self.payload)
        payload["points"] = [
            {"id": "x", "lat": 29.86, "lon": -95.39, "label_class": "mystery"}
        ]
        with self.assertRaises(ValueError):
            map_artifact_generation(payload)


if __name__ == "__main__":
    unittest.main()
