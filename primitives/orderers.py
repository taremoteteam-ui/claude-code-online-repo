"""Ordering strategies: the portfolio of ways to WIRE primitives into a solution.

Ordering is itself a decision portfolio - there is no single right way to order
primitives, so we store several and let the shared validator (and, over time,
receipts) decide:

  deterministic_compile  - the zero-model route compiler's topological order.
  framework_fill         - bind a reusable solution FRAMEWORK's declared slots to
                           concrete producers, in the framework's wiring order.
  llm_propose            - a model proposes an order; the deterministic
                           route_validator disposes, and repair() topologically
                           fixes any invalid proposal. (Offline here: a labeled
                           STUB proposer stands in for the model - 0 tokens - so
                           the propose -> validate -> repair safety loop is real
                           even though no model runs. A real model plugs into
                           `propose` unchanged.)

The load-bearing idea: however an order is proposed, it is only accepted if it
type-checks (primitives/route_validator.py). That is what makes LLM-based
ordering safe - a hallucinated wiring is rejected, not run. Stdlib only.
"""

from __future__ import annotations

from primitives.route_compiler import compile_route
from primitives.route_validator import validate_order
from primitives.edges import canonical_type


def _intended_order(have: list[str], want: str, nodes: list[dict]) -> list[str]:
    """The primitives the deterministic compiler selects, in topological order."""
    route = compile_route(have, want, nodes)
    return [s["node_id"] for s in route.get("route_steps", [])] if route.get("compiled") else []


def deterministic_compile(have: list[str], want: str, nodes: list[dict]) -> dict:
    order = _intended_order(have, want, nodes)
    return {"strategy": "deterministic_compile", "order": order, "effects": ["none"],
            "proposed_tokens": 0}


def framework_fill(framework: dict, have: list[str], want: str, nodes: list[dict]) -> dict:
    """Bind each framework slot's produces-type to a concrete producer whose
    inputs are available so far, in the framework's wiring order."""
    available = {canonical_type(h) for h in have}
    order: list[str] = []
    producers: dict[str, list[str]] = {}
    for n in nodes:
        for op in n.get("output_ports", []):
            producers.setdefault(op["canonical_type"], []).append(n["node_id"])
    for slot in framework.get("slots", []):
        target = canonical_type(slot["produces_type"])
        pick = None
        for nid in sorted(producers.get(target, [])):
            node = next(x for x in nodes if x["node_id"] == nid)
            reqs = [p["canonical_type"] for p in node.get("required_input_ports", [])]
            if all(r in available for r in reqs):
                pick = nid
                break
        if pick is None:
            return {"strategy": "framework_fill", "order": order, "filled": False,
                    "unfilled_slot": slot["role"], "effects": ["none"], "proposed_tokens": 0}
        order.append(pick)
        node = next(x for x in nodes if x["node_id"] == pick)
        for op in node.get("output_ports", []):
            available.add(op["canonical_type"])
    return {"strategy": "framework_fill", "order": order, "filled": True,
            "framework_id": framework.get("framework_id"), "effects": ["none"], "proposed_tokens": 0}


def _stub_propose(have: list[str], want: str, nodes: list[dict]) -> list[str]:
    """STUB standing in for a model proposal. It returns the needed primitives in
    a DELIBERATELY reversed (non-topological) order, so the validate->repair
    safety loop is exercised even offline. A real model replaces this body; the
    surrounding contract (propose a list of node_ids) is unchanged."""
    return list(reversed(_intended_order(have, want, nodes)))


def llm_propose(have: list[str], want: str, nodes: list[dict], propose=None) -> dict:
    """Model proposes an order; the validator disposes; repair() fixes an invalid
    proposal by topologically re-ordering the proposed SET."""
    propose = propose or _stub_propose
    proposed = propose(have, want, nodes)
    v = validate_order(proposed, have, want, nodes)
    repaired = None
    order = proposed
    if not v["valid"]:
        order = repair(proposed, have, want, nodes)
        repaired = order
    return {"strategy": "llm_propose", "order": order, "proposed_order": proposed,
            "proposal_valid": v["valid"], "repaired": repaired is not None,
            "effects": ["model_call"], "proposed_tokens": 0,
            "note": "STUB proposer offline (0 tokens); a real model plugs into `propose`; "
                    "the deterministic validator/repair gate the result"}


def repair(order: list[str], have: list[str], want: str, nodes: list[dict]) -> list[str]:
    """Topologically re-order the SET of `order` (plus any missing intermediates)
    into a valid order via the deterministic compiler - the 'compiler disposes'
    repair for an invalid proposal."""
    return _intended_order(have, want, nodes)


REGISTRY = {
    "deterministic_compile": deterministic_compile,
    "llm_propose": llm_propose,
}
