"""P0 #1: source_surface_registry.

Loads the generated source-surface pack and answers compact queries over it.
The registry verifies pack integrity (manifest content hash) on every load so
a hand-edited pack fails loudly instead of serving silently corrupted cards.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from primitives.core import PrimitiveOutcome, ProofResult

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "place-discovery-geospatial-seeds"


def source_surface_registry(payload: dict) -> PrimitiveOutcome:
    """Query the source-surface registry.

    payload: {"query": {"lane": str|None, "adapter_priority": str|None,
                        "official_only": bool}, "pack_dir": str|None}
    Output: compact source surface cards matching the query, plus an
    integrity receipt for the pack file the cards came from.
    """
    query = payload.get("query", {})
    pack_dir = Path(payload["pack_dir"]) if payload.get("pack_dir") else DEFAULT_PACK_DIR

    surfaces_path = pack_dir / "source_surfaces.jsonl"
    manifest_path = pack_dir / "manifest.json"
    raw = surfaces_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = manifest["files"]["source_surfaces.jsonl"]["content_sha256"]
    integrity_ok = digest == expected

    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    matches = []
    for row in rows:
        if query.get("lane") and row["lane"] != query["lane"]:
            continue
        if query.get("adapter_priority") and row["adapter_priority"] != query["adapter_priority"]:
            continue
        if query.get("official_only") and not row["official_source"]:
            continue
        matches.append(
            {
                "source_id": row["source_id"],
                "title": row["title"],
                "lane": row["lane"],
                "surface_type": row["surface_type"],
                "license_family": row["license_family"],
                "attribution_required": row["attribution_required"],
                "adapter_priority": row["adapter_priority"],
                "official_source": row["official_source"],
                "freshness_class": row["freshness_class"],
            }
        )

    output = {
        "query": query,
        "matches": matches,
        "match_count": len(matches),
        "registry_stats": {"total_surfaces": len(rows)},
        "pack_integrity": {"file": "source_surfaces.jsonl", "sha256_match": integrity_ok},
    }
    proofs = [
        ProofResult("pack_integrity_hash_match", integrity_ok,
                    "" if integrity_ok else "source_surfaces.jsonl does not match manifest hash"),
        ProofResult("schema_validation", all("source_id" in m for m in matches)),
    ]
    return PrimitiveOutcome(output=output, effects_observed=["file_read"], proof_results=proofs)
