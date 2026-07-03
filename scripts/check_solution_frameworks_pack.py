#!/usr/bin/env python3
"""Checker for the solution-frameworks pack.

Beyond schema + manifest hash + candidate boundary, the load-bearing check:
every framework must actually FILL against the real capability graph and the
resulting order must VALIDATE (type-check end to end). A framework whose slots
cannot be bound to real producers - or whose filled order does not produce its
declared output - is a broken scaffold and goes red.

Usage: python3 scripts/check_solution_frameworks_pack.py --self-test
"""

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "solution-frameworks"
GRAPH = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "capability-graph" / "capability_graph.jsonl"
SCHEMA_DIR = REPO_ROOT / "schemas"

from primitives.orderers import framework_fill  # noqa: E402
from primitives.route_validator import validate_order  # noqa: E402


def load_validator_class():
    spec = importlib.util.spec_from_file_location(
        "pack_checker", REPO_ROOT / "scripts" / "check_place_discovery_geospatial_pack.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.StructuralValidator


def run_checks() -> dict:
    problems = []
    SV = load_validator_class()
    manifest = json.loads((PACK_DIR / "manifest.json").read_text())
    problems += [f"manifest: {e}" for e in SV(
        json.loads((SCHEMA_DIR / "pack_manifest.schema.json").read_text())).validate(manifest)]

    raw = (PACK_DIR / "solution_frameworks.jsonl").read_bytes()
    rows = [json.loads(x) for x in raw.decode().splitlines() if x.strip()]
    mf = manifest.get("files", {}).get("solution_frameworks.jsonl", {})
    if mf.get("content_sha256") != hashlib.sha256(raw).hexdigest():
        problems.append("solution_frameworks.jsonl: content hash mismatch - regenerate via the builder")

    validator = SV(json.loads((SCHEMA_DIR / "solution_framework.schema.json").read_text()))
    nodes = [json.loads(l) for l in GRAPH.read_text().splitlines() if l.strip()]

    ids = [r["framework_id"] for r in rows]
    dupes = sorted({x for x in ids if ids.count(x) > 1})
    if dupes:
        problems.append(f"duplicate framework_ids: {dupes}")

    for i, r in enumerate(rows):
        for e in validator.validate(r)[:4]:
            problems.append(f"[{i}]: {e}")
        if r.get("candidate") is not True or r.get("serves_truth") is not False:
            problems.append(f"[{i}]: boundary violated")
        # THE check: the framework fills against the graph and the order validates.
        fill = framework_fill(r, [r["input_edge"]], r["output_edge"], nodes)
        if not fill.get("filled"):
            problems.append(f"{r['framework_id']}: unfillable slot {fill.get('unfilled_slot')}")
            continue
        v = validate_order(fill["order"], [r["input_edge"]], r["output_edge"], nodes)
        if not v["valid"]:
            problems.append(f"{r['framework_id']}: filled order does not validate "
                            f"(first_unsatisfied={v['first_unsatisfied']})")

    return {"ok": not problems, "problems": problems[:40],
            "counts": {"solution_frameworks.jsonl": len(rows)}, "total_rows": len(rows)}


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
