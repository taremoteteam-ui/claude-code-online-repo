"""Coding harness around the path-based system: solve a coding task by COMPILING
a primitive route (the generated program) and running it against test cases -
deterministically, zero model calls.

This is the compiled-AI shape applied to coding: a task is stated as
(have inputs -> wanted output) plus I/O test cases. The harness (1) compiles a
route of EXECUTABLE primitives over the runnable subgraph (nodes that have a real
handler), (2) executes that route through primitives/route_runtime.py on each
test input, and (3) checks the output equals the expected. The compiled route is
the 'program' - a PlanLock with a hash, replayable, emitting an ExecutionReceipt
per step. An unsolvable task is reported honestly (no route), never faked.

Extensible: add a primitive with a runtime handler and the harness can solve more
tasks with no change here. Today the runnable set is the foundry geo-chain
handlers (parse_geojson -> features_to_records -> records_to_rows), which follow
the route runtime's state contract.

Usage: python3 scripts/run_coding_harness.py --self-test | --write
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from primitives.route_compiler import compile_route  # noqa: E402
from primitives.route_runtime import execute_route  # noqa: E402
from primitives.foundry_handlers import HANDLERS as RUNNABLE  # noqa: E402

GRAPH = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "capability-graph" / "capability_graph.jsonl"
RUNS = REPO_ROOT / "benchmarks" / "coding_harness_runs"

_FC1 = {"type": "FeatureCollection", "features": [
    {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-74.0, 40.7]},
     "properties": {"name": "A"}}]}
_FC2 = {"type": "FeatureCollection", "features": [
    {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-74.0, 40.7]},
     "properties": {"name": "A"}},
    {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-73.9, 40.8]},
     "properties": {"name": "B"}}]}

# Each task: a coding problem stated as have -> want, plus I/O test cases.
TASKS = [
    {"name": "geojson_to_table",
     "description": "Turn a GeoJSON point document into a columns/rows table.",
     "have": ["GeoJsonDocument"], "want": "RowSet",
     "cases": [
         {"input": {"GeoJsonDocument": _FC1},
          "expected": {"columns": ["lat", "lon", "name"], "rows": [[40.7, -74.0, "A"]]}},
         {"input": {"GeoJsonDocument": _FC2},
          "expected": {"columns": ["lat", "lon", "name"],
                       "rows": [[40.7, -74.0, "A"], [40.8, -73.9, "B"]]}},
     ]},
    {"name": "geojson_to_records",
     "description": "Flatten a GeoJSON point document into entity records.",
     "have": ["GeoJsonDocument"], "want": "EntityRecordSet",
     "cases": [
         {"input": {"GeoJsonDocument": _FC1},
          "expected": [{"name": "A", "lon": -74.0, "lat": 40.7}]},
     ]},
    {"name": "features_to_table",
     "description": "Convert a point feature collection directly into a table.",
     "have": ["PointFeatureCollection"], "want": "RowSet",
     "cases": [
         {"input": {"PointFeatureCollection": _FC1},
          "expected": {"columns": ["lat", "lon", "name"], "rows": [[40.7, -74.0, "A"]]}},
     ]},
    {"name": "unsolvable_by_runnable_set",
     "description": "A target with no runnable route - the harness must say so.",
     "have": ["GeoJsonDocument"], "want": "ValidatedPatch", "cases": []},
]


def run(write: bool) -> dict:
    nodes = [json.loads(l) for l in GRAPH.read_text().splitlines() if l.strip()]
    runnable = [n for n in nodes if n["node_id"] in RUNNABLE]

    results = []
    for task in TASKS:
        route = compile_route(task["have"], task["want"], runnable)
        program = [s["node_id"] for s in route.get("route_steps", [])]
        rec = {"task": task["name"], "description": task["description"],
               "compiled": route["compiled"], "program": [p.split(":")[-1] for p in program],
               "route_hash": route.get("route_hash"), "step_count": route.get("step_count", 0)}
        if not route["compiled"]:
            rec["solved"] = False
            rec["reason"] = "no route over the runnable primitive set"
            results.append(rec)
            continue
        passed = 0
        case_details = []
        for i, case in enumerate(task["cases"]):
            run_out = execute_route(route, RUNNABLE, dict(case["input"]), run_id=f"{task['name']}-{i}")
            ok = run_out["ran"] and run_out["want_value"] == case["expected"]
            passed += 1 if ok else 0
            case_details.append({"case": i, "ok": ok, "steps_executed": run_out["steps_executed"],
                                 "receipts": len(run_out["step_receipts"])})
        rec["tests_passed"] = passed
        rec["tests_total"] = len(task["cases"])
        rec["solved"] = len(task["cases"]) > 0 and passed == len(task["cases"])
        rec["cases"] = case_details
        results.append(rec)

    solvable = [r for r in results if r["task"] != "unsolvable_by_runnable_set"]
    unsolvable = next(r for r in results if r["task"] == "unsolvable_by_runnable_set")
    summary = {
        "run_id": "codingharness",
        "harness": "compile a primitive route (the program) + run it against I/O tests, zero model calls",
        "runnable_primitives": sorted(RUNNABLE.keys()),
        "tasks": results,
        "solved": sum(1 for r in solvable if r.get("solved")),
        "solvable_tasks": len(solvable),
        "unsolvable_correctly_reported": unsolvable["compiled"] is False,
        "candidate": True, "serves_truth": False,
        "honesty_notes": [
            "the compiled route IS the generated program - a hashable, replayable PlanLock",
            "execution is real: each step emits an ExecutionReceipt; outputs are checked against expected",
            "zero model calls - the route is composed and run deterministically",
            "an unsolvable task is reported as 'no route', never faked; extending the runnable set solves more",
        ],
    }
    if write:
        RUNS.mkdir(parents=True, exist_ok=True)
        (RUNS / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if not (args.self_test or args.write):
        parser.print_help()
        return 2
    summary = run(write=args.write)
    print(json.dumps(summary, indent=2))
    ok = (summary["solved"] == summary["solvable_tasks"]
          and summary["unsolvable_correctly_reported"] is True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
