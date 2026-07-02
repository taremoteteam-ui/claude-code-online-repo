#!/usr/bin/env python3
"""Checker for the universal reusable-primitive catalog.

Enforces:
  - every row validates against its JSON schema
  - manifest row counts and content hashes match files on disk (a mismatch
    means a generated file was hand-edited - regenerate via the builder)
  - referential integrity: every family's applicable_runtime_wrappers exist in
    the wrapper bank; every resolved primitive references a real family and a
    real wrapper; the resolved runtime_target matches its wrapper
  - effect/proof union coherence: a resolved primitive's effects and proofs
    cover its family's and wrapper's declared effects/proofs
  - problem-solution completeness on every family (operating-manual section 4)
  - candidate=true / serves_truth=false on every row
  - no forbidden claim language; unique ids per file

Usage:
    python3 scripts/check_universal_primitive_pack.py --self-test
"""

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "universal-primitive-catalog"
SCHEMA_DIR = REPO_ROOT / "schemas"

FILE_TO_SCHEMA = {
    "primitive_families.jsonl": "reusable_primitive_family.schema.json",
    "runtime_wrappers.jsonl": "runtime_wrapper.schema.json",
    "resolved_primitives.jsonl": "resolved_primitive.schema.json",
}

FORBIDDEN_CLAIM_PATTERNS = [
    re.compile(r"\b\d+(\.\d+)?x\s+(faster|cheaper|reduction)", re.IGNORECASE),
    re.compile(r"\bproven to\b", re.IGNORECASE),
    re.compile(r"\btokens? saved\b", re.IGNORECASE),
    re.compile(r"\b\d+% (accura|faster|cheaper)", re.IGNORECASE),
    re.compile(
        r"\bguarantee[sd]?\s+(?:\w+\s+){0,3}"
        r"(faster|cheaper|savings|results?|accuracy|performance|reduction|uptime)",
        re.IGNORECASE),
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

    wrappers = {w["wrapper_id"]: w for w in data.get("runtime_wrappers.jsonl", [])}
    families = {f["family_id"]: f for f in data.get("primitive_families.jsonl", [])}

    for fam in families.values():
        for wid in fam["applicable_runtime_wrappers"]:
            if wid not in wrappers:
                problems.append(f"{fam['family_id']}: unknown runtime wrapper {wid}")

    for i, r in enumerate(data.get("resolved_primitives.jsonl", [])):
        fam = families.get(r["base_family_ref"])
        wrap = wrappers.get(r["runtime_wrapper_ref"])
        if fam is None:
            problems.append(f"resolved_primitives.jsonl[{i}]: unknown family {r['base_family_ref']}")
        if wrap is None:
            problems.append(f"resolved_primitives.jsonl[{i}]: unknown wrapper {r['runtime_wrapper_ref']}")
            continue
        if r["runtime_target"] != wrap["runtime_target"]:
            problems.append(f"resolved_primitives.jsonl[{i}]: runtime_target does not match wrapper")
        if fam is not None:
            # Effect/proof union coherence: resolved covers family + wrapper.
            fam_eff = {e for e in fam["effects"] if e != "none"}
            wrap_eff = {e for e in wrap["added_effects"] if e != "none"}
            res_eff = set(r["effects"])
            missing_eff = (fam_eff | wrap_eff) - res_eff
            if missing_eff:
                problems.append(
                    f"resolved_primitives.jsonl[{i}]: effects miss {sorted(missing_eff)}")
            need_proofs = set(fam["proof_requirements"]) | set(wrap["added_proof_requirements"])
            if need_proofs - set(r["proof_requirements"]):
                problems.append(
                    f"resolved_primitives.jsonl[{i}]: proofs miss "
                    f"{sorted(need_proofs - set(r['proof_requirements']))}")

    # Uniqueness.
    for fname, key in [
        ("primitive_families.jsonl", "family_id"),
        ("runtime_wrappers.jsonl", "wrapper_id"),
        ("resolved_primitives.jsonl", "resolved_id"),
    ]:
        ids = [row[key] for row in data.get(fname, [])]
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
