"""Executable handlers for decision paths that have a measurable runtime.

Each retrieval-plane handler has the uniform signature
``(index: GraphSearchIndex, query: str, want: str | None) -> list[str]`` and
returns ranked node_ids, so the decision-engine demo can run every plane over
the same probes and let the ledger decide which plane the data prefers. The
remix handlers reference the real mutator / adapter callables. Handlers are
named by execution_path.handler_ref and resolved by the pack checker. Stdlib
only; deterministic.
"""

from __future__ import annotations

from primitives.type_adapters import webhook_request_to_provider_webhook  # noqa: F401
from primitives.mutators import field_rename  # noqa: F401


def retrieval_lexical(index, query: str, want: str | None) -> list[str]:
    """Pure lexical plane: ignore the wanted type entirely."""
    return [r["node_id"] for r in index.search(query, want=None, top_k=5)]


def retrieval_typed_edge(index, query: str, want: str | None) -> list[str]:
    """Pure typed-edge plane: the producers of the wanted type, edge-truth only,
    with NO lexical ranking (deterministic by id). Precise membership, weak
    ranking - which is exactly why it is a plane, not the whole answer."""
    from primitives.edges import canonical_type
    if not want:
        return []
    ct = canonical_type(want)
    return sorted(index.producers_by_type.get(ct, []))[:5]


def retrieval_fused(index, query: str, want: str | None) -> list[str]:
    """Fused plane: lexical + typed-edge blocking, the two-plane search."""
    return [r["node_id"] for r in index.search(query, want=want, top_k=5)]
