#!/usr/bin/env python3
"""Checker for the decision-frameworks pack.

Beyond schema + hash + boundary, the load-bearing check: every framework's fork
order must COMPOSE by contracts - each fork exists, its declared order validates
under the wave rule (every consumed key produced by the initial state or an
earlier fork), and the goal keys are reached. A framework that does not compose
is a broken control-flow scaffold and goes red.

Usage: python3 scripts/check_decision_frameworks_pack.py --self-test
"""

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "decision-frameworks"
DPACK = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "decision-portfolios"
SCHEMA_DIR = REPO_ROOT / "schemas"

from primitives.decision_graph import validate_decision_dag  # noqa: E402


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

    raw = (PACK_DIR / "decision_frameworks.jsonl").read_bytes()
    rows = [json.loads(x) for x in raw.decode().splitlines() if x.strip()]
    if manifest.get("files", {}).get("decision_frameworks.jsonl", {}).get("content_sha256") \
            != hashlib.sha256(raw).hexdigest():
        problems.append("decision_frameworks.jsonl: content hash mismatch - regenerate via the builder")

    validator = SV(json.loads((SCHEMA_DIR / "decision_framework.schema.json").read_text()))
    decisions = [json.loads(l) for l in (DPACK / "decision_points.jsonl").read_text().splitlines() if l.strip()]
    by_id = {d["decision_id"] for d in decisions}

    for i, r in enumerate(rows):
        for e in validator.validate(r)[:4]:
            problems.append(f"[{i}]: {e}")
        if r.get("candidate") is not True or r.get("serves_truth") is not False:
            problems.append(f"[{i}]: boundary violated")
        for fork in r["forks"]:
            if fork not in by_id:
                problems.append(f"{r['framework_id']}: unknown fork {fork}")
        # THE check: the declared fork order validates by contracts and reaches the goal.
        v = validate_decision_dag(r["forks"], decisions, r["initial_state_keys"])
        if not v["valid"]:
            problems.append(f"{r['framework_id']}: fork order does not compose "
                            f"(first_unsatisfied={v['first_unsatisfied']})")
        missing_goal = [k for k in r["goal_state_keys"] if k not in v["final_state_keys"]]
        if missing_goal:
            problems.append(f"{r['framework_id']}: goal keys not produced: {missing_goal}")

    return {"ok": not problems, "problems": problems[:40],
            "counts": {"decision_frameworks.jsonl": len(rows)}, "total_rows": len(rows)}


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
