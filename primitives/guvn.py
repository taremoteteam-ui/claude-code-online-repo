"""Globally Unique Variable Name (GUVN) system + deterministic tracer.

The law: every meaningful data artifact in the system carries a GLOBALLY UNIQUE
NAME (a GUN). Because names are unique, the data-flow map is unambiguous *without*
type inference or call-graph analysis: wherever a GUN is produced and wherever it
is consumed, those are the same artifact - the names ARE the edges. This is the
typed-port idea (primitives/edges.py) generalized from primitive boundaries to
every named artifact, and it is what makes a deterministic, whole-repo code map
cheap to build and stable to diff.

Grammar (version-free; versions live in metadata, never in the name):

    <lane>.<component>.<artifact>[.<qualifier>...]

lowercase snake segments, dot-separated, at least two segments. A GUN denotes ONE
artifact semantics system-wide. Two units may produce the SAME GUN only when they
emit the same substitutable contract - that is not a collision, it is a
multiple-path artifact (the seam where GUVN meets multiple-path development).

A unit (function/step/service) declares what it consumes and produces via GUNs.
`build_code_map` turns a set of unit declarations into a deterministic code map
(nodes = units + artifacts, edges = consume/produce), classifies every artifact as
source / internal / sink / multi-path, and `lint` reports the ways the uniqueness
law can be broken. Pure and deterministic; stdlib only; candidate material.
"""

from __future__ import annotations

import hashlib
import json
import re

_GUN_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*(\.[a-z][a-z0-9]*(_[a-z0-9]+)*){1,}$")

# Registry the @unit decorator populates. Keyed by unit GUN so a duplicate
# declaration is visible to the linter rather than silently overwritten.
REGISTRY: dict[str, dict] = {}


def is_valid_gun(name: str) -> bool:
    """True if name matches the GUN grammar (>=2 lowercase snake segments)."""
    return isinstance(name, str) and bool(_GUN_RE.match(name))


def unit(gun: str, consumes: list[str] | None = None,
         produces: list[str] | None = None, effects: list[str] | None = None):
    """Decorator: declare a callable as a GUVN unit. Records the unit's own GUN
    and the GUNs it consumes/produces into REGISTRY (append-only per name so
    collisions are lintable). Does not alter the wrapped callable."""
    record = {
        "gun": gun, "kind": "unit",
        "consumes": list(consumes or []), "produces": list(produces or []),
        "effects": list(effects or ["none"]),
    }

    def deco(fn):
        record["module"] = getattr(fn, "__module__", "")
        record["qualname"] = getattr(fn, "__qualname__", getattr(fn, "__name__", ""))
        REGISTRY.setdefault(gun, [])
        REGISTRY[gun].append(record)
        fn.__guvn__ = record
        return fn

    return deco


def registered_units() -> list[dict]:
    """Flatten the registry to a deterministic unit list (sorted by gun then qualname)."""
    out = [r for records in REGISTRY.values() for r in records]
    return sorted(out, key=lambda r: (r["gun"], r.get("qualname", "")))


def build_code_map(units: list[dict]) -> dict:
    """Deterministic code map from unit declarations.

    Nodes: every unit GUN and every artifact GUN referenced. Edges: (artifact ->
    unit) for each consume and (unit -> artifact) for each produce. Artifacts are
    classified: 'source' (consumed, never produced = external input), 'sink'
    (produced, never consumed = terminal output), 'internal' (both), and
    'multi_path' (produced by >1 unit = substitutable paths). Includes a content
    hash so the map diffs cleanly."""
    unit_guns = sorted({u["gun"] for u in units})
    producers: dict[str, list[str]] = {}
    consumers: dict[str, list[str]] = {}
    edges = []
    artifacts: set[str] = set()
    for u in sorted(units, key=lambda r: r["gun"]):
        for c in sorted(u["consumes"]):
            artifacts.add(c)
            consumers.setdefault(c, []).append(u["gun"])
            edges.append({"from": c, "to": u["gun"], "kind": "consume"})
        for p in sorted(u["produces"]):
            artifacts.add(p)
            producers.setdefault(p, []).append(u["gun"])
            edges.append({"from": u["gun"], "to": p, "kind": "produce"})

    classified = {}
    for a in sorted(artifacts):
        made = producers.get(a, [])
        used = consumers.get(a, [])
        if len(made) > 1:
            kind = "multi_path"
        elif not made:
            kind = "source"
        elif not used:
            kind = "sink"
        else:
            kind = "internal"
        classified[a] = {"kind": kind, "produced_by": sorted(made), "consumed_by": sorted(used)}

    edges.sort(key=lambda e: (e["kind"], e["from"], e["to"]))
    payload = {"units": unit_guns, "artifacts": classified, "edges": edges}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return {
        "record_type": "guvn_code_map",
        "unit_count": len(unit_guns), "artifact_count": len(classified),
        "edge_count": len(edges),
        "sources": [a for a, m in classified.items() if m["kind"] == "source"],
        "sinks": [a for a, m in classified.items() if m["kind"] == "sink"],
        "multi_path_artifacts": [a for a, m in classified.items() if m["kind"] == "multi_path"],
        "units": unit_guns, "artifacts": classified, "edges": edges,
        "content_sha256": digest, "candidate": True, "serves_truth": False,
    }


def lint(units: list[dict]) -> dict:
    """Report violations of the GUVN law. Errors: an invalid GUN grammar; a GUN
    used both as a unit id and as an artifact (name means two things); a unit GUN
    declared by two different qualnames (duplicate name). Info: multi-producer
    artifacts (allowed, but flagged for review that they are truly substitutable)."""
    errors, info = [], []
    unit_guns = {u["gun"] for u in units}
    artifact_guns = {g for u in units for g in u["consumes"] + u["produces"]}

    for u in units:
        for g in [u["gun"], *u["consumes"], *u["produces"]]:
            if not is_valid_gun(g):
                errors.append(f"invalid GUN grammar: {g!r} (in unit {u['gun']})")

    # a name may not be both a unit and an artifact
    for clash in sorted(unit_guns & artifact_guns):
        errors.append(f"name used as both a unit and an artifact: {clash}")

    # duplicate unit declarations (same GUN, different qualname)
    by_gun: dict[str, set] = {}
    for u in units:
        by_gun.setdefault(u["gun"], set()).add(u.get("qualname", ""))
    for gun, names in sorted(by_gun.items()):
        if len(names) > 1:
            errors.append(f"duplicate unit GUN {gun} declared by {sorted(names)}")

    producers: dict[str, set] = {}
    for u in units:
        for p in u["produces"]:
            producers.setdefault(p, set()).add(u["gun"])
    for a, made in sorted(producers.items()):
        if len(made) > 1:
            info.append(f"multi-path artifact {a} produced by {sorted(made)} - "
                        f"confirm the producers are contract-substitutable")

    return {"record_type": "guvn_lint", "ok": not errors,
            "errors": sorted(errors), "info": sorted(info),
            "candidate": True, "serves_truth": False}


def render_mermaid(code_map: dict) -> str:
    """Render the code map as a Mermaid flowchart (units as rects, artifacts as
    rounded nodes). Deterministic node ordering."""
    lines = ["flowchart LR"]

    def nid(gun: str) -> str:
        return "n_" + re.sub(r"[^a-z0-9]", "_", gun)

    for u in code_map["units"]:
        lines.append(f'  {nid(u)}["{u}"]')
    for a, meta in code_map["artifacts"].items():
        shape = f'(["{a}"])' if meta["kind"] in ("source", "sink") else f'("{a}")'
        lines.append(f'  {nid(a)}{shape}')
    for e in code_map["edges"]:
        lines.append(f"  {nid(e['from'])} --> {nid(e['to'])}")
    return "\n".join(lines)
