"""Decision graph: make the control-flow tree edge-typed, exactly like the
capability graph makes primitives edge-typed.

Each decision (fork) carries a state CONTRACT - the keys it `consumes` and the
keys it `produces`. That turns forks into typed nodes whose EDGES are derived,
not hand-wired: fork A -> fork B whenever B consumes a key A produces. A reusable
typed DAG of forks is a DECISION FRAMEWORK. The same forward-chaining the route
compiler uses to order primitives orders decisions here, so the two graphs -
runtime capability and control flow - are the same kind of object composed the
same way.

Why this matters: the planner can now order coupled decisions by their contracts
(topologically) instead of treating them as an unordered set, and a decision
framework is validated by the same wave rule the warehouse pipelines use - every
consumed key must be produced by the initial state or an earlier fork. Stdlib
only.
"""

from __future__ import annotations

import hashlib
import json


def _contract(decision: dict) -> tuple[set, set]:
    c = decision.get("contract", {})
    return set(c.get("consumes", [])), set(c.get("produces", []))


def build_decision_edges(decisions: list[dict]) -> list[dict]:
    """Derive fork->fork edges: A -> B when B consumes a key A produces."""
    prod = {d["decision_id"]: _contract(d)[1] for d in decisions}
    edges = []
    for b in decisions:
        b_consumes, _ = _contract(b)
        for a in decisions:
            if a["decision_id"] == b["decision_id"]:
                continue
            shared = b_consumes & prod[a["decision_id"]]
            if shared:
                edges.append({"from": a["decision_id"], "to": b["decision_id"],
                              "on_keys": sorted(shared)})
    return sorted(edges, key=lambda e: (e["from"], e["to"]))


def compile_decision_order(decisions: list[dict], initial_keys: list[str],
                           goal_keys: list[str]) -> dict:
    """Order the forks needed to produce `goal_keys` from `initial_keys` by
    forward-chaining over produced state keys (the route compiler, for
    decisions). Returns a decision plan or a gap with the first unmet key."""
    by_id = {d["decision_id"]: d for d in decisions}
    available = set(initial_keys)
    order: list[str] = []
    used: set[str] = set()
    goal = set(goal_keys)

    changed = True
    while changed and not goal <= available:
        changed = False
        for d in sorted(decisions, key=lambda x: x["decision_id"]):
            did = d["decision_id"]
            if did in used:
                continue
            consumes, produces = _contract(d)
            if consumes <= available:
                used.add(did)
                order.append(did)
                available |= produces
                changed = True

    if not goal <= available:
        # nearest producers of the first unmet goal key
        unmet = sorted(goal - available)
        nearest = sorted(d["decision_id"] for d in decisions
                         if unmet and unmet[0] in _contract(d)[1])
        return {"record_type": "decision_plan", "compiled": False,
                "unmet_keys": unmet, "nearest_producers": nearest,
                "order": [], "candidate": True, "serves_truth": False}

    # minimal chain: keep only forks on a path to the goal
    needed = set(goal_keys)
    chosen: list[str] = []
    for did in reversed(order):
        _, produces = _contract(by_id[did])
        if produces & needed:
            chosen.append(did)
            needed |= _contract(by_id[did])[0]
    chain = [d for d in order if d in set(chosen)]

    steps = []
    avail = set(initial_keys)
    for i, did in enumerate(chain, start=1):
        consumes, produces = _contract(by_id[did])
        steps.append({"step": i, "decision_id": did,
                      "consumes_satisfied_by": sorted(consumes & avail) or ["<none>"],
                      "produces": sorted(produces)})
        avail |= produces
    plan_hash = "dhash:" + hashlib.sha256(
        json.dumps({"initial": sorted(initial_keys), "goal": sorted(goal_keys),
                    "order": [s["decision_id"] for s in steps]}, sort_keys=True).encode()).hexdigest()[:16]
    return {"record_type": "decision_plan", "compiled": True, "order": [s["decision_id"] for s in steps],
            "steps": steps, "plan_hash": plan_hash, "unmet_keys": [],
            "candidate": True, "serves_truth": False}


def validate_decision_dag(order: list[str], decisions: list[dict],
                          initial_keys: list[str]) -> dict:
    """A framework's declared fork order is valid iff each fork's consumed keys
    are produced by the initial state or an earlier fork (the wave rule)."""
    by_id = {d["decision_id"]: d for d in decisions}
    available = set(initial_keys)
    first_unsatisfied = None
    for i, did in enumerate(order, start=1):
        d = by_id.get(did)
        if d is None:
            first_unsatisfied = first_unsatisfied or {"step": i, "decision_id": did, "reason": "unknown"}
            continue
        consumes, produces = _contract(d)
        missing = sorted(consumes - available)
        if missing and first_unsatisfied is None:
            first_unsatisfied = {"step": i, "decision_id": did, "missing": missing}
        available |= produces
    return {"valid": first_unsatisfied is None, "first_unsatisfied": first_unsatisfied,
            "final_state_keys": sorted(available)}
