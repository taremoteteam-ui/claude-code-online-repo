"""Unit tests for the deterministic remix mutators.

Run from the repo root:
    python3 -m unittest tests.test_mutators -v

Roundtrip checks are verified INDEPENDENTLY here by feeding one
mutator's output into its inverse mutator and comparing in the test,
not just by trusting each mutator's own roundtrip_test proof.

Failure-path assertions call the mutator functions directly and inspect
proof_results; run_primitive is only used on happy paths (it raises on
any failed proof by design).
"""

from __future__ import annotations

import copy
import json
import unittest

from primitives.core import run_primitive
from primitives.mutators import (
    field_project,
    field_rename,
    geojson_points_to_records,
    json_records_to_rows,
    long_to_wide,
    records_to_geojson_points,
    rows_to_json_records,
    wide_to_long,
)


def _proofs_by_name(outcome):
    return {p.proof: p for p in outcome.proof_results}


def _cjson(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=True)


RECORDS = [
    {"name": "alpha", "beds": 12},
    {"beds": 30, "name": "beta", "rating": 4.5},
]

WIDE = [
    {"region": "r1", "pop": 100, "area": 50},
    {"region": "r2", "pop": 200, "area": 75},
]

LONG_COMPLETE = [
    {"region": "r1", "variable": "pop", "value": 100},
    {"region": "r1", "variable": "area", "value": 50},
    {"region": "r2", "variable": "pop", "value": 200},
    {"region": "r2", "variable": "area", "value": 75},
]

LONG_RAGGED = [
    {"region": "r1", "variable": "pop", "value": 100},
    {"region": "r1", "variable": "area", "value": 50},
    {"region": "r2", "variable": "pop", "value": 200},
]

# Asymmetric coordinate on purpose: lat=10, lon=20. A silent axis swap
# would surface immediately in every assertion below.
FEATURE_COLLECTION = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [20, 10]},
            "properties": {"name": "asym"},
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-84.512, 39.103]},
            "properties": {"name": "cinci", "kind": "clinic"},
        },
    ],
}

GEO_RECORDS = [
    {"name": "asym", "lat": 10, "lon": 20},
    {"name": "cinci", "kind": "clinic", "lat": 39.103, "lon": -84.512},
]


class TestJsonRecordsToRows(unittest.TestCase):
    def test_happy_path_sorted_union_columns(self):
        outcome = json_records_to_rows({"records": copy.deepcopy(RECORDS)})
        out = outcome.output
        self.assertEqual(out["columns"], ["beds", "name", "rating"])
        self.assertEqual(out["rows"], [[12, "alpha", None], [30, "beta", 4.5]])
        self.assertEqual(outcome.effects_observed, ["none"])
        proofs = _proofs_by_name(outcome)
        for name in ("schema_validation", "column_coverage", "roundtrip_test"):
            self.assertTrue(proofs[name].passed, name)

    def test_column_order_respected(self):
        outcome = json_records_to_rows(
            {
                "records": copy.deepcopy(RECORDS),
                "column_order": ["name", "beds", "rating"],
            }
        )
        out = outcome.output
        self.assertEqual(out["columns"], ["name", "beds", "rating"])
        self.assertEqual(out["rows"], [["alpha", 12, None], ["beta", 30, 4.5]])
        self.assertTrue(_proofs_by_name(outcome)["column_coverage"].passed)

    def test_independent_roundtrip_through_inverse_mutator(self):
        out = json_records_to_rows({"records": copy.deepcopy(RECORDS)}).output
        back = rows_to_json_records(
            {"columns": out["columns"], "rows": out["rows"]}
        ).output
        expected = [
            {col: rec.get(col) for col in out["columns"]} for rec in RECORDS
        ]
        self.assertEqual(back["records"], expected)

    def test_column_order_missing_observed_key_fails_coverage(self):
        outcome = json_records_to_rows(
            {"records": copy.deepcopy(RECORDS), "column_order": ["name"]}
        )
        proofs = _proofs_by_name(outcome)
        self.assertTrue(proofs["schema_validation"].passed)
        self.assertFalse(proofs["column_coverage"].passed)
        self.assertIn("beds", proofs["column_coverage"].detail)
        self.assertEqual(outcome.output["columns"], [])
        self.assertEqual(outcome.output["rows"], [])

    def test_mutation_receipt_shape(self):
        receipt = json_records_to_rows({"records": copy.deepcopy(RECORDS)}).output[
            "mutation_receipt"
        ]
        self.assertEqual(receipt["mutator"], "json_records_to_rows")
        self.assertEqual(receipt["lossiness"], "lossless")
        self.assertEqual(receipt["fields_dropped"], [])
        self.assertTrue(len(receipt["preconditions_checked"]) >= 1)


class TestRowsToJsonRecords(unittest.TestCase):
    def test_happy_path(self):
        outcome = rows_to_json_records(
            {"columns": ["a", "b"], "rows": [[1, None], [3, 4]]}
        )
        self.assertEqual(
            outcome.output["records"], [{"a": 1, "b": None}, {"a": 3, "b": 4}]
        )
        proofs = _proofs_by_name(outcome)
        for name in ("schema_validation", "width_consistency", "roundtrip_test"):
            self.assertTrue(proofs[name].passed, name)
        self.assertEqual(outcome.effects_observed, ["none"])

    def test_width_mismatch_fails_proof(self):
        outcome = rows_to_json_records(
            {"columns": ["a", "b"], "rows": [[1, 2], [3]]}
        )
        proofs = _proofs_by_name(outcome)
        self.assertTrue(proofs["schema_validation"].passed)
        self.assertFalse(proofs["width_consistency"].passed)
        self.assertIn("rows[1]", proofs["width_consistency"].detail)
        self.assertEqual(outcome.output["records"], [])

    def test_independent_roundtrip_through_inverse_mutator(self):
        columns = ["a", "b"]
        rows = [[1, None], [3, 4]]
        records = rows_to_json_records(
            {"columns": list(columns), "rows": copy.deepcopy(rows)}
        ).output["records"]
        back = json_records_to_rows(
            {"records": records, "column_order": list(columns)}
        ).output
        self.assertEqual(back["columns"], columns)
        self.assertEqual(back["rows"], rows)


class TestWideToLong(unittest.TestCase):
    def _payload(self, **overrides):
        payload = {
            "records": copy.deepcopy(WIDE),
            "id_fields": ["region"],
            "value_fields": ["pop", "area"],
        }
        payload.update(overrides)
        return payload

    def test_happy_path_and_row_count_arithmetic(self):
        outcome = wide_to_long(self._payload())
        long_records = outcome.output["records"]
        # 2 records * 2 value fields == 4 long rows, checked independently.
        self.assertEqual(len(long_records), len(WIDE) * 2)
        self.assertEqual(
            long_records[0], {"region": "r1", "variable": "pop", "value": 100}
        )
        self.assertEqual(
            long_records[3], {"region": "r2", "variable": "area", "value": 75}
        )
        proofs = _proofs_by_name(outcome)
        for name in ("schema_validation", "row_count_arithmetic", "roundtrip_test"):
            self.assertTrue(proofs[name].passed, name)
        self.assertEqual(outcome.effects_observed, ["none"])

    def test_custom_var_value_names(self):
        outcome = wide_to_long(
            self._payload(var_name="metric", value_name="amount")
        )
        self.assertEqual(
            outcome.output["records"][0],
            {"region": "r1", "metric": "pop", "amount": 100},
        )
        self.assertTrue(_proofs_by_name(outcome)["roundtrip_test"].passed)

    def test_independent_roundtrip_through_long_to_wide(self):
        long_records = wide_to_long(self._payload()).output["records"]
        back = long_to_wide(
            {
                "records": long_records,
                "id_fields": ["region"],
                "var_field": "variable",
                "value_field": "value",
            }
        ).output["records"]
        self.assertEqual(back, WIDE)

    def test_duplicate_id_tuple_fails_schema(self):
        records = copy.deepcopy(WIDE) + [copy.deepcopy(WIDE[0])]
        outcome = wide_to_long(self._payload(records=records))
        proofs = _proofs_by_name(outcome)
        self.assertFalse(proofs["schema_validation"].passed)
        self.assertIn("duplicate id tuple", proofs["schema_validation"].detail)
        self.assertEqual(outcome.output["records"], [])

    def test_undeclared_field_fails_schema(self):
        records = [{"region": "r1", "pop": 1, "mystery": 2}]
        outcome = wide_to_long(
            self._payload(records=records, value_fields=["pop"])
        )
        proofs = _proofs_by_name(outcome)
        self.assertFalse(proofs["schema_validation"].passed)
        self.assertIn("undeclared", proofs["schema_validation"].detail)


class TestLongToWide(unittest.TestCase):
    def _payload(self, records):
        return {
            "records": copy.deepcopy(records),
            "id_fields": ["region"],
            "var_field": "variable",
            "value_field": "value",
        }

    def test_happy_path(self):
        outcome = long_to_wide(self._payload(LONG_RAGGED))
        self.assertEqual(
            outcome.output["records"],
            [{"region": "r1", "pop": 100, "area": 50}, {"region": "r2", "pop": 200}],
        )
        proofs = _proofs_by_name(outcome)
        for name in ("schema_validation", "no_duplicate_cells", "roundtrip_test"):
            self.assertTrue(proofs[name].passed, name)
        self.assertEqual(outcome.effects_observed, ["none"])

    def test_identical_duplicate_cell_allowed(self):
        records = copy.deepcopy(LONG_RAGGED) + [
            {"region": "r1", "variable": "pop", "value": 100}
        ]
        outcome = long_to_wide(self._payload(records))
        proofs = _proofs_by_name(outcome)
        self.assertTrue(proofs["no_duplicate_cells"].passed)
        self.assertTrue(proofs["roundtrip_test"].passed)
        self.assertEqual(
            outcome.output["records"][0], {"region": "r1", "pop": 100, "area": 50}
        )

    def test_conflicting_duplicate_cell_fails_proof_with_detail(self):
        records = copy.deepcopy(LONG_RAGGED) + [
            {"region": "r1", "variable": "pop", "value": 999}
        ]
        outcome = long_to_wide(self._payload(records))
        proofs = _proofs_by_name(outcome)
        self.assertTrue(proofs["schema_validation"].passed)
        self.assertFalse(proofs["no_duplicate_cells"].passed)
        self.assertIn("pop", proofs["no_duplicate_cells"].detail)
        self.assertIn("100", proofs["no_duplicate_cells"].detail)
        self.assertIn("999", proofs["no_duplicate_cells"].detail)
        self.assertEqual(outcome.output["records"], [])

    def test_independent_roundtrip_through_wide_to_long(self):
        wide = long_to_wide(self._payload(LONG_COMPLETE)).output["records"]
        back = wide_to_long(
            {
                "records": wide,
                "id_fields": ["region"],
                "value_fields": ["pop", "area"],
            }
        ).output["records"]
        self.assertEqual(
            sorted(_cjson(r) for r in back),
            sorted(_cjson(r) for r in LONG_COMPLETE),
        )


class TestFieldRename(unittest.TestCase):
    def test_happy_path_preserves_order_and_values(self):
        outcome = field_rename(
            {
                "records": [{"name": "alpha", "beds": 12}],
                "rename_map": {"name": "place_name"},
            }
        )
        renamed = outcome.output["records"]
        self.assertEqual(renamed, [{"place_name": "alpha", "beds": 12}])
        self.assertEqual(list(renamed[0].keys()), ["place_name", "beds"])
        proofs = _proofs_by_name(outcome)
        for name in ("schema_validation", "no_collision", "roundtrip_test"):
            self.assertTrue(proofs[name].passed, name)
        self.assertEqual(outcome.effects_observed, ["none"])

    def test_independent_roundtrip_with_inverse_map(self):
        records = copy.deepcopy(RECORDS)
        rename_map = {"name": "place_name", "beds": "bed_count"}
        renamed = field_rename(
            {"records": records, "rename_map": rename_map}
        ).output["records"]
        inverse = {new: old for old, new in rename_map.items()}
        restored = field_rename(
            {"records": renamed, "rename_map": inverse}
        ).output["records"]
        self.assertEqual(restored, RECORDS)

    def test_rename_onto_existing_key_fails_no_collision(self):
        outcome = field_rename(
            {"records": [{"a": 1, "b": 2}], "rename_map": {"a": "b"}}
        )
        proofs = _proofs_by_name(outcome)
        self.assertTrue(proofs["schema_validation"].passed)
        self.assertFalse(proofs["no_collision"].passed)
        self.assertIn("'b'", proofs["no_collision"].detail)
        self.assertEqual(outcome.output["records"], [])

    def test_unrenamed_target_key_fails_no_collision(self):
        # 'b' pre-exists and is a rename target of 'a': the inverse map
        # would turn it into 'a', so the mutation is not invertible here.
        outcome = field_rename(
            {"records": [{"b": 2}], "rename_map": {"a": "b"}}
        )
        proofs = _proofs_by_name(outcome)
        self.assertFalse(proofs["no_collision"].passed)
        self.assertIn("rename target", proofs["no_collision"].detail)

    def test_non_invertible_map_fails_schema(self):
        outcome = field_rename(
            {"records": [{"a": 1}], "rename_map": {"a": "x", "b": "x"}}
        )
        proofs = _proofs_by_name(outcome)
        self.assertFalse(proofs["schema_validation"].passed)
        self.assertIn("not invertible", proofs["schema_validation"].detail)

    def test_swap_rename_roundtrips(self):
        outcome = field_rename(
            {"records": [{"a": 1, "b": 2}], "rename_map": {"a": "b", "b": "a"}}
        )
        self.assertEqual(outcome.output["records"], [{"b": 1, "a": 2}])
        proofs = _proofs_by_name(outcome)
        self.assertTrue(proofs["no_collision"].passed)
        self.assertTrue(proofs["roundtrip_test"].passed)


class TestFieldProject(unittest.TestCase):
    RECORDS = [
        {"name": "alpha", "lat": 1.0, "lon": 2.0, "phone": "555", "owner": "x"},
        {"name": "beta", "lat": 3.0, "lon": 4.0, "notes": "hidden"},
    ]

    def test_lossy_disclosure(self):
        outcome = field_project(
            {"records": copy.deepcopy(self.RECORDS), "keep_fields": ["name", "lat", "lon"]}
        )
        out = outcome.output
        self.assertEqual(
            out["records"],
            [
                {"name": "alpha", "lat": 1.0, "lon": 2.0},
                {"name": "beta", "lat": 3.0, "lon": 4.0},
            ],
        )
        receipt = out["mutation_receipt"]
        self.assertEqual(receipt["mutator"], "field_project")
        self.assertEqual(receipt["lossiness"], "lossy")
        self.assertEqual(receipt["fields_dropped"], ["notes", "owner", "phone"])
        proofs = _proofs_by_name(outcome)
        for name in ("schema_validation", "projection_exactness", "drop_disclosure"):
            self.assertTrue(proofs[name].passed, name)
        self.assertEqual(outcome.effects_observed, ["none"])

    def test_projection_with_missing_keep_field(self):
        outcome = field_project(
            {
                "records": copy.deepcopy(self.RECORDS),
                "keep_fields": ["name", "notes"],
            }
        )
        # "notes" only exists on the second record; output keys must be
        # keep_fields intersect input keys per record.
        self.assertEqual(
            outcome.output["records"],
            [{"name": "alpha"}, {"name": "beta", "notes": "hidden"}],
        )
        self.assertTrue(_proofs_by_name(outcome)["projection_exactness"].passed)

    def test_no_roundtrip_claimed_for_lossy_mutator(self):
        outcome = field_project(
            {"records": copy.deepcopy(self.RECORDS), "keep_fields": ["name"]}
        )
        proofs = _proofs_by_name(outcome)
        self.assertNotIn("roundtrip_test", proofs)
        self.assertEqual(
            outcome.output["mutation_receipt"]["lossiness"], "lossy"
        )


class TestGeojsonPointsToRecords(unittest.TestCase):
    def test_asymmetric_coordinates_do_not_swap(self):
        # GeoJSON position [20, 10] is lon=20, lat=10. The record must
        # carry lat=10 and lon=20; any swap fails here.
        outcome = geojson_points_to_records(
            {"feature_collection": copy.deepcopy(FEATURE_COLLECTION)}
        )
        records = outcome.output["records"]
        self.assertEqual(records[0]["lat"], 10)
        self.assertEqual(records[0]["lon"], 20)
        self.assertEqual(records[0]["name"], "asym")
        self.assertEqual(records[1]["lat"], 39.103)
        self.assertEqual(records[1]["lon"], -84.512)
        self.assertEqual(outcome.effects_observed, ["none"])

    def test_coordinate_order_receipt(self):
        outcome = geojson_points_to_records(
            {"feature_collection": copy.deepcopy(FEATURE_COLLECTION)}
        )
        self.assertEqual(
            outcome.output["coordinate_order"],
            {"geojson_position": "lon,lat", "record_fields": "lat,lon"},
        )
        proofs = _proofs_by_name(outcome)
        for name in (
            "schema_validation",
            "geometry_type_gate",
            "coordinate_order_receipt",
            "roundtrip_test",
        ):
            self.assertTrue(proofs[name].passed, name)

    def test_independent_roundtrip_through_records_to_geojson_points(self):
        records = geojson_points_to_records(
            {"feature_collection": copy.deepcopy(FEATURE_COLLECTION)}
        ).output["records"]
        rebuilt = records_to_geojson_points({"records": records}).output[
            "feature_collection"
        ]
        self.assertEqual(rebuilt, FEATURE_COLLECTION)

    def test_non_point_geometry_fails_gate(self):
        fc = copy.deepcopy(FEATURE_COLLECTION)
        fc["features"].append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[0, 0], [1, 1]],
                },
                "properties": {"name": "road"},
            }
        )
        outcome = geojson_points_to_records({"feature_collection": fc})
        proofs = _proofs_by_name(outcome)
        self.assertTrue(proofs["schema_validation"].passed)
        self.assertFalse(proofs["geometry_type_gate"].passed)
        self.assertIn("LineString", proofs["geometry_type_gate"].detail)
        self.assertEqual(outcome.output["records"], [])

    def test_lat_lon_property_collision_fails_schema(self):
        fc = copy.deepcopy(FEATURE_COLLECTION)
        fc["features"][0]["properties"]["lat"] = 99
        outcome = geojson_points_to_records({"feature_collection": fc})
        proofs = _proofs_by_name(outcome)
        self.assertFalse(proofs["schema_validation"].passed)
        self.assertIn("'lat'", proofs["schema_validation"].detail)


class TestRecordsToGeojsonPoints(unittest.TestCase):
    def test_asymmetric_coordinates_written_lon_lat(self):
        # Record lat=10, lon=20 must serialize as position [20, 10].
        outcome = records_to_geojson_points(
            {"records": copy.deepcopy(GEO_RECORDS)}
        )
        fc = outcome.output["feature_collection"]
        self.assertEqual(fc["type"], "FeatureCollection")
        self.assertEqual(fc["features"][0]["geometry"]["coordinates"], [20, 10])
        self.assertEqual(fc["features"][0]["properties"], {"name": "asym"})
        self.assertEqual(
            fc["features"][1]["geometry"]["coordinates"], [-84.512, 39.103]
        )
        proofs = _proofs_by_name(outcome)
        for name in ("schema_validation", "coordinate_range_check", "roundtrip_test"):
            self.assertTrue(proofs[name].passed, name)
        self.assertEqual(outcome.effects_observed, ["none"])

    def test_range_violation_fails_proof(self):
        outcome = records_to_geojson_points(
            {"records": [{"name": "bad", "lat": 95, "lon": 20}]}
        )
        proofs = _proofs_by_name(outcome)
        self.assertTrue(proofs["schema_validation"].passed)
        self.assertFalse(proofs["coordinate_range_check"].passed)
        self.assertIn("records[0]", proofs["coordinate_range_check"].detail)

    def test_independent_roundtrip_through_geojson_points_to_records(self):
        fc = records_to_geojson_points(
            {"records": copy.deepcopy(GEO_RECORDS)}
        ).output["feature_collection"]
        back = geojson_points_to_records({"feature_collection": fc}).output[
            "records"
        ]
        self.assertEqual(back, GEO_RECORDS)


class TestRunPrimitiveReceipts(unittest.TestCase):
    def test_every_mutator_produces_a_clean_receipt(self):
        cases = [
            ("json_records_to_rows", json_records_to_rows,
             {"records": copy.deepcopy(RECORDS)}),
            ("rows_to_json_records", rows_to_json_records,
             {"columns": ["a", "b"], "rows": [[1, 2]]}),
            ("wide_to_long", wide_to_long,
             {"records": copy.deepcopy(WIDE), "id_fields": ["region"],
              "value_fields": ["pop", "area"]}),
            ("long_to_wide", long_to_wide,
             {"records": copy.deepcopy(LONG_COMPLETE), "id_fields": ["region"],
              "var_field": "variable", "value_field": "value"}),
            ("field_rename", field_rename,
             {"records": [{"name": "x"}], "rename_map": {"name": "place_name"}}),
            ("field_project", field_project,
             {"records": [{"name": "x", "secret": 1}], "keep_fields": ["name"]}),
            ("geojson_points_to_records", geojson_points_to_records,
             {"feature_collection": copy.deepcopy(FEATURE_COLLECTION)}),
            ("records_to_geojson_points", records_to_geojson_points,
             {"records": copy.deepcopy(GEO_RECORDS)}),
        ]
        for name, fn, payload in cases:
            with self.subTest(mutator=name):
                output, receipt = run_primitive(
                    f"prim:{name}",
                    fn,
                    payload,
                    run_id="run:test:mutators",
                    declared_effects=["none"],
                )
                self.assertIsNone(receipt["error"])
                self.assertTrue(receipt["candidate"])
                self.assertFalse(receipt["serves_truth"])
                self.assertEqual(receipt["effects_observed"], ["none"])
                self.assertTrue(receipt["input_hash"].startswith("sha256:"))
                self.assertTrue(receipt["output_hash"].startswith("sha256:"))
                self.assertTrue(receipt["proof_results"])
                self.assertTrue(
                    all(p["passed"] for p in receipt["proof_results"]), name
                )
                self.assertEqual(output["mutation_receipt"]["mutator"], name)


if __name__ == "__main__":
    unittest.main()
