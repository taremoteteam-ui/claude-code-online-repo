"""Contract tests for the primitive-foundry ingestion pipeline."""

import unittest

from primitives.foundry import acquire, form, verify, ALLOWED_LICENSES

GEO = {
    "source_id": "src:fixture.t", "library": "t_lib", "license": "MIT",
    "retrieved_mode": "fixture_synthetic",
    "functions": [
        {"name": "parse_x", "params": [{"name": "raw", "type": "GeoJsonDocument"}],
         "returns": "PointFeatureCollection", "does": "parse a geojson doc into points", "effects": ["none"]},
        {"name": "fetch_y", "params": [{"name": "aoi", "type": "AreaOfInterest"},
                                       {"name": "p", "type": "FetchPolicy"}],
         "returns": "TileImageSet", "does": "fetch raster tiles for an area", "effects": ["network_read"]},
    ],
}
GPL = {"source_id": "src:fixture.g", "library": "g_lib", "license": "GPL-3.0",
       "retrieved_mode": "fixture_synthetic",
       "functions": [{"name": "c", "params": [{"name": "r", "type": "EntityRecordSet"}],
                      "returns": "ClusterSet", "does": "cluster the records into groups", "effects": ["none"]}]}


class FoundryTests(unittest.TestCase):
    def test_acquire_discloses_provenance(self):
        snap, receipt = acquire(GEO, path="cached_snapshot")
        self.assertEqual(receipt["retrieved_mode"], "fixture_synthetic")
        self.assertEqual(receipt["acquire_path"], "cached_snapshot")
        self.assertEqual(receipt["symbols_seen"], 2)

    def test_acquire_rejects_unknown_path(self):
        with self.assertRaises(ValueError):
            acquire(GEO, path="teleport")

    def test_form_edge_types_signatures(self):
        snap, _ = acquire(GEO)
        mined = form(snap)
        by_symbol = {m["symbol"]: m for m in mined}
        self.assertEqual(by_symbol["parse_x"]["input_edge"], "GeoJsonDocument")
        self.assertEqual(by_symbol["parse_x"]["output_edge"], "PointFeatureCollection")
        # config port stays on the input edge; effect drives a proof obligation
        self.assertIn("FetchPolicy", by_symbol["fetch_y"]["input_edge"])
        self.assertIn("source_snapshot_receipt", by_symbol["fetch_y"]["proof_obligations"])

    def test_license_gate_blocks_non_permissive(self):
        snap, _ = acquire(GPL)
        mined = form(snap)
        self.assertEqual(mined[0]["verification_status"], "license_blocked")
        self.assertTrue(mined[0]["promotion_blockers"])
        # and a permissive one is not blocked
        self.assertIn("MIT", ALLOWED_LICENSES)

    def test_verify_flips_verified_and_recomputes(self):
        snap, _ = acquire(GEO)
        for m in form(snap):
            v = verify(m)
            self.assertTrue(v["passed"])
            self.assertEqual(v["verification_status"], "fixture_verified")

    def test_verify_never_passes_license_blocked(self):
        snap, _ = acquire(GPL)
        m = form(snap)[0]
        v = verify(m)
        self.assertFalse(v["passed"])
        self.assertEqual(v["verification_status"], "license_blocked")

    def test_boundary_on_every_mined_row(self):
        snap, _ = acquire(GEO)
        for m in form(snap):
            self.assertIs(m["candidate"], True)
            self.assertIs(m["serves_truth"], False)


if __name__ == "__main__":
    unittest.main()
