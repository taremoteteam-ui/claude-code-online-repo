#!/usr/bin/env python3
"""Coding-problem primitive pipeline: harvest -> solve -> verify -> decompose ->
store, then MEASURE reuse.

This is the end-to-end story of the user's request - scan coding problems (here:
synthetic LeetCode / competitive / interview / hackathon fixtures), actually
solve them, break each solution down into reusable primitives, store them, and -
the point of an atlas - show that a small set of kernels covers many problems, so
each new problem is assembled from stored parts rather than solved from scratch.

Everything is run live and measured; nothing is asserted. The reuse factor,
top-kernel coverage, and per-source tallies are computed from the actual
solve+decompose pass. Zero model calls; stdlib only; candidate / serves_truth=false.

Usage:
    python3 scripts/run_coding_primitive_pipeline.py --self-test
    python3 scripts/run_coding_primitive_pipeline.py --write   # persist scorecard
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from primitives.algorithmic_primitives import PRIMITIVES, run_self_test  # noqa: E402
from primitives.coding_solutions import SOLUTIONS  # noqa: E402

PROBLEMS_PATH = REPO_ROOT / "fixtures" / "coding-problems" / "problems.json"


def run() -> dict:
    problems = json.loads(PROBLEMS_PATH.read_text(encoding="utf-8"))["problems"]

    solved, cases_passed, cases_total = 0, 0, 0
    unsolved = []
    usage = Counter()
    by_source = defaultdict(lambda: {"problems": 0, "solved": 0})
    for p in problems:
        pid = p["problem_id"]
        by_source[p["source"]]["problems"] += 1
        ok_all = True
        for tc in p["test_cases"]:
            cases_total += 1
            try:
                got = SOLUTIONS[pid]["fn"](**tc["args"])
            except Exception:  # noqa: BLE001
                got, ok_all = None, False
            if got == tc["expected"]:
                cases_passed += 1
            else:
                ok_all = False
        if ok_all:
            solved += 1
            by_source[p["source"]]["solved"] += 1
            for k in SOLUTIONS[pid]["uses"]:
                usage[k] += 1
        else:
            unsolved.append(pid)

    distinct = [k for k, _ in usage.most_common()]
    # top-3 kernel coverage: fraction of solved problems using at least one top-3 kernel
    top3 = set(k for k, _ in usage.most_common(3))
    covered_by_top3 = sum(1 for p in problems
                          if p["problem_id"] not in unsolved
                          and set(SOLUTIONS[p["problem_id"]]["uses"]) & top3)

    kernels_registered = sum(1 for pid in PRIMITIVES if run_self_test(pid))

    return {
        "run_id": "codingprim", "record_type": "coding_primitive_scorecard",
        "harvested_problems": len(problems),
        "problems_solved": solved, "problems_unsolved": unsolved,
        "test_cases_passed": cases_passed, "test_cases_total": cases_total,
        "kernels_registered": kernels_registered, "kernels_total": len(PRIMITIVES),
        "distinct_kernels_used": len(distinct),
        "reuse_factor": round(solved / max(1, len(distinct)), 3),
        "kernel_usage": dict(usage.most_common()),
        "top3_kernels": sorted(top3),
        "top3_problem_coverage": round(covered_by_top3 / max(1, solved), 3),
        "by_source": {s: dict(v) for s, v in sorted(by_source.items())},
        "candidate": True, "serves_truth": False,
        "honesty_notes": [
            "problems are SYNTHETIC fixtures (fixture_synthetic); source is a style label",
            "every 'solved' is a live run passing that problem's fixture test cases - not asserted",
            "reuse_factor = solved problems / distinct kernels; a small kernel set covering "
            "many problems is the atlas thesis, measured here",
            "kernels are registered only if their self-test runs green; zero model calls",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if not (args.self_test or args.write):
        parser.print_help()
        return 2
    result = run()
    print(json.dumps(result, indent=2))
    if args.write:
        out = REPO_ROOT / "benchmarks" / "coding_runs"
        out.mkdir(parents=True, exist_ok=True)
        (out / "coding_primitive_scorecard.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8")
    # honest success: all harvested problems solved and all used kernels registered
    return 0 if (not result["problems_unsolved"]
                 and result["kernels_registered"] == result["kernels_total"]) else 1


if __name__ == "__main__":
    sys.exit(main())
