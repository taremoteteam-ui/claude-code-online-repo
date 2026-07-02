#!/usr/bin/env python3
"""Checker for the document-extraction seed pack.

Enforces:
  - every row validates against its JSON schema
  - manifest row counts and content hashes match files on disk (a mismatch
    means a generated file was hand-edited - regenerate via the builder)
  - referential integrity: every extraction target references a document
    type and a field that exist; every field's family that a doc type
    declares applicable actually has fields
  - THE LANE INVARIANT: every extraction target and every field-emitting
    primitive carries source_span_verification - no ungrounded extraction
  - candidate=true / serves_truth=false on every row
  - no forbidden claim language in descriptive fields
  - unique ids per file

Usage:
    python3 scripts/check_document_extraction_pack.py --self-test
"""

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "document-extraction-seeds"
SCHEMA_DIR = REPO_ROOT / "schemas"

FILE_TO_SCHEMA = {
    "document_types.jsonl": "document_type.schema.json",
    "extraction_fields.jsonl": "extraction_field.schema.json",
    "extraction_targets.jsonl": "extraction_target.schema.json",
    "extraction_primitives.jsonl": "document_extraction_primitive.schema.json",
}

# Canonical field families a document type may declare applicable.
KNOWN_FAMILIES = {
    "parties", "identifiers", "dates", "monetary", "quantities", "obligations",
    "term_termination", "governing_law_jurisdiction", "signatures_execution",
    "definitions", "conditions", "representations_warranties",
    "indemnification_liability", "confidentiality", "dispute_resolution",
    "property_description", "real_estate_specific", "oil_gas_specific",
    "employment_specific", "ip_specific", "financial_specific", "insurance_specific",
}

# Primitive kinds that emit field values must ground them in source spans.
FIELD_EMITTING_KINDS = {"extract.worker", "verify.worker"}

# "guarantee"/"guaranty" is core legal vocabulary in this lane (guaranty
# agreements, guaranteed maximum price), so the gate targets the MARKETING
# sense - guaranteeing an outcome or metric - not the legal noun.
FORBIDDEN_CLAIM_PATTERNS = [
    re.compile(r"\b\d+(\.\d+)?x\s+(faster|cheaper|reduction)", re.IGNORECASE),
    re.compile(r"\bproven to\b", re.IGNORECASE),
    re.compile(
        r"\bguarantee[sd]?\s+(?:\w+\s+){0,3}"
        r"(faster|cheaper|savings|results?|accuracy|performance|reduction|uptime|success)",
        re.IGNORECASE),
    re.compile(r"\btokens? saved\b", re.IGNORECASE),
    re.compile(r"\b\d+% accura", re.IGNORECASE),
]


def load_validator_class():
    spec = importlib.util.spec_from_file_location(
        "pack_checker", REPO_ROOT / "scripts" / "check_place_discovery_geospatial_pack.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.StructuralValidator


def iter_text(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from iter_text(v)
    elif isinstance(value, list):
        for v in value:
            yield from iter_text(v)


def load_jsonl(path: Path) -> list:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_checks() -> dict:
    problems: list[str] = []
    counts: dict[str, int] = {}
    StructuralValidator = load_validator_class()

    manifest_path = PACK_DIR / "manifest.json"
    if not manifest_path.exists():
        return {"ok": False, "problems": [f"missing {manifest_path}"], "counts": {}}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_validator = StructuralValidator(
        json.loads((SCHEMA_DIR / "pack_manifest.schema.json").read_text(encoding="utf-8")))
    problems += [f"manifest: {e}" for e in manifest_validator.validate(manifest)]

    data: dict[str, list] = {}
    for fname, schema_name in FILE_TO_SCHEMA.items():
        fpath = PACK_DIR / fname
        if not fpath.exists():
            problems.append(f"missing pack file {fname}")
            continue
        raw = fpath.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        rows = load_jsonl(fpath)
        data[fname] = rows
        counts[fname] = len(rows)

        mf = manifest.get("files", {}).get(fname)
        if not mf:
            problems.append(f"{fname}: not listed in manifest")
        else:
            if mf.get("rows") != len(rows):
                problems.append(f"{fname}: manifest rows={mf.get('rows')} but file has {len(rows)}")
            if mf.get("content_sha256") != digest:
                problems.append(f"{fname}: content hash mismatch - regenerate via the builder")

        validator = StructuralValidator(
            json.loads((SCHEMA_DIR / schema_name).read_text(encoding="utf-8")))
        for i, row in enumerate(rows):
            for e in validator.validate(row)[:4]:
                problems.append(f"{fname}[{i}]: {e}")
            if row.get("candidate") is not True or row.get("serves_truth") is not False:
                problems.append(f"{fname}[{i}]: candidate/serves_truth boundary violated")
            for text in iter_text(row):
                for pat in FORBIDDEN_CLAIM_PATTERNS:
                    if pat.search(text):
                        problems.append(f"{fname}[{i}]: forbidden claim language {pat.pattern!r}")

    doc_types = {r["doc_type_id"]: r for r in data.get("document_types.jsonl", [])}
    fields = {r["field_id"]: r for r in data.get("extraction_fields.jsonl", [])}
    families_present = {f["family"] for f in fields.values()}

    # Document types must declare only known families, and each declared family
    # must have at least one field (otherwise the cross product silently drops).
    for dt in doc_types.values():
        for fam in dt["applicable_field_families"]:
            if fam not in KNOWN_FAMILIES:
                problems.append(f"{dt['doc_type_id']}: unknown field family {fam!r}")
            elif fam not in families_present:
                problems.append(
                    f"{dt['doc_type_id']}: declares family {fam!r} but no field has it")

    # Targets: referential integrity + the source-span invariant.
    for i, t in enumerate(data.get("extraction_targets.jsonl", [])):
        if t["doc_type_ref"] not in doc_types:
            problems.append(f"extraction_targets.jsonl[{i}]: unknown doc_type_ref {t['doc_type_ref']}")
        if t["field_ref"] not in fields:
            problems.append(f"extraction_targets.jsonl[{i}]: unknown field_ref {t['field_ref']}")
        if "source_span_verification" not in t["proof_requirements"]:
            problems.append(
                f"extraction_targets.jsonl[{i}]: LANE INVARIANT - target lacks "
                "source_span_verification (ungrounded extraction)")

    # Every field must require source_span_verification too.
    for fid, f in fields.items():
        if "source_span_verification" not in f["proof_requirements"]:
            problems.append(f"field {fid}: lacks source_span_verification")

    # Field-emitting primitives must ground values in spans.
    for p in data.get("extraction_primitives.jsonl", []):
        if p["kind"] in FIELD_EMITTING_KINDS:
            joined = " ".join(p["proof_requirements"])
            if "span" not in joined and "hallucinat" not in joined:
                problems.append(
                    f"{p['primitive_id']}: field-emitting primitive without a span/"
                    "hallucination proof")

    # Uniqueness.
    for fname, key in [
        ("document_types.jsonl", "doc_type_id"),
        ("extraction_fields.jsonl", "field_id"),
        ("extraction_targets.jsonl", "target_id"),
        ("extraction_primitives.jsonl", "primitive_id"),
    ]:
        ids = [r[key] for r in data.get(fname, [])]
        dupes = {x for x in ids if ids.count(x) > 1}
        if dupes:
            problems.append(f"{fname}: duplicate ids {sorted(dupes)[:5]}")

    return {"ok": not problems, "problems": problems[:80], "counts": counts,
            "total_rows": sum(counts.values())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test:
        parser.print_help()
        return 2
    result = run_checks()
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
