#!/usr/bin/env python3
"""Builder for the document-extraction seed pack.

Single source for every file under
catalog/knowledge-packs/data/document-extraction-seeds/. Never hand-edit
emitted pack files; edit the seed modules under scripts/seeds/ or this
builder, then re-run with --write.

The extraction-target lattice is materialized by crossing each document type
with the fields whose family it declares applicable - a principled cross
product, never a blind cartesian. Counts/hashes in manifest.json are
computed, never typed. Every row is candidate=true / serves_truth=false.

Usage:
    python3 scripts/build_document_extraction_pack.py --self-test
    python3 scripts/build_document_extraction_pack.py --write
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SEEDS_DIR = REPO_ROOT / "scripts" / "seeds"
PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "document-extraction-seeds"

PACK_ID = "document-extraction-seeds"
PACK_VERSION = "0.1.0"
ROW_VERSION = "0.1.0"
GENERATED_BY = "scripts/build_document_extraction_pack.py"

SCHEMA_REFS = [
    "schemas/document_type.schema.json",
    "schemas/extraction_field.schema.json",
    "schemas/extraction_target.schema.json",
    "schemas/document_extraction_primitive.schema.json",
    "schemas/pack_manifest.schema.json",
]

TARGET_INPUT_EDGE = "DocumentText+FieldSpec+ExtractionPolicy"
TARGET_OUTPUT_EDGE = "ExtractedFieldValue+SourceSpanReceipt"

# Field families that raise a target's review bar regardless of doc type.
HIGH_STAKES_FAMILIES = {
    "indemnification_liability",
    "dispute_resolution",
    "representations_warranties",
    "obligations",
    "conditions",
}


def load_seed_module(name: str) -> dict:
    path = SEEDS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"missing seed module: {path}")
    namespace: dict = {}
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), namespace)  # noqa: S102
    return namespace


def stamp(row: dict, record_type: str) -> dict:
    for forbidden in ("record_type", "version", "candidate", "serves_truth"):
        if forbidden in row:
            raise ValueError(f"seed row illegally sets builder-owned field {forbidden!r}")
    out = {"record_type": record_type}
    out.update(row)
    out["version"] = ROW_VERSION
    out["candidate"] = True
    out["serves_truth"] = False
    return out


def choose_route(field: dict) -> str:
    vt = field["value_type"]
    diff = field["extraction_difficulty"]
    if diff == "hard":
        return "semantic_model_bounded"
    if vt in ("free_text_clause",):
        return "section_scoped"
    if vt in ("list",):
        return "table_cell"
    if vt in ("identifier", "percentage", "money_amount", "date", "duration"):
        return "anchor_regex"
    if diff == "medium":
        return "keyword_proximity"
    return "hybrid"


def build_document_types() -> list[dict]:
    ns = load_seed_module("document_types_seed.py")
    rows = [stamp(dict(r), "document_type") for r in ns["DOCUMENT_TYPES"]]
    return sorted(rows, key=lambda r: r["doc_type_id"])


def build_extraction_fields() -> list[dict]:
    ns = load_seed_module("extraction_field_families_seed.py")
    rows = [stamp(dict(r), "extraction_field") for r in ns["EXTRACTION_FIELDS"]]
    return sorted(rows, key=lambda r: r["field_id"])


def build_extraction_primitives() -> list[dict]:
    ns = load_seed_module("extraction_primitives_seed.py")
    rows = [stamp(dict(r), "document_extraction_primitive") for r in ns["EXTRACTION_PRIMITIVES"]]
    return sorted(rows, key=lambda r: r["primitive_id"])


def build_extraction_targets(doc_types: list[dict], fields: list[dict]) -> list[dict]:
    fields_by_family: dict[str, list[dict]] = {}
    for f in fields:
        fields_by_family.setdefault(f["family"], []).append(f)

    targets: list[dict] = []
    seen_ids: set[str] = set()
    for dt in doc_types:
        dt_a, dt_b = dt["doc_type_id"].split(":", 1)[1].split(".", 1)
        for family in dt["applicable_field_families"]:
            for field in fields_by_family.get(family, []):
                f_a, f_b = field["field_id"].split(":", 1)[1].split(".", 1)
                target_id = f"target:{dt_a}.{dt_b}.{f_a}.{f_b}"
                if target_id in seen_ids:
                    continue
                seen_ids.add(target_id)
                proofs = list(field["proof_requirements"])
                if "source_span_verification" not in proofs:
                    proofs.insert(0, "source_span_verification")
                high_stakes = (family in HIGH_STAKES_FAMILIES
                               or field["extraction_difficulty"] == "hard")
                targets.append({
                    "record_type": "document_extraction_target",
                    "target_id": target_id,
                    "doc_type_ref": dt["doc_type_id"],
                    "field_ref": field["field_id"],
                    "title": f"{field['title']} from {dt['title']}",
                    "input_edge": TARGET_INPUT_EDGE,
                    "output_edge": TARGET_OUTPUT_EDGE,
                    "value_type": field["value_type"],
                    "cardinality": field["cardinality"],
                    "extraction_route": choose_route(field),
                    "proof_requirements": proofs,
                    "risk_class": "high" if (high_stakes and dt["risk_class"] != "low")
                                  else dt["risk_class"],
                    "human_review_required": bool(dt["human_review_required"] or high_stakes),
                    "version": ROW_VERSION,
                    "candidate": True,
                    "serves_truth": False,
                })
    targets.sort(key=lambda r: r["target_id"])
    return targets


def jsonl_bytes(rows: list[dict]) -> bytes:
    return "".join(json.dumps(r, ensure_ascii=True) + "\n" for r in rows).encode("utf-8")


def build_pack() -> dict[str, bytes]:
    doc_types = build_document_types()
    fields = build_extraction_fields()
    primitives = build_extraction_primitives()
    targets = build_extraction_targets(doc_types, fields)

    files = {
        "document_types.jsonl": doc_types,
        "extraction_fields.jsonl": fields,
        "extraction_primitives.jsonl": primitives,
        "extraction_targets.jsonl": targets,
    }
    payloads = {name: jsonl_bytes(rows) for name, rows in files.items()}

    manifest = {
        "pack_id": PACK_ID,
        "pack_version": PACK_VERSION,
        "generated_by": GENERATED_BY,
        "schema_refs": SCHEMA_REFS,
        "files": {
            name: {"rows": len(files[name]),
                   "content_sha256": hashlib.sha256(payloads[name]).hexdigest()}
            for name in sorted(files)
        },
        "row_counts": {name: len(rows) for name, rows in sorted(files.items())},
        "total_rows": sum(len(rows) for rows in files.values()),
        "candidate": True,
        "serves_truth": False,
    }
    payloads["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
    return payloads


def self_test() -> int:
    payloads = build_pack()
    manifest = json.loads(payloads["manifest.json"])
    problems = []
    for name, data in payloads.items():
        if name == "manifest.json":
            continue
        rows = [json.loads(line) for line in data.decode("utf-8").splitlines()]
        if manifest["files"][name]["rows"] != len(rows):
            problems.append(f"{name}: row count mismatch")
        for row in rows:
            if row.get("candidate") is not True or row.get("serves_truth") is not False:
                problems.append(f"{name}: candidate/serves_truth boundary violated")
                break
    if problems:
        print(json.dumps({"ok": False, "problems": problems}, indent=2))
        return 1
    print(json.dumps({"ok": True, "self_test": "builder", "row_counts": manifest["row_counts"],
                      "total_rows": manifest["total_rows"]}))
    return 0


def write_pack() -> int:
    payloads = build_pack()
    PACK_DIR.mkdir(parents=True, exist_ok=True)
    for name, data in sorted(payloads.items()):
        (PACK_DIR / name).write_bytes(data)
    manifest = json.loads(payloads["manifest.json"])
    print(json.dumps({"ok": True, "pack_dir": str(PACK_DIR.relative_to(REPO_ROOT)),
                      "row_counts": manifest["row_counts"], "total_rows": manifest["total_rows"]},
                     indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.write:
        return write_pack()
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
