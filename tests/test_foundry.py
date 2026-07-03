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

    def test_robust_to_messy_and_missing_types(self):
        # Real mined signatures carry messy type strings and missing returns;
        # form() must still emit parseable edges and never crash.
        messy = {"source_id": "src:fixture.messy", "library": "messy", "license": "MIT",
                 "retrieved_mode": "fixture_synthetic",
                 "functions": [
                     {"name": "f", "params": [{"name": "x", "type": "List[str]"},
                                              {"name": "y", "type": "dict|None"}],
                      "returns": "record_set", "does": "handles messy types cleanly", "effects": ["none"]},
                     {"name": "g", "params": [], "does": "no return type declared at all", "effects": ["none"]},
                 ]}
        import re as _re
        snap, _ = acquire(messy)
        rows = {m["symbol"]: m for m in form(snap)}
        # messy param/return types sanitized to CamelCase alphanumeric edges
        self.assertTrue(_re.match(r"^[A-Za-z0-9+]+$", rows["f"]["input_edge"]))
        self.assertTrue(_re.match(r"^[A-Za-z0-9+]+$", rows["f"]["output_edge"]))
        self.assertEqual(rows["f"]["output_edge"], "RecordSet")
        # missing return -> Unit output, still forms and verifies structurally
        self.assertEqual(rows["g"]["input_edge"], "NoInput")
        self.assertEqual(rows["g"]["output_edge"], "Unit")

    def test_acquire_secret_scan_and_exclusion(self):
        dirty = {"source_id": "src:fixture.d", "library": "d", "license": "MIT",
                 "retrieved_mode": "fixture_synthetic",
                 "functions": [
                     {"name": "keep", "params": [], "returns": "X", "does": "kept function", "effects": ["none"]},
                     {"name": "vend", "params": [], "returns": "Y", "does": "vendored", "effects": ["none"], "vendored": True},
                     {"name": "leaky", "params": [], "returns": "Z", "does": "has api_key='abcdefzzzz'", "effects": ["none"]},
                 ]}
        snap, receipt = acquire(dirty)
        self.assertIn("vend", receipt["excluded_symbols"])
        self.assertEqual(receipt["symbols_kept"], 2)
        self.assertFalse(receipt["secret_scan_clean"])
        self.assertTrue(receipt["secret_findings"])

    def test_form_sets_port_roles(self):
        snap, _ = acquire(GEO)
        m = {x["symbol"]: x for x in form(snap)}["fetch_y"]
        self.assertIn("AreaOfInterest", m["port_roles"]["required_inputs"])
        self.assertIn("FetchPolicy", m["port_roles"]["config_inputs"])

    def test_handler_backed_is_executable(self):
        src = {"source_id": "src:fixture.h", "library": "geoutils_fixture", "license": "MIT",
               "retrieved_mode": "fixture_synthetic",
               "functions": [{"name": "parse_geojson",
                              "params": [{"name": "raw", "type": "GeoJsonDocument"}],
                              "returns": "PointFeatureCollection", "does": "parse geojson into points",
                              "effects": ["none"],
                              "handler": "primitives.foundry_handlers:parse_geojson"}]}
        snap, _ = acquire(src)
        m = form(snap)[0]
        self.assertEqual(m["handler_ref"], "primitives.foundry_handlers:parse_geojson")
        self.assertEqual(verify(m)["verification_status"], "fixture_executable")


class RouteRuntimeTests(unittest.TestCase):
    def test_executes_mined_chain_and_emits_receipts(self):
        from primitives.route_runtime import execute_route
        from primitives.foundry_handlers import HANDLERS
        route = {
            "compiled": True, "want": "RowSet", "want_canonical_type": "TabularDataset",
            "route_steps": [
                {"node_id": "mined:geoutils_fixture.parse_geojson"},
                {"node_id": "mined:geoutils_fixture.features_to_records"},
                {"node_id": "mined:geoutils_fixture.records_to_rows"},
            ],
        }
        fc = {"type": "FeatureCollection", "features": [
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-74.0, 40.7]},
             "properties": {"name": "A"}}]}
        run = execute_route(route, HANDLERS, {"GeoJsonDocument": fc}, run_id="t")
        self.assertTrue(run["ran"])
        self.assertEqual(run["steps_executed"], 3)
        self.assertEqual(len(run["step_receipts"]), 3)
        self.assertEqual(run["want_value"]["rows"], [[40.7, -74.0, "A"]])

    def test_unimplemented_node_stops_honestly(self):
        from primitives.route_runtime import execute_route
        route = {"compiled": True, "want": "X", "want_canonical_type": "X",
                 "route_steps": [{"node_id": "mined:nope.missing"}]}
        run = execute_route(route, {}, {}, run_id="t")
        self.assertFalse(run["ran"])
        self.assertEqual(run["unimplemented"], ["mined:nope.missing"])


if __name__ == "__main__":
    unittest.main()
