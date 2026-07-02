"""Socrata SoQL dataset ingester (P0 source adapter).

Mimics the shape of a Socrata SODA resource endpoint, which returns a JSON
array of row objects with string-typed values. The adapter infers a field
type per column (integer/float/datetime/text) and emits typed rows plus the
inference summary.

Fixtures are SYNTHETIC; ``retrieved_mode`` is propagated into
``snapshot_meta`` so downstream evidence bundles disclose it.
Stdlib only.
"""

from __future__ import annotations

from datetime import datetime

from primitives.adapters._common import build_snapshot_meta, effects_for
from primitives.core import PrimitiveOutcome, ProofResult

LICENSE_FAMILY = "open_data_portal_requires_review"
ATTRIBUTION = (
    "Data source shape: Socrata SODA (SoQL) resource rows (synthetic fixture)"
)


def _is_int(text: str) -> bool:
    try:
        int(text)
        return True
    except ValueError:
        return False


def _is_float(text: str) -> bool:
    try:
        float(text)
        return True
    except ValueError:
        return False


def _is_datetime(text: str) -> bool:
    try:
        datetime.fromisoformat(text)
        return True
    except ValueError:
        return False


def _infer_field_type(values: list) -> str:
    non_empty = [v for v in values if v not in (None, "")]
    if not non_empty:
        return "text"
    if all(isinstance(v, bool) for v in non_empty):
        return "boolean"
    if all(isinstance(v, int) and not isinstance(v, bool) for v in non_empty):
        return "integer"
    if all(
        isinstance(v, (int, float)) and not isinstance(v, bool) for v in non_empty
    ):
        return "float"
    if all(isinstance(v, str) for v in non_empty):
        if all(_is_int(v) for v in non_empty):
            return "integer"
        if all(_is_float(v) for v in non_empty):
            return "float"
        if all(_is_datetime(v) for v in non_empty):
            return "datetime"
    return "text"


def _typed_value(value, field_type: str):
    if value in (None, ""):
        return None
    if isinstance(value, str):
        if field_type == "integer":
            return int(value)
        if field_type == "float":
            return float(value)
    # datetime values stay as their original ISO strings (JSON-safe).
    return value


def socrata_soql_dataset_ingester(payload: dict, transport) -> PrimitiveOutcome:
    """Ingest Socrata-shaped rows and infer per-field types.

    payload: {"domain", "dataset_id", "soql", "fixture_name"}
    """
    domain = payload["domain"]
    dataset_id = payload["dataset_id"]
    source_id = f"src:socrata.{domain}.{dataset_id}"
    url_family = f"https://{domain}/resource/{dataset_id}.json"

    response, snapshot_id = transport.get_json(
        url_family,
        {"$query": payload.get("soql", "")},
        payload["fixture_name"],
    )

    schema_problems: list[str] = []
    if not isinstance(response, list):
        schema_problems.append("response is not a JSON array of rows")
        rows = []
    else:
        rows = response
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                schema_problems.append(f"row[{i}] not an object")
    rows = [r for r in rows if isinstance(r, dict)]

    field_names: list[str] = []
    for row in rows:
        for key in row:
            if key not in field_names:
                field_names.append(key)
    field_types = {
        name: _infer_field_type([row.get(name) for row in rows])
        for name in field_names
    }

    records = []
    for i, row in enumerate(rows, start=1):
        typed = {
            key: _typed_value(value, field_types.get(key, "text"))
            for key, value in row.items()
        }
        records.append(
            {
                "record_id": f"socrata:{dataset_id}:{i}",
                "source_id": source_id,
                "fields": typed,
            }
        )

    schema_proof = ProofResult(
        "schema_validation",
        not schema_problems,
        "; ".join(schema_problems[:5])
        if schema_problems
        else f"response is an array of {len(records)} row objects",
    )
    count_proof = ProofResult(
        "row_count_positive", len(records) > 0, f"rows={len(records)}"
    )
    types_proof = ProofResult(
        "field_types_inferred",
        bool(field_types) and all(name in field_types for name in field_names),
        f"{len(field_types)} fields typed: "
        + ", ".join(f"{k}={v}" for k, v in sorted(field_types.items())),
    )

    output = {
        "domain": domain,
        "dataset_id": dataset_id,
        "records": records,
        "row_count": len(records),
        "field_types": field_types,
        "snapshot_meta": build_snapshot_meta(
            snapshot_id, source_id, LICENSE_FAMILY, ATTRIBUTION, transport
        ),
    }
    return PrimitiveOutcome(
        output=output,
        effects_observed=effects_for(transport),
        proof_results=[schema_proof, count_proof, types_proof],
        source_snapshot_ids=[snapshot_id],
    )
