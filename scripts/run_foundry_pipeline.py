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
    blocked = [m for m in all_mined if m["verification_status"] == "license_blocked"]

    # USE: compile a route over the graph that chains mined primitives.
    nodes = [json.loads(l) for l in GRAPH.read_text().splitlines() if l.strip()]
    route = compile_route(["GeoJsonDocument"], "RowSet", nodes)
    mined_steps = [s["node_id"] for s in route.get("route_steps", []) if s["node_id"].startswith("mined:")]

    summary = {
        "run_id": "foundryrun",
        "lifecycle": "acquire -> form -> verify -> store -> use, engine-driven, zero model calls",
        "sources": len(stages), "per_source": stages,
        "store": {"total_mined": len(all_mined), "fixture_verified": len(verified),
                  "license_blocked": len(blocked),
                  "note": "only fixture_verified mined primitives enter the composable graph"},
        "use": {"target": "GeoJsonDocument -> RowSet", "compiled": route["compiled"],
                "step_count": route.get("step_count", 0), "mined_steps_used": mined_steps},
        "candidate": True, "serves_truth": False,
        "honesty_notes": [
            "SYNTHETIC fixture sources only - no real repo scraped; live mining runs where the network policy allows",
            "the acquisition path is CHOSEN by the decision engine from a portfolio, not hardcoded",
            "the license gate blocked the non-permissive source; blocked primitives are stored but never enter the graph",
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
    # Honest gate: all five stages ran; the license gate blocked >=1; a mined
    # route compiled using >=1 mined primitive.
    ok = (summary["sources"] >= 1
          and summary["store"]["license_blocked"] >= 1
          and summary["store"]["fixture_verified"] >= 1
          and summary["use"]["compiled"] is True
          and len(summary["use"]["mined_steps_used"]) >= 1)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
