"""Dataset schema fingerprinting primitive.

Profiles the field structure of a batch of records: per-field observed
JSON types, null/missing counts, distinct-value counts over a capped
sample, and a truncated example value. Emits a deterministic
fingerprint hash over the field profile so two structurally identical
datasets produce the same fingerprint.

Pure and stdlib-only: no I/O, no network, no side effects. Output is
candidate material; nothing here promotes truth.
"""

from __future__ import annotations

import json

from primitives.core import PrimitiveOutcome, ProofResult, canonical_hash

DISTINCT_SAMPLE_CAP = 1000
EXAMPLE_MAX_CHARS = 80


def _json_type(value: object) -> str:
    """Name the JSON type of a Python value (bool checked before int)."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _stable_repr(value: object) -> str:
    """Deterministic string form of a value, usable as a distinct key."""
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=True)
    except (TypeError, ValueError):
        return str(value)


def _profile_fields(records: list[dict]) -> dict:
    """Build the per-field profile across all records.

    Types, null/missing counts, and examples scan every record;
    distinct counts scan only the first ``DISTINCT_SAMPLE_CAP`` records.
    """
    sample = records[:DISTINCT_SAMPLE_CAP]
    names: set[str] = set()
    for rec in records:
        names.update(rec.keys())

    fields: dict[str, dict] = {}
    for name in sorted(names):
        observed_types: set[str] = set()
        null_or_missing = 0
        example: str | None = None
        for rec in records:
            if name not in rec:
                null_or_missing += 1
                continue
            value = rec[name]
            if value is None:
                null_or_missing += 1
                observed_types.add("null")
                continue
            observed_types.add(_json_type(value))
            if example is None:
                example = _stable_repr(value)[:EXAMPLE_MAX_CHARS]

        distinct: set[str] = set()
        for rec in sample:
            if name in rec and rec[name] is not None:
                distinct.add(_stable_repr(rec[name]))

        fields[name] = {
            "observed_types": sorted(observed_types),
            "null_or_missing_count": null_or_missing,
            "distinct_count": len(distinct),
            "distinct_sample_size": len(sample),
            "example": example,
        }
    return fields


def _validate_payload(records: object) -> tuple[bool, str]:
    if not isinstance(records, list):
        return False, "records must be a list"
    if not records:
        return False, "records must be a nonempty list"
    for idx, rec in enumerate(records):
        if not isinstance(rec, dict):
            return False, f"records[{idx}] is not an object"
    return True, f"{len(records)} record objects validated"


def dataset_schema_fingerprint(payload: dict) -> PrimitiveOutcome:
    """Profile record fields and emit a deterministic schema fingerprint.

    payload:
        dataset_id: str
        records: nonempty list of dict rows

    output:
        dataset_id, row_count, field_count,
        fields: {name: {observed_types, null_or_missing_count,
                        distinct_count, distinct_sample_size, example}},
        fingerprint_hash: canonical hash of the fields profile

    proofs:
        schema_validation - records is a nonempty list of dicts
        fingerprint_determinism - hash recomputed from the emitted
            fields profile equals fingerprint_hash
    """
    dataset_id = str(payload.get("dataset_id", ""))
    records = payload.get("records")

    schema_ok, schema_detail = _validate_payload(records)
    proofs = [ProofResult("schema_validation", schema_ok, schema_detail)]
    if not schema_ok:
        return PrimitiveOutcome(
            output={
                "dataset_id": dataset_id,
                "row_count": 0,
                "field_count": 0,
                "fields": {},
                "fingerprint_hash": None,
            },
            effects_observed=["none"],
            proof_results=proofs,
        )

    fields = _profile_fields(records)
    fingerprint_hash = canonical_hash(fields)
    output = {
        "dataset_id": dataset_id,
        "row_count": len(records),
        "field_count": len(fields),
        "fields": fields,
        "fingerprint_hash": fingerprint_hash,
    }

    recomputed = canonical_hash(output["fields"])
    proofs.append(
        ProofResult(
            "fingerprint_determinism",
            recomputed == fingerprint_hash,
            "recomputed hash matches"
            if recomputed == fingerprint_hash
            else f"recomputed {recomputed} != emitted {fingerprint_hash}",
        )
    )

    return PrimitiveOutcome(
        output=output,
        effects_observed=["none"],
        proof_results=proofs,
    )
