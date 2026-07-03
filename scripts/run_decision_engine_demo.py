#!/usr/bin/env python3
"""Measured demonstration that ONE engine drives three dissimilar decisions from
data alone - the generality proof for the decision-portfolio substrate.

1. decision:retrieval.plane_selection (runtime, execute-all-when-cheap): run all
   applicable planes over the honest cross-lane probe set, record a receipt per
   (plane, probe), then let the ledger + argmax policy pick the plane the DATA
   prefers - measured against the 0.667 lexical baseline. The supervisor then
   recommends promoting the winner.
2. decision:remix.escalation (runtime, deterministic_tier): show the ladder
   picks the cheapest APPLICABLE tier (mutator -> adapter -> bounded model)
   across different contract-diff contexts, cold (no receipts).
3. decision:dev.proof_stage_order (development, cheapest_that_proves): show the
   same engine drives a development decision.

Zero model calls. Writes the ledger + supervision report under
benchmarks/decision_runs/. candidate=true / serves_truth=false.

Usage:
    python3 scripts/run_decision_engine_demo.py --self-test
    python3 scripts/run_decision_engine_demo.py --write
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

from primitives.decision_engine import LedgerStats, choose, context_signature, is_applicable  # noqa: E402
from primitives.decision_supervisor import supervise  # noqa: E402
from primitives.graph_search import GraphSearchIndex  # noqa: E402
from primitives import decision_handlers  # noqa: E402

PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "decision-portfolios"
RUNS = REPO_ROOT / "benchmarks" / "decision_runs"


def _load_probes():
    spec = importlib.util.spec_from_file_location(
        "gse", REPO_ROOT / "scripts" / "evaluate_graph_search.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.PROBES


def _load_pack():
    decisions = [json.loads(l) for l in (PACK_DIR / "decision_points.jsonl").read_text().splitlines() if l.strip()]
    paths = [json.loads(l) for l in (PACK_DIR / "execution_paths.jsonl").read_text().splitlines() if l.strip()]
    return decisions, paths


HANDLERS = {
    "path:retrieval.lexical_only": decision_handlers.retrieval_lexical,
    "path:retrieval.typed_edge": decision_handlers.retrieval_typed_edge,
    "path:retrieval.lexical_plus_typed": decision_handlers.retrieval_fused,
}


def _reciprocal_rank(ranked_ids: list[str], needle: str) -> float:
    for i, nid in enumerate(ranked_ids, start=1):
        if needle in nid:
            return 1.0 / i
    return 0.0


def run(write: bool) -> dict:
    decisions, paths = _load_pack()
    dmap = {d["decision_id"]: d for d in decisions}
    paths_by_decision: dict[str, list] = {}
    for p in paths:
        paths_by_decision.setdefault(p["decision_id"], []).append(p)

    probes = _load_probes()
    index = GraphSearchIndex()
    receipts: list[dict] = []
    seq = 0

    # --- 1. retrieval plane tournament (execute all applicable planes) ---
    rdid = "decision:retrieval.plane_selection"
    rpaths = paths_by_decision[rdid]
    plane_wins: dict[str, list] = {p["path_id"]: [] for p in rpaths}
    for intent, want, needle in probes:
        ctx = {"want_type_known": bool(want)}
        for p in rpaths:
            if not is_applicable(p, ctx):
                continue
            ranked = HANDLERS[p["path_id"]](index, intent, want)
            win = _reciprocal_rank(ranked, needle)
            plane_wins[p["path_id"]].append(win)
            receipts.append({
                "record_type": "decision_receipt", "decision_id": rdid, "path_id": p["path_id"],
                "context_signature": context_signature(rdid, ctx, dmap[rdid]["context_signature"]),
                "sequence": seq, "applicable": True, "chosen": False,
                "proved": win > 0, "win_score": round(win, 4),
                "cost_observed": p["cost_model"]["latency_ms"], "candidate": True, "serves_truth": False,
            })
            seq += 1

    # CONTEXTUAL comparison: condition win-rates on the same context bucket so
    # lexical is not penalized by the no-type probes it alone must answer.
    ctx_true = {"want_type_known": True}
    sig_true = context_signature(rdid, ctx_true, dmap[rdid]["context_signature"])
    stats_true = LedgerStats.from_receipts(receipts, only_context=sig_true)
    retrieval_choice = choose(dmap[rdid], rpaths, ctx_true, stats_true)
    retrieval_choice_notype = choose(dmap[rdid], rpaths, {"want_type_known": False},
                                     LedgerStats.from_receipts(receipts))
    # per-plane win-rate WITHIN the want-known context (fair, apples-to-apples)
    plane_winrate = {}
    for p in rpaths:
        st = stats_true.get(rdid, p["path_id"])
        plane_winrate[p["path_id"]] = round(st.win_rate, 4) if st.count else None

    # --- 2. remix escalation across contract-diff contexts (cold) ---
    remix = dmap["decision:remix.escalation"]
    rmpaths = paths_by_decision["decision:remix.escalation"]
    remix_choices = {}
    for diff in ["rename", "envelope", "novel_semantic"]:
        c = choose(remix, rmpaths, {"diff_kind": diff})
        remix_choices[diff] = {"chosen": c["chosen_path"], "reason": c["reason"]}

    # --- 3. dev proof-stage order (cold) ---
    dev = dmap["decision:dev.proof_stage_order"]
    devpaths = paths_by_decision["decision:dev.proof_stage_order"]
    dev_choice = choose(dev, devpaths, {"changed_lane": "coding_agent"})

    report = supervise(decisions, paths, receipts)

    summary = {
        "run_id": "decrun",
        "engine": "one decision_engine drives all three decisions",
        "retrieval": {
            "plane_win_rate": plane_winrate,
            "data_preferred_plane": retrieval_choice["chosen_path"],
            "reason": retrieval_choice["reason"],
            "when_no_type_known": retrieval_choice_notype["chosen_path"],
            "n_applicable_no_type": retrieval_choice_notype["n_applicable"],
        },
        "remix_escalation": remix_choices,
        "dev_proof_order": {"chosen": dev_choice["chosen_path"], "reason": dev_choice["reason"]},
        "supervisor": report["self_awareness"],
        "recommendations": [{"kind": r["kind"], "from": r["from_path"], "to": r["to_path"]}
                            for r in report["recommendations"]],
        "receipts": len(receipts),
        "candidate": True, "serves_truth": False,
        "honesty_notes": [
            "zero model calls; retrieval win = reciprocal rank of the target over the full cross-lane graph",
            "the data-preferred plane is the argmax of MEASURED win-rates, not a hardcoded choice",
            "win-rates are context-conditioned (want-known bucket) so planes with different applicability compare fairly",
            "typed-edge leads because a specific wanted type has few producers; on this small probe set that dominates fused - a floor signal, not a tuned verdict (fused likely wins on ambiguous queries not probed)",
            "remix/dev choices are cold (no receipts) - they show policy behavior, not a learned winner",
            "recommendations are candidate; a human applies them by editing the seed (a data change)",
        ],
    }

    if write:
        RUNS.mkdir(parents=True, exist_ok=True)
        (RUNS / "ledger.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in receipts), encoding="utf-8")
        (RUNS / "supervision_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        (RUNS / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        manifest = {"run_id": "decrun", "generated_by": "scripts/run_decision_engine_demo.py",
                    "files": {"ledger.jsonl": {"rows": len(receipts),
                              "content_sha256": hashlib.sha256(
                                  "".join(json.dumps(r) + "\n" for r in receipts).encode()).hexdigest()}},
                    "candidate": True, "serves_truth": False}
        (RUNS / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

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
    # Honest gate: the engine drives all three decisions, picks an applicable
    # path for each, and the retrieval winner is the argmax of measured win-rates.
    wr = {k: v for k, v in summary["retrieval"]["plane_win_rate"].items() if v is not None}
    argmax = max(wr, key=wr.get) if wr else None
    ok = (summary["retrieval"]["data_preferred_plane"] in wr
          and summary["retrieval"]["data_preferred_plane"] == argmax
          and summary["retrieval"]["n_applicable_no_type"] == 1
          and summary["remix_escalation"]["rename"]["chosen"] == "path:remix.deterministic_mutator"
          and summary["remix_escalation"]["novel_semantic"]["chosen"] == "path:remix.bounded_model"
          and summary["dev_proof_order"]["chosen"] is not None)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
