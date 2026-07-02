"""ArcGIS FeatureServer layer ingester (P0 source adapter).

Mimics the shape of an ArcGIS FeatureServer ``/query`` response with
``f=json`` point geometries (``geometry.x`` = lon, ``geometry.y`` = lat)
and normalizes features into common point records.

Fixtures are SYNTHETIC; ``retrieved_mode`` is propagated into
``snapshot_meta`` so downstream evidence bundles disclose it.
Stdlib only.
"""

from __future__ import annotations

from primitives.adapters._common import (
    build_snapshot_meta,
    coordinates_in_range,
    effects_for,
)
from primitives.core import PrimitiveOutcome, ProofResult

SOURCE_ID = "src:arcgis.featureserver"
LICENSE_FAMILY = "government_open_data_requires_review"
ATTRIBUTION = (
    "Data source shape: ArcGIS FeatureServer query response (synthetic fixture)"
)


def _attr(attributes: dict, *names: str):
    """Case-insensitive attribute lookup across common field spellings."""
    lowered = {str(k).lower(): v for k, v in attributes.items()}
    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return None


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def arcgis_featureserver_layer_ingester(payload: dict, transport) -> PrimitiveOutcome:
    """Ingest ArcGIS-FeatureServer-shaped point features.

    payload: {"layer_url_family", "where", "fixture_name"}
    """
    response, snapshot_id = transport.get_json(
        payload["layer_url_family"] + "/query",
        {"where": payload.get("where", "1=1"), "outFields": "*", "f": "json"},
        payload["fixture_name"],
    )

    schema_problems: list[str] = []
    features = response.get("features")
    if not isinstance(features, list):
        schema_problems.append("response.features missing or not a list")
        features = []

    geometry_missing: list[str] = []
    records = []
    for i, feature in enumerate(features, start=1):
        if not isinstance(feature, dict) or not isinstance(
            feature.get("attributes"), dict
        ):
            schema_problems.append(f"features[{i - 1}] missing attributes object")
            continue
        attrs = feature["attributes"]
        geom = feature.get("geometry")
        record_key = _attr(attrs, "OBJECTID", "FID")
        record_id = f"arcgis:{record_key if record_key is not None else i}"
        if (
            not isinstance(geom, dict)
            or not _is_number(geom.get("x"))
            or not _is_number(geom.get("y"))
        ):
            geometry_missing.append(record_id)
            geom = {}
        records.append(
            {
                "record_id": record_id,
                "source_id": SOURCE_ID,
                "name": _attr(attrs, "NAME", "FACILITY_NAME", "SITE_NAME"),
                "address": _attr(attrs, "ADDRESS", "STREET_ADDRESS"),
                "city": _attr(attrs, "CITY"),
                "state": _attr(attrs, "STATE"),
                "zip": _attr(attrs, "ZIP", "ZIPCODE", "POSTAL_CODE"),
                "phone": None,
                "lat": geom.get("y"),
                "lon": geom.get("x"),
                "attributes": attrs,
            }
        )

    schema_proof = ProofResult(
        "schema_validation",
        not schema_problems,
        "; ".join(schema_problems[:5])
        if schema_problems
        else f"{len(records)} features carry attribute objects",
    )
    geometry_proof = ProofResult(
        "geometry_present",
        not geometry_missing and len(records) > 0,
        "features missing point geometry: " + ", ".join(geometry_missing[:5])
        if geometry_missing
        else f"{len(records)} features carry x/y point geometry",
    )
    coords_proof = coordinates_in_range(records)

    output = {
        "layer_url_family": payload["layer_url_family"],
        "where": payload.get("where", "1=1"),
        "records": records,
        "record_count": len(records),
        "snapshot_meta": build_snapshot_meta(
            snapshot_id, SOURCE_ID, LICENSE_FAMILY, ATTRIBUTION, transport
        ),
    }
    return PrimitiveOutcome(
        output=output,
        effects_observed=effects_for(transport),
        proof_results=[schema_proof, geometry_proof, coords_proof],
        source_snapshot_ids=[snapshot_id],
    )
