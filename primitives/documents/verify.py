"""Standalone source-span guardrail and schema-validation gate.

- :func:`source_span_verify` -- the honesty guardrail. Given the document text
  and a list of extractions, it re-derives every span and flags any whose
  ``document_text[start:end]`` does not equal ``span_text`` or that does not
  contain the extracted value. The ``no_hallucinated_span`` proof FAILS when
  any violation is present -- this is the whole point of the lane.
- :func:`extraction_schema_validate` -- a policy gate that checks required
  fields are present and extracted values are shape-coherent with their
  declared value_types.

Stdlib only. Pure computation: effects_observed == ["none"].
"""

from __future__ import annotations

from typing import Any

from primitives.core import PrimitiveOutcome, ProofResult
from primitives.documents.normalize import raw_value_type_ok


# ---------------------------------------------------------------------------
# Primitive: source_span_verify
# ---------------------------------------------------------------------------

def source_span_verify(payload: dict) -> PrimitiveOutcome:
    """Re-verify that every extraction's source span slices back to its text.

    payload: {"document_text": str,
              "extractions": [{"value","source_span","span_text"}, ...]}
    output:  {"verified": [...], "violations": [{"index","reason"}, ...],
              "span_coverage_ratio": float}
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    document_text = payload.get("document_text")
    extractions = payload.get("extractions")
    errors: list[str] = []
    if not isinstance(document_text, str):
        errors.append("'document_text' must be a string")
    if not isinstance(extractions, list):
        errors.append("'extractions' must be a list")
    if errors:
        raise ValueError("schema_validation failed: " + "; ".join(errors))

    verified: list[dict] = []
    violations: list[dict] = []
    for i, ext in enumerate(extractions):
        reason = _span_violation_reason(document_text, ext)
        if reason is None:
            verified.append({
                "index": i,
                "value": ext.get("value"),
                "source_span": ext.get("source_span"),
            })
        else:
            violations.append({"index": i, "reason": reason})

    total = len(extractions)
    span_coverage_ratio = (len(verified) / total) if total else 1.0

    output = {
        "verified": verified,
        "violations": violations,
        "span_coverage_ratio": round(span_coverage_ratio, 6),
    }
    offending = [v["index"] for v in violations]
    proofs = [
        ProofResult("schema_validation", True,
                    f"{total} extractions checked"),
        ProofResult(
            "no_hallucinated_span", not violations,
            "all spans slice back to their span_text and contain their value"
            if not violations
            else f"hallucinated span(s) at extraction indices {offending}",
        ),
    ]
    return PrimitiveOutcome(
        output=output,
        effects_observed=["none"],
        proof_results=proofs,
    )


def _span_violation_reason(document_text: str, ext: Any) -> str | None:
    if not isinstance(ext, dict):
        return "extraction is not an object"
    span = ext.get("source_span")
    span_text = ext.get("span_text")
    value = ext.get("value")
    if (not isinstance(span, (list, tuple)) or len(span) != 2
            or not all(isinstance(x, int) for x in span)):
        return "source_span must be [start, end] integers"
    start, end = span
    if not (0 <= start <= end <= len(document_text)):
        return "span_out_of_bounds"
    if not isinstance(span_text, str):
        return "span_text must be a string"
    if document_text[start:end] != span_text:
        return "span_text_mismatch: document_text[span] != span_text"
    if not isinstance(value, str) or value not in span_text:
        return "value_not_in_span_text"
    return None


# ---------------------------------------------------------------------------
# Primitive: extraction_schema_validate
# ---------------------------------------------------------------------------

def extraction_schema_validate(payload: dict) -> PrimitiveOutcome:
    """Check required-field coverage and value_type coherence.

    payload: {"extractions": [{"field_ref","value", ...}, ...],
              "required_field_refs": [field_ref, ...],
              "field_types": {field_ref: value_type}}
    output:  {"missing_required": [...], "type_mismatches": [...], "ok": bool}
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    extractions = payload.get("extractions")
    required = payload.get("required_field_refs", [])
    field_types = payload.get("field_types", {})
    errors: list[str] = []
    if not isinstance(extractions, list):
        errors.append("'extractions' must be a list")
    if not isinstance(required, list):
        errors.append("'required_field_refs' must be a list")
    if not isinstance(field_types, dict):
        errors.append("'field_types' must be an object")
    if errors:
        raise ValueError("schema_validation failed: " + "; ".join(errors))

    present = {
        ext.get("field_ref") for ext in extractions if isinstance(ext, dict)
    }
    missing_required = [ref for ref in required if ref not in present]

    type_mismatches: list[dict] = []
    for ext in extractions:
        if not isinstance(ext, dict):
            continue
        ref = ext.get("field_ref")
        if ref in field_types:
            expected = field_types[ref]
            value = ext.get("value")
            if not (isinstance(value, str)
                    and raw_value_type_ok(value, expected)):
                type_mismatches.append({
                    "field_ref": ref,
                    "expected_type": expected,
                    "value": value,
                })

    ok = not missing_required and not type_mismatches
    output = {
        "missing_required": missing_required,
        "type_mismatches": type_mismatches,
        "ok": ok,
    }
    proofs = [
        ProofResult("schema_validation", True,
                    f"{len(extractions)} extractions, {len(required)} required"),
        ProofResult(
            "required_coverage", not missing_required,
            "all required field_refs are present"
            if not missing_required
            else f"missing required field_refs: {missing_required}",
        ),
        ProofResult(
            "type_coherence", not type_mismatches,
            "all typed values are shape-coherent with their value_type"
            if not type_mismatches
            else f"{len(type_mismatches)} value_type mismatch(es)",
        ),
    ]
    return PrimitiveOutcome(
        output=output,
        effects_observed=["none"],
        proof_results=proofs,
    )
