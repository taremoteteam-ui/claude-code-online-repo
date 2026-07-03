"""Decision planner: find the most efficient COMBINATION of gates/checkpoints/
paths across a whole pipeline, not just the locally-best choice per decision.

The engine (decision_engine.py) picks one path for one decision. Real pipelines
couple decisions - the cheapest per-decision pick is not the cheapest end-to-end
plan, and the ORDER you run gates in changes the expected cost of discovering a
failure. This module adds the two pieces that make the substrate a planner:

  1. optimal_gate_order - order independent gates to MINIMISE expected cost until
     the first failure. This is provably optimal (adjacent-exchange argument):
     run gates by DECREASING failure-probability-per-unit-cost (p_fail / cost).
     Cheapest-most-likely-to-fail first = fail fast for the least spend.

  2. plan_combination - branch-and-bound over the product of applicable paths
     across several coupled decisions to find the min-expected-cost combination
     that still clears a whole-plan reliability checkpoint (and optional budget).
     Exact for the small portfolios real pipelines have; falls back to greedy
     per-decision with disclosure when the space is too large.

Both are driven by RECEIPTS (win-rates -> success/failure probabilities, cost
models -> cost) and disclose their arithmetic - never a silent plan. The
engineer declares only the path space, the cost model, and what a win is; the
planner derives the optimal gated plan from data, so no further engineering
decision about ordering/selection/combination is needed. Stdlib only.
"""

from __future__ import annotations

from itertools import product

from primitives.decision_engine import LedgerStats, is_applicable, normalize_cost

_MIN_SUCCESS = 0.05   # floor so expected-cost division never blows up
_PRIOR_SUCCESS = 0.5  # cold-start success prior
_MAX_EXACT = 20000    # combination-space size above which we fall back to greedy


# ---------------------------------------------------------------------------
# 1. Optimal gate ordering (minimise expected cost to first failure)
# ---------------------------------------------------------------------------

def _expected_cost_to_failure(order: list[dict]) -> float:
    """E[cost] = sum_k cost_k * P(all earlier gates passed)."""
    total = 0.0
    reach = 1.0
    for g in order:
        total += g["cost"] * reach
        reach *= (1.0 - g["p_fail"])
    return total


def optimal_gate_order(gates: list[dict], stats: LedgerStats | None = None,
                       decision_id: str = "gates") -> dict:
    """gates: [{gate_id, cost, p_fail?}]. p_fail may be given, else derived from
    the ledger win-rate (fail = 1 - decayed_win_rate), else the cold prior.

    Returns the optimal order, its expected cost, and the expected cost of the
    given order for comparison - the measured saving, not a claim."""
    stats = stats or LedgerStats()
    resolved = []
    for g in gates:
        cost = float(g["cost"])
        if "p_fail" in g:
            p = float(g["p_fail"])
        else:
            st = stats.get(decision_id, g["gate_id"])
            p = 1.0 - (st.decayed_win_rate if not st.cold else _PRIOR_SUCCESS)
        resolved.append({"gate_id": g["gate_id"], "cost": max(cost, 0.0),
                         "p_fail": min(max(p, 0.0), 1.0),
                         "ratio": (min(max(p, 0.0), 1.0) / cost) if cost > 0 else float("inf")})
    given_cost = _expected_cost_to_failure(resolved)
    ordered = sorted(resolved, key=lambda g: (-g["ratio"], g["gate_id"]))
    opt_cost = _expected_cost_to_failure(ordered)
    return {
        "record_type": "gate_order_plan",
        "policy": "descending p_fail/cost (fail-fast per unit cost) - provably optimal for independent gates",
        "order": [g["gate_id"] for g in ordered],
        "expected_cost_optimal": round(opt_cost, 4),
        "expected_cost_given_order": round(given_cost, 4),
        "expected_cost_reduction": round(given_cost - opt_cost, 4),
        "gates": ordered,
        "candidate": True, "serves_truth": False,
    }


# ---------------------------------------------------------------------------
# 2. Combination planning (min expected cost s.t. a whole-plan reliability gate)
# ---------------------------------------------------------------------------

def _path_metrics(decision_id: str, path: dict, stats: LedgerStats) -> tuple[float, float]:
    st = stats.get(decision_id, path["path_id"])
    success = st.decayed_win_rate if not st.cold else _PRIOR_SUCCESS
    success = min(max(success, _MIN_SUCCESS), 1.0)
    exp_cost = normalize_cost(path["cost_model"]) / success   # amortised retry cost
    return exp_cost, success


def plan_combination(decisions: list[dict], paths_by_decision: dict, context: dict,
                     stats: LedgerStats | None = None, min_reliability: float = 0.0,
                     budget: float | None = None, compatible=None) -> dict:
    """Find the min-expected-cost COMBINATION (one path per decision) that clears
    a whole-plan reliability gate (product of path success >= min_reliability)
    and an optional budget, honouring an optional compatibility predicate over
    the chosen {decision_id: path_id} map (the coupling).

    Branch-and-bound: build the combination decision by decision, pruning any
    partial plan whose accumulated cost already exceeds the best complete plan or
    whose best-possible remaining reliability cannot meet the gate. Exact when the
    space is small; greedy fallback (disclosed) otherwise."""
    stats = stats or LedgerStats()
    order = sorted(decisions, key=lambda d: d["decision_id"])
    # applicable options per decision, with metrics
    options = []
    for d in order:
        did = d["decision_id"]
        opts = []
        for p in paths_by_decision.get(did, []):
            if not is_applicable(p, context):
                continue
            ec, s = _path_metrics(did, p, stats)
            opts.append({"path_id": p["path_id"], "exp_cost": ec, "success": s})
        if not opts:
            return {"record_type": "combination_plan", "feasible": False,
                    "reason": f"{did}: no applicable path", "candidate": True, "serves_truth": False}
        opts.sort(key=lambda o: o["exp_cost"])
        options.append((did, opts))

    space = 1
    for _, opts in options:
        space *= len(opts)

    best = {"cost": float("inf"), "combo": None, "reliability": 0.0}

    def feasible(combo: dict) -> bool:
        return compatible is None or compatible(combo)

    if space <= _MAX_EXACT:
        method = "branch_and_bound_exact"
        # best-possible remaining reliability per suffix (max success products)
        max_success_suffix = [1.0] * (len(options) + 1)
        for i in range(len(options) - 1, -1, -1):
            max_success_suffix[i] = max_success_suffix[i + 1] * max(o["success"] for o in options[i][1])

        def recurse(i: int, combo: dict, cost: float, reliab: float):
            if cost >= best["cost"]:
                return
            if reliab * max_success_suffix[i] < min_reliability:
                return
            if i == len(options):
                if reliab >= min_reliability and (budget is None or cost <= budget) and feasible(combo):
                    if cost < best["cost"]:
                        best.update(cost=cost, combo=dict(combo), reliability=reliab)
                return
            did, opts = options[i]
            for o in opts:
                if budget is not None and cost + o["exp_cost"] > budget:
                    continue
                combo[did] = o["path_id"]
                recurse(i + 1, combo, cost + o["exp_cost"], reliab * o["success"])
            combo.pop(did, None)

        recurse(0, {}, 0.0, 1.0)
    else:
        method = "greedy_fallback_space_too_large"
        combo, cost, reliab = {}, 0.0, 1.0
        for did, opts in options:
            o = opts[0]  # cheapest applicable
            combo[did] = o["path_id"]
            cost += o["exp_cost"]
            reliab *= o["success"]
        if reliab >= min_reliability and (budget is None or cost <= budget) and feasible(combo):
            best.update(cost=cost, combo=combo, reliability=reliab)

    if best["combo"] is None:
        return {"record_type": "combination_plan", "feasible": False,
                "reason": "no combination meets the reliability/budget/compatibility constraints",
                "method": method, "space": space, "candidate": True, "serves_truth": False}
    return {
        "record_type": "combination_plan", "feasible": True, "method": method,
        "space": space, "chosen": best["combo"],
        "expected_cost": round(best["cost"], 4),
        "plan_reliability": round(best["reliability"], 4),
        "min_reliability": min_reliability, "budget": budget,
        "candidate": True, "serves_truth": False,
    }
