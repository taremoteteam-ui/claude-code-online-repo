"""NPPES provider identity resolver (P0 source adapter).

Mimics the shape of the NPPES NPI Registry API (organization search) and
resolves candidate facility names against registered organizations using
normalized-name equality/containment plus a same-state check. Every match
decision is recorded as a receipt so entity-resolution work stays auditable.

Fixtures are SYNTHETIC; ``retrieved_mode`` is propagated into
``snapshot_meta`` so downstream evidence bundles disclose it.
Stdlib only.
"""

from __future__ import annotations

import re

from primitives.adapters._common import build_snapshot_meta, effects_for
from primitives.core import PrimitiveOutcome, ProofResult

SOURCE_ID = "src:nppes.npi_registry"
LICENSE_FAMILY = "public_domain_us_gov"
ATTRIBUTION = (
    "Data source shape: NPPES NPI Registry API organization search "
    "(synthetic fixture)"
)
URL_FAMILY = "https://npiregistry.cms.hhs.gov/api/"

_NPI_RE = re.compile(r"^\d{10}$")

# Common health-facility abbreviations expanded during name normalization so
# near-duplicate variants ("GULF COAST COMM HEALTH CTR" vs "Gulf Coast
# Community Health Center") resolve to the same normalized string.
_ABBREVIATIONS = {
    "CTR": "CENTER",
    "CTRS": "CENTERS",
    "COMM": "COMMUNITY",
    "CMTY": "COMMUNITY",
    "HLTH": "HEALTH",
    "SVCS": "SERVICES",
    "SVC": "SERVICE",
    "MED": "MEDICAL",
    "CLNC": "CLINIC",
    "FAM": "FAMILY",
    "HOSP": "HOSPITAL",
    "DEPT": "DEPARTMENT",
    "GRP": "GROUP",
    "ASSOC": "ASSOCIATES",
}

# Corporate suffixes dropped during normalization.
_DROP_TOKENS = {"INC", "LLC", "PLLC", "PA", "PC", "LTD", "LLP", "CORP"}


def normalize_org_name(name: str) -> str:
    """Uppercase, strip punctuation, expand abbreviations, drop suffixes."""
    tokens = re.sub(r"[^A-Z0-9 ]", " ", str(name).upper()).split()
    out = []
    for tok in tokens:
        if tok in _DROP_TOKENS:
            continue
        out.append(_ABBREVIATIONS.get(tok, tok))
    return " ".join(out)


def nppes_provider_identity_resolver(payload: dict, transport) -> PrimitiveOutcome:
    """Resolve candidate facility names against NPPES-shaped org records.

    payload: {"aoi_id", "state", "candidate_names": [...], "fixture_name"}
    """
    response, snapshot_id = transport.get_json(
        URL_FAMILY,
        {"version": "2.1", "enumeration_type": "NPI-2", "state": payload["state"]},
        payload["fixture_name"],
    )

    results = response.get("results", [])
    schema_problems: list[str] = []
    if not isinstance(response.get("result_count"), int):
        schema_problems.append("result_count missing or not an integer")
    records = []
    for i, item in enumerate(results):
        if not isinstance(item, dict):
            schema_problems.append(f"results[{i}] not an object")
            continue
        basic = item.get("basic")
        addresses = item.get("addresses")
        if "number" not in item:
            schema_problems.append(f"results[{i}].number missing")
        if not isinstance(basic, dict) or "organization_name" not in basic:
            schema_problems.append(f"results[{i}].basic.organization_name missing")
        if not isinstance(addresses, list) or not addresses:
            schema_problems.append(f"results[{i}].addresses missing or empty")
            addresses = [{}]
        addr = addresses[0] if isinstance(addresses[0], dict) else {}
        npi = str(item.get("number", ""))
        records.append(
            {
                "record_id": f"nppes:{npi}",
                "source_id": SOURCE_ID,
                "name": (basic or {}).get("organization_name"),
                "address": addr.get("address_1"),
                "city": addr.get("city"),
                "state": addr.get("state"),
                "zip": addr.get("postal_code"),
                "phone": None,
                "lat": None,
                "lon": None,
                "npi": npi,
            }
        )

    schema_proof = ProofResult(
        "schema_validation",
        not schema_problems,
        "; ".join(schema_problems[:5])
        if schema_problems
        else f"{len(records)} NPPES org results carry required fields",
    )

    bad_npis = [r["npi"] for r in records if not _NPI_RE.match(r["npi"])]
    npi_proof = ProofResult(
        "npi_format_check",
        not bad_npis,
        "non-10-digit NPIs: " + ", ".join(bad_npis[:5])
        if bad_npis
        else f"{len(records)} NPIs are 10 digits",
    )

    target_state = str(payload["state"]).upper()
    match_decisions = []
    for candidate in payload.get("candidate_names", []):
        norm_candidate = normalize_org_name(candidate)
        matched_any = False
        for rec in records:
            if str(rec.get("state", "")).upper() != target_state:
                continue
            norm_org = normalize_org_name(rec.get("name") or "")
            if not norm_candidate or not norm_org:
                continue
            if norm_candidate == norm_org:
                reason = "normalized_name_equality;state_match"
            elif norm_candidate in norm_org or norm_org in norm_candidate:
                reason = "normalized_name_containment;state_match"
            else:
                continue
            matched_any = True
            match_decisions.append(
                {
                    "candidate": candidate,
                    "npi": rec["npi"],
                    "matched": True,
                    "reason": reason,
                }
            )
        if not matched_any:
            match_decisions.append(
                {
                    "candidate": candidate,
                    "npi": None,
                    "matched": False,
                    "reason": "no_normalized_name_match_in_state",
                }
            )

    candidates = list(payload.get("candidate_names", []))
    decided = {d["candidate"] for d in match_decisions}
    receipt_proof = ProofResult(
        "match_decision_receipt_present",
        all(c in decided for c in candidates),
        f"{len(match_decisions)} decisions cover {len(candidates)} candidates",
    )

    output = {
        "aoi_id": payload["aoi_id"],
        "records": records,
        "record_count": len(records),
        "match_decisions": match_decisions,
        "snapshot_meta": build_snapshot_meta(
            snapshot_id, SOURCE_ID, LICENSE_FAMILY, ATTRIBUTION, transport
        ),
    }
    return PrimitiveOutcome(
        output=output,
        effects_observed=effects_for(transport),
        proof_results=[schema_proof, npi_proof, receipt_proof],
        source_snapshot_ids=[snapshot_id],
    )
