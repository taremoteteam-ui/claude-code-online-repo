#!/usr/bin/env python3
"""Checker for the warehouse-analytics lane.

Enforces, beyond schema validity + manifest hash gate + candidate boundary:
  - effect/proof UNION coherence on resolved primitives (as the universal lane)
  - templates and pipelines validate against their schemas
  - pipeline referential integrity: every member_family_ref exists in the
    families
  - THE MULTI-WAVE CONTRACT: for every pipeline, each wave consumes only ports
    that are pipeline_inputs OR produced by an earlier wave (a valid topological
    layering - the same typed-edge rule the route compiler enforces). Wave 1
    consumes only pipeline_inputs.
  - no forbidden claim language; unique ids

Usage:
    python3 scripts/check_warehouse_analytics_pack.py --self-test
"""

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "warehouse-analytics-catalog"
SCHEMA_DIR = REPO_ROOT / "schemas"

FILE_TO_SCHEMA = {
    "primitive_families.jsonl": "reusable_primitive_family.schema.json",
    "resolved_primitives.jsonl": "resolved_primitive.schema.json",
    "primitive_templates.jsonl": "primitive_template.schema.json",
    "pipeline_wave_templates.jsonl": "pipeline_wave_template.schema.json",
}

FORBIDDEN = [
    re.compile(r"\b\d+(\.\d+)?x\s+(faster|cheaper|reduction)", re.IGNORECASE),
    re.compile(r"\bproven to\b", re.IGNORECASE),
    re.compile(r"\btokens? saved\b", re.IGNORECASE),
    re.compile(r"\b\d+% (accura|faster|cheaper)", re.IGNORECASE),
]


def load_validator_class():
    spec = importlib.util.spec_from_file_location(
        "pack_checker", REPO_ROOT / "scripts" / "check_place_discovery_geospatial_pack.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.StructuralValidator


def iter_text(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for x in v.values():
            yield from iter_text(x)
    elif isinstance(v, list):
        for x in v:
            yield from iter_text(x)


def load_jsonl(p: Path):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def run_checks() -> dict:
    problems = []
    counts = {}
    SV = load_validator_class()

    mpath = PACK_DIR / "manifest.json"
    if not mpath.exists():
        return {"ok": False, "problems": [f"missing {mpath}"], "counts": {}}
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    problems += [f"manifest: {e}" for e in SV(
        json.loads((SCHEMA_DIR / "pack_manifest.schema.json").read_text())).validate(manifest)]

    data = {}
    for fname, schema_name in FILE_TO_SCHEMA.items():
        fpath = PACK_DIR / fname
        if not fpath.exists():
            problems.append(f"missing pack file {fname}")
            continue
        raw = fpath.read_bytes()
        rows = load_jsonl(fpath)
        data[fname] = rows
        counts[fname] = len(rows)
        mf = manifest.get("files", {}).get(fname, {})
        if mf.get("rows") != len(rows):
            problems.append(f"{fname}: manifest rows mismatch")
        if mf.get("content_sha256") != hashlib.sha256(raw).hexdigest():
            problems.append(f"{fname}: content hash mismatch - regenerate via the builder")
        validator = SV(json.loads((SCHEMA_DIR / schema_name).read_text()))
        for i, row in enumerate(rows):
            for e in validator.validate(row)[:4]:
                problems.append(f"{fname}[{i}]: {e}")
            if row.get("candidate") is not True or row.get("serves_truth") is not False:
                problems.append(f"{fname}[{i}]: boundary violated")
            for text in iter_text(row):
                for pat in FORBIDDEN:
                    if pat.search(text):
                        problems.append(f"{fname}[{i}]: forbidden claim {pat.pattern!r}")

    families = {f["family_id"] for f in data.get("primitive_families.jsonl", [])}
    wrappers_needed = set()
    for f in data.get("primitive_families.jsonl", []):
        wrappers_needed.update(f["applicable_runtime_wrappers"])

    # resolved effect/proof union coherence.
    fam_by_id = {f["family_id"]: f for f in data.get("primitive_families.jsonl", [])}
    for i, r in enumerate(data.get("resolved_primitives.jsonl", [])):
        fam = fam_by_id.get(r["base_family_ref"])
        if fam is None:
            problems.append(f"resolved_primitives.jsonl[{i}]: unknown family {r['base_family_ref']}")
            continue
        fam_eff = {e for e in fam["effects"] if e != "none"}
        if fam_eff - set(r["effects"]):
            problems.append(f"resolved_primitives.jsonl[{i}]: effects miss {sorted(fam_eff - set(r['effects']))}")
        if set(fam["proof_requirements"]) - set(r["proof_requirements"]):
            problems.append(f"resolved_primitives.jsonl[{i}]: proofs miss family requirements")

    # Pipelines: referential integrity + the multi-wave topological contract.
    for i, p in enumerate(data.get("pipeline_wave_templates.jsonl", [])):
        for ref in {ref for w in p["waves"] for ref in w["member_family_refs"]}:
            if ref not in families:
                problems.append(f"pipeline_wave_templates.jsonl[{i}] ({p['pipeline_id']}): "
                                f"unknown family ref {ref}")
        available = set(p["pipeline_inputs"])
        last_idx = 0
        for w in sorted(p["waves"], key=lambda x: x["wave_index"]):
            if w["wave_index"] != last_idx + 1:
                problems.append(f"{p['pipeline_id']}: wave_index not contiguous at {w['wave_index']}")
            last_idx = w["wave_index"]
            unmet = [c for c in w["consumes"] if c not in available]
            if unmet:
                problems.append(
                    f"{p['pipeline_id']} wave {w['wave_index']} ({w['wave_name']}): "
                    f"consumes {unmet} not produced by inputs or earlier waves "
                    "(multi-wave ordering violated)")
            available.update(w["produces"])
        for out in p["pipeline_outputs"]:
            if out not in available:
                problems.append(f"{p['pipeline_id']}: declared output {out} not produced by any wave")

    for fname, key in [
        ("primitive_families.jsonl", "family_id"),
        ("resolved_primitives.jsonl", "resolved_id"),
        ("primitive_templates.jsonl", "template_id"),
        ("pipeline_wave_templates.jsonl", "pipeline_id"),
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
