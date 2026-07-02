#!/usr/bin/env python3
"""Measured retrieval evaluation for the CandidateBundle search.

For every generated benchmark task demand, the DIRECTED QUESTION TEXT ALONE
(never the task family label, never the primitive_demands answer key) is fed
to primitives.search.candidate_bundle_search. The task's primitive_demands
list is the ground truth. A demanded primitive counts as covered when it
appears in the top-k bundle directly, or when any group in the bundle lists
it as a member (group hits count - hiding member routes behind one visible
edge is the point of groups).

Metrics (all computed, per family and overall):
  demand_recall_at_k   mean fraction of each task's demanded primitives covered
  full_route_hit_at_k  fraction of tasks with ALL demands covered

These numbers are retrieval receipts for the matcher as it exists today.
They are not benchmark task results and make no claim about baselines.

Usage:
    python3 scripts/evaluate_candidate_search.py --self-test      (print only)
    python3 scripts/evaluate_candidate_search.py --write          (persist eval)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from primitives.search import bundle_covered_primitives, candidate_bundle_search  # noqa: E402

PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "place-discovery-geospatial-seeds"
EVALS_ROOT = REPO_ROOT / "benchmarks" / "search_evals"
TOP_K = 10


def evaluate() -> tuple[dict, list[dict]]:
    tasks = [json.loads(line) for line in
             (PACK_DIR / "benchmark_task_demands.jsonl").read_text(encoding="utf-8").splitlines()
             if line.strip()]

    per_task: list[dict] = []
    for task in tasks:
        bundle = candidate_bundle_search(task["directed_question"], top_k=TOP_K)
        covered = bundle_covered_primitives(bundle)
        demands = set(task["primitive_demands"])
        hit = demands & covered
        per_task.append({
            "task_id": task["task_id"],
            "task_family": task["task_family"],
            "bundle_id": bundle["bundle_id"],
            "demands": len(demands),
            "covered": len(hit),
            "missed": sorted(demands - covered),
            "recall": round(len(hit) / len(demands), 4),
            "full_route_hit": demands <= covered,
        })

    families: dict[str, list[dict]] = {}
    for row in per_task:
        families.setdefault(row["task_family"], []).append(row)

    def agg(rows: list[dict]) -> dict:
        return {
            "tasks": len(rows),
            "demand_recall_at_k": round(sum(r["recall"] for r in rows) / len(rows), 4),
            "full_route_hit_at_k": round(
                sum(1 for r in rows if r["full_route_hit"]) / len(rows), 4),
        }

    report = {
        "record_type": "candidate_search_eval_report",
        "top_k": TOP_K,
        "query_input": "directed_question text only (no family label, no answer key)",
        "overall": agg(per_task),
        "by_family": {fam: agg(rows) for fam, rows in sorted(families.items())},
        "most_missed_primitives": _most_missed(per_task),
        "candidate": True,
        "serves_truth": False,
    }
    return report, per_task


def _most_missed(per_task: list[dict], limit: int = 8) -> list[dict]:
    counts: dict[str, int] = {}
    for row in per_task:
        for pid in row["missed"]:
            counts[pid] = counts.get(pid, 0) + 1
    ranked = sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:limit]
    return [{"primitive_id": pid, "missed_in_tasks": n} for pid, n in ranked]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="evaluate and print, persist nothing")
    parser.add_argument("--write", action="store_true", help="persist the evaluation")
    args = parser.parse_args()
    if not (args.self_test or args.write):
        parser.print_help()
        return 2

    report, per_task = evaluate()
    ok = report["overall"]["tasks"] > 0

    if args.write:
        eval_id = "eval-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        eval_dir = EVALS_ROOT / eval_id
        eval_dir.mkdir(parents=True, exist_ok=True)
        files = {
            "report.json": json.dumps(report, indent=2) + "\n",
            "per_task_results.jsonl": "".join(json.dumps(r) + "\n" for r in per_task),
        }
        for name, content in files.items():
            (eval_dir / name).write_text(content, encoding="utf-8")
        manifest = {
            "eval_id": eval_id,
            "generated_by": "scripts/evaluate_candidate_search.py",
            "files": {name: {"rows": content.count("\n") if name.endswith(".jsonl") else 1,
                             "content_sha256": hashlib.sha256(content.encode()).hexdigest()}
                      for name, content in files.items()},
            "candidate": True,
            "serves_truth": False,
        }
        (eval_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        report["eval_dir"] = str(eval_dir.relative_to(REPO_ROOT))

    print(json.dumps(report, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
