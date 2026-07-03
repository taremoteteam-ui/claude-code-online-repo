"""Deterministic edge-graph route compiler.

Given what a caller HAS (a set of available ports) and what they WANT (a target
port), this assembles an ordered chain of primitives whose typed ports connect
- reading only the edges, never a primitive's internals, with zero model calls.
This is the payoff of the primitive bank: an LLM (or plain search) composes a
large task from small primitives by edge compatibility, instead of rereading
source or rewriting code.

Method: forward-chaining saturation over canonical port types. A node is
runnable when every required input port's canonical_type is already available
(config ports are the caller's to supply, so they never block). Running a node
makes its output types available. When the wanted type becomes available, the
chain is reconstructed backward to a minimal, topologically ordered PlanLock
whose route_hash is stable and replayable. Unreachable targets return a gap
carrying the first unmet type and the nearest producers - the exact connector
the bank is missing.

Stdlib only.
"""

from __future__ import annotations

import hashlib
import json

from primitives.edges import canonical_type


def _canon_set(ports: list[str]) -> dict:
    """Map available port names -> their canonical types, keeping the name for
    exact-tier reporting."""
    out: dict[str, str] = {}
    for name in ports:
        out.setdefault(canonical_type(name), name)
    return out


def compile_route(have: list[str], want: str, nodes: list[dict],
                  max_nodes: int = 40) -> dict:
    """Compile a route from ``have`` to ``want`` over the capability graph.

    nodes: capability_graph.jsonl rows (dicts with required_input_ports,
    output_ports, node_id). Returns a compiled_route dict (a PlanLock) or a
    gap record with compiled=False.
    """
    want_type = canonical_type(want)
    have_types = _canon_set(have)  # canonical_type -> a provided port name

    # available[ctype] = (source_step:int or 'request', producing port name)
    available: dict[str, tuple] = {ct: ("request", nm) for ct, nm in have_types.items()}
    produced_by: dict[str, str] = {}  # ctype -> node_id
    order: list[str] = []  # node_ids in production order (topological)
    used: set[str] = set()

    ordered_nodes = sorted(nodes, key=lambda n: n["node_id"])
    changed = True
    while changed and want_type not in available:
        changed = False
        for n in ordered_nodes:
            if n["node_id"] in used:
                continue
            reqs = [p["canonical_type"] for p in n["required_input_ports"]]
            if all(ct in available for ct in reqs):
                used.add(n["node_id"])
                order.append(n["node_id"])
                for p in n["output_ports"]:
                    ct = p["canonical_type"]
                    if ct not in available:
                        available[ct] = (n["node_id"], p["name"])
                        produced_by[ct] = n["node_id"]
                changed = True

    node_by_id = {n["node_id"]: n for n in nodes}

    if want_type not in available:
        # Gap: first unmet type is want itself; find nearest producers of it.
        nearest = sorted(n["node_id"] for n in nodes
                         if any(op["canonical_type"] == want_type for op in n["output_ports"]))
        return _gap(have, want, want_type, ["".join(want_type)], nearest[:10])

    if available[want_type][0] == "request":
        # Already available; empty route (nothing to compile).
        return _route(have, want, want_type, [], node_by_id, have_types)

    # Reconstruct a minimal chain: pull producers for want and its transitive
    # required types, stopping at request-provided types.
    needed: list[str] = [want_type]
    chosen: set[str] = set()
    seen_types: set[str] = set()
    while needed:
        t = needed.pop()
        if t in seen_types:
            continue
        seen_types.add(t)
        if t in have_types:
            continue
        nid = produced_by.get(t)
        if nid is None or nid in chosen:
            continue
        chosen.add(nid)
        for p in node_by_id[nid]["required_input_ports"]:
            needed.append(p["canonical_type"])

    # Order chosen nodes by their production order (topological).
    chain = [nid for nid in order if nid in chosen]
    if len(chain) > max_nodes:
        chain = chain[:max_nodes]
    return _route(have, want, want_type, chain, node_by_id, have_types)


def _tier(node: dict, ctype: str, have_types: dict, upstream_names: dict) -> tuple:
    """Return (source, tier) for a required input of canonical_type ctype."""
    # Prefer an exact port-name match from the request or an upstream output.
    if ctype in have_types:
        return "request", ("exact" if any(canonical_type(nm) == ctype and nm == have_types[ctype]
                                          for nm in [have_types[ctype]]) else "typed")
    src_node, out_name = upstream_names.get(ctype, (None, None))
    if src_node is not None:
        # exact if the upstream output port name equals one of this node's
        # input port names of the same type; typed otherwise.
        exact = any(ip["name"] == out_name for ip in node["required_input_ports"]
                    if ip["canonical_type"] == ctype)
        return src_node, ("exact" if exact else "typed")
    return "request", "typed"


def _route(have, want, want_type, chain, node_by_id, have_types) -> dict:
    # upstream_names[ctype] = (node_id, output port name) as produced along chain
    upstream: dict[str, tuple] = {}
    step_index: dict[str, int] = {}
    steps = []
    for i, nid in enumerate(chain, start=1):
        node = node_by_id[nid]
        satisfied = []
        for ip in node["required_input_ports"]:
            ct = ip["canonical_type"]
            if ct in have_types:
                satisfied.append({"input_port": ip["name"], "canonical_type": ct,
                                  "source": "request",
                                  "tier": "exact" if have_types[ct] == ip["name"] else "typed"})
            elif ct in upstream:
                src_nid, out_name = upstream[ct]
                satisfied.append({"input_port": ip["name"], "canonical_type": ct,
                                  "source": f"step:{step_index[ct]}",
                                  "tier": "exact" if out_name == ip["name"] else "typed"})
            else:
                satisfied.append({"input_port": ip["name"], "canonical_type": ct,
                                  "source": "request", "tier": "typed"})
        produces = [op["name"] for op in node["output_ports"]]
        for op in node["output_ports"]:
            if op["canonical_type"] not in upstream:
                upstream[op["canonical_type"]] = (nid, op["name"])
                step_index[op["canonical_type"]] = i
        steps.append({"step": i, "node_id": nid, "satisfied_by": satisfied,
                      "produces": produces})

    route_repr = [[s["node_id"], [c["canonical_type"] for c in s["satisfied_by"]]] for s in steps]
    route_hash = "sha256:" + hashlib.sha256(
        json.dumps({"have": sorted(have), "want": want, "steps": route_repr},
                   sort_keys=True).encode()).hexdigest()
    return {
        "record_type": "compiled_route",
        "route_id": "route:" + hashlib.sha256(
            json.dumps({"have": sorted(have), "want": want}, sort_keys=True).encode()).hexdigest()[:16],
        "compiled": True,
        "have": list(have),
        "want": want,
        "want_canonical_type": want_type,
        "route_steps": steps,
        "route_hash": route_hash,
        "step_count": len(steps),
        "unmet_types": [],
        "nearest_producers": [],
        "candidate": True,
        "serves_truth": False,
    }


def _gap(have, want, want_type, unmet_types, nearest) -> dict:
    return {
        "record_type": "compiled_route",
        "route_id": "route:" + hashlib.sha256(
            json.dumps({"have": sorted(have), "want": want}, sort_keys=True).encode()).hexdigest()[:16],
        "compiled": False,
        "have": list(have),
        "want": want,
        "want_canonical_type": want_type,
        "route_steps": [],
        "route_hash": "sha256:" + "0" * 64,
        "step_count": 0,
        "unmet_types": list(unmet_types),
        "nearest_producers": list(nearest),
        "candidate": True,
        "serves_truth": False,
    }
