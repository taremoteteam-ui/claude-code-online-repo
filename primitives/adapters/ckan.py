"""CKAN package/resource harvester (P0 source adapter).

Mimics the shape of the CKAN ``package_search`` action API. Every dataset
candidate gets a per-dataset license recorded; datasets without a
``license_id`` are flagged ``unspecified_requires_review`` - nothing here
assumes a license that was not stated.

Fixtures are SYNTHETIC; ``retrieved_mode`` is propagated into
``snapshot_meta`` so downstream evidence bundles disclose it.
Stdlib only.
"""

from __future__ import annotations

from primitives.adapters._common import build_snapshot_meta, effects_for
from primitives.core import PrimitiveOutcome, ProofResult

SOURCE_ID = "src:ckan.package_search"
LICENSE_FAMILY = "mixed_per_dataset_see_records"
ATTRIBUTION = (
    "Data source shape: CKAN package_search action API (synthetic fixture)"
)
URL_FAMILY = "https://catalog.example.gov/api/3/action/package_search"

_LICENSE_FAMILY_BY_ID = {
    "cc-by": "cc_by",
    "cc-by-sa": "cc_by_sa",
    "cc-zero": "cc0",
    "odc-by": "odc_by",
    "odc-odbl": "odbl",
    "odc-pddl": "pddl",
    "uk-ogl": "ogl_uk",
    "us-pd": "public_domain_us_gov",
    "other-open": "other_open_requires_review",
}


def _license_family_for(license_id) -> str:
    if not license_id or license_id == "notspecified":
        return "unspecified_requires_review"
    return _LICENSE_FAMILY_BY_ID.get(license_id, "unrecognized_requires_review")


def ckan_package_resource_harvester(payload: dict, transport) -> PrimitiveOutcome:
    """Harvest CKAN-shaped dataset candidates for a search query.

    payload: {"query", "fixture_name"}
    """
    response, snapshot_id = transport.get_json(
        URL_FAMILY,
        {"q": payload["query"]},
        payload["fixture_name"],
    )

    schema_problems: list[str] = []
    if response.get("success") is not True:
        schema_problems.append("response.success is not true")
    result = response.get("result")
    if not isinstance(result, dict):
        schema_problems.append("response.result missing or not an object")
        result = {}
    raw_datasets = result.get("results", [])
    if not isinstance(raw_datasets, list):
        schema_problems.append("result.results is not a list")
        raw_datasets = []

    datasets = []
    for i, ds in enumerate(raw_datasets):
        if not isinstance(ds, dict):
            schema_problems.append(f"result.results[{i}] not an object")
            continue
        for key in ("name", "title", "resources"):
            if key not in ds:
                schema_problems.append(f"result.results[{i}].{key} missing")
        license_id = ds.get("license_id")
        license_family = _license_family_for(license_id)
        resources = []
        for res in ds.get("resources", []) or []:
            if not isinstance(res, dict):
                continue
            resources.append(
                {
                    "format": res.get("format"),
                    "url": res.get("url"),
                    "name": res.get("name"),
                }
            )
        org = ds.get("organization") or {}
        datasets.append(
            {
                "record_id": f"ckan:{ds.get('name', f'unnamed-{i}')}",
                "source_id": SOURCE_ID,
                "name": ds.get("name"),
                "title": ds.get("title"),
                "publisher": org.get("title") if isinstance(org, dict) else None,
                "license_id": license_id if license_id else None,
                "license_family": license_family,
                "requires_license_review": license_family.endswith("requires_review"),
                "resources": resources,
            }
        )

    schema_proof = ProofResult(
        "schema_validation",
        not schema_problems,
        "; ".join(schema_problems[:5])
        if schema_problems
        else f"{len(datasets)} CKAN dataset results carry required fields",
    )

    unrecorded = [d["record_id"] for d in datasets if not d.get("license_family")]
    flagged = sum(1 for d in datasets if d["requires_license_review"])
    license_proof = ProofResult(
        "license_recorded_per_dataset",
        not unrecorded,
        f"{len(datasets)} datasets carry a license_family; "
        f"{flagged} flagged requires_review"
        if not unrecorded
        else "missing license_family: " + ", ".join(unrecorded[:5]),
    )

    missing_urls = []
    for d in datasets:
        for j, res in enumerate(d["resources"]):
            if not res.get("url"):
                missing_urls.append(f"{d['record_id']}.resources[{j}]")
    url_proof = ProofResult(
        "resource_url_present",
        not missing_urls,
        "resources missing url: " + ", ".join(missing_urls[:5])
        if missing_urls
        else "every resource carries a url",
    )

    output = {
        "query": payload["query"],
        "datasets": datasets,
        "dataset_count": len(datasets),
        "snapshot_meta": build_snapshot_meta(
            snapshot_id, SOURCE_ID, LICENSE_FAMILY, ATTRIBUTION, transport
        ),
    }
    return PrimitiveOutcome(
        output=output,
        effects_observed=effects_for(transport),
        proof_results=[schema_proof, license_proof, url_proof],
        source_snapshot_ids=[snapshot_id],
    )
