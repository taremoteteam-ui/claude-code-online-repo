#!/usr/bin/env python3
"""Checker for the foundry-mined-primitives pack.

Enforces, beyond schema validity + manifest hash gate + candidate boundary:
  - the license gate is coherent: verification_status == license_blocked IFF the
    license is not permissive, and a blocked row carries a promotion_blocker and
    is NEVER fixture_verified;
  - verification is recomputable: re-running primitives.foundry.verify on each
    row reproduces its verification_status (no hand-tuned statuses);
  - both edges parse to real typed ports; unique ids; no forbidden claims.

Usage:
    python3 scripts/check_foundry_pack.py --self-test
"""

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "foundry-mined-primitives"
SCHEMA_DIR = REPO_ROOT / "schemas"

from primitives.foundry import ALLOWED_LICENSES, verify  # noqa: E402
from primitives.edges import parse_edge  # noqa: E402

FORBIDDEN = [re.compile(r"\b\d+(\.\d+)?x\s+(faster|cheaper)", re.IGNORECASE),
             re.compile(r"\bproven to\b", re.IGNORECASE)]


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


def run_checks() -> dict:
    problems = []
    SV = load_validator_class()
    mpath = PACK_DIR / "manifest.json"
    if not mpath.exists():
        return {"ok": False, "problems": [f"missing {mpath}"], "counts": {}}
    manifest = json.loads(mpath.read_text())
    problems += [f"manifest: {e}" for e in SV(
        json.loads((SCHEMA_DIR / "pack_manifest.schema.json").read_text())).validate(manifest)]

    fpath = PACK_DIR / "mined_primitives.jsonl"
    raw = fpath.read_bytes()
    rows = [json.loads(x) for x in raw.decode().splitlines() if x.strip()]
    mf = manifest.get("files", {}).get("mined_primitives.jsonl", {})
    if mf.get("rows") != len(rows):
        problems.append("mined_primitives.jsonl: manifest rows mismatch")
    if mf.get("content_sha256") != hashlib.sha256(raw).hexdigest():
        problems.append("mined_primitives.jsonl: content hash mismatch - regenerate via the builder")

    validator = SV(json.loads((SCHEMA_DIR / "mined_primitive.schema.json").read_text()))
    ids = [r.get("mined_primitive_id") for r in rows]
    dupes = sorted({x for x in ids if ids.count(x) > 1})
    if dupes:
        problems.append(f"duplicate mined_primitive_ids: {dupes}")

    for i, r in enumerate(rows):
        for e in validator.validate(r)[:4]:
            problems.append(f"[{i}]: {e}")
        if r.get("candidate") is not True or r.get("serves_truth") is not False:
            problems.append(f"[{i}]: boundary violated")
        # license gate coherence
        permissive = r["license"] in ALLOWED_LICENSES
        blocked = r["verification_status"] == "license_blocked"
        if permissive and blocked:
            problems.append(f"{r['mined_primitive_id']}: permissive license but license_blocked")
        if not permissive and not blocked and not r.get("promotion_blockers"):
            problems.append(f"{r['mined_primitive_id']}: non-permissive license not blocked")
        if blocked and r["verification_status"] in ("fixture_verified", "fixture_executable"):
            problems.append(f"{r['mined_primitive_id']}: license_blocked cannot be verified/executable")
        # verification recomputable
        recomputed = verify(r)["verification_status"]
        if recomputed != r["verification_status"]:
            problems.append(f"{r['mined_primitive_id']}: verification_status {r['verification_status']} "
                            f"!= recomputed {recomputed}")
        # edges parse
        if not parse_edge(r["output_edge"]):
            problems.append(f"{r['mined_primitive_id']}: output_edge does not parse")
        for text in iter_text(r):
            for pat in FORBIDDEN:
                if pat.search(text):
                    problems.append(f"{r['mined_primitive_id']}: forbidden claim {pat.pattern!r}")

    return {"ok": not problems, "problems": problems[:60],
            "counts": {"mined_primitives.jsonl": len(rows)}, "total_rows": len(rows)}


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
