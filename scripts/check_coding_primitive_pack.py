#!/usr/bin/env python3
"""Checker for the coding-problem primitive pack.

Validates the generated pack the way the other lane checkers do (schemas,
manifest row-counts + content hashes, candidate/truth boundary) AND enforces the
two things that make this lane meaningful:

  * every kernel's self-test actually passes (the primitives work), and
  * every solution actually solves its problem's test cases (the solutions work),

re-run here from the live code so a pack claiming verified=true that no longer
runs green goes red. Plus referential integrity: each solution's problem exists,
its `uses` matches the problem's declared decomposition, and every referenced
kernel exists. Reports the measured reuse factor. Zero model calls; stdlib only.

Usage: python3 scripts/check_coding_primitive_pack.py --self-test
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
SCHEMA_DIR = REPO_ROOT / "schemas"
PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "coding-problem-primitives"
PROBLEMS_PATH = REPO_ROOT / "fixtures" / "coding-problems" / "problems.json"

from primitives.algorithmic_primitives import PRIMITIVES, run_self_test  # noqa: E402
from primitives.coding_solutions import SOLUTIONS  # noqa: E402

FILE_TO_SCHEMA = {
    "algorithmic_primitives.jsonl": "algorithmic_primitive_card.schema.json",
    "coding_problems.jsonl": "coding_problem_card.schema.json",
    "coding_solutions.jsonl": "coding_solution_card.schema.json",
}


def load_validator_class():
    spec = importlib.util.spec_from_file_location(
        "pack_checker", REPO_ROOT / "scripts" / "check_place_discovery_geospatial_pack.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.StructuralValidator


def load_jsonl(path: Path) -> list:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_checks() -> dict:
    problems: list[str] = []
    StructuralValidator = load_validator_class()

    manifest_path = PACK_DIR / "manifest.json"
    if not manifest_path.exists():
        return {"ok": False, "problems": [f"missing {manifest_path} - run the builder --write"]}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    problems += [f"manifest: {e}" for e in StructuralValidator(
        json.loads((SCHEMA_DIR / "pack_manifest.schema.json").read_text())).validate(manifest)]

    data: dict[str, list] = {}
    for fname, schema_name in FILE_TO_SCHEMA.items():
        fpath = PACK_DIR / fname
        if not fpath.exists():
            problems.append(f"missing pack file {fname}")
            continue
        digest = hashlib.sha256(fpath.read_bytes()).hexdigest()
        rows = load_jsonl(fpath)
        data[fname] = rows
        mf = manifest.get("files", {}).get(fname, {})
        if mf.get("rows") != len(rows):
            problems.append(f"{fname}: manifest rows={mf.get('rows')} but file has {len(rows)}")
        if mf.get("content_sha256") != digest:
            problems.append(f"{fname}: content hash mismatch - regenerate via the builder")
        validator = StructuralValidator(json.loads((SCHEMA_DIR / schema_name).read_text()))
        for i, row in enumerate(rows):
            for e in validator.validate(row)[:4]:
                problems.append(f"{fname}[{i}]: {e}")
            if row.get("candidate") is not True or row.get("serves_truth") is not False:
                problems.append(f"{fname}[{i}]: candidate/serves_truth boundary violated")

    prim_ids = {r["primitive_id"] for r in data.get("algorithmic_primitives.jsonl", [])}
    prob_ids = {r["problem_id"] for r in data.get("coding_problems.jsonl", [])}
    prob_uses = {r["problem_id"]: r["primitive_uses"] for r in data.get("coding_problems.jsonl", [])}

    # referential integrity: problem_uses -> real kernels
    for pid, uses in prob_uses.items():
        for u in uses:
            if u not in prim_ids:
                problems.append(f"problem {pid} uses unknown kernel {u}")
    # solutions reference real problems and match the declared decomposition
    for r in data.get("coding_solutions.jsonl", []):
        pref = r["problem_ref"]
        if pref not in prob_ids:
            problems.append(f"solution {r['solution_id']} references unknown problem {pref}")
        elif r["uses"] != prob_uses.get(pref):
            problems.append(f"solution {r['solution_id']} uses {r['uses']} != problem decomposition {prob_uses.get(pref)}")

    # EXECUTION GATE 1: every kernel self-test passes (re-run live)
    kernel_fail = [pid for pid in PRIMITIVES if not run_self_test(pid)]
    problems += [f"kernel self-test failed: {pid}" for pid in kernel_fail]

    # EXECUTION GATE 2: every solution solves its problem's test cases (re-run live)
    fixtures = {p["problem_id"]: p for p in json.loads(PROBLEMS_PATH.read_text())["problems"]}
    solved = cases_passed = cases_total = 0
    for r in data.get("coding_solutions.jsonl", []):
        p = fixtures.get(r["problem_ref"])
        if not p:
            continue
        ok_all = True
        for tc in p["test_cases"]:
            cases_total += 1
            try:
                got = SOLUTIONS[r["problem_ref"]]["fn"](**tc["args"])
            except Exception as exc:  # noqa: BLE001
                got, ok_all = f"<crash: {exc}>", False
            if got == tc["expected"]:
                cases_passed += 1
            else:
                ok_all = False
                problems.append(f"solution {r['solution_id']} FAILS a test case")
        solved += 1 if ok_all else 0

    distinct_used = {u for uses in prob_uses.values() for u in uses}
    reuse_factor = round(len(prob_ids) / max(1, len(distinct_used)), 3)
    return {
        "ok": not problems, "problems": problems,
        "counts": {f: len(r) for f, r in data.items()},
        "measured": {"problems_solved": solved, "problems_total": len(prob_ids),
                     "test_cases_passed": cases_passed, "test_cases_total": cases_total,
                     "distinct_kernels_used": len(distinct_used), "reuse_factor": reuse_factor},
        "candidate": True, "serves_truth": False,
    }


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
