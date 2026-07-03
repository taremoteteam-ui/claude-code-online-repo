#!/usr/bin/env python3
"""End-to-end primitive-foundry pipeline: one run covering the WHOLE lifecycle,
driven by the flexible decision engine, zero model calls, fully offline.

  ACQUIRE (scrape)  -> the decision engine picks the acquisition path from a
                       portfolio; acquire() reads the synthetic fixture source
                       and emits a snapshot + receipt (retrieved_mode disclosed).
  FORM (ingest)     -> form() edge-types each signature into a candidate mined
                       primitive; the license gate blocks non-permissive sources.
  VERIFY            -> verify() gates use-readiness (edges parse, effects valid,
                       license permissive) and emits receipts.
  STORE             -> the foundry pack (built by build_foundry_pack.py) is the
                       storage layer; here we report what would be stored.
  USE               -> load the capability graph (which already includes the
                       verified mined primitives) and COMPILE a route that chains
                       them - proving a mined primitive composes with the bank
                       without anyone reading its body.

Usage:
    python3 scripts/run_foundry_pipeline.py --self-test
    python3 scripts/run_foundry_pipeline.py --write
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from primitives.foundry import acquire, form, verify  # noqa: E402
from primitives.decision_engine import choose  # noqa: E402
from primitives.route_compiler import compile_route  # noqa: E402
from primitives.route_runtime import execute_route  # noqa: E402
from primitives.graph_search import GraphSearchIndex  # noqa: E402
from primitives.foundry_handlers import HANDLERS  # noqa: E402

# A tiny fixture GeoJSON input the mined route actually runs on (USE-execute).
FIXTURE_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-74.0, 40.7]},
         "properties": {"name": "A", "kind": "clinic"}},
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-73.9, 40.8]},
         "properties": {"name": "B", "kind": "clinic"}},
    ],
}
# Targets to test compose-lift: which only compile because the mined source exists.
LIFT_TARGETS = [
    (["GeoJsonDocument"], "RowSet"),
    (["GeoJsonDocument"], "EntityRecordSet"),
    (["PointFeatureCollection"], "RowSet"),
]

FIXTURES = REPO_ROOT / "fixtures" / "foundry"
PACK = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "decision-portfolios"
GRAPH = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "capability-graph" / "capability_graph.jsonl"
RUNS = REPO_ROOT / "benchmarks" / "foundry_runs"


def _decision_and_paths(decision_id: str):
    decisions = [json.loads(l) for l in (PACK / "decision_points.jsonl").read_text().splitlines() if l.strip()]
    paths = [json.loads(l) for l in (PACK / "execution_paths.jsonl").read_text().splitlines() if l.strip()]
    d = next(x for x in decisions if x["decision_id"] == decision_id)
    p = [x for x in paths if x["decision_id"] == decision_id]
    return d, p


def run(write: bool) -> dict:
    acq_decision, acq_paths = _decision_and_paths("decision:ingest.acquire_strategy")
    stages = []
    all_mined = []
    for src_path in sorted(FIXTURES.glob("*.json")):
        source = json.loads(src_path.read_text())
        # ACQUIRE: the engine chooses the acquisition path from the portfolio.
        ctx = {"has_cached_snapshot": True, "has_structured_api": bool(source.get("functions"))}
        decision = choose(acq_decision, acq_paths, ctx)
        chosen_path = decision["chosen_path"].split(".")[-1]  # cached_snapshot / ...
        snapshot, acq_receipt = acquire(source, path=chosen_path if chosen_path in
                                        ("cached_snapshot", "structured_api", "ast_parse") else "cached_snapshot")
        # FORM + VERIFY
        mined = form(snapshot)
        verifications = [verify(m) for m in mined]
        for m, v in zip(mined, verifications):
            m["verification_status"] = v["verification_status"]
        all_mined.extend(mined)
        stages.append({
            "source_id": source["source_id"], "license": source.get("license"),
            "acquire_path_chosen": decision["chosen_path"],
            "retrieved_mode": acq_receipt["retrieved_mode"], "symbols": len(mined),
            "fixture_verified": sum(1 for v in verifications if v["passed"]),
            "license_blocked": sum(1 for m in mined if m["verification_status"] == "license_blocked"),
        })

    verified = [m for m in all_mined if m["verification_status"] == "fixture_verified"]
    executable = [m for m in all_mined if m["verification_status"] == "fixture_executable"]
    blocked = [m for m in all_mined if m["verification_status"] == "license_blocked"]
    mined_ids = {m["mined_primitive_id"] for m in all_mined}
    new_ports = sorted({t for m in (verified + executable)
                        for t in m["port_roles"]["outputs"]})

    # === USE stage (expanded) ===
    nodes = [json.loads(l) for l in GRAPH.read_text().splitlines() if l.strip()]
    nodes_without_foundry = [n for n in nodes if n.get("lane") != "foundry"]

    # (a) RETRIEVE: find the mined primitives by a natural-language intent.
    index = GraphSearchIndex(nodes=nodes)
    retrieved = [r["node_id"] for r in index.search(
        "parse a geojson document into a point feature collection",
        want="PointFeatureCollection", top_k=5)
        if r["node_id"].startswith("mined:")]

    # (b) COMPOSE + compose-LIFT: how many targets only compile because the
    # mined source exists (compile with vs without the foundry lane).
    lift = []
    for have, want in LIFT_TARGETS:
        with_f = compile_route(have, want, nodes)["compiled"]
        without_f = compile_route(have, want, nodes_without_foundry)["compiled"]
        lift.append({"have": have, "want": want, "compiles": with_f,
                     "unlocked_by_foundry": bool(with_f and not without_f)})
    unlocked = [t for t in lift if t["unlocked_by_foundry"]]

    # (c) PlanLock for the flagship mined route.
    route = compile_route(["GeoJsonDocument"], "RowSet", nodes)
    mined_steps = [s["node_id"] for s in route.get("route_steps", []) if s["node_id"].startswith("mined:")]

    # (d) EXECUTE: actually RUN the compiled mined route on the fixture GeoJSON,
    # emitting an ExecutionReceipt per step - USE is real, not just a plan.
    run = execute_route(route, HANDLERS, {"GeoJsonDocument": FIXTURE_GEOJSON}, run_id="foundryrun")

    summary = {
        "run_id": "foundryrun",
        "lifecycle": "acquire -> form -> verify -> store -> use, engine-driven, zero model calls",
        "sources": len(stages), "per_source": stages,
        "store": {"total_mined": len(all_mined),
                  "fixture_verified": len(verified), "fixture_executable": len(executable),
                  "license_blocked": len(blocked), "new_ports_introduced": new_ports,
                  "note": "only fixture_verified/executable mined primitives enter the composable graph"},
        "use": {
            "retrieve": {"intent": "parse a geojson document into a point feature collection",
                         "mined_hits": retrieved},
            "compose_lift": {"targets": lift, "unlocked_by_foundry": len(unlocked),
                             "note": "targets that compile ONLY because the mined source exists"},
            "planlock": {"target": "GeoJsonDocument -> RowSet", "compiled": route["compiled"],
                         "route_hash": route.get("route_hash"), "step_count": route.get("step_count", 0),
                         "mined_steps_used": mined_steps},
            "execute": {"ran": run["ran"], "steps_executed": run["steps_executed"],
                        "effects_union": run["effects_union"],
                        "output_columns": (run["want_value"] or {}).get("columns"),
                        "output_row_count": len((run["want_value"] or {}).get("rows", [])),
                        "receipt_ids": [r["receipt_id"] for r in run["step_receipts"]],
                        "unimplemented": run["unimplemented"]},
        },
        "candidate": True, "serves_truth": False,
        "honesty_notes": [
            "SYNTHETIC fixture sources only - no real repo scraped; live mining runs where the network policy allows",
            "the acquisition path is CHOSEN by the decision engine; secret-scan + vendored-exclusion gates run at acquire",
            "the license gate blocked the non-permissive source; blocked primitives are stored but never enter the graph",
            "USE executes the mined route for real: each step emits an ExecutionReceipt (input/output hash, effects, proofs, timing)",
            "compose-lift is measured by compiling WITH vs WITHOUT the foundry lane - no hand-typed number",
            "mined primitives stay candidate=true / serves_truth=false until a live source ref + receipts attach",
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
    # Honest gate: all five stages produced real output - license gate blocked
    # >=1, >=1 executable mined primitive, a mined route compiled AND executed
    # end-to-end emitting receipts, and the source unlocked >=1 target.
    use = summary["use"]
    ok = (summary["sources"] >= 1
          and summary["store"]["license_blocked"] >= 1
          and summary["store"]["fixture_executable"] >= 1
          and use["planlock"]["compiled"] is True
          and len(use["planlock"]["mined_steps_used"]) >= 1
          and use["execute"]["ran"] is True
          and use["execute"]["output_row_count"] >= 1
          and use["compose_lift"]["unlocked_by_foundry"] >= 1)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
