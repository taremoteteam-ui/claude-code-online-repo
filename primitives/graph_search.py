"""Universal, lane-agnostic retrieval over the WHOLE capability graph.

Why this exists: primitives/search.py (PackSearchIndex) is hard-coupled to the
place-discovery pack row schema and indexes ~50 of the 2,867 graph nodes (1.7%).
A coding-lane or warehouse prompt cannot retrieve the primitives that solve it,
because those lanes are not in its corpus. This module indexes EVERY
capability_graph node uniformly, and adds the two matching planes the flat
lexical index lacks:

  1. Lexical plane  - IDF over node title / id tail / lane / edge port names.
  2. Typed-edge plane (blocking keys) - producers_by_type and consumers_by_type
     indexes so a query that names a wanted output type (or held inputs) PRUNES
     the universe to the few nodes that can actually produce/consume it in one
     hop, then reranks lexically within that block. This is the columnar
     "prune by key, rerank by score" path the flat index cannot do.

Retrieval fuses the two planes: a node that both produces the wanted type AND
lexically matches the intent ranks above a node that only does one. The typed
plane is edge-truth (the same canonical types the route compiler composes on),
so it is precise where lexical is fuzzy, and lexical is recall where types are
absent. Deterministic, stdlib-only. Results are candidate material.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from primitives.edges import canonical_type
from primitives.search import tokenize

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GRAPH = (REPO_ROOT / "catalog" / "knowledge-packs" / "data"
                 / "capability-graph" / "capability_graph.jsonl")


def _node_tokens(node: dict) -> list[str]:
    parts = [node.get("title", ""), node["node_id"].split(":")[-1].replace(".", " "),
             node.get("lane", "").replace("_", " "),
             node.get("input_edge", ""), node.get("output_edge", "")]
    toks: list[str] = []
    for p in parts:
        toks.extend(tokenize(p))
    return toks


class GraphSearchIndex:
    """Lexical + typed-edge index over every capability-graph node."""

    def __init__(self, graph_path: Path | None = None, nodes: list[dict] | None = None):
        if nodes is None:
            graph_path = graph_path or DEFAULT_GRAPH
            nodes = [json.loads(l) for l in graph_path.read_text(encoding="utf-8").splitlines()
                     if l.strip()]
        self.nodes = {n["node_id"]: n for n in nodes}
        self.tokens = {nid: _node_tokens(n) for nid, n in self.nodes.items()}

        # Typed-edge blocking keys.
        self.producers_by_type: dict[str, list[str]] = {}
        self.consumers_by_type: dict[str, list[str]] = {}
        for nid, n in self.nodes.items():
            for op in n.get("output_ports", []):
                self.producers_by_type.setdefault(op["canonical_type"], []).append(nid)
            for ip in n.get("required_input_ports", []):
                self.consumers_by_type.setdefault(ip["canonical_type"], []).append(nid)

        # IDF over the universe.
        df: dict[str, int] = {}
        for toks in self.tokens.values():
            for t in set(toks):
                df[t] = df.get(t, 0) + 1
        n_docs = max(len(self.nodes), 1)
        self.idf = {t: math.log((n_docs + 1) / (c + 0.5)) for t, c in df.items()}

    def _lexical(self, query: str) -> dict[str, float]:
        q = set(tokenize(query))
        out: dict[str, float] = {}
        for nid, toks in self.tokens.items():
            counts: dict[str, int] = {}
            for t in toks:
                counts[t] = counts.get(t, 0) + 1
            overlap = q & set(counts)
            if not overlap:
                continue
            raw = sum(self.idf.get(t, 0.0) * (1.0 + math.log(counts[t])) for t in overlap)
            out[nid] = raw / math.sqrt(len(toks) + 1)
        return out

    def search(self, query: str, want: str | None = None, have: list[str] | None = None,
               top_k: int = 10) -> list[dict]:
        """Rank nodes for a natural-language intent, optionally focused by a
        wanted output type and/or held input types (the typed-edge plane).

        Fusion: lexical score, plus a typed bonus when the node produces `want`
        (blocking key hit) and a smaller bonus per held input type it consumes.
        Every hit discloses which planes fired.
        """
        lex = self._lexical(query)
        want_ct = canonical_type(want) if want else None
        have_cts = {canonical_type(h) for h in (have or [])}

        producers = set(self.producers_by_type.get(want_ct, [])) if want_ct else set()
        # Candidate pool: lexical hits UNION typed producers of the wanted type.
        pool = set(lex) | producers
        results = []
        for nid in pool:
            n = self.nodes[nid]
            planes = []
            score = 0.0
            if nid in lex:
                score += lex[nid]
                planes.append("lexical")
            if want_ct and nid in producers:
                score += 2.0  # edge-truth: this node actually produces the target type
                planes.append("produces_want")
            if have_cts:
                consumed = {ip["canonical_type"] for ip in n.get("required_input_ports", [])}
                if consumed & have_cts:
                    score += 0.5 * len(consumed & have_cts)
                    planes.append("consumes_have")
            results.append({"node_id": nid, "lane": n.get("lane"), "kind": n.get("kind"),
                            "title": n.get("title"), "score": round(score, 4),
                            "planes": planes, "output_edge": n.get("output_edge")})
        results.sort(key=lambda r: (-r["score"], r["node_id"]))
        return results[:top_k]

    def coverage(self) -> int:
        return len(self.nodes)
