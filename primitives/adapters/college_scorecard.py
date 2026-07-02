"""College Scorecard / IPEDS program adapter (P0 source adapter).

Mimics the shape of the U.S. Department of Education College Scorecard API,
which returns flat dotted keys (``"school.name"``, ``"location.lat"``,
``"latest.programs.cip_4_digit"``, ...). Fixtures are SYNTHETIC;
``retrieved_mode`` is propagated into ``snapshot_meta`` so downstream
evidence bundles disclose it.

Filtering contract: each institution's ``programs`` list is filtered to
CIP-4 codes starting with ``payload["program_cip_prefix"]``; institutions
with no matching program are dropped. ``record_id`` keeps the source row
index so retained records stay traceable to the snapshot, and the output
reports total vs retained institution counts.

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

SOURCE_ID = "src:college_scorecard.ipeds_programs_api"
LICENSE_FAMILY = "public_domain_us_gov"
ATTRIBUTION = (
    "Data source shape: U.S. Department of Education College Scorecard API "
    "(synthetic fixture)"
)
URL_FAMILY = "https://api.data.gov/ed/collegescorecard/v1/schools"

_REQUIRED_ROW_FIELDS = [
    "school.name",
    "school.city",
    "school.state",
    "school.zip",
    "location.lat",
    "location.lon",
    "latest.programs.cip_4_digit",
]


def _cip_filter_applied(
    records: list[dict],
    prefix: str,
    programs_total: int,
    institutions_total: int,
) -> ProofResult:
    """Proof that every retained program matches the CIP prefix and that
    every retained institution kept at least one program."""
    bad: list[str] = []
    programs_kept = 0
    for rec in records:
        programs = rec.get("programs", [])
        if not programs:
            bad.append(f"{rec.get('record_id', '?')} retained with no programs")
            continue
        for prog in programs:
            code = str(prog.get("code", ""))
            if not code.startswith(prefix):
                bad.append(f"{rec.get('record_id', '?')} program {code}")
            programs_kept += 1
    if bad:
        return ProofResult(
            "cip_filter_applied", False, "; ".join(bad[:5])
        )
    return ProofResult(
        "cip_filter_applied",
        True,
        f"prefix={prefix}: kept {programs_kept}/{programs_total} programs "
        f"across {len(records)}/{institutions_total} institutions",
    )


def college_scorecard_ipeds_program_adapter(
    payload: dict, transport
) -> PrimitiveOutcome:
    """Ingest Scorecard-shaped institution rows filtered to a CIP-4 prefix.

    payload: {"aoi_id", "state", "program_cip_prefix", "fixture_name"}
    """
    prefix = str(payload["program_cip_prefix"])
    response, snapshot_id = transport.get_json(
        URL_FAMILY,
        {"school.state": payload["state"], "latest.programs.cip_4_digit": prefix},
        payload["fixture_name"],
    )
    rows = response.get("results", [])
    schema_proof = require_fields(rows, _REQUIRED_ROW_FIELDS)

    records = []
    programs_total = 0
    institutions_total = 0
    for i, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        institutions_total += 1
        all_programs = row.get("latest.programs.cip_4_digit", [])
        if not isinstance(all_programs, list):
            all_programs = []
        programs_total += len(all_programs)
        programs = [
            {"code": prog.get("code"), "title": prog.get("title")}
            for prog in all_programs
            if isinstance(prog, dict)
            and str(prog.get("code", "")).startswith(prefix)
        ]
        if not programs:
            continue
        records.append(
            {
                "record_id": f"csc:{i}",
                "source_id": SOURCE_ID,
                "name": row.get("school.name"),
                "address": "",
                "city": row.get("school.city"),
                "state": row.get("school.state"),
                "zip": row.get("school.zip"),
                "phone": None,
                "lat": row.get("location.lat"),
                "lon": row.get("location.lon"),
                "programs": programs,
            }
        )

    proofs = [
        schema_proof,
        ProofResult("row_count_positive", len(records) > 0, f"rows={len(records)}"),
        coordinates_in_range(records),
        _cip_filter_applied(records, prefix, programs_total, institutions_total),
    ]

    output = {
        "aoi_id": payload["aoi_id"],
        "program_cip_prefix": prefix,
        "records": records,
        "record_count": len(records),
        "institutions_total": institutions_total,
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
