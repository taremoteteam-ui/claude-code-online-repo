"""Route runtime: EXECUTE a compiled route (PlanLock), not just compile it.

The route compiler produces an ordered chain of nodes whose typed ports connect.
This runtime threads real values through that chain: it keeps a state dict
(canonical_type -> value), runs each step's handler through
``primitives.core.run_primitive`` (so every step emits an ExecutionReceipt with
input/output hashes, effects, proofs, and timing), merges the produced values
back into the state, and returns the wanted artifact plus the full receipt trail.

A step with no registered handler is an honest stop: the run reports the
unimplemented node and returns a partial trail rather than faking a result -
consistent with the candidate boundary (an unimplemented primitive is not
executed into existence). Stdlib only.
"""

from __future__ import annotations

from primitives.core import PrimitiveExecutionError, run_primitive
from primitives.edges import canonical_type


def _merge(state: dict, values: dict) -> None:
    """Store each value under BOTH its port name and its canonical type, so a
    handler reading by port name and the want-lookup by canonical type both
    resolve (RowSet and TabularDataset point at the same value)."""
    for k, v in values.items():
        state[k] = v
        state[canonical_type(k)] = v


def execute_route(route: dict, handlers: dict, initial_state: dict, run_id: str,
                  effects_by_node: dict | None = None) -> dict:
    """Run a compiled route over a handler registry.

    route: a compiled_route dict (compiled=True) with route_steps.
    handlers: node_id -> callable(state)->PrimitiveOutcome.
    initial_state: canonical_type -> value for the request's `have` ports.
    Returns a run record: ran (all steps executed), final value for the wanted
    type, per-step receipts, the observed-effects union, and any unimplemented
    node that stopped the run.
    """
    effects_by_node = effects_by_node or {}
    if not route.get("compiled"):
        return {"ran": False, "reason": "route did not compile", "step_receipts": [],
                "effects_union": [], "unimplemented": [], "want_value": None}

    state: dict = {}
    _merge(state, initial_state)
    step_receipts = []
    effects: set[str] = set()
    unimplemented = []
    error = None

    for step in route["route_steps"]:
        nid = step["node_id"]
        handler = handlers.get(nid)
        if handler is None:
            unimplemented.append(nid)
            break
        try:
            output, receipt = run_primitive(
                nid, handler, state, run_id,
                declared_effects=effects_by_node.get(nid, ["none"]))
        except PrimitiveExecutionError as exc:
            step_receipts.append(exc.receipt)
            error = str(exc)
            break
        step_receipts.append(receipt)
        effects.update(receipt["effects_observed"])
        if isinstance(output, dict):
            _merge(state, output)

    want_type = route.get("want_canonical_type")
    ran = not unimplemented and error is None
    return {
        "ran": ran,
        "want": route.get("want"),
        "want_value": state.get(want_type),
        "steps_executed": len(step_receipts),
        "step_receipts": step_receipts,
        "effects_union": sorted(effects),
        "unimplemented": unimplemented,
        "error": error,
    }
