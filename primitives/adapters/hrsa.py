"""HRSA health center site ingester (P0 source adapter).

Mimics the shape of HRSA Health Center Service Delivery Sites data.
Fixtures are SYNTHETIC; ``retrieved_mode`` is propagated into
``snapshot_meta`` so downstream evidence bundles disclose it.
Stdlib only.
"""

from __future__ import annotations

from primitives.adapters._common import (
    build_snapshot_meta,
    coordinates_in_range,
    effects_for,
    require_fields,
)
from primitives.core import PrimitiveOutcome, ProofResult

SOURCE_ID = "src:hrsa.health_center_sites"
LICENSE_FAMILY = "public_domain_us_gov"
ATTRIBUTION = (
    "Data source shape: HRSA Health Center Service Delivery Sites "
    "(synthetic fixture)"
)
URL_FAMILY = "https://data.hrsa.gov/api/health-center-service-delivery-sites"

_REQUIRED_ROW_FIELDS = [
    "site_name",
    "address",
    "city",
    "state",
    "zip",
    "latitude",
    "longitude",
    "site_type",
]


def hrsa_health_center_ingester(payload: dict, transport) -> PrimitiveOutcome:
    """Ingest HRSA-shaped health center site rows for one AOI.

    payload: {"aoi_id", "state", "fixture_name"}
    """
    response, snapshot_id = transport.get_json(
        URL_FAMILY,
        {"state": payload["state"]},
        payload["fixture_name"],
    )
    rows = response.get("rows", [])
    schema_proof = require_fields(rows, _REQUIRED_ROW_FIELDS)

    records = []
    for i, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        records.append(
            {
                "record_id": f"hrsa:{i}",
                "source_id": SOURCE_ID,
                "name": row.get("site_name"),
                "address": row.get("address"),
                "city": row.get("city"),
                "state": row.get("state"),
                "zip": row.get("zip"),
                "phone": None,
                "lat": row.get("latitude"),
                "lon": row.get("longitude"),
            }
        )

    proofs = [
        schema_proof,
        ProofResult("row_count_positive", len(records) > 0, f"rows={len(records)}"),
        coordinates_in_range(records),
    ]

    output = {
        "aoi_id": payload["aoi_id"],
        "records": records,
        "record_count": len(records),
        "snapshot_meta": build_snapshot_meta(
            snapshot_id, SOURCE_ID, LICENSE_FAMILY, ATTRIBUTION, transport
        ),
    }
    return PrimitiveOutcome(
        output=output,
        effects_observed=effects_for(transport),
        proof_results=proofs,
        source_snapshot_ids=[snapshot_id],
    )
