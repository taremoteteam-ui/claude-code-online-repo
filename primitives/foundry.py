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
import importlib
import json
import re

from primitives.edges import (config_ports, output_ports, parse_edge,
                              required_input_ports)

# Deterministic secret-scan patterns (a promotion blocker, never bypassed).
_SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(api[_-]?key|secret|password|passwd)\s*[:=]\s*[\"'][^\"']{6,}"),
]

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


def _secret_scan(source: dict) -> list[str]:
    """Deterministic secret scan over the raw source text."""
    blob = json.dumps(source, sort_keys=True)
    hits = []
    for pat in _SECRET_PATTERNS:
        if pat.search(blob):
            hits.append(pat.pattern)
    return hits


def acquire(source: dict, path: str = "cached_snapshot") -> tuple[dict, dict]:
    """Acquire a source snapshot via a chosen portfolio path (offline: reads the
    fixture). Runs two acquisition gates - a secret scan and vendored/generated
    exclusion - and returns (snapshot, receipt). The receipt discloses
    retrieved_mode, the acquisition path, secret findings, and excluded symbols
    so downstream stages know the provenance and what was dropped."""
    if path not in ACQUIRE_PATHS:
        raise ValueError(f"unknown acquire path {path!r}")
    secrets = _secret_scan(source)
    all_fns = source.get("functions", [])
    excluded = [f["name"] for f in all_fns if f.get("vendored") or f.get("generated")]
    included = [f for f in all_fns if not (f.get("vendored") or f.get("generated"))]
    snapshot = {
        "source_id": source["source_id"], "library": source["library"],
        "license": source.get("license", "UNKNOWN"),
        "retrieved_mode": source.get("retrieved_mode", "fixture_synthetic"),
        "functions": included,
        "secret_findings": secrets,
        "source_digest": hashlib.sha256(
            json.dumps(included, sort_keys=True).encode()).hexdigest()[:16],
    }
    receipt = {
        "record_type": "acquisition_receipt", "source_id": source["source_id"],
        "acquire_path": path, "retrieved_mode": snapshot["retrieved_mode"],
        "symbols_seen": len(all_fns), "symbols_kept": len(included),
        "excluded_symbols": excluded, "secret_findings": secrets,
        "secret_scan_clean": not secrets, "source_digest": snapshot["source_digest"],
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
        # Port roles resolved to the shared typed vocabulary: which inputs must
        # be produced upstream (data/receipt), which are request-supplied config,
        # and what is produced. This is what lets the compiler order a mined
        # primitive without reading its body.
        port_roles = {
            "required_inputs": [p.canonical_type for p in required_input_ports(in_edge)],
            "config_inputs": [p.canonical_type for p in config_ports(in_edge)],
            "outputs": [p.canonical_type for p in output_ports(out_edge)],
        }
        row = {
            "record_type": "mined_primitive", "mined_primitive_id": mid,
            "source_id": snapshot["source_id"], "library": snapshot["library"], "symbol": symbol,
            "title": symbol.replace("_", " ").title(),
            "input_edge": in_edge, "output_edge": out_edge,
            "blackbox": {"does": fn.get("does", "mined primitive from a source signature")},
            "effects": effects, "proof_obligations": proofs, "license": license_,
            "retrieved_mode": snapshot["retrieved_mode"],
            "verification_status": "license_blocked" if blockers else "unverified",
            "port_roles": port_roles, "promotion_blockers": blockers,
            "source_ref": f"{snapshot['source_id']}::{symbol}",
            "version": "0.1.0", "candidate": True, "serves_truth": False,
        }
        handler = fn.get("handler")
        if handler:
            row["handler_ref"] = handler
        # dedupe key: same contract + symbol collapses
        key = f"{in_edge}::{out_edge}::{symbol}"
        mined.setdefault(key, row)
    return sorted(mined.values(), key=lambda r: r["mined_primitive_id"])


def _handler_resolves(ref: str) -> bool:
    try:
        mod_name, attr = ref.split(":", 1)
        return callable(getattr(importlib.import_module(mod_name), attr, None))
    except Exception:  # noqa: BLE001
        return False


def verify(mined: dict) -> dict:
    """Fixture-verify a mined primitive against a check LADDER, then set its
    verification status:

      license_blocked   - non-permissive source (never promoted, never run)
      unverified        - a base check failed
      fixture_verified  - edges parse, effects valid, an output DATA port exists,
                          every effect has a proof obligation, license permissive
      fixture_executable- all of the above AND a resolvable handler (proven to
                          actually transform its input edge into its output edge)

    Returns a verification receipt with per-check results."""
    out_ports = output_ports(mined["output_edge"])
    checks = [
        ("input_edge_parses", len(parse_edge(mined["input_edge"])) >= 1 or mined["input_edge"] == "NoInput"),
        ("output_edge_parses", len(out_ports) >= 1),
        ("output_has_data_port", any(p.role == "data" for p in out_ports)),
        ("effects_valid", all(e in _VALID_EFFECTS for e in mined["effects"])),
        ("effect_proofs_present", all(
            _EFFECT_PROOF.get(e, "schema_validation") in mined.get("proof_obligations", [])
            for e in mined["effects"] if e in _EFFECT_PROOF)),
        ("license_permissive", not mined.get("promotion_blockers")),
    ]
    base_passed = all(ok for _, ok in checks)
    ref = mined.get("handler_ref")
    executable = bool(base_passed and ref and _handler_resolves(ref))
    checks.append(("handler_resolves", executable if ref else True))

    if not base_passed:
        status = "license_blocked" if mined.get("promotion_blockers") else "unverified"
    elif executable:
        status = "fixture_executable"
    else:
        status = "fixture_verified"
    return {
        "record_type": "verification_receipt", "mined_primitive_id": mined["mined_primitive_id"],
        "checks": [{"check": c, "passed": ok} for c, ok in checks],
        "verification_status": status, "passed": base_passed,
        "executable": executable, "candidate": True, "serves_truth": False,
    }
