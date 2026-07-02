"""Evidence-bundle generator for the document-extraction lane.

:func:`extraction_evidence_bundle` collects verified extractions, their source
snapshots, and any uncertainty notes into a single evidence bundle carrying a
stable content hash. Every field in the bundle must retain its source span --
the bundle is the artifact a reviewer inspects to confirm each value is
grounded in the document.

Stdlib only. Pure computation: effects_observed == ["none"].
"""

from __future__ import annotations

from typing import Any

from primitives.core import PrimitiveOutcome, ProofResult, canonical_hash


def extraction_evidence_bundle(payload: dict) -> PrimitiveOutcome:
    """Assemble a span-grounded evidence bundle for a document.

    payload: {"document_id": str,
              "extractions": [{"field_ref","value","normalized_value",
                               "source_span","span_text"}, ...],
              "source_snapshots": [...], "uncertainty_notes": [...]}
    output:  {"evidence_bundle": {"document_id","fields":[...],"source_refs",
              "uncertainty_report","bundle_hash"}}
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    document_id = payload.get("document_id")
    extractions = payload.get("extractions")
    source_snapshots = payload.get("source_snapshots", [])
    uncertainty_notes = payload.get("uncertainty_notes", [])
    errors: list[str] = []
    if not isinstance(document_id, str) or not document_id:
        errors.append("'document_id' must be a non-empty string")
    if not isinstance(extractions, list):
        errors.append("'extractions' must be a list")
    if not isinstance(source_snapshots, list):
        errors.append("'source_snapshots' must be a list")
    if not isinstance(uncertainty_notes, list):
        errors.append("'uncertainty_notes' must be a list")
    if errors:
        raise ValueError("schema_validation failed: " + "; ".join(errors))

    fields = []
    for ext in extractions:
        if not isinstance(ext, dict):
            errors.append("extraction is not an object")
            fields.append({})
            continue
        fields.append({
            "field_ref": ext.get("field_ref"),
            "value": ext.get("value"),
            "normalized_value": ext.get("normalized_value"),
            "source_span": ext.get("source_span"),
            "span_text": ext.get("span_text"),
        })

    uncertainty_report = {
        "notes": list(uncertainty_notes),
        "count": len(uncertainty_notes),
    }

    bundle_core = {
        "document_id": document_id,
        "fields": fields,
        "source_refs": list(source_snapshots),
        "uncertainty_report": uncertainty_report,
    }
    bundle_hash = canonical_hash(bundle_core)
    evidence_bundle = dict(bundle_core)
    evidence_bundle["bundle_hash"] = bundle_hash

    # source_span_present_on_every_field: each field carries a [start,end]
    # span and a non-empty span_text.
    span_ok = True
    for f in fields:
        span = f.get("source_span")
        span_text = f.get("span_text")
        if (not isinstance(span, (list, tuple)) or len(span) != 2
                or not all(isinstance(x, int) for x in span)
                or not isinstance(span_text, str) or not span_text):
            span_ok = False
            break

    # bundle_hash_stable: recomputing the hash over the same core is identical.
    recomputed = canonical_hash(bundle_core)
    hash_stable = recomputed == bundle_hash

    output = {"evidence_bundle": evidence_bundle}
    proofs = [
        ProofResult(
            "source_span_present_on_every_field", span_ok,
            f"all {len(fields)} field(s) carry a source span and span_text"
            if span_ok else "a field is missing its source span or span_text",
        ),
        ProofResult(
            "uncertainty_report_present",
            isinstance(uncertainty_report, dict)
            and "notes" in uncertainty_report,
            f"uncertainty_report present with {uncertainty_report['count']} "
            "note(s)",
        ),
        ProofResult(
            "bundle_hash_stable", hash_stable,
            f"bundle_hash recomputes identically ({bundle_hash})"
            if hash_stable else "bundle_hash is not stable",
        ),
    ]
    return PrimitiveOutcome(
        output=output,
        effects_observed=["none"],
        proof_results=proofs,
    )
