"""Route validator: the deterministic truth gate for ANY proposed ordering.

Whatever proposes a wiring - the deterministic route compiler, a framework fill,
or an LLM - the order is only trustworthy if it type-checks: every step's
required inputs must already be available (from the request's `have` or an
earlier step's output), and the wanted type must ultimately be produced. This
module validates that, over the same canonical types the compiler composes on.

This is what makes LLM-based ordering SAFE: the model proposes freely, and this
gate disposes - an ordering that does not type-check is rejected (or repaired),
so a hallucinated wiring never runs. Stdlib only.
"""

from __future__ import annotations

from primitives.edges import canonical_type


def validate_order(order: list[str], have: list[str], want: str, nodes: list[dict]) -> dict:
    """Check that running `order` (node_ids) from `have` produces `want`.

    Returns a validation record: valid, per-step satisfaction, the first
    unsatisfied step (if any), and whether the wanted type is produced. Config
    ports never block (they are request-supplied); receipt ports chain like data.
    """
    node_by_id = {n["node_id"]: n for n in nodes}
    available = {canonical_type(h) for h in have}
    steps = []
    first_unsatisfied = None
    for i, nid in enumerate(order, start=1):
        node = node_by_id.get(nid)
        if node is None:
            steps.append({"step": i, "node_id": nid, "satisfied": False, "reason": "unknown node"})
            if first_unsatisfied is None:
                first_unsatisfied = {"step": i, "node_id": nid, "reason": "unknown node"}
            continue
        reqs = [p["canonical_type"] for p in node.get("required_input_ports", [])]
        missing = [r for r in reqs if r not in available]
        ok = not missing
        steps.append({"step": i, "node_id": nid, "satisfied": ok,
                      "missing": missing, "produces": [op["canonical_type"] for op in node.get("output_ports", [])]})
        if ok:
            for op in node.get("output_ports", []):
                available.add(op["canonical_type"])
        elif first_unsatisfied is None:
            first_unsatisfied = {"step": i, "node_id": nid, "missing": missing}

    want_ct = canonical_type(want)
    produces_want = want_ct in available
    valid = first_unsatisfied is None and produces_want
    return {
        "record_type": "order_validation", "valid": valid,
        "produces_want": produces_want, "want_canonical_type": want_ct,
        "steps": steps, "first_unsatisfied": first_unsatisfied,
        "candidate": True, "serves_truth": False,
    }
