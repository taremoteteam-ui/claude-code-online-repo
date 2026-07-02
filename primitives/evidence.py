"""Evidence bundle wrapper primitive.

Wraps an answer payload with its source snapshot references, a
deduplicated attribution block, and an uncertainty report, then seals
the bundle with a deterministic content hash. Automatically appends a
synthetic-fixture disclosure note when any snapshot was retrieved in
fixture_offline mode.

Pure and stdlib-only: no I/O, no network, no side effects. Bundles are
candidate material; wrapping an answer never promotes it to truth.
"""

from __future__ import annotations

from primitives.core import PrimitiveOutcome, ProofResult, canonical_hash

ATTRIBUTION_REQUIRED_LICENSES = frozenset({"odbl", "cc_by", "cc_by_sa"})
FIXTURE_OFFLINE_NOTE = (
    "fixture_offline data - synthetic fixtures, not real-world measurements"
)


def _snapshot_summary(snapshot: dict) -> dict:
    return {
        "snapshot_id": str(snapshot.get("snapshot_id", "")),
        "source_id": str(snapshot.get("source_id", "")),
        "license_family": str(snapshot.get("license_family", "")),
        "retrieved_mode": str(snapshot.get("retrieved_mode", "")),
    }


def evidence_bundle_wrapper(payload: dict) -> PrimitiveOutcome:
    """Assemble an evidence bundle around an answer.

    payload:
        answer: dict
        source_snapshots: [{snapshot_id, source_id, license_family,
            attribution, retrieved_mode}, ...]
        uncertainty_notes: [str, ...]
        attributions: [str, ...]

    output:
        evidence_bundle: {answer, source_refs, attribution_block,
            uncertainty_report, bundle_hash}

    proofs:
        attribution_complete - every snapshot whose license family
            requires attribution (odbl, cc_by, cc_by_sa) has its
            attribution string present in the attribution block
        source_ref_coverage - at least one source snapshot is present
        uncertainty_report_present - the report carries at least one note
    """
    answer = payload.get("answer")
    if not isinstance(answer, dict):
        answer = {}
    snapshots = payload.get("source_snapshots")
    if not isinstance(snapshots, list):
        snapshots = []
    snapshots = [s for s in snapshots if isinstance(s, dict)]
    notes = payload.get("uncertainty_notes")
    if not isinstance(notes, list):
        notes = []
    attributions = payload.get("attributions")
    if not isinstance(attributions, list):
        attributions = []

    source_refs = [_snapshot_summary(s) for s in snapshots]
    attribution_block = sorted({
        a.strip() for a in attributions if isinstance(a, str) and a.strip()
    })

    uncertainty_report = [
        n.strip() for n in notes if isinstance(n, str) and n.strip()
    ]
    if any(
        s.get("retrieved_mode") == "fixture_offline" for s in snapshots
    ) and FIXTURE_OFFLINE_NOTE not in uncertainty_report:
        uncertainty_report.append(FIXTURE_OFFLINE_NOTE)

    bundle = {
        "answer": answer,
        "source_refs": source_refs,
        "attribution_block": attribution_block,
        "uncertainty_report": uncertainty_report,
    }
    bundle["bundle_hash"] = canonical_hash(bundle)
    output = {"evidence_bundle": bundle}

    missing_attribution = []
    for snapshot in snapshots:
        license_family = str(snapshot.get("license_family", "")).lower()
        if license_family not in ATTRIBUTION_REQUIRED_LICENSES:
            continue
        attribution = snapshot.get("attribution")
        attribution = attribution.strip() if isinstance(attribution, str) else ""
        if not attribution or attribution not in attribution_block:
            missing_attribution.append(
                f"{snapshot.get('snapshot_id', '?')} ({license_family})"
            )
    proofs = [
        ProofResult(
            "attribution_complete",
            not missing_attribution,
            "all attribution-required snapshots covered"
            if not missing_attribution
            else "snapshots missing attribution: " + "; ".join(missing_attribution),
        ),
        ProofResult(
            "source_ref_coverage",
            len(source_refs) >= 1,
            f"{len(source_refs)} source snapshot(s) referenced"
            if source_refs
            else "no source snapshots present",
        ),
        ProofResult(
            "uncertainty_report_present",
            len(uncertainty_report) >= 1,
            f"{len(uncertainty_report)} uncertainty note(s)"
            if uncertainty_report
            else "uncertainty report is empty",
        ),
    ]

    return PrimitiveOutcome(
        output=output,
        effects_observed=["none"],
        proof_results=proofs,
        source_snapshot_ids=[
            r["snapshot_id"] for r in source_refs if r["snapshot_id"]
        ],
    )
