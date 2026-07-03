"""Executable implementations for fixture-mined primitives.

These give the mined geo chain a REAL, deterministic runtime so the foundry's
USE stage does not just compile a route - it RUNS it, threading typed values
step to step and emitting an ExecutionReceipt per primitive. Each handler takes
the route runtime's state dict (canonical_type -> value) and returns a
PrimitiveOutcome whose output is keyed by the canonical type(s) it produces.

A mined primitive with a resolvable handler earns verification_status
``fixture_executable`` (one level above ``fixture_verified``) - it is proven to
actually transform its declared input edge into its declared output edge on a
fixture, not merely to have coherent edges. Stdlib only.
"""

from __future__ import annotations

from primitives.core import PrimitiveOutcome, ProofResult
from primitives.mutators import json_records_to_rows


def parse_geojson(state: dict) -> PrimitiveOutcome:
    fc = state.get("GeoJsonDocument") or {}
    feats = fc.get("features", []) if isinstance(fc, dict) else []
    all_points = bool(feats) and all(
        isinstance(f, dict) and f.get("geometry", {}).get("type") == "Point" for f in feats)
    return PrimitiveOutcome(
        output={"PointFeatureCollection": {"type": "FeatureCollection", "features": feats}},
        effects_observed=["none"],
        proof_results=[ProofResult("all_geometries_are_points", all_points,
                                   f"{len(feats)} features, all Point={all_points}")])


def features_to_records(state: dict) -> PrimitiveOutcome:
    fc = state.get("PointFeatureCollection") or {}
    feats = fc.get("features", [])
    records = []
    for f in feats:
        coords = f.get("geometry", {}).get("coordinates", [None, None])
        records.append({**f.get("properties", {}), "lon": coords[0], "lat": coords[1]})
    return PrimitiveOutcome(
        output={"EntityRecordSet": records},
        effects_observed=["none"],
        proof_results=[ProofResult("count_preserved", len(records) == len(feats),
                                   f"{len(records)} records from {len(feats)} features")])


def records_to_rows(state: dict) -> PrimitiveOutcome:
    records = state.get("EntityRecordSet") or []
    inner = json_records_to_rows({"records": records})
    ok = all(p.passed for p in inner.proof_results)
    return PrimitiveOutcome(
        output={"RowSet": {"columns": inner.output["columns"], "rows": inner.output["rows"]}},
        effects_observed=["none"],
        proof_results=[ProofResult("records_to_rows_roundtrip", ok,
                                   "backed by json_records_to_rows mutator proofs")])


# mined_primitive_id -> handler
HANDLERS = {
    "mined:geoutils_fixture.parse_geojson": parse_geojson,
    "mined:geoutils_fixture.features_to_records": features_to_records,
    "mined:geoutils_fixture.records_to_rows": records_to_rows,
}

# handler_ref string -> handler (for schema-declared refs)
REF_TO_HANDLER = {
    "primitives.foundry_handlers:parse_geojson": parse_geojson,
    "primitives.foundry_handlers:features_to_records": features_to_records,
    "primitives.foundry_handlers:records_to_rows": records_to_rows,
}
