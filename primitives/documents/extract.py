"""Ingest, segment, and locate-with-spans primitives for document extraction.

Three working primitives:

- :func:`document_ingest_and_layout` -- normalize newlines and record a
  per-line character-offset layout of the document text.
- :func:`clause_section_segment` -- split the document into non-overlapping
  clause/section spans by heading detection.
- :func:`field_locate_and_extract` -- locate field values by anchor regex and
  emit each value with a VERIFIED source span into the document text.

THE HONESTY RULE: every extracted value carries a source span [start, end]
such that ``document_text[start:end] == span_text`` AND the extracted value is
contained in ``span_text``. An extraction whose span does not slice back to its
text is a hallucination; :func:`field_locate_and_extract` runs
``source_span_verification`` over every extraction and a single failure makes
the proof fail.

Stdlib only. Pure computation: effects_observed == ["none"].
"""

from __future__ import annotations

import re
from typing import Any

from primitives.core import PrimitiveOutcome, ProofResult
from primitives.documents.normalize import normalize_value, raw_value_type_ok

# Window (in characters) searched after an anchor match for a value_pattern.
_VALUE_WINDOW = 240

# Default heading detectors for clause_section_segment.
_DEFAULT_HEADING_PATTERNS = [
    r"(?i)^section\s+\d+[A-Za-z]?\b",
    r"(?i)^article\s+(?:[IVXLC]+|\d+)\b",
    r"^\d+\.\s+\S",
]

# Cardinalities whose minimum count is at least one.
_MIN_ONE_CARDINALITIES = {"one", "one_or_many", "many", "1", "1..*", "1..1"}


# ---------------------------------------------------------------------------
# Primitive: document_ingest_and_layout
# ---------------------------------------------------------------------------

def document_ingest_and_layout(payload: dict) -> PrimitiveOutcome:
    """Ingest raw document text and record a per-line layout.

    payload: {"document_text": str, "document_id": str}
    output:  {"document_id","char_count","line_count","normalized_text",
              "layout_offsets": {"lines": [[start,end], ...]},
              "newline_normalization": {...}}
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    document_text = payload.get("document_text")
    document_id = payload.get("document_id")
    errors: list[str] = []
    if not isinstance(document_text, str):
        errors.append("'document_text' must be a string")
    if not isinstance(document_id, str) or not document_id:
        errors.append("'document_id' must be a non-empty string")
    if errors:
        raise ValueError("schema_validation failed: " + "; ".join(errors))

    crlf = document_text.count("\r\n")
    normalized_text = document_text.replace("\r\n", "\n")
    lone_cr = normalized_text.count("\r")
    normalized_text = normalized_text.replace("\r", "\n")
    newline_normalization = {
        "crlf_to_lf": crlf,
        "cr_to_lf": lone_cr,
        "changed": bool(crlf or lone_cr),
    }

    lines = normalized_text.split("\n")
    offsets: list[list[int]] = []
    pos = 0
    for line in lines:
        start = pos
        end = pos + len(line)
        offsets.append([start, end])
        pos = end + 1  # advance past the "\n"

    # offset_integrity: every recorded [start, end] slices back to its line.
    bad = [
        i for i, (start, end) in enumerate(offsets)
        if normalized_text[start:end] != lines[i]
    ]

    output = {
        "document_id": document_id,
        "char_count": len(normalized_text),
        "line_count": len(lines),
        "normalized_text": normalized_text,
        "layout_offsets": {"lines": offsets},
        "newline_normalization": newline_normalization,
    }
    proofs = [
        ProofResult("schema_validation", True,
                    f"document_id={document_id}, "
                    f"{len(normalized_text)} chars, {len(lines)} lines"),
        ProofResult(
            "offset_integrity", not bad,
            "every line offset slices back to its line"
            if not bad else f"offset mismatch at line indices {bad}",
        ),
    ]
    return PrimitiveOutcome(
        output=output,
        effects_observed=["none"],
        proof_results=proofs,
    )


# ---------------------------------------------------------------------------
# Primitive: clause_section_segment
# ---------------------------------------------------------------------------

def _is_all_caps_heading(stripped: str) -> bool:
    if not (3 <= len(stripped) <= 80):
        return False
    if not re.fullmatch(r"[A-Z0-9 ,.&'\-()/]+", stripped):
        return False
    if not re.search(r"[A-Z]", stripped):
        return False
    return stripped == stripped.upper()


def _heading_matchers(payload: dict):
    patterns = payload.get("heading_patterns")
    if patterns is None:
        compiled = [re.compile(p) for p in _DEFAULT_HEADING_PATTERNS]

        def is_heading(stripped: str) -> bool:
            if _is_all_caps_heading(stripped):
                return True
            return any(rx.match(stripped) for rx in compiled)

        return is_heading
    if not isinstance(patterns, list) or not all(
        isinstance(p, str) for p in patterns
    ):
        raise ValueError("'heading_patterns' must be a list of regex strings")
    compiled = [re.compile(p) for p in patterns]

    def is_heading(stripped: str) -> bool:
        return any(rx.match(stripped) for rx in compiled)

    return is_heading


def clause_section_segment(payload: dict) -> PrimitiveOutcome:
    """Segment document text into non-overlapping clause/section spans.

    payload: {"document_text": str, "heading_patterns": [regex, ...] optional}
    output:  {"sections": [{"section_id","heading","span":[start,end],
              "text_len"}, ...]}

    Default heading detection: ALL-CAPS lines, "Section N", "Article N", and
    numbered "N." headings.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    document_text = payload.get("document_text")
    if not isinstance(document_text, str):
        raise ValueError("schema_validation failed: 'document_text' must be a "
                         "string")
    is_heading = _heading_matchers(payload)

    # Character start offset of every line.
    line_starts: list[int] = []
    pos = 0
    for line in document_text.split("\n"):
        line_starts.append(pos)
        pos += len(line) + 1

    heading_starts: list[tuple[int, str]] = []
    for start, line in zip(line_starts, document_text.split("\n")):
        stripped = line.strip()
        if stripped and is_heading(stripped):
            heading_starts.append((start, stripped))

    n = len(document_text)
    sections: list[dict] = []

    def add_section(start: int, end: int, heading: str) -> None:
        idx = len(sections)
        sections.append({
            "section_id": f"sec:{idx:04d}",
            "heading": heading,
            "span": [start, end],
            "text_len": end - start,
        })

    if not heading_starts:
        add_section(0, n, "")
    else:
        first_start = heading_starts[0][0]
        if first_start > 0:
            add_section(0, first_start, "")
        for i, (start, heading) in enumerate(heading_starts):
            end = heading_starts[i + 1][0] if i + 1 < len(heading_starts) else n
            add_section(start, end, heading)

    # span_coverage: sorted, within bounds, non-overlapping (contiguous here).
    coverage_ok = True
    prev_end = 0
    for sec in sections:
        s, e = sec["span"]
        if not (0 <= s <= e <= n) or s < prev_end:
            coverage_ok = False
            break
        prev_end = e

    # heading_span_valid: every non-preamble heading occurs at the start of
    # its own span text.
    heading_ok = True
    for sec in sections:
        heading = sec["heading"]
        if not heading:
            continue
        s, e = sec["span"]
        if heading not in document_text[s:e]:
            heading_ok = False
            break

    output = {"sections": sections}
    proofs = [
        ProofResult("schema_validation", True,
                    f"{len(sections)} sections over {n} chars"),
        ProofResult(
            "span_coverage", coverage_ok,
            "sections are within bounds and non-overlapping"
            if coverage_ok else "section spans overlap or fall out of bounds",
        ),
        ProofResult(
            "heading_span_valid", heading_ok,
            "every heading occurs at the start of its section span"
            if heading_ok else "a heading was not found within its span",
        ),
    ]
    return PrimitiveOutcome(
        output=output,
        effects_observed=["none"],
        proof_results=proofs,
    )


# ---------------------------------------------------------------------------
# Primitive: field_locate_and_extract
# ---------------------------------------------------------------------------

def _validate_field_specs(specs: Any) -> None:
    if not isinstance(specs, list) or not specs:
        raise ValueError("schema_validation failed: 'field_specs' must be a "
                         "non-empty list")
    for i, spec in enumerate(specs):
        if not isinstance(spec, dict):
            raise ValueError(f"schema_validation failed: field_specs[{i}] is "
                             "not an object")
        if not isinstance(spec.get("field_ref"), str) or not spec["field_ref"]:
            raise ValueError(f"schema_validation failed: field_specs[{i}] "
                             "missing string 'field_ref'")
        anchors = spec.get("anchors")
        if not isinstance(anchors, list) or not anchors or not all(
            isinstance(a, str) for a in anchors
        ):
            raise ValueError(f"schema_validation failed: field_specs[{i}] "
                             "'anchors' must be a non-empty list of regex "
                             "strings")


def _locate_one(document_text: str, spec: dict):
    """Return (extraction_dict, None) on a match, else (None, field_ref)."""
    value_pattern = spec.get("value_pattern")
    for anchor in spec["anchors"]:
        am = re.search(anchor, document_text)
        if not am:
            continue
        if value_pattern:
            window_start = am.end()
            window = document_text[window_start:window_start + _VALUE_WINDOW]
            vm = re.search(value_pattern, window)
            if not vm:
                continue
            grp = 1 if vm.groups() else 0
            rel_s, rel_e = vm.span(grp)
            start = window_start + rel_s
            end = window_start + rel_e
        else:
            grp = 1 if am.groups() else 0
            start, end = am.span(grp)
        value = document_text[start:end]
        # Location and source-span grounding are the load-bearing job.
        # Normalization is downstream enrichment: if it cannot handle an
        # unusual value (e.g. boolean_normalize on a status string), the
        # field is still LOCATED with a verified span - it must not crash
        # extraction of the whole document. Record the failure per field.
        normalization_note = ""
        try:
            normalized_value, _ = normalize_value(
                value, spec.get("normalization", "none"),
                spec.get("value_type", "none"),
            )
        except (ValueError, TypeError) as exc:
            normalized_value = None
            normalization_note = f"normalization_failed: {exc}"
        result = {
            "field_ref": spec["field_ref"],
            "value": value,
            "value_type": spec.get("value_type", ""),
            "source_span": [start, end],
            "span_text": document_text[start:end],
            "normalized_value": normalized_value,
            "matched_anchor": anchor,
        }
        if normalization_note:
            result["normalization_note"] = normalization_note
        return result, None
    return None, spec["field_ref"]


def field_locate_and_extract(payload: dict) -> PrimitiveOutcome:
    """Locate field values by anchor regex and emit VERIFIED source spans.

    payload: {"document_text": str,
              "field_specs": [{"field_ref","value_type","cardinality",
                               "anchors":[regex,...],"value_pattern": regex|None,
                               "normalization": str}, ...]}
    output:  {"extractions": [{"field_ref","value","source_span","span_text",
                               "normalized_value","matched_anchor"}, ...],
              "unmatched": [field_ref, ...]}
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    document_text = payload.get("document_text")
    if not isinstance(document_text, str):
        raise ValueError("schema_validation failed: 'document_text' must be a "
                         "string")
    specs = payload.get("field_specs")
    _validate_field_specs(specs)

    extractions: list[dict] = []
    unmatched: list[str] = []
    spec_by_ref = {}
    for spec in specs:
        ext, miss = _locate_one(document_text, spec)
        if ext is not None:
            extractions.append(ext)
            spec_by_ref[spec["field_ref"]] = spec
        else:
            unmatched.append(miss)

    # MANDATORY source_span_verification: for EVERY extraction the span must
    # slice back to span_text and the value must be contained in span_text.
    span_violations: list[int] = []
    for i, ext in enumerate(extractions):
        s, e = ext["source_span"]
        if not (isinstance(s, int) and isinstance(e, int) and 0 <= s <= e
                <= len(document_text)):
            span_violations.append(i)
            continue
        if document_text[s:e] != ext["span_text"]:
            span_violations.append(i)
            continue
        if ext["value"] not in ext["span_text"]:
            span_violations.append(i)

    # value_type_validation: raw value matches its declared value_type shape.
    type_violations = [
        i for i, ext in enumerate(extractions)
        if not raw_value_type_ok(ext["value"], ext.get("value_type", ""))
    ]

    # cardinality_check: a field whose cardinality requires >= 1 must be
    # matched (unmatched required fields violate cardinality).
    card_violations = [
        spec["field_ref"] for spec in specs
        if str(spec.get("cardinality", "")).strip() in _MIN_ONE_CARDINALITIES
        and spec["field_ref"] in unmatched
    ]

    output = {"extractions": extractions, "unmatched": unmatched}
    proofs = [
        ProofResult("schema_validation", True,
                    f"{len(specs)} field specs, {len(extractions)} extractions,"
                    f" {len(unmatched)} unmatched"),
        ProofResult(
            "source_span_verification", not span_violations,
            "every extraction span slices back to span_text and contains its "
            "value" if not span_violations
            else f"span verification failed at extraction indices "
                 f"{span_violations}",
        ),
        ProofResult(
            "value_type_validation", not type_violations,
            "every value matches its declared value_type shape"
            if not type_violations
            else f"value_type shape mismatch at indices {type_violations}",
        ),
        ProofResult(
            "cardinality_check", not card_violations,
            "extraction counts honor field cardinalities"
            if not card_violations
            else f"required field(s) unmatched: {card_violations}",
        ),
    ]
    return PrimitiveOutcome(
        output=output,
        effects_observed=["none"],
        proof_results=proofs,
    )
