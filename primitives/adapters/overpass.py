"""OSM Overpass bounded POI query (P0 source adapter).

Mimics the shape of Overpass API JSON output for a bounded node query.
OpenStreetMap-shaped data carries MANDATORY attribution metadata: license
family ``odbl`` and an explicit contributor credit, and every record is
flagged ``attribution_required``.

Fixtures are SYNTHETIC; ``retrieved_mode`` is propagated into
``snapshot_meta`` so downstream evidence bundles disclose it.
Stdlib only.
"""

from __future__ import annotations

from primitives.adapters._common import build_snapshot_meta, effects_for
from primitives.core import PrimitiveOutcome, ProofResult

SOURCE_ID = "src:osm.overpass_api"
LICENSE_FAMILY = "odbl"
ATTRIBUTION = (
    "(c) OpenStreetMap contributors, ODbL "
    "(synthetic fixture shaped like Overpass output)"
)
URL_FAMILY = "https://overpass-api.example.org/api/interpreter"


def _overpass_query(bbox: list, tags: dict) -> str:
    south, west, north, east = bbox
    tag_filters = "".join(f'["{k}"="{v}"]' for k, v in sorted(tags.items()))
    return f"[out:json];node{tag_filters}({south},{west},{north},{east});out;"


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def osm_overpass_bounded_poi_query(payload: dict, transport) -> PrimitiveOutcome:
    """Query Overpass-shaped POI nodes inside a bbox.

    payload: {"bbox": [south, west, north, east], "tags": {...},
              "fixture_name"}
    """
    bbox = payload["bbox"]
    tags = payload.get("tags", {})
    response, snapshot_id = transport.get_json(
        URL_FAMILY,
        {"data": _overpass_query(bbox, tags)},
        payload["fixture_name"],
    )

    schema_problems: list[str] = []
    elements = response.get("elements")
    if not isinstance(elements, list):
        schema_problems.append("response.elements missing or not a list")
        elements = []

    records = []
    for i, el in enumerate(elements):
        if not isinstance(el, dict):
            schema_problems.append(f"elements[{i}] not an object")
            continue
        for key in ("type", "id", "lat", "lon"):
            if key not in el:
                schema_problems.append(f"elements[{i}].{key} missing")
        el_tags = el.get("tags") or {}
        records.append(
            {
                "record_id": f"osm:{el.get('type', 'node')}:{el.get('id')}",
                "source_id": SOURCE_ID,
                "name": el_tags.get("name"),
                "address": None,
                "city": None,
                "state": None,
                "zip": None,
                "phone": None,
                "lat": el.get("lat"),
                "lon": el.get("lon"),
                "tags": el_tags,
                "license_family": LICENSE_FAMILY,
                "attribution_required": True,
            }
        )

    schema_proof = ProofResult(
        "schema_validation",
        not schema_problems,
        "; ".join(schema_problems[:5])
        if schema_problems
        else f"{len(records)} elements carry type/id/lat/lon",
    )

    attribution_ok = (
        LICENSE_FAMILY == "odbl"
        and "OpenStreetMap" in ATTRIBUTION
        and all(r.get("attribution_required") is True for r in records)
    )
    attribution_proof = ProofResult(
        "attribution_flag_set",
        attribution_ok,
        "odbl license family + contributor attribution set on snapshot and "
        f"attribution_required on {len(records)} records",
    )

    south, west, north, east = bbox
    outside = []
    for rec in records:
        lat, lon = rec.get("lat"), rec.get("lon")
        if (
            not _is_number(lat)
            or not _is_number(lon)
            or not (south <= lat <= north)
            or not (west <= lon <= east)
        ):
            outside.append(rec["record_id"])
    bbox_proof = ProofResult(
        "bbox_containment",
        not outside,
        "elements outside bbox: " + ", ".join(outside[:5])
        if outside
        else f"{len(records)} elements inside bbox {bbox}",
    )

    output = {
        "bbox": list(bbox),
        "tags": dict(tags),
        "records": records,
        "record_count": len(records),
        "snapshot_meta": build_snapshot_meta(
            snapshot_id, SOURCE_ID, LICENSE_FAMILY, ATTRIBUTION, transport
        ),
    }
    return PrimitiveOutcome(
        output=output,
        effects_observed=effects_for(transport),
        proof_results=[schema_proof, attribution_proof, bbox_proof],
        source_snapshot_ids=[snapshot_id],
    )
