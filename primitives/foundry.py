"""The primitive foundry: the ingestion -> primitive-forming pipeline.

Covers the acquisition and formation stages of the lifecycle
(scrape/acquire -> ingest/form -> verify) that turn a source into edge-typed
candidate primitives ready to STORE and USE. Deterministic and offline: this
workspace has restricted outbound network, so acquisition runs against SYNTHETIC
fixture sources (labeled fixture_synthetic) via an acquisition PORTFOLIO - the
same shape a live miner uses, with LiveTransport swapped in where the network
policy allows. Nothing formed here is source-backed; every mined primitive stays
candidate=true / serves_truth=false until a live source ref + receipts attach.

Stages:
  acquire(source, path)  -> (snapshot, acquisition_receipt)   [scraping]
  form(snapshot)         -> [mined_primitive, ...]            [primitive-forming]
  verify(mined)          -> verification_receipt              [use-readiness gate]

The load-bearing form step edge-TYPES each mined signature to the shared port
vocabulary (primitives/edges.py) so a mined primitive composes on the same
capability graph as the seeded lanes - a mined `def f(x: PointFeatureCollection)
-> EntityRecordSet` chains after `parse_geojson` without anyone reading its body.
Stdlib only.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from primitives.edges import parse_edge

# Acquisition portfolio: the ordered ladder a live miner climbs. Offline, each
# rung resolves to reading the fixture snapshot; the CHOSEN rung is recorded so
# the receipt is honest about how the source was obtained.
ACQUIRE_PATHS = ["cached_snapshot", "structured_api", "ast_parse",
                 "html_fetch_parse", "headless_browser"]

# Permissive licenses whose formed primitives may become use-ready. Anything
# else is a promotion blocker (recorded, never bypassed).
ALLOWED_LICENSES = {"MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause", "ISC",
                    "MPL-2.0", "Unlicense", "CC0-1.0"}

_VALID_EFFECTS = {"none", "file_read", "file_write", "network_read", "network_write",
                  "database_read", "database_write", "artifact_write", "secret_read",
                  "model_call", "human_review"}

_EFFECT_PROOF = {
    "network_read": "source_snapshot_receipt",
    "network_write": "idempotency_test",
    "file_write": "roundtrip_test",
    "database_write": "idempotency_test",
    "model_call": "human_review",
}


def acquire(source: dict, path: str = "cached_snapshot") -> tuple[dict, dict]:
    """Acquire a source snapshot via a chosen portfolio path (offline: reads the
    fixture). Returns (snapshot, receipt). The receipt discloses retrieved_mode
    and the acquisition path so downstream stages know the provenance."""
    if path not in ACQUIRE_PATHS:
        raise ValueError(f"unknown acquire path {path!r}")
    snapshot = {
        "source_id": source["source_id"], "library": source["library"],
        "license": source.get("license", "UNKNOWN"),
        "retrieved_mode": source.get("retrieved_mode", "fixture_synthetic"),
        "functions": source.get("functions", []),
        "source_digest": hashlib.sha256(
            json.dumps(source.get("functions", []), sort_keys=True).encode()).hexdigest()[:16],
    }
    receipt = {
        "record_type": "acquisition_receipt", "source_id": source["source_id"],
        "acquire_path": path, "retrieved_mode": snapshot["retrieved_mode"],
        "symbols_seen": len(snapshot["functions"]), "source_digest": snapshot["source_digest"],
        "candidate": True, "serves_truth": False,
    }
    return snapshot, receipt


def _edge_from_params(params: list[dict]) -> str:
    ports = [p["type"] for p in params if p.get("type")]
    return "+".join(ports) if ports else "NoInput"


def form(snapshot: dict) -> list[dict]:
    """Form edge-typed candidate primitives from an acquired snapshot. Each
    function signature becomes a mined_primitive; ports are typed to the shared
    vocabulary. License is gated: a non-permissive source's primitives are
    recorded license_blocked. Deduped by (input_edge, output_edge, symbol)."""
    license_ = snapshot.get("license", "UNKNOWN")
    licensed_ok = license_ in ALLOWED_LICENSES
    mined: dict[str, dict] = {}
    for fn in snapshot["functions"]:
        symbol = fn["name"]
        in_edge = _edge_from_params(fn.get("params", []))
        out_edge = fn.get("returns", "Unit")
        effects = [e for e in fn.get("effects", ["none"]) if e in _VALID_EFFECTS] or ["none"]
        proofs = ["schema_validation"]
        for e in effects:
            if e in _EFFECT_PROOF and _EFFECT_PROOF[e] not in proofs:
                proofs.append(_EFFECT_PROOF[e])
        if len(proofs) < 2:
            proofs.append("determinism_test")
        blockers = [] if licensed_ok else [f"non_permissive_license:{license_}"]
        lib = snapshot["library"].replace("-", "_").lower()
        mid = f"mined:{lib}.{symbol.lower()}"
        row = {
            "record_type": "mined_primitive", "mined_primitive_id": mid,
            "source_id": snapshot["source_id"], "library": snapshot["library"], "symbol": symbol,
            "title": symbol.replace("_", " ").title(),
            "input_edge": in_edge, "output_edge": out_edge,
            "blackbox": {"does": fn.get("does", "mined primitive from a source signature")},
            "effects": effects, "proof_obligations": proofs, "license": license_,
            "retrieved_mode": snapshot["retrieved_mode"],
            "verification_status": "license_blocked" if blockers else "unverified",
            "promotion_blockers": blockers,
            "source_ref": f"{snapshot['source_id']}::{symbol}",
            "version": "0.1.0", "candidate": True, "serves_truth": False,
        }
        # dedupe key: same contract + symbol collapses
        key = f"{in_edge}::{out_edge}::{symbol}"
        mined.setdefault(key, row)
    return sorted(mined.values(), key=lambda r: r["mined_primitive_id"])


def verify(mined: dict) -> dict:
    """Fixture-verify a mined primitive: its edges must parse to real typed
    ports, its effects must be valid, and it must not be license-blocked. Passing
    flips verification_status to fixture_verified (still candidate). Returns a
    verification receipt with per-check results."""
    checks = []
    in_ports = parse_edge(mined["input_edge"])
    out_ports = parse_edge(mined["output_edge"])
    checks.append(("input_edge_parses", len(in_ports) >= 1 or mined["input_edge"] == "NoInput"))
    checks.append(("output_edge_parses", len(out_ports) >= 1))
    checks.append(("effects_valid", all(e in _VALID_EFFECTS for e in mined["effects"])))
    checks.append(("license_permissive", not mined.get("promotion_blockers")))
    passed = all(ok for _, ok in checks)
    return {
        "record_type": "verification_receipt", "mined_primitive_id": mined["mined_primitive_id"],
        "checks": [{"check": c, "passed": ok} for c, ok in checks],
        "verification_status": "fixture_verified" if passed else mined["verification_status"],
        "passed": passed, "candidate": True, "serves_truth": False,
    }
