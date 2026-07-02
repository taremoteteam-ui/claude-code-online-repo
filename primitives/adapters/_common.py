"""Shared helpers for source adapters. Stdlib only.

These helpers keep the adapters honest and uniform:

- ``effects_for`` maps the transport mode to the observed effect list
  (``live_network`` -> ``["network_read"]``, ``fixture_offline`` ->
  ``["file_read"]``) and refuses unknown modes.
- ``build_snapshot_meta`` builds the snapshot metadata entry every adapter
  places in its output, including ``retrieved_mode`` so downstream evidence
  bundles disclose whether data came from a live endpoint or a synthetic
  offline fixture.
"""

from __future__ import annotations

from primitives.core import ProofResult

_EFFECTS_BY_MODE = {
    "live_network": ["network_read"],
    "fixture_offline": ["file_read"],
}


def effects_for(transport) -> list[str]:
    """Observed-effect list for a transport; raises on unknown modes."""
    mode = getattr(transport, "mode", None)
    if mode not in _EFFECTS_BY_MODE:
        raise ValueError(f"unknown transport mode: {mode!r}")
    return list(_EFFECTS_BY_MODE[mode])


def build_snapshot_meta(
    snapshot_id: str,
    source_id: str,
    license_family: str,
    attribution: str,
    transport,
) -> dict:
    return {
        "snapshot_id": snapshot_id,
        "source_id": source_id,
        "license_family": license_family,
        "attribution": attribution,
        "retrieved_mode": transport.mode,
    }


def require_fields(
    items: list, required: list[str], proof_name: str = "schema_validation"
) -> ProofResult:
    """Proof that every item is a dict carrying every required field."""
    problems: list[str] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            problems.append(f"[{i}] not an object")
            continue
        for key in required:
            if key not in item:
                problems.append(f"[{i}].{key} missing")
    if problems:
        detail = "; ".join(problems[:5])
        if len(problems) > 5:
            detail += f"; +{len(problems) - 5} more"
        return ProofResult(proof_name, False, detail)
    return ProofResult(
        proof_name, True, f"{len(items)} items carry all required fields"
    )


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def coordinates_in_range(
    records: list[dict],
    lat_key: str = "lat",
    lon_key: str = "lon",
    proof_name: str = "coordinates_in_range",
) -> ProofResult:
    """Proof that every record has numeric lat/lon inside WGS84 bounds."""
    bad: list[str] = []
    for rec in records:
        lat = rec.get(lat_key)
        lon = rec.get(lon_key)
        if (
            not _is_number(lat)
            or not _is_number(lon)
            or not (-90.0 <= lat <= 90.0)
            or not (-180.0 <= lon <= 180.0)
        ):
            bad.append(str(rec.get("record_id", "?")))
    if bad:
        return ProofResult(proof_name, False, "out of range: " + ", ".join(bad[:5]))
    return ProofResult(
        proof_name, True, f"{len(records)} records within WGS84 bounds"
    )
