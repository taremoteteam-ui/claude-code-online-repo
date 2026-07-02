"""CareerOneStop training-provider adapter (P0 source adapter).

Mimics the shape of the CareerOneStop Training Provider API (ETPL-flagged
school/program listings). Fixtures are SYNTHETIC; ``retrieved_mode`` is
propagated into ``snapshot_meta`` so downstream evidence bundles disclose it.

Honesty note: ETPL/WIOA eligibility is maintained by each state and changes
over time. The adapter records the flag per record exactly as retrieved and
attaches an ``eligibility_note`` to the output so downstream consumers never
treat the flag as verified truth.

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

SOURCE_ID = "src:careeronestop.training_providers_api"
LICENSE_FAMILY = "public_domain_us_gov"
ATTRIBUTION = (
    "Data source shape: CareerOneStop Training Provider API, "
    "U.S. Department of Labor (synthetic fixture)"
)
URL_FAMILY = "https://api.careeronestop.org/v1/training"

ELIGIBILITY_NOTE = (
    "ETPL/WIOA eligibility is state-maintained and time-sensitive; "
    "verify against the state list before relying on it"
)

_REQUIRED_ROW_FIELDS = [
    "SchoolName",
    "ProgramName",
    "City",
    "StateName",
    "Zip",
    "Latitude",
    "Longitude",
    "EtplFlag",
]


def _wioa_flag_recorded(records: list[dict]) -> ProofResult:
    """Proof that every record carries a boolean ``wioa_eligible`` flag."""
    bad: list[str] = []
    for rec in records:
        if not isinstance(rec.get("wioa_eligible"), bool):
            bad.append(str(rec.get("record_id", "?")))
    if bad:
        return ProofResult(
            "wioa_flag_recorded_per_record",
            False,
            "missing or non-boolean wioa_eligible: " + ", ".join(bad[:5]),
        )
    eligible = sum(1 for rec in records if rec["wioa_eligible"])
    return ProofResult(
        "wioa_flag_recorded_per_record",
        True,
        f"{len(records)} records carry a boolean flag; "
        f"{eligible} flagged eligible as retrieved",
    )


def careeronestop_training_provider_adapter(
    payload: dict, transport
) -> PrimitiveOutcome:
    """Ingest CareerOneStop-shaped training-provider rows for one AOI.

    payload: {"aoi_id", "state", "program_keyword", "fixture_name"}
    """
    response, snapshot_id = transport.get_json(
        URL_FAMILY,
        {"state": payload["state"], "keyword": payload["program_keyword"]},
        payload["fixture_name"],
    )
    rows = response.get("SchoolPrograms", [])
    schema_proof = require_fields(rows, _REQUIRED_ROW_FIELDS)

    records = []
    for i, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        records.append(
            {
                "record_id": f"cos:{i}",
                "source_id": SOURCE_ID,
                "name": row.get("SchoolName"),
                "address": "",
                "city": row.get("City"),
                "state": row.get("StateName"),
                "zip": row.get("Zip"),
                "phone": None,
                "lat": row.get("Latitude"),
                "lon": row.get("Longitude"),
                "program_name": row.get("ProgramName"),
                "wioa_eligible": row.get("EtplFlag"),
            }
        )

    proofs = [
        schema_proof,
        ProofResult("row_count_positive", len(records) > 0, f"rows={len(records)}"),
        coordinates_in_range(records),
        _wioa_flag_recorded(records),
    ]

    output = {
        "aoi_id": payload["aoi_id"],
        "records": records,
        "record_count": len(records),
        "eligibility_note": ELIGIBILITY_NOTE,
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
