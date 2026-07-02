"""Ranking primitive for the place-discovery-geospatial lane.

One pure-computation primitive:

- :func:`coverage_gap_ranker` -- ranks coverage gap areas (demand points
  whose nearest-facility distance exceeds the policy threshold) under an
  explicit gap ranking policy.

Pack contract: ``PopulationCoverageReport+GapRankingPolicy ->
RankedGapAreaSet+MethodReceipt`` (primitive card
``prim:place_discovery.coverage_gap_ranker``; closes the
``site_selection_ranking`` gap family).

HONESTY NOTES
- Upstream distances come from ``nearest_facility_catchment`` and are
  straight-line haversine PROXIES. This ranking inherits that proxy; it
  does not add travel time, roads, or terrain.
- Site suitability factors (zoning, transit, cost) are NOT modeled. The
  method receipt in the output says so explicitly, and a proof asserts
  that it says so.
- Ranked rows are planning inputs only, never siting decisions.

Stdlib only. Pure computation: effects_observed == ["none"].
"""

from __future__ import annotations

from typing import Any

from primitives.core import PrimitiveOutcome, ProofResult

WEIGHT_KEYS = ("uncovered_population", "distance_beyond_threshold")

METHOD_RECEIPT = {
    "scoring": "weighted_linear_normalized",
    "distance_basis": "straight_line_haversine_proxy_from_upstream",
    "caveat": (
        "ranking inherits the straight-line proxy; site suitability "
        "factors (zoning, transit, cost) are NOT modeled"
    ),
}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_nonneg_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


# ---------------------------------------------------------------------------
# Scoring core (pure, deterministic)
# ---------------------------------------------------------------------------

def _score_and_rank(candidates: list[dict], max_km: float, weights: dict) -> list[dict]:
    """Score and order gap candidates. Deterministic in inputs.

    score = weights.uncovered_population * (population / max candidate
    population) + weights.distance_beyond_threshold * (distance excess /
    max candidate distance excess). Normalization is within the candidate
    set, so both factors land on [0, 1] before weighting (guards the
    "ranking dominated by one unnormalized factor" failure mode). Order is
    descending score with ascending ``demand_id`` as the tiebreak, so the
    result never depends on input order.
    """
    if not candidates:
        return []
    max_pop = max(c["population"] for c in candidates)
    max_excess = max(c["distance_km"] - max_km for c in candidates)
    scored = []
    for c in candidates:
        excess = c["distance_km"] - max_km
        pop_norm = (c["population"] / max_pop) if max_pop > 0 else 0.0
        excess_norm = (excess / max_excess) if max_excess > 0 else 0.0
        pop_term = weights["uncovered_population"] * pop_norm
        dist_term = weights["distance_beyond_threshold"] * excess_norm
        scored.append({
            "demand_id": c["demand_id"],
            "lat": c["lat"],
            "lon": c["lon"],
            "population": c["population"],
            "nearest_facility_id": c["nearest_facility_id"],
            "distance_km": c["distance_km"],
            "score": round(pop_term + dist_term, 9),
            "score_components": {
                "uncovered_population": round(pop_term, 9),
                "distance_beyond_threshold": round(dist_term, 9),
                "population_normalized": round(pop_norm, 9),
                "excess_km": round(excess, 6),
                "excess_normalized": round(excess_norm, 9),
            },
        })
    scored.sort(key=lambda r: (-r["score"], r["demand_id"]))
    return scored


# ---------------------------------------------------------------------------
# Primitive: coverage_gap_ranker
# ---------------------------------------------------------------------------

def coverage_gap_ranker(payload: dict) -> PrimitiveOutcome:
    """Rank coverage gap areas from a population coverage report.

    payload:
      coverage_report: {"total_population", "covered_population",
                        "uncovered_population", "coverage_ratio", "max_km"}
                       (from nearest_facility_catchment)
      assignments:     [{"demand_id", "facility_id", "distance_km"}, ...]
                       (from nearest_facility_catchment)
      demand_points:   [{"id", "lat", "lon", "population"}, ...]
      facilities:      [{"id", "lat", "lon"}, ...]
      ranking_policy:  {"max_km": float, "top_n": int,
                        "weights": {"uncovered_population": float,
                                    "distance_beyond_threshold": float}}

    Candidate gap areas are demand points whose nearest-facility distance
    strictly exceeds ``ranking_policy.max_km``. Output is the top_n ranked
    gap areas plus a tradeoff report and an honest method receipt.
    """
    errors: list[str] = []
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")

    coverage_report = payload.get("coverage_report")
    assignments = payload.get("assignments")
    demand_points = payload.get("demand_points")
    facilities = payload.get("facilities")
    policy = payload.get("ranking_policy")

    # -- coverage_report -----------------------------------------------------
    if not isinstance(coverage_report, dict):
        errors.append("'coverage_report' must be an object")
        coverage_report = {}
    else:
        for key in ("total_population", "covered_population", "uncovered_population"):
            if not _is_nonneg_int(coverage_report.get(key)):
                errors.append(f"coverage_report.{key} must be a non-negative int")
        if not _is_number(coverage_report.get("coverage_ratio")):
            errors.append("coverage_report.coverage_ratio must be a number")
        cr_max = coverage_report.get("max_km")
        if not _is_number(cr_max) or cr_max <= 0:
            errors.append("coverage_report.max_km must be a positive number")
        if (
            _is_nonneg_int(coverage_report.get("total_population"))
            and _is_nonneg_int(coverage_report.get("covered_population"))
            and _is_nonneg_int(coverage_report.get("uncovered_population"))
            and coverage_report["covered_population"]
            + coverage_report["uncovered_population"]
            != coverage_report["total_population"]
        ):
            errors.append(
                "coverage_report populations do not conserve "
                "(covered + uncovered != total)"
            )

    # -- demand_points ---------------------------------------------------------
    demand_ids: set[str] = set()
    if not isinstance(demand_points, list):
        errors.append("'demand_points' must be a list")
        demand_points = []
    for idx, row in enumerate(demand_points):
        if not isinstance(row, dict):
            errors.append(f"demand_points[{idx}] is not an object")
            continue
        rid = row.get("id")
        if not isinstance(rid, str) or not rid:
            errors.append(f"demand_points[{idx}] missing string 'id'")
            continue
        if rid in demand_ids:
            errors.append(f"demand_points[{idx}] duplicate id {rid!r}")
        demand_ids.add(rid)
        for key in ("lat", "lon"):
            if not _is_number(row.get(key)):
                errors.append(f"demand_points[{idx}] missing numeric '{key}'")
        if not _is_nonneg_int(row.get("population")):
            errors.append(
                f"demand_points[{idx}] missing non-negative int 'population'"
            )

    # -- facilities ------------------------------------------------------------
    facility_ids: set[str] = set()
    if not isinstance(facilities, list) or not facilities:
        errors.append("'facilities' must be a non-empty list")
        facilities = []
    for idx, row in enumerate(facilities):
        if not isinstance(row, dict):
            errors.append(f"facilities[{idx}] is not an object")
            continue
        rid = row.get("id")
        if not isinstance(rid, str) or not rid:
            errors.append(f"facilities[{idx}] missing string 'id'")
            continue
        if rid in facility_ids:
            errors.append(f"facilities[{idx}] duplicate id {rid!r}")
        facility_ids.add(rid)
        for key in ("lat", "lon"):
            if not _is_number(row.get(key)):
                errors.append(f"facilities[{idx}] missing numeric '{key}'")

    # -- assignments -------------------------------------------------------
    assigned_ids: set[str] = set()
    if not isinstance(assignments, list):
        errors.append("'assignments' must be a list")
        assignments = []
    for idx, row in enumerate(assignments):
        if not isinstance(row, dict):
            errors.append(f"assignments[{idx}] is not an object")
            continue
        did = row.get("demand_id")
        if not isinstance(did, str) or not did:
            errors.append(f"assignments[{idx}] missing string 'demand_id'")
            continue
        if did in assigned_ids:
            errors.append(f"assignments[{idx}] duplicate demand_id {did!r}")
        assigned_ids.add(did)
        if did not in demand_ids:
            errors.append(f"assignments[{idx}] references unknown demand_id {did!r}")
        fid = row.get("facility_id")
        if not isinstance(fid, str) or not fid:
            errors.append(f"assignments[{idx}] missing string 'facility_id'")
        elif fid not in facility_ids:
            errors.append(
                f"assignments[{idx}] references unknown facility_id {fid!r}"
            )
        dist = row.get("distance_km")
        if not _is_number(dist) or dist < 0:
            errors.append(
                f"assignments[{idx}] missing non-negative numeric 'distance_km'"
            )
    missing = demand_ids - assigned_ids
    if missing:
        errors.append(
            "demand points without an assignment: " + ", ".join(sorted(missing))
        )

    # -- ranking_policy ----------------------------------------------------
    if not isinstance(policy, dict):
        errors.append("'ranking_policy' must be an object")
        policy = {}
    p_max = policy.get("max_km")
    if not _is_number(p_max) or p_max <= 0:
        errors.append("ranking_policy.max_km must be a positive number")
    top_n = policy.get("top_n")
    if not isinstance(top_n, int) or isinstance(top_n, bool) or top_n < 1:
        errors.append("ranking_policy.top_n must be a positive int")
    weights_in = policy.get("weights")
    if not isinstance(weights_in, dict):
        errors.append("ranking_policy.weights must be an object")
        weights_in = {}
    weights_valid = True
    for key in WEIGHT_KEYS:
        wv = weights_in.get(key)
        if not _is_number(wv) or wv < 0:
            errors.append(
                f"ranking_policy.weights.{key} must be a non-negative number"
            )
            weights_valid = False
    unknown = sorted(set(weights_in) - set(WEIGHT_KEYS))
    if unknown:
        errors.append(
            "ranking_policy.weights has unknown factors: " + ", ".join(unknown)
        )
    if weights_valid and sum(float(weights_in[k]) for k in WEIGHT_KEYS) == 0:
        errors.append("at least one ranking_policy weight must be positive")

    if errors:
        raise ValueError("schema_validation failed: " + "; ".join(errors))

    max_km = float(p_max)
    weights = {k: float(weights_in[k]) for k in WEIGHT_KEYS}

    # -- candidate gap areas: strictly beyond the policy threshold ----------
    demand_by_id = {dp["id"]: dp for dp in demand_points}
    candidates = []
    for asg in assignments:
        distance_km = round(float(asg["distance_km"]), 6)
        if distance_km <= max_km:
            continue
        dp = demand_by_id[asg["demand_id"]]
        candidates.append({
            "demand_id": asg["demand_id"],
            "lat": float(dp["lat"]),
            "lon": float(dp["lon"]),
            "population": int(dp["population"]),
            "nearest_facility_id": asg["facility_id"],
            "distance_km": distance_km,
        })

    ranked = _score_and_rank(candidates, max_km, weights)
    ranked_gap_areas = []
    for i, row in enumerate(ranked[: int(top_n)]):
        ranked_gap_areas.append({
            "rank": i + 1,
            "demand_id": row["demand_id"],
            "lat": row["lat"],
            "lon": row["lon"],
            "population": row["population"],
            "nearest_facility_id": row["nearest_facility_id"],
            "distance_km": row["distance_km"],
            "score": row["score"],
            "score_components": row["score_components"],
        })

    population_in_gaps = sum(c["population"] for c in candidates)
    total_population = int(coverage_report["total_population"])
    share_of_total = (
        round(population_in_gaps / total_population, 6) if total_population else 0.0
    )

    output = {
        "ranked_gap_areas": ranked_gap_areas,
        "tradeoff_report": {
            "candidates_considered": len(candidates),
            "population_in_gaps": population_in_gaps,
            "share_of_total_population": share_of_total,
            "weights_used": weights,
        },
        "method": dict(METHOD_RECEIPT),
    }

    # -- proofs --------------------------------------------------------
    # deterministic_ranking: recompute from reversed candidate input; order
    # and scores must be identical (input-order invariance).
    recheck = _score_and_rank(list(reversed(candidates)), max_km, weights)
    det_ok = (
        [(r["demand_id"], r["score"]) for r in recheck]
        == [(r["demand_id"], r["score"]) for r in ranked]
    )

    # score_monotonicity over the full ranked set (not just the top_n cut).
    mono_ok = all(
        ranked[i]["score"] >= ranked[i + 1]["score"] for i in range(len(ranked) - 1)
    )

    # population_accounting: tradeoff figure equals the sum over the ranked
    # candidate set.
    ranked_pop = sum(r["population"] for r in ranked)
    pop_ok = ranked_pop == population_in_gaps

    method = output["method"]
    honest_ok = (
        "proxy" in method["distance_basis"]
        and "proxy" in method["caveat"]
        and "NOT modeled" in method["caveat"]
    )

    proofs = [
        ProofResult(
            "schema_validation", True,
            f"{len(demand_points)} demand points, {len(assignments)} assignments, "
            f"{len(facilities)} facilities, policy validated",
        ),
        ProofResult(
            "deterministic_ranking", det_ok,
            f"reversed-input recompute over {len(candidates)} candidates "
            "reproduced identical order and scores"
            if det_ok else "recompute produced a different order",
        ),
        ProofResult(
            "score_monotonicity", mono_ok,
            f"scores nonincreasing across {len(ranked)} ranked candidates"
            if mono_ok else "a lower rank carries a higher score",
        ),
        ProofResult(
            "population_accounting", pop_ok,
            f"population_in_gaps({population_in_gaps}) == "
            f"sum of candidate populations({ranked_pop})",
        ),
        ProofResult(
            "method_receipt_honest", honest_ok,
            "method receipt discloses the straight-line proxy and that site "
            "suitability factors are NOT modeled",
        ),
    ]
    return PrimitiveOutcome(
        output=output,
        effects_observed=["none"],
        proof_results=proofs,
    )
