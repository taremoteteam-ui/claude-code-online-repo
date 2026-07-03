#!/usr/bin/env python3
"""Measured demo: forks compose by their state contracts, exactly like primitives
compose by their edges - and a decision framework wires them into a solved plan.

For the dframework:solve control-flow scaffold:
  1. build the fork EDGES from contracts (fork A -> B when B consumes what A produces);
  2. COMPILE the fork order by forward-chaining over state keys (the route
     compiler, for decisions) and confirm it matches the framework's declared order;
  3. for each fork in order, the engine RESOLVES a path and threads the produced
     state forward - a fully wired decision plan (which fork, which path).

Zero model calls. candidate=true / serves_truth=false.

Usage: python3 scripts/run_decision_dag_demo.py --self-test | --write
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from primitives.decision_engine import choose  # noqa: E402
from primitives.decision_graph import (build_decision_edges, compile_decision_order,
                                       validate_decision_dag)  # noqa: E402

DPACK = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "decision-portfolios"
DFPACK = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "decision-frameworks"
RUNS = REPO_ROOT / "benchmarks" / "decision_runs"


def run(write: bool) -> dict:
    decisions = [json.loads(l) for l in (DPACK / "decision_points.jsonl").read_text().splitlines() if l.strip()]
    paths = [json.loads(l) for l in (DPACK / "execution_paths.jsonl").read_text().splitlines() if l.strip()]
    frameworks = [json.loads(l) for l in (DFPACK / "decision_frameworks.jsonl").read_text().splitlines() if l.strip()]
    by_id = {d["decision_id"]: d for d in decisions}
    paths_by = {}
    for p in paths:
        paths_by.setdefault(p["decision_id"], []).append(p)

    fw = next(f for f in frameworks if f["framework_id"] == "dframework:solve")

    # 1. fork edges from contracts
    edges = build_decision_edges(decisions)
    solve_edges = [e for e in edges if e["from"] in fw["forks"] and e["to"] in fw["forks"]]

    # 2. compile the fork order from contracts; confirm it matches the framework
    plan = compile_decision_order(decisions, fw["initial_state_keys"], fw["goal_state_keys"])
    matches_declared = plan["compiled"] and plan["order"] == fw["forks"]
    dag_valid = validate_decision_dag(fw["forks"], decisions, fw["initial_state_keys"])["valid"]

    # 3. resolve each fork to a path, threading state (a wired decision plan)
    context = {"want_type_known": True, "has_framework": True, "effect_profile": "pure",
               "diff_kind": "rename", "changed_lane": "coding_agent"}
    state = set(fw["initial_state_keys"])
    wired = []
    for did in plan.get("order", []):
        d = by_id[did]
        decision = choose(d, paths_by[did], context)
        consumes = set(d["contract"].get("consumes", []))
        produces = set(d["contract"].get("produces", []))
        wired.append({"fork": did, "consumes": sorted(consumes),
                      "consumes_available": consumes <= state,
                      "chosen_path": decision["chosen_path"], "produces": sorted(produces)})
        state |= produces

    summary = {
        "run_id": "dagrun", "framework": fw["framework_id"], "problem": fw["problem"],
        "fork_edges": [{"from": e["from"].split(":")[-1], "to": e["to"].split(":")[-1],
                        "on": e["on_keys"]} for e in solve_edges],
        "compiled_order": [f.split(":")[-1] for f in plan.get("order", [])],
        "matches_declared_framework": matches_declared, "dag_valid": dag_valid,
        "plan_hash": plan.get("plan_hash"),
        "wired_plan": [{"fork": w["fork"].split(":")[-1], "path": w["chosen_path"].split(":")[-1],
                        "consumes_available": w["consumes_available"], "produces": w["produces"]}
                       for w in wired],
        "reached_goal": set(fw["goal_state_keys"]) <= state,
        "candidate": True, "serves_truth": False,
        "honesty_notes": [
            "fork edges are DERIVED from consumes/produces contracts, not hand-wired",
            "the fork order is compiled by the same forward-chaining the route compiler uses for primitives",
            "each fork's path is resolved by the engine; the wired plan threads state fork to fork",
            "the decision framework is validated by the same wave rule as the warehouse multi-wave pipelines",
        ],
    }
    if write:
        RUNS.mkdir(parents=True, exist_ok=True)
        (RUNS / "decision_dag_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not (args.write or args.self_test):
        parser.print_help()
        return 2
    summary = run(write=args.write)
    print(json.dumps(summary, indent=2))
    ok = (summary["matches_declared_framework"] is True and summary["dag_valid"] is True
          and len(summary["fork_edges"]) >= 2 and summary["reached_goal"] is True
          and all(w["consumes_available"] for w in summary["wired_plan"])
          and all(w["path"] for w in summary["wired_plan"]))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
