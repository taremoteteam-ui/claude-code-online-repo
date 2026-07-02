"""Contract tests for the CandidateBundle search layer."""

import importlib.util
import json
import unittest
from pathlib import Path

from primitives.search import (
    PackSearchIndex,
    bundle_covered_primitives,
    candidate_bundle_search,
    tokenize,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "candidate_bundle.schema.json"


def load_validator():
    spec = importlib.util.spec_from_file_location(
        "pack_checker", REPO_ROOT / "scripts" / "check_place_discovery_geospatial_pack.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.StructuralValidator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


class TokenizeTests(unittest.TestCase):
    def test_camel_case_edges_split(self):
        tokens = tokenize("AreaOfInterest+ClinicSearchPolicy")
        self.assertIn("clinic", tokens)
        self.assertIn("interest", tokens)
        self.assertIn("policy", tokens)

    def test_stopwords_removed(self):
        self.assertNotIn("the", tokenize("the clinic of the county"))


class BundleTests(unittest.TestCase):
    def test_bundle_is_schema_valid(self):
        bundle = candidate_bundle_search(
            "Find all federally funded health centers near this county and map coverage gaps")
        errors = load_validator().validate(bundle)
        self.assertEqual(errors, [], errors)

    def test_bundle_deterministic(self):
        q = "rank underserved areas for a new clinic site"
        b1 = candidate_bundle_search(q)
        b2 = candidate_bundle_search(q)
        self.assertEqual(b1, b2)

    def test_bundle_never_single_answer(self):
        bundle = candidate_bundle_search("harvest open data portal datasets about health")
        self.assertGreaterEqual(
            len(bundle["exact_matches"]) + len(bundle["near_matches"]), 2)
        self.assertTrue(bundle["fallback_options"])
        self.assertTrue(bundle["ranking_explanation"])

    def test_group_hit_covers_members(self):
        bundle = candidate_bundle_search(
            "which populated areas are more than 30 minutes from the nearest primary care site")
        covered = bundle_covered_primitives(bundle)
        self.assertIn("prim:place_discovery.nearest_facility_isochrone_catchment_analysis",
                      covered)
        self.assertIn("prim:place_discovery.hrsa_health_center_ingester", covered)

    def test_index_scores_sorted_desc(self):
        index = PackSearchIndex()
        scored = index.score("clinic discovery evidence map")
        values = [s for _, s in scored]
        self.assertEqual(values, sorted(values, reverse=True))


if __name__ == "__main__":
    unittest.main()
