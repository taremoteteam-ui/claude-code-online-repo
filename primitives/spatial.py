"""Spatial P0 primitives for the place-discovery-geospatial lane.

Two pure-computation primitives:

- :func:`point_to_boundary_spatial_join` -- ray-casting point-in-polygon
  join of points against a GeoJSON FeatureCollection of Polygon boundaries.
- :func:`nearest_facility_catchment` -- nearest-facility assignment of
  demand points using great-circle (haversine) distance.

HONESTY NOTES
- Haversine straight-line distance is a PROXY. It is NOT travel time and
  does not model roads, terrain, or congestion. The method receipt in the
  output says so explicitly, and a proof asserts that it says so.
- All fixture geometry in this repo is SYNTHETIC. When boundary features
  are flagged ``fixture_synthetic``, the method receipt records
  ``boundary_source: "fixture_synthetic"``.

Stdlib only. Pure computation: effects_observed == ["none"].
"""

from __future__ import annotations

import math
from typing import Any

from primitives.core import PrimitiveOutcome, ProofResult

EARTH_RADIUS_KM = 6371.0088  # IUGG mean earth radius


# ---------------------------------------------------------------------------
# Geometry helpers (pure functions, stdlib only)
# ---------------------------------------------------------------------------

def _point_in_ring(lon: float, lat: float, ring: list) -> bool:
    """Even-odd ray casting against one linear ring.

    ``ring`` is a GeoJSON linear ring: list of [lon, lat] positions.
    A duplicated closing vertex contributes a degenerate segment that the
    algorithm ignores naturally (yi == yj fails the crossing test).
    """
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = float(ring[i][0]), float(ring[i][1])
        xj, yj = float(ring[j][0]), float(ring[j][1])
        if (yi > lat) != (yj > lat):
            x_cross = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lon < x_cross:
                inside = not inside
        j = i
    return inside


def point_in_polygon(lon: float, lat: float, coordinates: list) -> bool:
    """Even-odd containment for a GeoJSON Polygon coordinate array.

    ``coordinates`` is ``[exterior_ring, hole_ring, ...]``. Even-odd over
    all rings handles holes: inside the exterior XOR inside a hole.
    """
    inside = False
    for ring in coordinates:
        if _point_in_ring(lon, lat, ring):
            inside = not inside
    return inside


def _first_ring_centroid(coordinates: list) -> tuple[float, float]:
    """(lon, lat) vertex-average centroid of the polygon's first ring.

    This is a vertex mean, not an area centroid; adequate as a sanity
    probe for convex fixture hexagons.
    """
    ring = coordinates[0]
    verts = list(ring)
    if len(verts) > 1 and verts[0] == verts[-1]:
        verts = verts[:-1]
    lon = sum(float(v[0]) for v in verts) / len(verts)
    lat = sum(float(v[1]) for v in verts) / len(verts)
    return lon, lat


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km. Straight-line PROXY, not travel time."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2.0) ** 2
    )
    return 2.0 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


# ---------------------------------------------------------------------------
# Payload validation helpers
# ---------------------------------------------------------------------------

def _require_point_fields(row: Any, idx: int, kind: str, errors: list) -> None:
    if not isinstance(row, dict):
        errors.append(f"{kind}[{idx}] is not an object")
        return
    if not isinstance(row.get("id"), str) or not row.get("id"):
        errors.append(f"{kind}[{idx}] missing string 'id'")
    for key in ("lat", "lon"):
        if not isinstance(row.get(key), (int, float)) or isinstance(row.get(key), bool):
            errors.append(f"{kind}[{idx}] missing numeric '{key}'")


# ---------------------------------------------------------------------------
# Primitive: point_to_boundary_spatial_join
# ---------------------------------------------------------------------------

def point_to_boundary_spatial_join(payload: dict) -> PrimitiveOutcome:
    """Join points to containing Polygon boundaries via ray casting.

    payload:
      points:     [{"id", "lat", "lon"}, ...]
      boundaries: GeoJSON FeatureCollection of Polygon features whose
                  properties include "boundary_id", "name",
                  "boundary_vintage", "fixture_synthetic".

    CRS assumption: coordinates are EPSG:4326; GeoJSON positions are
    [lon, lat] order. Points are lat/lon fields.
    """
    errors: list[str] = []
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    points = payload.get("points")
    boundaries = payload.get("boundaries")
    if not isinstance(points, list):
        errors.append("'points' must be a list")
        points = []
    for idx, row in enumerate(points):
        _require_point_fields(row, idx, "points", errors)
    features: list[dict] = []
    if not isinstance(boundaries, dict) or boundaries.get("type") != "FeatureCollection":
        errors.append("'boundaries' must be a GeoJSON FeatureCollection")
    else:
        raw_features = boundaries.get("features")
        if not isinstance(raw_features, list) or not raw_features:
            errors.append("'boundaries.features' must be a non-empty list")
        else:
            for idx, feat in enumerate(raw_features):
                geom = feat.get("geometry") if isinstance(feat, dict) else None
                props = feat.get("properties") if isinstance(feat, dict) else None
                if not isinstance(geom, dict) or geom.get("type") != "Polygon":
                    errors.append(f"features[{idx}] geometry must be a Polygon")
                    continue
                if not isinstance(props, dict) or not props.get("boundary_id"):
                    errors.append(f"features[{idx}] properties missing 'boundary_id'")
                    continue
                features.append(feat)
    if errors:
        raise ValueError("schema_validation failed: " + "; ".join(errors))

    # Join: first containing boundary wins (features are disjoint fixtures;
    # order of the FeatureCollection breaks any tie deterministically).
    joined = []
    matched = 0
    for row in points:
        lat = float(row["lat"])
        lon = float(row["lon"])
        hit = None
        for feat in features:
            if point_in_polygon(lon, lat, feat["geometry"]["coordinates"]):
                hit = feat["properties"]["boundary_id"]
                break
        if hit is not None:
            matched += 1
        joined.append({"id": row["id"], "lat": lat, "lon": lon, "boundary_id": hit})

    vintages = sorted({
        str(f["properties"].get("boundary_vintage", "")) for f in features
    } - {""})
    if not vintages:
        boundary_vintage: Any = "unspecified"
    elif len(vintages) == 1:
        boundary_vintage = vintages[0]
    else:
        boundary_vintage = vintages
    all_synthetic = bool(features) and all(
        f["properties"].get("fixture_synthetic") is True for f in features
    )
    boundary_source = "fixture_synthetic" if all_synthetic else "unspecified"

    output = {
        "joined_points": joined,
        "method": {
            "algorithm": "ray_casting",
            "crs_assumed": "EPSG:4326",
            "boundary_vintage": boundary_vintage,
            "boundary_source": boundary_source,
        },
        "stats": {
            "points": len(points),
            "matched": matched,
            "unmatched": len(points) - matched,
        },
    }

    # Containment sanity: the first-ring vertex centroid of every polygon
    # must be contained by that same polygon.
    sanity_failures = []
    for feat in features:
        coords = feat["geometry"]["coordinates"]
        clon, clat = _first_ring_centroid(coords)
        if not point_in_polygon(clon, clat, coords):
            sanity_failures.append(feat["properties"]["boundary_id"])
    proofs = [
        ProofResult(
            "schema_validation", True,
            f"{len(points)} points, {len(features)} polygon features validated",
        ),
        ProofResult(
            "crs_receipt_present",
            output["method"]["crs_assumed"] == "EPSG:4326",
            "method.crs_assumed=EPSG:4326",
        ),
        ProofResult(
            "boundary_vintage_receipt",
            boundary_vintage != "unspecified" and bool(boundary_vintage),
            f"boundary_vintage={boundary_vintage!r}",
        ),
        ProofResult(
            "containment_sanity",
            not sanity_failures,
            ("all polygon first-ring centroids contained"
             if not sanity_failures
             else "centroid not contained for: " + ", ".join(sanity_failures)),
        ),
    ]
    return PrimitiveOutcome(
        output=output,
        effects_observed=["none"],
        proof_results=proofs,
    )


# ---------------------------------------------------------------------------
# Primitive: nearest_facility_catchment
# ---------------------------------------------------------------------------

def nearest_facility_catchment(payload: dict) -> PrimitiveOutcome:
    """Assign each demand point to its nearest facility by haversine.

    payload:
      facilities:    [{"id", "lat", "lon"}, ...]
      demand_points: [{"id", "lat", "lon", "population": int}, ...]
      travel_policy: {"max_km": float,
                      "method": "straight_line_haversine_proxy"}

    HONESTY: distances are great-circle straight lines. Travel time is
    NOT computed; roads and terrain are not modeled. The output method
    receipt states this and a proof enforces that statement.
    """
    errors: list[str] = []
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    facilities = payload.get("facilities")
    demand_points = payload.get("demand_points")
    travel_policy = payload.get("travel_policy")
    if not isinstance(facilities, list) or not facilities:
        errors.append("'facilities' must be a non-empty list")
        facilities = []
    for idx, row in enumerate(facilities):
        _require_point_fields(row, idx, "facilities", errors)
    if not isinstance(demand_points, list):
        errors.append("'demand_points' must be a list")
        demand_points = []
    for idx, row in enumerate(demand_points):
        _require_point_fields(row, idx, "demand_points", errors)
        if isinstance(row, dict):
            pop = row.get("population")
            if not isinstance(pop, int) or isinstance(pop, bool) or pop < 0:
                errors.append(
                    f"demand_points[{idx}] missing non-negative int 'population'"
                )
    if not isinstance(travel_policy, dict):
        errors.append("'travel_policy' must be an object")
        travel_policy = {}
    max_km = travel_policy.get("max_km")
    if not isinstance(max_km, (int, float)) or isinstance(max_km, bool) or max_km <= 0:
        errors.append("travel_policy.max_km must be a positive number")
    if travel_policy.get("method") != "straight_line_haversine_proxy":
        errors.append(
            "travel_policy.method must be 'straight_line_haversine_proxy' "
            "(the only method this primitive implements)"
        )
    if errors:
        raise ValueError("schema_validation failed: " + "; ".join(errors))
    max_km = float(max_km)

    assignments = []
    total_population = 0
    covered_population = 0
    for dp in demand_points:
        best_id = None
        best_km = None
        for fac in facilities:
            d = haversine_km(
                float(dp["lat"]), float(dp["lon"]),
                float(fac["lat"]), float(fac["lon"]),
            )
            # strict < plus id tiebreak keeps assignment deterministic
            if best_km is None or d < best_km or (d == best_km and fac["id"] < best_id):
                best_km = d
                best_id = fac["id"]
        assignments.append({
            "demand_id": dp["id"],
            "facility_id": best_id,
            "distance_km": round(best_km, 6),
        })
        pop = int(dp["population"])
        total_population += pop
        if best_km <= max_km:
            covered_population += pop
    uncovered_population = total_population - covered_population
    coverage_ratio = (
        round(covered_population / total_population, 6) if total_population else 0.0
    )

    output = {
        "assignments": assignments,
        "coverage_report": {
            "total_population": total_population,
            "covered_population": covered_population,
            "uncovered_population": uncovered_population,
            "coverage_ratio": coverage_ratio,
            "max_km": max_km,
        },
        "method": {
            "distance": "haversine_great_circle",
            "travel_time": "NOT_COMPUTED_straight_line_proxy",
            "caveat": (
                "straight-line distance is a proxy; roads/terrain/travel "
                "time not modeled"
            ),
        },
    }

    # Distance symmetry spot check: haversine(a,b) == haversine(b,a) for a
    # sample of (demand, facility) pairs.
    symmetry_ok = True
    symmetry_detail = "no pairs to check"
    sample = [(dp, fac) for dp in demand_points[:3] for fac in facilities[:3]]
    if sample:
        worst = 0.0
        for dp, fac in sample:
            fwd = haversine_km(dp["lat"], dp["lon"], fac["lat"], fac["lon"])
            rev = haversine_km(fac["lat"], fac["lon"], dp["lat"], dp["lon"])
            worst = max(worst, abs(fwd - rev))
        symmetry_ok = worst < 1e-9
        symmetry_detail = f"{len(sample)} pairs, max |d(a,b)-d(b,a)| = {worst:.3e} km"

    method = output["method"]
    proofs = [
        ProofResult(
            "schema_validation", True,
            f"{len(facilities)} facilities, {len(demand_points)} demand points validated",
        ),
        ProofResult(
            "method_receipt_honest",
            "NOT_COMPUTED" in method["travel_time"]
            and "proxy" in method["travel_time"]
            and "proxy" in method["caveat"],
            "method.travel_time explicitly marks straight-line proxy; "
            "travel time not computed",
        ),
        ProofResult(
            "population_conservation",
            covered_population + uncovered_population == total_population,
            f"covered({covered_population}) + uncovered({uncovered_population}) "
            f"== total({total_population})",
        ),
        ProofResult("distance_symmetry_spot_check", symmetry_ok, symmetry_detail),
    ]
    return PrimitiveOutcome(
        output=output,
        effects_observed=["none"],
        proof_results=proofs,
    )
