"""CandidateBundle search over the place-discovery primitive pack.

This is the "compact edge search" stage of the route-market loop: a natural-
language task intent goes in, a schema-valid CandidateBundle comes out -
never a single overconfident answer. Deterministic, stdlib-only hybrid
matcher: lexical IDF scoring over title/blackbox/lane/edge tokens with a
group-first boost (group cards hide member routes behind one visible edge,
so they are the preferred compression target).

Retrieval quality is MEASURED, not assumed: see
scripts/evaluate_candidate_search.py, which scores this matcher against all
generated benchmark task demands using their primitive_demands as ground
truth. Bundles remain candidate material (candidate=true, serves_truth=false).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "place-discovery-geospatial-seeds"
NEGATIVE_MEMORY_SOURCES = [
    REPO_ROOT / "examples" / "core_objects" / "negative_memory.json",
]

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in",
    "into", "is", "it", "of", "on", "or", "that", "the", "this", "to",
    "with", "all", "any", "each", "their", "them", "then", "these", "those",
}

_CAMEL_RE = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|[0-9]+")
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _split_camel(text: str) -> list[str]:
    return [m.group(0).lower() for m in _CAMEL_RE.finditer(text)]


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for raw in re.split(r"[^A-Za-z0-9]+", text):
        if not raw:
            continue
        if raw.lower() == raw or raw.upper() == raw:
            tokens.extend(t for t in _TOKEN_RE.findall(raw.lower()))
        else:
            tokens.extend(_split_camel(raw))
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class PackSearchIndex:
    """In-memory lexical index over primitive cards and groups."""

    def __init__(self, pack_dir: Path | None = None):
        pack_dir = pack_dir or DEFAULT_PACK_DIR
        cards = _load_jsonl(pack_dir / "primitive_cards.jsonl")
        groups = _load_jsonl(pack_dir / "primitive_groups.jsonl")

        self.docs: dict[str, dict] = {}
        self.group_members: dict[str, list[str]] = {}
        for card in cards:
            self.docs[card["primitive_id"]] = {
                "id": card["primitive_id"],
                "kind": "primitive",
                "tokens": self._doc_tokens(card),
                "title": card["title"],
            }
        for grp in groups:
            self.docs[grp["group_id"]] = {
                "id": grp["group_id"],
                "kind": "group",
                "tokens": self._doc_tokens(grp, is_group=True),
                "title": grp["title"],
            }
            self.group_members[grp["group_id"]] = list(grp["member_primitive_refs"])

        self.idf: dict[str, float] = {}
        n_docs = len(self.docs)
        df: dict[str, int] = {}
        for doc in self.docs.values():
            for tok in set(doc["tokens"]):
                df[tok] = df.get(tok, 0) + 1
        for tok, count in df.items():
            self.idf[tok] = math.log((n_docs + 1) / (count + 0.5))

    @staticmethod
    def _doc_tokens(row: dict, is_group: bool = False) -> list[str]:
        parts = [
            row["title"],
            row["blackbox"]["does"],
            row["lane"].replace("_", " "),
            row["input_edge"],
            row["output_edge"],
        ]
        if is_group:
            parts.extend(row.get("hidden_member_edges", []))
        else:
            parts.append(row["primitive_id"].split(".")[-1].replace("_", " "))
        tokens: list[str] = []
        for part in parts:
            tokens.extend(tokenize(part))
        return tokens

    def score(self, query: str) -> list[tuple[str, float]]:
        q_tokens = set(tokenize(query))
        scored: list[tuple[str, float]] = []
        for doc_id, doc in self.docs.items():
            doc_tok_counts: dict[str, int] = {}
            for t in doc["tokens"]:
                doc_tok_counts[t] = doc_tok_counts.get(t, 0) + 1
            overlap = q_tokens & set(doc_tok_counts)
            if not overlap:
                continue
            raw = sum(self.idf.get(t, 0.0) * (1.0 + math.log(doc_tok_counts[t])) for t in overlap)
            norm = raw / math.sqrt(len(doc["tokens"]) + 1)
            if doc["kind"] == "group":
                norm *= 1.25  # group-first: one visible edge beats N member cards
            scored.append((doc_id, norm))
        scored.sort(key=lambda x: (-x[1], x[0]))
        return scored


def _load_negative_memory() -> list[dict]:
    records: list[dict] = []
    for path in NEGATIVE_MEMORY_SOURCES:
        if path.exists():
            records.append(json.loads(path.read_text(encoding="utf-8")))
    runs_root = REPO_ROOT / "benchmarks" / "runs"
    if runs_root.exists():
        for negmem_file in sorted(runs_root.glob("*/negative_memory.jsonl")):
            records.extend(_load_jsonl(negmem_file))
    return records


_INDEX_CACHE: dict[str, PackSearchIndex] = {}


def candidate_bundle_search(query_intent: str, top_k: int = 10,
                            pack_dir: Path | None = None) -> dict:
    """Return a schema-valid CandidateBundle for a natural-language intent."""
    cache_key = str(pack_dir or DEFAULT_PACK_DIR)
    if cache_key not in _INDEX_CACHE:
        _INDEX_CACHE[cache_key] = PackSearchIndex(pack_dir)
    index = _INDEX_CACHE[cache_key]

    scored = index.score(query_intent)[:top_k]
    ids = [doc_id for doc_id, _ in scored]
    exact = ids[:3]
    near = ids[3:]

    warnings: list[str] = []
    candidate_set = set(ids)
    for group_id in ids:
        candidate_set.update(index.group_members.get(group_id, []))
    for record in _load_negative_memory():
        if record.get("resolution_status") == "fixed":
            continue
        if candidate_set & set(record.get("affected_primitive_ids", [])):
            warnings.append(record["memory_id"])

    top_lines = "; ".join(f"{doc_id}={score:.3f}" for doc_id, score in scored[:5])
    bundle = {
        "record_type": "candidate_bundle",
        "bundle_id": "bundle:place_discovery." + hashlib.sha256(
            query_intent.encode("utf-8")).hexdigest()[:16],
        "query_intent": query_intent,
        "exact_matches": exact,
        "near_matches": near,
        "template_candidates": [],
        "mutator_candidates": [],
        "negative_memory_warnings": sorted(set(warnings)),
        "fallback_options": [
            "source_slice_escalation",
            "bounded_model_plan_delta",
            "human_review_packet",
        ],
        "ranking_explanation": (
            "lexical idf over title/blackbox/lane/edge tokens with 1.25x "
            f"group-first boost; top scores: {top_lines}"),
        "version": "0.1.0",
        "candidate": True,
        "serves_truth": False,
    }
    return bundle


def bundle_covered_primitives(bundle: dict, pack_dir: Path | None = None) -> set[str]:
    """All primitive ids reachable from a bundle: direct hits plus members of
    any group in the bundle (groups hide member routes, so a group hit covers
    its members)."""
    cache_key = str(pack_dir or DEFAULT_PACK_DIR)
    if cache_key not in _INDEX_CACHE:
        _INDEX_CACHE[cache_key] = PackSearchIndex(pack_dir)
    index = _INDEX_CACHE[cache_key]
    covered: set[str] = set()
    for doc_id in bundle["exact_matches"] + bundle["near_matches"]:
        covered.add(doc_id)
        covered.update(index.group_members.get(doc_id, []))
    return covered
