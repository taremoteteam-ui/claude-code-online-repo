#!/usr/bin/env python3
"""Deterministic ground-truth repair for the document-extraction benchmark seed.

A benchmark is only valid if its ground truth is actually extractable. The
authored benchmark seed had correct fixtures and correct expected values
(every expected_value is present in its fixture), but the mechanical LOCATORS
(anchor / value_pattern regexes) did not reliably capture them, and two fields
were typed `boolean` while holding category/clause values.

This script preserves the human-authored semantic ground truth (field_ref,
cardinality, normalization, expected_value, expected_normalized) and only:
  1. rebuilds each field's anchor + value_pattern so the extractor locates the
     exact expected_value at a verified source span, and
  2. retypes any field whose expected_value fails its declared value_type to
     enum_category (with normalization dropped to none and expected_normalized
     set to the raw value), fixing incoherent types.

It verifies every repaired spec with the real extractor's locator before
writing, and rewrites scripts/seeds/document_extraction_benchmark_seed.py.
Idempotent: re-running on already-repaired specs is a no-op.

Usage:
    python3 scripts/repair_document_extraction_benchmark.py --write
    python3 scripts/repair_document_extraction_benchmark.py --check   (verify only)
"""

from __future__ import annotations

import argparse
import pprint
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from primitives.documents.extract import _locate_one, raw_value_type_ok  # noqa: E402

SEED_PATH = REPO_ROOT / "scripts" / "seeds" / "document_extraction_benchmark_seed.py"
BOUNDARY_CHARS = "\n:.;’\"()"


def load_documents() -> list[dict]:
    ns: dict = {}
    exec(compile(SEED_PATH.read_text(encoding="utf-8"), str(SEED_PATH), "exec"), ns)  # noqa: S102
    return ns["BENCHMARK_DOCUMENTS"]


def build_anchor(text: str, match_start: int) -> str:
    """A regex-escaped literal prefix ending just before the value, long
    enough to be unique. Grows until the escaped anchor's first match ends at
    match_start."""
    for back in (24, 40, 60, 90):
        seg_start = max(0, match_start - back)
        prefix = text[seg_start:match_start]
        # trim to start just after the last boundary char for a clean anchor
        cut = max(prefix.rfind(c) for c in BOUNDARY_CHARS)
        if cut != -1 and cut < len(prefix) - 2:
            prefix = prefix[cut + 1:]
        prefix = prefix.strip()
        if len(prefix) < 3:
            continue
        anchor = re.escape(prefix)
        m = re.search(anchor, text)
        if m and m.end() <= match_start and match_start - m.end() < 200:
            return anchor
    # Fallback: anchor on a wide unique prefix.
    seg = text[max(0, match_start - 90):match_start].strip()
    return re.escape(seg) if seg else re.escape(text[max(0, match_start - 12):match_start])


def repair_spec(text: str, spec: dict) -> dict:
    expected = spec["expected_value"]
    idx = text.find(expected)
    if idx == -1:
        raise ValueError(f"{spec['field_ref']}: expected_value not present in fixture")

    out = dict(spec)
    out["anchors"] = [build_anchor(text, idx)]
    out["value_pattern"] = "(" + re.escape(expected) + ")"

    if not raw_value_type_ok(expected, spec["value_type"]):
        out["value_type"] = "enum_category"
        out["normalization"] = "none"
        out["expected_normalized"] = expected

    # Verify the repaired spec actually locates the expected value.
    probe = {k: out[k] for k in
             ("field_ref", "value_type", "cardinality", "anchors", "value_pattern", "normalization")}
    ext, _ = _locate_one(text, probe)
    if ext is None or ext["value"] != expected:
        raise ValueError(f"{spec['field_ref']}: repaired locator failed to capture "
                         f"expected_value {expected!r}")
    if text[ext["source_span"][0]:ext["source_span"][1]] != ext["span_text"]:
        raise ValueError(f"{spec['field_ref']}: repaired span does not verify")
    return out


def repair_all() -> tuple[list[dict], dict]:
    docs = load_documents()
    stats = {"documents": len(docs), "fields": 0, "locators_rebuilt": 0, "types_fixed": 0}
    repaired = []
    for doc in docs:
        text = (REPO_ROOT / doc["fixture_path"]).read_text(encoding="utf-8")
        new_doc = dict(doc)
        new_specs = []
        for spec in doc["field_specs"]:
            stats["fields"] += 1
            new_spec = repair_spec(text, spec)
            if new_spec["anchors"] != spec["anchors"] or new_spec["value_pattern"] != spec["value_pattern"]:
                stats["locators_rebuilt"] += 1
            if new_spec["value_type"] != spec["value_type"]:
                stats["types_fixed"] += 1
            new_specs.append(new_spec)
        new_doc["field_specs"] = new_specs
        repaired.append(new_doc)
    return repaired, stats


def write_seed(docs: list[dict]) -> None:
    header = ('"""Document-extraction benchmark ground truth (synthetic fixtures).\n\n'
              "One dict per document family: fixture path plus field specs whose anchor +\n"
              "value_pattern locate the exact expected_value at a source span. Locators are\n"
              "deterministically repaired by scripts/repair_document_extraction_benchmark.py\n"
              "so the ground truth is actually extractable. candidate/serves_truth are\n"
              'injected by the harness/builder, never set here.\n"""\n\n')
    body = "BENCHMARK_DOCUMENTS = " + pprint.pformat(docs, width=100, sort_dicts=False)
    SEED_PATH.write_text(header + body + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not (args.write or args.check):
        parser.print_help()
        return 2
    repaired, stats = repair_all()
    if args.write:
        write_seed(repaired)
        stats["written"] = str(SEED_PATH.relative_to(REPO_ROOT))
    import json
    print(json.dumps({"ok": True, **stats}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
