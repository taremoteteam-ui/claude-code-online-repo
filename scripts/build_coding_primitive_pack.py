#!/usr/bin/env python3
"""Builder for the coding-problem primitive pack.

The single source for all pack files. It reads three seeds - the working kernels
(primitives/algorithmic_primitives.py), the working solutions
(primitives/coding_solutions.py), and the problem fixtures
(fixtures/coding-problems/problems.json) - runs every kernel self-test and every
solution against its problem's test cases, and emits candidate cards:

  algorithmic_primitives.jsonl  one card per reusable kernel (+ reuse_count)
  coding_problems.jsonl         one card per harvested problem
  coding_solutions.jsonl        one card per verified solution (+ pass counts)
  manifest.json                 computed row counts + content hashes

Never hand-edit the emitted pack; edit the seeds and rebuild. Verification is
recorded from ACTUALLY RUNNING the code (our own deterministic, effect-free
solutions), and the checker re-runs it to gate. Zero model calls; stdlib only;
every row candidate=true / serves_truth=false.

Usage:
    python3 scripts/build_coding_primitive_pack.py --self-test   # in-memory
    python3 scripts/build_coding_primitive_pack.py --write       # persist pack
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from primitives.algorithmic_primitives import PRIMITIVES, run_self_test  # noqa: E402
from primitives.coding_solutions import SOLUTIONS  # noqa: E402

PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "coding-problem-primitives"
PROBLEMS_PATH = REPO_ROOT / "fixtures" / "coding-problems" / "problems.json"
PACK_ID = "coding-problem-primitives"
PACK_VERSION = "0.1.0"


def _load_problems() -> list[dict]:
    return json.loads(PROBLEMS_PATH.read_text(encoding="utf-8"))["problems"]


def _run_solution_tests(problem: dict) -> tuple[int, int]:
    """Return (passed, total) for a problem's solution against its fixtures."""
    sol = SOLUTIONS[problem["problem_id"]]
    passed = 0
    for tc in problem["test_cases"]:
        try:
            if sol["fn"](**tc["args"]) == tc["expected"]:
                passed += 1
        except Exception:  # noqa: BLE001 - a crash is a failed case, recorded honestly
            pass
    return passed, len(problem["test_cases"])


def build() -> dict:
    problems = _load_problems()

    # reuse count per kernel across all problems
    reuse: dict[str, int] = {pid: 0 for pid in PRIMITIVES}
    for p in problems:
        for pid in p["primitive_uses"]:
            reuse[pid] = reuse.get(pid, 0) + 1

    primitive_cards = []
    for pid, meta in sorted(PRIMITIVES.items()):
        primitive_cards.append({
            "record_type": "algorithmic_primitive_card", "primitive_id": pid,
            "title": meta["pattern"].replace("_", " ").title(),
            "does": meta["does"], "pattern": meta["pattern"],
            "input_edge": meta["input_edge"], "output_edge": meta["output_edge"],
            "effects": ["none"], "self_test_passes": run_self_test(pid),
            "reuse_count": reuse.get(pid, 0), "version": PACK_VERSION,
            "candidate": True, "serves_truth": False,
        })

    problem_cards, solution_cards = [], []
    for p in sorted(problems, key=lambda x: x["problem_id"]):
        pid = p["problem_id"]
        passed, total = _run_solution_tests(p)
        problem_cards.append({
            "record_type": "coding_problem_card", "problem_id": pid,
            "source": p["source"], "difficulty": p["difficulty"], "category": p["category"],
            "statement": p["statement"], "primitive_uses": p["primitive_uses"],
            "test_case_count": total, "retrieved_mode": "fixture_synthetic",
            "version": PACK_VERSION, "candidate": True, "serves_truth": False,
        })
        solution_cards.append({
            "record_type": "coding_solution_card", "solution_id": f"sol:{pid}",
            "problem_ref": pid, "uses": SOLUTIONS[pid]["uses"],
            "verified": passed == total, "test_cases_passed": passed, "test_cases_total": total,
            "runtime_target": "local.python", "effects": ["none"],
            "version": PACK_VERSION, "candidate": True, "serves_truth": False,
        })

    return {
        "algorithmic_primitives.jsonl": primitive_cards,
        "coding_problems.jsonl": problem_cards,
        "coding_solutions.jsonl": solution_cards,
    }


def _dumps_rows(rows: list[dict]) -> str:
    return "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)


def _manifest(files: dict) -> dict:
    file_meta, row_counts, total = {}, {}, 0
    for fname, rows in files.items():
        blob = _dumps_rows(rows)
        file_meta[fname] = {"rows": len(rows),
                            "content_sha256": hashlib.sha256(blob.encode("utf-8")).hexdigest()}
        row_counts[fname] = len(rows)
        total += len(rows)
    return {
        "pack_id": PACK_ID, "pack_version": PACK_VERSION,
        "generated_by": "scripts/build_coding_primitive_pack.py",
        "schema_refs": ["schemas/algorithmic_primitive_card.schema.json",
                        "schemas/coding_problem_card.schema.json",
                        "schemas/coding_solution_card.schema.json"],
        "files": file_meta, "row_counts": row_counts, "total_rows": total,
        "candidate": True, "serves_truth": False,
    }


def _reuse_summary(files: dict) -> dict:
    prims = files["algorithmic_primitives.jsonl"]
    probs = files["coding_problems.jsonl"]
    distinct_used = {pid for p in probs for pid in p["primitive_uses"]}
    return {
        "problems": len(probs), "kernels": len(prims), "kernels_used": len(distinct_used),
        "reuse_factor": round(len(probs) / max(1, len(distinct_used)), 3),
        "all_solutions_verified": all(s["verified"] for s in files["coding_solutions.jsonl"]),
        "all_kernels_self_test": all(k["self_test_passes"] for k in prims),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if not (args.self_test or args.write):
        parser.print_help()
        return 2

    files = build()
    manifest = _manifest(files)
    summary = _reuse_summary(files)
    ok = summary["all_solutions_verified"] and summary["all_kernels_self_test"]

    if args.write:
        PACK_DIR.mkdir(parents=True, exist_ok=True)
        for fname, rows in files.items():
            (PACK_DIR / fname).write_text(_dumps_rows(rows), encoding="utf-8")
        (PACK_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"pack_id": PACK_ID, "manifest": manifest, "reuse_summary": summary,
                      "ok": ok, "candidate": True, "serves_truth": False}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
