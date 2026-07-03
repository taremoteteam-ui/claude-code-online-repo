"""Decision supervisor: the self-aware / self-tuning layer over the ledger.

Pure and deterministic: given the decision portfolio + the append-only receipt
ledger, it computes a health report and emits TUNING RECOMMENDATIONS as
candidate records - it never silently rewrites a policy. What it watches:

  - coverage / cold-start: which decisions have enough receipts to trust, which
    are still on their prior;
  - promotion: a challenger whose decayed win-rate beats the current default by
    a margin with enough samples -> recommend making it the default;
  - domination: a path worse on BOTH win-rate and cost than another, with
    enough samples -> recommend retiring it (kept as data for revival);
  - drift (non-stationarity): a path whose RECENT-window win-rate fell well
    below its lifetime rate -> recommend re-opening exploration (raise epsilon),
    because a past winner may be stale.

Recommendations are candidate=true / serves_truth=false; a human/gate applies
them by editing the seed (a data change), keeping the non-commitment law honest.
Stdlib only.
"""

from __future__ import annotations

from primitives.decision_engine import LedgerStats, normalize_cost

MIN_SAMPLES = 5          # below this a path is cold; no promote/retire
PROMOTE_MARGIN = 0.10    # challenger must beat default by this decayed-win-rate
DRIFT_DROP = 0.25        # recent window this far below lifetime => drift
RECENT_WINDOW = 5        # receipts counted as "recent" per path


def _recent_win_rate(receipts: list[dict], decision_id: str, path_id: str) -> float | None:
    rs = sorted([r for r in receipts
                 if r["decision_id"] == decision_id and r["path_id"] == path_id
                 and r.get("applicable", True)],
                key=lambda x: x["sequence"])
    if len(rs) < RECENT_WINDOW:
        return None
    window = rs[-RECENT_WINDOW:]
    return sum(float(r["win_score"]) for r in window) / len(window)


def supervise(decisions: list[dict], paths: list[dict], receipts: list[dict],
              decay: float = 0.9) -> dict:
    stats = LedgerStats.from_receipts(receipts, decay=decay)
    paths_by_decision: dict[str, list[dict]] = {}
    for p in paths:
        paths_by_decision.setdefault(p["decision_id"], []).append(p)

    reports = []
    recommendations = []
    for d in sorted(decisions, key=lambda x: x["decision_id"]):
        did = d["decision_id"]
        dpaths = paths_by_decision.get(did, [])
        cost_by_id = {p["path_id"]: normalize_cost(p["cost_model"]) for p in dpaths}
        path_health = []
        for p in sorted(dpaths, key=lambda x: x["path_id"]):
            st = stats.get(did, p["path_id"])
            path_health.append({
                "path_id": p["path_id"], "count": st.count, "cold": st.cold,
                "win_rate": round(st.win_rate, 4),
                "decayed_win_rate": round(st.decayed_win_rate, 4),
                "norm_cost": round(cost_by_id[p["path_id"]], 4),
            })
        warm = [h for h in path_health if not h["cold"] and h["count"] >= MIN_SAMPLES]
        total = sum(h["count"] for h in path_health)

        # Promotion: best warm challenger vs current default.
        if warm:
            best = max(warm, key=lambda h: h["decayed_win_rate"])
            if best["path_id"] != d["default_path"] and best["decayed_win_rate"] - \
                    stats.get(did, d["default_path"]).decayed_win_rate >= PROMOTE_MARGIN:
                recommendations.append({
                    "record_type": "decision_tuning_recommendation", "kind": "promote_default",
                    "decision_id": did, "from_path": d["default_path"], "to_path": best["path_id"],
                    "evidence": f"decayed_win_rate {best['decayed_win_rate']} beats default by >= {PROMOTE_MARGIN}",
                    "candidate": True, "serves_truth": False,
                })

        # Domination: worse on BOTH win-rate and cost than some sibling.
        for h in warm:
            dominators = [g for g in warm if g["path_id"] != h["path_id"]
                          and g["decayed_win_rate"] >= h["decayed_win_rate"]
                          and g["norm_cost"] <= h["norm_cost"]
                          and (g["decayed_win_rate"] > h["decayed_win_rate"] or g["norm_cost"] < h["norm_cost"])]
            if dominators:
                recommendations.append({
                    "record_type": "decision_tuning_recommendation", "kind": "retire_dominated",
                    "decision_id": did, "from_path": h["path_id"],
                    "to_path": dominators[0]["path_id"],
                    "evidence": "dominated on win-rate and cost; kept as data for revival",
                    "candidate": True, "serves_truth": False,
                })

        # Drift: a warm path whose recent window fell below its lifetime rate.
        for h in warm:
            recent = _recent_win_rate(receipts, did, h["path_id"])
            if recent is not None and h["win_rate"] - recent >= DRIFT_DROP:
                recommendations.append({
                    "record_type": "decision_tuning_recommendation", "kind": "reopen_exploration",
                    "decision_id": did, "from_path": h["path_id"], "to_path": h["path_id"],
                    "evidence": f"recent win-rate {round(recent,4)} fell >= {DRIFT_DROP} below lifetime {h['win_rate']}",
                    "candidate": True, "serves_truth": False,
                })

        reports.append({
            "decision_id": did, "regime": d["regime"], "policy": d["selection_policy"],
            "total_receipts": total, "warm_paths": len(warm), "cold_paths": len(path_health) - len(warm),
            "trusted": len(warm) >= 1, "path_health": path_health,
        })

    warm_total = sum(r["warm_paths"] for r in reports)
    path_total = sum(len(paths_by_decision.get(r["decision_id"], [])) for r in reports)
    return {
        "record_type": "decision_supervision_report",
        "decisions": len(reports),
        "self_awareness": {
            "decisions_trusted": sum(1 for r in reports if r["trusted"]),
            "decisions_cold": sum(1 for r in reports if not r["trusted"]),
            "warm_path_fraction": round(warm_total / path_total, 4) if path_total else 0.0,
            "open_recommendations": len(recommendations),
        },
        "per_decision": reports,
        "recommendations": recommendations,
        "candidate": True,
        "serves_truth": False,
    }
