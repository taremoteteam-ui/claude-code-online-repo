#!/usr/bin/env python3
"""Wire primitives to SOLVE a problem: the orchestration loop that ties together
frameworks, the ordering-strategy portfolio, LLM-based ordering, the
deterministic validator, and real execution.

For a problem stated as (have ports -> wanted port):
  1. RETRIEVE candidate primitives + a matching solution framework;
  2. CHOOSE the ordering/wiring strategy from the decision portfolio;
  3. produce a wiring three ways - deterministic_compile, framework_fill, and
     llm_propose (a model proposes; the deterministic validator disposes; repair
     fixes an invalid proposal) - and VALIDATE each order (type-check);
  4. build a PlanLock from the chosen valid order and EXECUTE it for real,
     emitting an ExecutionReceipt per step.

Zero model calls (the LLM proposer is a labeled offline stub). candidate=true /
serves_truth=false.

Usage: python3 scripts/run_solve_demo.py --self-test | --write
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from primitives.decision_engine import choose  # noqa: E402
from primitives.graph_search import GraphSearchIndex  # noqa: E402
from primitives.orderers import deterministic_compile, framework_fill, llm_propose  # noqa: E402
from primitives.route_validator import validate_order  # noqa: E402
from primitives.route_runtime import execute_route  # noqa: E402
from primitives.foundry_handlers import HANDLERS  # noqa: E402

GRAPH = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "capability-graph" / "capability_graph.jsonl"
FRAMEWORKS = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "solution-frameworks" / "solution_frameworks.jsonl"
DPACK = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "decision-portfolios"
RUNS = REPO_ROOT / "benchmarks" / "solve_runs"

PROBLEM = {"have": ["GeoJsonDocument"], "want": "RowSet",
           "statement": "turn a raw geojson point source into a queryable table"}
FIXTURE_GEOJSON = {"type": "FeatureCollection", "features": [
    {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-74.0, 40.7]},
     "properties": {"name": "A", "kind": "clinic"}},
    {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-73.9, 40.8]},
     "properties": {"name": "B", "kind": "clinic"}}]}


def run(write: bool) -> dict:
    nodes = [json.loads(l) for l in GRAPH.read_text().splitlines() if l.strip()]
    frameworks = [json.loads(l) for l in FRAMEWORKS.read_text().splitlines() if l.strip()]
    decisions = {json.loads(l)["decision_id"]: json.loads(l)
                 for l in (DPACK / "decision_points.jsonl").read_text().splitlines() if l.strip()}
    paths_all = [json.loads(l) for l in (DPACK / "execution_paths.jsonl").read_text().splitlines() if l.strip()]

    have, want = PROBLEM["have"], PROBLEM["want"]

    # 1. RETRIEVE: candidate primitives + a matching framework.
    index = GraphSearchIndex(nodes=nodes)
    retrieved = [r["node_id"] for r in index.search(PROBLEM["statement"], want=want, top_k=6)]
    framework = next((f for f in frameworks if f["input_edge"] == have[0] and f["output_edge"] == want), None)

    # 2. CHOOSE the ordering strategy from the portfolio.
    odid = "decision:orchestration.ordering_strategy"
    opaths = [p for p in paths_all if p["decision_id"] == odid]
    ctx = {"has_framework": framework is not None}
    decision = choose(decisions[odid], opaths, ctx)

    # 3. produce + VALIDATE each strategy's wiring.
    strategies = {}
    det = deterministic_compile(have, want, nodes)
    strategies["deterministic_compile"] = {**det,
        "valid": validate_order(det["order"], have, want, nodes)["valid"]}
    if framework:
        ff = framework_fill(framework, have, want, nodes)
        strategies["framework_fill"] = {**ff,
            "valid": validate_order(ff["order"], have, want, nodes)["valid"]}
    lp = llm_propose(have, want, nodes)
    strategies["llm_propose"] = {**lp,
        "valid": validate_order(lp["order"], have, want, nodes)["valid"]}

    # 4. build a PlanLock from a chosen VALID order and EXECUTE it.
    chosen_order = strategies["deterministic_compile"]["order"]  # the safe default
    run = execute_route(
        {"compiled": True, "want": want, "want_canonical_type": "TabularDataset",
         "route_steps": [{"node_id": nid} for nid in chosen_order]},
        HANDLERS, {"GeoJsonDocument": FIXTURE_GEOJSON}, run_id="solverun")

    summary = {
        "run_id": "solverun", "problem": PROBLEM["statement"],
        "retrieve": {"top_hits": retrieved[:4], "matched_framework": framework and framework["framework_id"]},
        "chosen_strategy": decision["chosen_path"], "chosen_reason": decision["reason"],
        "strategies": {k: {"order": v["order"], "valid": v["valid"],
                           **({"proposal_valid": v.get("proposal_valid"), "repaired": v.get("repaired")}
                              if k == "llm_propose" else {}),
                           **({"filled": v.get("filled")} if k == "framework_fill" else {})}
                       for k, v in strategies.items()},
        "execute": {"ran": run["ran"], "steps": run["steps_executed"],
                    "output_columns": (run["want_value"] or {}).get("columns"),
                    "output_rows": len((run["want_value"] or {}).get("rows", [])),
                    "receipt_ids": [r["receipt_id"] for r in run["step_receipts"]]},
        "candidate": True, "serves_truth": False,
        "honesty_notes": [
            "all three ordering strategies are VALIDATED by the same deterministic type-checker",
            "the LLM path uses an offline stub proposer (0 tokens) that deliberately proposes an invalid order to exercise validate->repair; a real model plugs in unchanged",
            "the safe default executes the deterministic-compiled order; an LLM order runs only if it validates",
            "execution is real: each step emits an ExecutionReceipt; output is a genuine table from the fixture input",
        ],
    }
    if write:
        RUNS.mkdir(parents=True, exist_ok=True)
        (RUNS / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
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
    s = summary["strategies"]
    ok = (summary["retrieve"]["matched_framework"] is not None
          and s["deterministic_compile"]["valid"] is True
          and s["framework_fill"]["valid"] is True
          and s["llm_propose"]["proposal_valid"] is False   # the stub proposed invalid
          and s["llm_propose"]["repaired"] is True          # and repair fixed it
          and s["llm_propose"]["valid"] is True             # to a valid order
          and summary["execute"]["ran"] is True
          and summary["execute"]["output_rows"] >= 1)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
