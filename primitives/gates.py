"""Geocoding provider policy gate primitive.

Evaluates a planned geocoding/extraction job against a deterministic
policy table for known providers (public Nominatim, public Overpass,
US Census geocoder, self-hosted Nominatim). Emits an allow/deny
decision with reasons and constraints, and flags attribution duties.

Policy values encode published usage-policy shapes as candidate gate
material; they are conservative defaults, not measured limits. Pure and
stdlib-only: no I/O, no network, no side effects.
"""

from __future__ import annotations

from primitives.core import PrimitiveOutcome, ProofResult

KNOWN_PROVIDERS = (
    "nominatim_public",
    "overpass_public",
    "census_geocoder",
    "self_hosted_nominatim",
)

NOMINATIM_PUBLIC_MAX_REQUESTS = 1000
OVERPASS_PUBLIC_MAX_ELEMENTS = 10000
CENSUS_MAX_BATCH_RECORDS_PER_FILE = 10000


def _evaluate(provider: str, planned_request_count: int, bulk_job: bool) -> dict:
    """Deterministic policy table lookup. Returns decision fields."""
    reasons: list[str] = []
    constraints: dict = {}

    if provider == "nominatim_public":
        attribution_required = True
        reasons.append("public Nominatim requires OSM/ODbL attribution")
        if bulk_job or planned_request_count > NOMINATIM_PUBLIC_MAX_REQUESTS:
            decision = "self_host_or_bulk_required"
            if bulk_job:
                reasons.append(
                    "bulk jobs are not permitted against the public Nominatim endpoint"
                )
            if planned_request_count > NOMINATIM_PUBLIC_MAX_REQUESTS:
                reasons.append(
                    f"planned_request_count {planned_request_count} exceeds "
                    f"{NOMINATIM_PUBLIC_MAX_REQUESTS} for the public endpoint"
                )
            constraints["alternatives"] = ["self_hosted_nominatim", "bulk_extract"]
        else:
            decision = "allow_with_rate_limit"
            reasons.append("small ad-hoc job within public endpoint policy")
            constraints["max_rate_per_sec"] = 1
            constraints["max_requests"] = NOMINATIM_PUBLIC_MAX_REQUESTS

    elif provider == "overpass_public":
        attribution_required = True
        reasons.append("public Overpass serves OSM data; ODbL attribution required")
        if bulk_job or planned_request_count > OVERPASS_PUBLIC_MAX_ELEMENTS:
            decision = "use_planet_extract"
            if bulk_job:
                reasons.append(
                    "bulk extraction belongs on planet/region extracts, not the "
                    "shared public Overpass endpoint"
                )
            if planned_request_count > OVERPASS_PUBLIC_MAX_ELEMENTS:
                reasons.append(
                    f"planned volume {planned_request_count} exceeds "
                    f"{OVERPASS_PUBLIC_MAX_ELEMENTS} elements for the public endpoint"
                )
            constraints["alternatives"] = ["planet_extract", "regional_extract"]
        else:
            decision = "allow_with_rate_limit"
            reasons.append("small query load within shared endpoint courtesy limits")
            constraints["max_rate_per_sec"] = 1
            constraints["max_elements_per_query"] = OVERPASS_PUBLIC_MAX_ELEMENTS

    elif provider == "census_geocoder":
        attribution_required = False
        decision = "allow"
        reasons.append(
            "US Census geocoder permits batch geocoding of public-domain data"
        )
        constraints["max_batch_records_per_file"] = CENSUS_MAX_BATCH_RECORDS_PER_FILE

    elif provider == "self_hosted_nominatim":
        attribution_required = True
        decision = "allow"
        reasons.append("self-hosted instance: no shared-endpoint rate policy applies")
        reasons.append(
            "ODbL attribution still required on published artifacts derived "
            "from OSM data"
        )

    else:
        attribution_required = False
        decision = "deny_unknown_provider"
        reasons.append(f"provider '{provider}' is not in the policy table")

    return {
        "decision": decision,
        "reasons": reasons,
        "constraints": constraints,
        "attribution_required": attribution_required,
    }


def geocode_policy_gate(payload: dict) -> PrimitiveOutcome:
    """Gate a planned geocoding job against the provider policy table.

    payload:
        provider: str
        planned_request_count: int
        bulk_job: bool
        attribution_planned: bool

    output:
        provider, decision, reasons, constraints, attribution_required

    proofs:
        policy_table_coverage - provider is handled by the table or
            explicitly denied as unknown
        attribution_consistency - fails when the provider requires
            attribution but the caller has not planned it
    """
    provider = str(payload.get("provider", ""))
    try:
        planned_request_count = int(payload.get("planned_request_count", 0) or 0)
    except (TypeError, ValueError):
        planned_request_count = 0
    bulk_job = bool(payload.get("bulk_job", False))
    attribution_planned = bool(payload.get("attribution_planned", False))

    verdict = _evaluate(provider, planned_request_count, bulk_job)
    output = {
        "provider": provider,
        "decision": verdict["decision"],
        "reasons": verdict["reasons"],
        "constraints": verdict["constraints"],
        "attribution_required": verdict["attribution_required"],
    }

    covered = (
        provider in KNOWN_PROVIDERS
        or output["decision"] == "deny_unknown_provider"
    )
    proofs = [
        ProofResult(
            "policy_table_coverage",
            covered,
            f"provider '{provider}' handled by policy table"
            if provider in KNOWN_PROVIDERS
            else f"provider '{provider}' explicitly denied as unknown",
        )
    ]

    attribution_gap = output["attribution_required"] and not attribution_planned
    proofs.append(
        ProofResult(
            "attribution_consistency",
            not attribution_gap,
            (
                f"provider '{provider}' requires attribution but "
                "attribution_planned is false"
            )
            if attribution_gap
            else "attribution plan consistent with provider requirements",
        )
    )

    return PrimitiveOutcome(
        output=output,
        effects_observed=["none"],
        proof_results=proofs,
    )
