#!/usr/bin/env python3
"""Benchmark harness for the place-discovery-geospatial lane.

Executes generated benchmark task demands from the seed pack through the
DETERMINISTIC ROUTE REPLAY arm (A4) in fixture_offline mode and writes
MEASURED scorecards, execution receipts, artifacts, gap records, and a
computed manifest under benchmarks/runs/<run_id>/.

Honesty rules enforced here:
  - Only arms that actually run get scorecards. Baseline arms A1/A2 require a
    model-in-the-loop harness and are NOT simulated or estimated.
  - runtime_llm_tokens is 0 for A4 because no model is invoked - that is a
    measured fact of this arm, not a claim about other arms.
  - Fixture mode is recorded on every receipt and disclosed in every evidence
    bundle: fixtures are synthetic data shaped like the real APIs. These runs
    measure the route machinery, not real-world data accuracy.
  - Families that cannot run (missing adapters/fixtures) emit GapRecords
    instead of fake scorecards.

Usage:
    python3 scripts/run_place_discovery_benchmark.py --write
    python3 scripts/run_place_discovery_benchmark.py --self-test   (dry run, no files)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from primitives.core import PrimitiveExecutionError, canonical_hash, run_primitive  # noqa: E402
from primitives.registry import source_surface_registry  # noqa: E402

PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "place-discovery-geospatial-seeds"
FIXTURE_ROOT = REPO_ROOT / "fixtures" / "place-discovery"
RUNS_ROOT = REPO_ROOT / "benchmarks" / "runs"

ARM_ID = "A4"  # deterministic template fill / promoted route replay
DEPTH = "L4"  # route card replay - no source escalation needed

AOI_FIXTURES = {
    "aoi:harris_county_tx": {
        "state": "TX",
        "hrsa": "hrsa_sites_harris_tx.json",
        "nppes": "nppes_orgs_harris_tx.json",
        "overpass": "overpass_clinics_harris_tx.json",
        "careeronestop": "careeronestop_providers_harris_tx.json",
        "college_scorecard": "college_scorecard_harris_tx.json",
        "bbox": [29.5, -95.8, 30.2, -95.0],
        "max_km": 30.0,
    },
    "aoi:glacier_county_mt": {
        "state": "MT",
        "hrsa": "hrsa_sites_glacier_mt.json",
        "nppes": "nppes_orgs_glacier_mt.json",
        "overpass": "overpass_clinics_glacier_mt.json",
        "careeronestop": "careeronestop_providers_glacier_mt.json",
        "college_scorecard": "college_scorecard_glacier_mt.json",
        "bbox": [48.4, -113.4, 49.0, -112.6],
        "max_km": 60.0,
    },
}

RUNNABLE_FAMILIES = [
    "clinic_discovery",
    "training_provider_discovery",
    "care_desert_analysis",
    "portal_dataset_harvest",
    "osm_poi_extraction",
    "schema_drift_detection",
    "site_selection_ranking",
    "map_dashboard_generation",
]
# All 8 task families are now runnable offline; the gap records emitted by
# earlier runs (training_provider_discovery, site_selection_ranking) are
# closed by the careeronestop/college_scorecard adapters and the
# coverage_gap_ranker primitive.
UNRUNNABLE_FAMILIES: dict[str, list[str]] = {}

# Canonical route per family: the primitive sequence each runner executes.
# Compiled into PlanLocks; the executed receipt sequence is validated against
# the lock, and every successful task is executed twice to prove replay
# determinism (identical output-hash sequences).
FAMILY_ROUTES = {
    "clinic_discovery": [
        "source_surface_registry", "hrsa_health_center_ingester",
        "nppes_provider_identity_resolver", "osm_overpass_bounded_poi_query",
        "entity_normalize_and_dedupe", "point_to_boundary_spatial_join",
        "evidence_bundle_wrapper",
    ],
    "training_provider_discovery": [
        "geocode_policy_gate", "careeronestop_training_provider_adapter",
        "college_scorecard_ipeds_program_adapter", "entity_normalize_and_dedupe",
        "evidence_bundle_wrapper",
    ],
    "care_desert_analysis": [
        "hrsa_health_center_ingester", "entity_normalize_and_dedupe",
        "nearest_facility_isochrone_catchment_analysis",
        "map_artifact_generation", "evidence_bundle_wrapper",
    ],
    "osm_poi_extraction": [
        "geocode_policy_gate", "osm_overpass_bounded_poi_query",
        "entity_normalize_and_dedupe", "point_to_boundary_spatial_join",
        "evidence_bundle_wrapper",
    ],
    "portal_dataset_harvest": [
        "ckan_package_resource_harvester", "socrata_soql_dataset_ingester",
        "dataset_schema_fingerprint", "evidence_bundle_wrapper",
    ],
    "schema_drift_detection": [
        "socrata_soql_dataset_ingester", "dataset_schema_fingerprint",
        "dataset_schema_fingerprint", "evidence_bundle_wrapper",
    ],
    "site_selection_ranking": [
        "hrsa_health_center_ingester", "entity_normalize_and_dedupe",
        "nearest_facility_isochrone_catchment_analysis", "coverage_gap_ranker",
        "map_artifact_generation", "evidence_bundle_wrapper",
    ],
    "map_dashboard_generation": [
        "hrsa_health_center_ingester",
        "nearest_facility_isochrone_catchment_analysis",
        "map_artifact_generation", "evidence_bundle_wrapper",
    ],
}


def compile_plan_locks() -> dict[str, dict]:
    """Compile each family route into a PlanLock (schemas/plan_lock.schema.json).

    Edges come from the generated primitive cards - never retyped. The
    route_hash makes the lock stable, hashable, and replayable."""
    cards = {c["primitive_id"]: c for c in (
        json.loads(line) for line in
        (PACK_DIR / "primitive_cards.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip())}
    locks: dict[str, dict] = {}
    for family, names in FAMILY_ROUTES.items():
        route = []
        for i, name in enumerate(names, start=1):
            pid = f"prim:place_discovery.{name}"
            card = cards[pid]
            route.append({
                "step": i,
                "primitive_id": pid,
                "input_edge": card["input_edge"],
                "output_edge": card["output_edge"],
            })
        locks[family] = {
            "record_type": "plan_lock",
            "lock_id": f"lock:place_discovery.{family}",
            "route": route,
            "route_hash": canonical_hash(route),
            "compiled_from": "deterministic_route_definition",
            "proof_plan": [
                "executed_sequence_matches_lock",
                "replay_output_hash_stability",
            ],
            "replayable": True,
            "version": "0.1.0",
            "candidate": True,
            "serves_truth": False,
        }
    return locks


class TaskContext:
    """Collects receipts and artifacts for one task execution."""

    def __init__(self, run_id: str, artifacts_dir: Path | None):
        self.run_id = run_id
        self.artifacts_dir = artifacts_dir
        self.receipts: list[dict] = []
        self.artifact_files: list[str] = []
        self.snapshot_meta: list[dict] = []

    def exec(self, primitive_id: str, fn, payload, effects: list[str], mode: str = "pure_local"):
        output, receipt = run_primitive(
            primitive_id, fn, payload, run_id=self.run_id,
            declared_effects=effects, execution_mode=mode,
        )
        self.receipts.append(receipt)
        if isinstance(output, dict) and "snapshot_meta" in output:
            self.snapshot_meta.append(output["snapshot_meta"])
        return output, receipt

    def save_artifact(self, name: str, content: str) -> str:
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if self.artifacts_dir is not None:
            self.artifacts_dir.mkdir(parents=True, exist_ok=True)
            (self.artifacts_dir / name).write_text(content, encoding="utf-8")
        self.artifact_files.append(f"{name} sha256:{digest}")
        return digest


def load_fixture_json(name: str) -> dict:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def load_boundary(aoi_id: str) -> dict:
    fc = load_fixture_json("aoi_boundaries.geojson")
    for feat in fc["features"]:
        if feat["properties"]["boundary_id"] == aoi_id:
            return feat
    raise KeyError(f"no boundary fixture for {aoi_id}")


def load_demand_points(aoi_id: str) -> list[dict]:
    data = load_fixture_json("demand_points.json")
    return data["by_aoi"][aoi_id]


def poi_to_record(poi: dict, idx: int) -> dict:
    tags = poi.get("tags", {})
    return {
        "record_id": f"osm:{poi.get('id', idx)}",
        "source_id": "src:osm.overpass_api",
        "name": tags.get("name", f"unnamed poi {idx}"),
        "address": tags.get("addr:street", ""),
        "city": tags.get("addr:city", ""),
        "state": tags.get("addr:state", ""),
        "zip": tags.get("addr:postcode"),
        "phone": tags.get("phone"),
        "lat": poi["lat"],
        "lon": poi["lon"],
    }


# ---------------------------------------------------------------------------
# Family route runners. Each returns (task_success, answer_note, artifacts).
# ---------------------------------------------------------------------------

def run_clinic_discovery(ctx: TaskContext, aoi_id: str, prims: dict) -> tuple[bool, str]:
    cfg = AOI_FIXTURES[aoi_id]
    reg_out, _ = ctx.exec(
        "prim:place_discovery.source_surface_registry", source_surface_registry,
        {"query": {"lane": "health_facilities", "adapter_priority": "P0"}},
        effects=["file_read"], mode="pure_local",
    )
    transport = prims["FixtureTransport"](str(FIXTURE_ROOT))
    hrsa_out, _ = ctx.exec(
        "prim:place_discovery.hrsa_health_center_ingester",
        lambda p: prims["hrsa"](p, transport),
        {"aoi_id": aoi_id, "state": cfg["state"], "fixture_name": cfg["hrsa"]},
        effects=["network_read"], mode="fixture_offline",
    )
    candidate_names = [r["name"] for r in hrsa_out["records"][:4]]
    nppes_out, _ = ctx.exec(
        "prim:place_discovery.nppes_provider_identity_resolver",
        lambda p: prims["nppes"](p, transport),
        {"aoi_id": aoi_id, "state": cfg["state"], "candidate_names": candidate_names,
         "fixture_name": cfg["nppes"]},
        effects=["network_read"], mode="fixture_offline",
    )
    osm_out, _ = ctx.exec(
        "prim:place_discovery.osm_overpass_bounded_poi_query",
        lambda p: prims["overpass"](p, transport),
        {"bbox": cfg["bbox"], "tags": {"amenity": "clinic"}, "fixture_name": cfg["overpass"]},
        effects=["network_read"], mode="fixture_offline",
    )
    all_records = list(hrsa_out["records"]) + [
        poi_to_record(p, i) if "record_id" not in p else p
        for i, p in enumerate(osm_out["records"])
    ]
    dedupe_out, _ = ctx.exec(
        "prim:place_discovery.entity_normalize_and_dedupe", prims["dedupe"],
        {"records": all_records,
         "match_policy": {"name_similarity_threshold": 0.82, "max_distance_m": 500.0,
                          "require_same_zip5": False}},
        effects=["none"], mode="pure_local",
    )
    entities = dedupe_out["entities"]
    points = [{"id": e["entity_id"], "lat": e["lat"], "lon": e["lon"]}
              for e in entities if e.get("lat") is not None]
    join_out, _ = ctx.exec(
        "prim:place_discovery.point_to_boundary_spatial_join", prims["spatial_join"],
        {"points": points, "boundaries": {"type": "FeatureCollection",
                                          "features": [load_boundary(aoi_id)]}},
        effects=["none"], mode="pure_local",
    )
    in_boundary = [p for p in join_out["joined_points"] if p.get("boundary_id") == aoi_id]
    answer = {
        "question_family": "clinic_discovery",
        "aoi_id": aoi_id,
        "facilities_resolved": len(entities),
        "facilities_in_boundary": len(in_boundary),
        "duplicates_merged": dedupe_out["stats"]["duplicates_merged"],
        "sources_compared": ["src:hrsa.health_center_sites", "src:cms.nppes_npi_registry",
                             "src:osm.overpass_api"],
        "registry_sources_considered": reg_out["match_count"],
        "nppes_matches": sum(1 for d in nppes_out["match_decisions"] if d["matched"]),
    }
    ctx.exec(
        "prim:place_discovery.evidence_bundle_wrapper", prims["evidence"],
        {"answer": answer, "source_snapshots": ctx.snapshot_meta,
         "uncertainty_notes": ["entity match thresholds are policy-set, not learned",
                               "OSM coverage is community-maintained and may lag official sources"],
         "attributions": [m.get("attribution", "") for m in ctx.snapshot_meta]},
        effects=["none"], mode="pure_local",
    )
    ok = len(in_boundary) >= 1 and dedupe_out["stats"]["duplicates_merged"] >= (
        1 if aoi_id == "aoi:harris_county_tx" else 0)
    return ok, f"{len(in_boundary)} facilities in boundary, {dedupe_out['stats']['duplicates_merged']} duplicates merged"


def run_care_desert(ctx: TaskContext, aoi_id: str, prims: dict) -> tuple[bool, str]:
    cfg = AOI_FIXTURES[aoi_id]
    transport = prims["FixtureTransport"](str(FIXTURE_ROOT))
    hrsa_out, _ = ctx.exec(
        "prim:place_discovery.hrsa_health_center_ingester",
        lambda p: prims["hrsa"](p, transport),
        {"aoi_id": aoi_id, "state": cfg["state"], "fixture_name": cfg["hrsa"]},
        effects=["network_read"], mode="fixture_offline",
    )
    dedupe_out, _ = ctx.exec(
        "prim:place_discovery.entity_normalize_and_dedupe", prims["dedupe"],
        {"records": hrsa_out["records"],
         "match_policy": {"name_similarity_threshold": 0.85, "max_distance_m": 300.0,
                          "require_same_zip5": False}},
        effects=["none"], mode="pure_local",
    )
    facilities = [{"id": e["entity_id"], "lat": e["lat"], "lon": e["lon"]}
                  for e in dedupe_out["entities"] if e.get("lat") is not None]
    demand = load_demand_points(aoi_id)
    catch_out, _ = ctx.exec(
        "prim:place_discovery.nearest_facility_isochrone_catchment_analysis",
        prims["catchment"],
        {"facilities": facilities, "demand_points": demand,
         "travel_policy": {"max_km": cfg["max_km"], "method": "straight_line_haversine_proxy"}},
        effects=["none"], mode="pure_local",
    )
    covered_ids = {a["demand_id"] for a in catch_out["assignments"]
                   if a["distance_km"] <= cfg["max_km"]}
    map_points = (
        [{"id": f["id"], "lat": f["lat"], "lon": f["lon"], "label_class": "facility"}
         for f in facilities]
        + [{"id": d["id"], "lat": d["lat"], "lon": d["lon"],
            "label_class": "covered" if d["id"] in covered_ids else "uncovered"}
           for d in demand]
    )
    map_out, _ = ctx.exec(
        "prim:place_discovery.map_artifact_generation", prims["map"],
        {"title": f"Care access proxy map - {aoi_id} (synthetic fixture data)",
         "boundary": load_boundary(aoi_id), "points": map_points,
         "attribution": "Synthetic fixture data; boundary synthetic; distances are straight-line proxies"},
        effects=["none"], mode="pure_local",
    )
    digest = ctx.save_artifact(f"care_desert_{aoi_id.split(':')[1]}.svg", map_out["svg"])
    answer = {
        "question_family": "care_desert_analysis",
        "aoi_id": aoi_id,
        "coverage_report": catch_out["coverage_report"],
        "method": catch_out["method"],
        "map_artifact_sha256": digest,
    }
    ctx.exec(
        "prim:place_discovery.evidence_bundle_wrapper", prims["evidence"],
        {"answer": answer, "source_snapshots": ctx.snapshot_meta,
         "uncertainty_notes": ["straight-line haversine distance is a proxy - road travel time not modeled",
                               "demand points are synthetic fixtures, not census population data"],
         "attributions": [m.get("attribution", "") for m in ctx.snapshot_meta]},
        effects=["none"], mode="pure_local",
    )
    cr = catch_out["coverage_report"]
    ok = cr["total_population"] > 0 and cr["covered_population"] + cr["uncovered_population"] == cr["total_population"]
    return ok, f"coverage_ratio={cr['coverage_ratio']:.2f} (fixture demand, proxy distance)"


def run_osm_poi(ctx: TaskContext, aoi_id: str, prims: dict) -> tuple[bool, str]:
    cfg = AOI_FIXTURES[aoi_id]
    gate_out, _ = ctx.exec(
        "prim:place_discovery.geocode_policy_gate", prims["gate"],
        {"provider": "overpass_public", "planned_request_count": 1, "bulk_job": False,
         "attribution_planned": True},
        effects=["none"], mode="pure_local",
    )
    if gate_out["decision"].startswith("deny"):
        return False, f"policy gate denied: {gate_out['decision']}"
    transport = prims["FixtureTransport"](str(FIXTURE_ROOT))
    osm_out, _ = ctx.exec(
        "prim:place_discovery.osm_overpass_bounded_poi_query",
        lambda p: prims["overpass"](p, transport),
        {"bbox": cfg["bbox"], "tags": {"amenity": "clinic"}, "fixture_name": cfg["overpass"]},
        effects=["network_read"], mode="fixture_offline",
    )
    records = [poi_to_record(p, i) if "record_id" not in p else p
               for i, p in enumerate(osm_out["records"])]
    dedupe_out, _ = ctx.exec(
        "prim:place_discovery.entity_normalize_and_dedupe", prims["dedupe"],
        {"records": records,
         "match_policy": {"name_similarity_threshold": 0.85, "max_distance_m": 250.0,
                          "require_same_zip5": False}},
        effects=["none"], mode="pure_local",
    )
    points = [{"id": e["entity_id"], "lat": e["lat"], "lon": e["lon"]}
              for e in dedupe_out["entities"] if e.get("lat") is not None]
    join_out, _ = ctx.exec(
        "prim:place_discovery.point_to_boundary_spatial_join", prims["spatial_join"],
        {"points": points, "boundaries": {"type": "FeatureCollection",
                                          "features": [load_boundary(aoi_id)]}},
        effects=["none"], mode="pure_local",
    )
    answer = {
        "question_family": "osm_poi_extraction",
        "aoi_id": aoi_id,
        "policy_gate_decision": gate_out["decision"],
        "pois_extracted": len(records),
        "entities_after_dedupe": len(dedupe_out["entities"]),
        "in_boundary": sum(1 for p in join_out["joined_points"] if p.get("boundary_id") == aoi_id),
    }
    ctx.exec(
        "prim:place_discovery.evidence_bundle_wrapper", prims["evidence"],
        {"answer": answer, "source_snapshots": ctx.snapshot_meta,
         "uncertainty_notes": ["OSM tag completeness varies by region"],
         "attributions": [m.get("attribution", "") for m in ctx.snapshot_meta]},
        effects=["none"], mode="pure_local",
    )
    return answer["pois_extracted"] >= 1, f"{answer['pois_extracted']} POIs, {answer['in_boundary']} in boundary"


def run_portal_harvest(ctx: TaskContext, aoi_id: str, prims: dict) -> tuple[bool, str]:
    transport = prims["FixtureTransport"](str(FIXTURE_ROOT))
    ckan_out, _ = ctx.exec(
        "prim:place_discovery.ckan_package_resource_harvester",
        lambda p: prims["ckan"](p, transport),
        {"query": "health facilities", "fixture_name": "ckan_package_search_health.json"},
        effects=["network_read"], mode="fixture_offline",
    )
    soc_out, _ = ctx.exec(
        "prim:place_discovery.socrata_soql_dataset_ingester",
        lambda p: prims["socrata"](p, transport),
        {"domain": "data.example.gov", "dataset_id": "abcd-1234",
         "soql": "SELECT * LIMIT 100", "fixture_name": "socrata_health_inspections.json"},
        effects=["network_read"], mode="fixture_offline",
    )
    fp_out, _ = ctx.exec(
        "prim:place_discovery.dataset_schema_fingerprint", prims["fingerprint"],
        {"dataset_id": "socrata:abcd-1234", "records": soc_out["records"]},
        effects=["none"], mode="pure_local",
    )
    unlicensed = [d for d in ckan_out["datasets"] if d.get("requires_license_review")]
    answer = {
        "question_family": "portal_dataset_harvest",
        "aoi_id": aoi_id,
        "datasets_found": len(ckan_out["datasets"]),
        "datasets_requiring_license_review": len(unlicensed),
        "ingested_dataset_fingerprint": fp_out["fingerprint_hash"],
        "ingested_rows": fp_out["row_count"],
    }
    ctx.exec(
        "prim:place_discovery.evidence_bundle_wrapper", prims["evidence"],
        {"answer": answer, "source_snapshots": ctx.snapshot_meta,
         "uncertainty_notes": [f"{len(unlicensed)} dataset(s) lack explicit license and require review before reuse"],
         "attributions": [m.get("attribution", "") for m in ctx.snapshot_meta]},
        effects=["none"], mode="pure_local",
    )
    return answer["datasets_found"] >= 1 and answer["ingested_rows"] >= 1, (
        f"{answer['datasets_found']} datasets, {answer['datasets_requiring_license_review']} need license review")


def run_schema_drift(ctx: TaskContext, aoi_id: str, prims: dict) -> tuple[bool, str]:
    transport = prims["FixtureTransport"](str(FIXTURE_ROOT))
    soc_out, _ = ctx.exec(
        "prim:place_discovery.socrata_soql_dataset_ingester",
        lambda p: prims["socrata"](p, transport),
        {"domain": "data.example.gov", "dataset_id": "abcd-1234",
         "soql": "SELECT * LIMIT 100", "fixture_name": "socrata_health_inspections.json"},
        effects=["network_read"], mode="fixture_offline",
    )
    rows = soc_out["records"]
    fp1_out, _ = ctx.exec(
        "prim:place_discovery.dataset_schema_fingerprint", prims["fingerprint"],
        {"dataset_id": "socrata:abcd-1234@t0", "records": rows},
        effects=["none"], mode="pure_local",
    )
    # Synthetic drift injection (harness-side, disclosed): rename one field,
    # drop another. This exercises drift DETECTION mechanics only.
    fields = sorted(fp1_out["fields"])
    renamed, dropped = fields[0], fields[-1]
    drifted = []
    for r in rows:
        r2 = {(f"{renamed}_v2" if k == renamed else k): v for k, v in r.items() if k != dropped}
        drifted.append(r2)
    fp2_out, _ = ctx.exec(
        "prim:place_discovery.dataset_schema_fingerprint", prims["fingerprint"],
        {"dataset_id": "socrata:abcd-1234@t1", "records": drifted},
        effects=["none"], mode="pure_local",
    )
    added = sorted(set(fp2_out["fields"]) - set(fp1_out["fields"]))
    removed = sorted(set(fp1_out["fields"]) - set(fp2_out["fields"]))
    drift_detected = fp1_out["fingerprint_hash"] != fp2_out["fingerprint_hash"]
    answer = {
        "question_family": "schema_drift_detection",
        "aoi_id": aoi_id,
        "drift_detected": drift_detected,
        "fields_added": added,
        "fields_removed": removed,
        "note": "drift injected synthetically by harness to exercise detection; comparison computed harness-side",
    }
    ctx.exec(
        "prim:place_discovery.evidence_bundle_wrapper", prims["evidence"],
        {"answer": answer, "source_snapshots": ctx.snapshot_meta,
         "uncertainty_notes": ["drift scenario is synthetic",
                               "GAP: dedicated schema_drift_compare primitive not yet implemented - diff computed in harness"],
         "attributions": [m.get("attribution", "") for m in ctx.snapshot_meta]},
        effects=["none"], mode="pure_local",
    )
    ok = (drift_detected and f"{renamed}_v2" in added
          and renamed in removed and dropped in removed)
    return ok, f"drift detected: +{added} -{removed}"


def run_map_dashboard(ctx: TaskContext, aoi_id: str, prims: dict) -> tuple[bool, str]:
    cfg = AOI_FIXTURES[aoi_id]
    transport = prims["FixtureTransport"](str(FIXTURE_ROOT))
    hrsa_out, _ = ctx.exec(
        "prim:place_discovery.hrsa_health_center_ingester",
        lambda p: prims["hrsa"](p, transport),
        {"aoi_id": aoi_id, "state": cfg["state"], "fixture_name": cfg["hrsa"]},
        effects=["network_read"], mode="fixture_offline",
    )
    facilities = [{"id": r["record_id"], "lat": r["lat"], "lon": r["lon"]}
                  for r in hrsa_out["records"]]
    demand = load_demand_points(aoi_id)
    catch_out, _ = ctx.exec(
        "prim:place_discovery.nearest_facility_isochrone_catchment_analysis",
        prims["catchment"],
        {"facilities": facilities, "demand_points": demand,
         "travel_policy": {"max_km": cfg["max_km"], "method": "straight_line_haversine_proxy"}},
        effects=["none"], mode="pure_local",
    )
    covered_ids = {a["demand_id"] for a in catch_out["assignments"]
                   if a["distance_km"] <= cfg["max_km"]}
    map_points = (
        [{"id": f["id"], "lat": f["lat"], "lon": f["lon"], "label_class": "facility"}
         for f in facilities]
        + [{"id": d["id"], "lat": d["lat"], "lon": d["lon"],
            "label_class": "covered" if d["id"] in covered_ids else "uncovered"}
           for d in demand]
    )
    map_out, _ = ctx.exec(
        "prim:place_discovery.map_artifact_generation", prims["map"],
        {"title": f"Facility dashboard map - {aoi_id} (synthetic fixture data)",
         "boundary": load_boundary(aoi_id), "points": map_points,
         "attribution": "Synthetic fixture data; straight-line proxy distances"},
        effects=["none"], mode="pure_local",
    )
    digest = ctx.save_artifact(f"dashboard_{aoi_id.split(':')[1]}.svg", map_out["svg"])
    answer = {
        "question_family": "map_dashboard_generation",
        "aoi_id": aoi_id,
        "facilities_mapped": len(facilities),
        "demand_points_mapped": len(demand),
        "map_artifact_sha256": digest,
        "points_rendered": map_out["artifact_stats"]["points_rendered"],
    }
    ctx.exec(
        "prim:place_discovery.evidence_bundle_wrapper", prims["evidence"],
        {"answer": answer, "source_snapshots": ctx.snapshot_meta,
         "uncertainty_notes": ["map renders synthetic fixture geometry"],
         "attributions": [m.get("attribution", "") for m in ctx.snapshot_meta]},
        effects=["none"], mode="pure_local",
    )
    ok = map_out["artifact_stats"]["points_rendered"] == len(map_points)
    return ok, f"map rendered {map_out['artifact_stats']['points_rendered']} points"


def run_training_provider_discovery(ctx: TaskContext, aoi_id: str, prims: dict) -> tuple[bool, str]:
    cfg = AOI_FIXTURES[aoi_id]
    transport = prims["FixtureTransport"](str(FIXTURE_ROOT))
    gate_out, _ = ctx.exec(
        "prim:place_discovery.geocode_policy_gate", prims["gate"],
        {"provider": "census_geocoder", "planned_request_count": 50, "bulk_job": False,
         "attribution_planned": True},
        effects=["none"], mode="pure_local",
    )
    cos_out, _ = ctx.exec(
        "prim:place_discovery.careeronestop_training_provider_adapter",
        lambda p: prims["careeronestop"](p, transport),
        {"aoi_id": aoi_id, "state": cfg["state"], "program_keyword": "nursing",
         "fixture_name": cfg["careeronestop"]},
        effects=["network_read"], mode="fixture_offline",
    )
    csc_out, _ = ctx.exec(
        "prim:place_discovery.college_scorecard_ipeds_program_adapter",
        lambda p: prims["college_scorecard"](p, transport),
        {"aoi_id": aoi_id, "state": cfg["state"], "program_cip_prefix": "5138",
         "fixture_name": cfg["college_scorecard"]},
        effects=["network_read"], mode="fixture_offline",
    )
    all_records = list(cos_out["records"]) + list(csc_out["records"])
    dedupe_out, _ = ctx.exec(
        "prim:place_discovery.entity_normalize_and_dedupe", prims["dedupe"],
        {"records": all_records,
         "match_policy": {"name_similarity_threshold": 0.85, "max_distance_m": 500.0,
                          "require_same_zip5": False}},
        effects=["none"], mode="pure_local",
    )
    wioa_count = sum(1 for r in cos_out["records"] if r.get("wioa_eligible"))
    answer = {
        "question_family": "training_provider_discovery",
        "aoi_id": aoi_id,
        "providers_found": len(cos_out["records"]),
        "institutions_found": len(csc_out["records"]),
        "providers_resolved": len(dedupe_out["entities"]),
        "duplicates_merged": dedupe_out["stats"]["duplicates_merged"],
        "wioa_eligible_count": wioa_count,
        "eligibility_note": cos_out.get("eligibility_note", ""),
        "policy_gate_decision": gate_out["decision"],
    }
    ctx.exec(
        "prim:place_discovery.evidence_bundle_wrapper", prims["evidence"],
        {"answer": answer, "source_snapshots": ctx.snapshot_meta,
         "uncertainty_notes": [
             "ETPL/WIOA eligibility is state-maintained and time-sensitive; verify against the state list",
             "program filtering uses CIP prefix matching only"],
         "attributions": [m.get("attribution", "") for m in ctx.snapshot_meta]},
        effects=["none"], mode="pure_local",
    )
    ok = (answer["providers_found"] >= 1 and answer["institutions_found"] >= 1
          and answer["providers_resolved"] >= 1)
    return ok, (f"{answer['providers_resolved']} providers resolved, "
                f"{answer['wioa_eligible_count']} WIOA-flagged, "
                f"{answer['duplicates_merged']} duplicates merged")


def run_site_selection(ctx: TaskContext, aoi_id: str, prims: dict) -> tuple[bool, str]:
    cfg = AOI_FIXTURES[aoi_id]
    transport = prims["FixtureTransport"](str(FIXTURE_ROOT))
    hrsa_out, _ = ctx.exec(
        "prim:place_discovery.hrsa_health_center_ingester",
        lambda p: prims["hrsa"](p, transport),
        {"aoi_id": aoi_id, "state": cfg["state"], "fixture_name": cfg["hrsa"]},
        effects=["network_read"], mode="fixture_offline",
    )
    dedupe_out, _ = ctx.exec(
        "prim:place_discovery.entity_normalize_and_dedupe", prims["dedupe"],
        {"records": hrsa_out["records"],
         "match_policy": {"name_similarity_threshold": 0.85, "max_distance_m": 300.0,
                          "require_same_zip5": False}},
        effects=["none"], mode="pure_local",
    )
    facilities = [{"id": e["entity_id"], "lat": e["lat"], "lon": e["lon"]}
                  for e in dedupe_out["entities"] if e.get("lat") is not None]
    demand = load_demand_points(aoi_id)
    # Site selection uses a deliberately tighter access threshold than the
    # care-desert family so genuine gap candidates exist to rank; the policy
    # choice is recorded in the payload and method receipts.
    site_max_km = cfg["max_km"] / 3.0
    catch_out, _ = ctx.exec(
        "prim:place_discovery.nearest_facility_isochrone_catchment_analysis",
        prims["catchment"],
        {"facilities": facilities, "demand_points": demand,
         "travel_policy": {"max_km": site_max_km, "method": "straight_line_haversine_proxy"}},
        effects=["none"], mode="pure_local",
    )
    rank_out, _ = ctx.exec(
        "prim:place_discovery.coverage_gap_ranker", prims["gap_ranker"],
        {"coverage_report": catch_out["coverage_report"],
         "assignments": catch_out["assignments"],
         "demand_points": demand,
         "facilities": facilities,
         "ranking_policy": {"max_km": site_max_km, "top_n": 5,
                            "weights": {"uncovered_population": 0.7,
                                        "distance_beyond_threshold": 0.3}}},
        effects=["none"], mode="pure_local",
    )
    ranked = rank_out["ranked_gap_areas"]
    map_points = (
        [{"id": f["id"], "lat": f["lat"], "lon": f["lon"], "label_class": "facility"}
         for f in facilities]
        + [{"id": g["demand_id"], "lat": g["lat"], "lon": g["lon"],
            "label_class": "uncovered"} for g in ranked]
    )
    map_out, _ = ctx.exec(
        "prim:place_discovery.map_artifact_generation", prims["map"],
        {"title": f"Ranked site candidates - {aoi_id} (synthetic fixture data)",
         "boundary": load_boundary(aoi_id), "points": map_points,
         "attribution": "Synthetic fixture data; straight-line proxy distances; suitability factors not modeled"},
        effects=["none"], mode="pure_local",
    )
    digest = ctx.save_artifact(f"site_selection_{aoi_id.split(':')[1]}.svg", map_out["svg"])
    answer = {
        "question_family": "site_selection_ranking",
        "aoi_id": aoi_id,
        "ranked_site_candidates": ranked,
        "tradeoff_report": rank_out["tradeoff_report"],
        "method": rank_out["method"],
        "map_artifact_sha256": digest,
    }
    ctx.exec(
        "prim:place_discovery.evidence_bundle_wrapper", prims["evidence"],
        {"answer": answer, "source_snapshots": ctx.snapshot_meta,
         "uncertainty_notes": [
             "ranking inherits the straight-line distance proxy",
             "site suitability factors (zoning, transit, cost) are not modeled",
             "demand points are synthetic fixtures, not census population data"],
         "attributions": [m.get("attribution", "") for m in ctx.snapshot_meta]},
        effects=["none"], mode="pure_local",
    )
    cr = catch_out["coverage_report"]
    ok = (len(ranked) >= 1 or cr["coverage_ratio"] == 1.0)
    return ok, f"{len(ranked)} gap areas ranked (threshold {site_max_km:.1f} km)"


FAMILY_RUNNERS = {
    "clinic_discovery": run_clinic_discovery,
    "training_provider_discovery": run_training_provider_discovery,
    "care_desert_analysis": run_care_desert,
    "osm_poi_extraction": run_osm_poi,
    "portal_dataset_harvest": run_portal_harvest,
    "schema_drift_detection": run_schema_drift,
    "site_selection_ranking": run_site_selection,
    "map_dashboard_generation": run_map_dashboard,
}


def import_primitives() -> dict:
    from primitives.adapters.transport import FixtureTransport
    from primitives.adapters.hrsa import hrsa_health_center_ingester
    from primitives.adapters.nppes import nppes_provider_identity_resolver
    from primitives.adapters.ckan import ckan_package_resource_harvester
    from primitives.adapters.socrata import socrata_soql_dataset_ingester
    from primitives.adapters.overpass import osm_overpass_bounded_poi_query
    from primitives.adapters.careeronestop import careeronestop_training_provider_adapter
    from primitives.adapters.college_scorecard import college_scorecard_ipeds_program_adapter
    from primitives.entity import entity_normalize_and_dedupe
    from primitives.fingerprint import dataset_schema_fingerprint
    from primitives.gates import geocode_policy_gate
    from primitives.evidence import evidence_bundle_wrapper
    from primitives.ranking import coverage_gap_ranker
    from primitives.spatial import nearest_facility_catchment, point_to_boundary_spatial_join
    from primitives.maps import map_artifact_generation

    return {
        "FixtureTransport": FixtureTransport,
        "hrsa": hrsa_health_center_ingester,
        "nppes": nppes_provider_identity_resolver,
        "ckan": ckan_package_resource_harvester,
        "socrata": socrata_soql_dataset_ingester,
        "overpass": osm_overpass_bounded_poi_query,
        "careeronestop": careeronestop_training_provider_adapter,
        "college_scorecard": college_scorecard_ipeds_program_adapter,
        "dedupe": entity_normalize_and_dedupe,
        "fingerprint": dataset_schema_fingerprint,
        "gate": geocode_policy_gate,
        "evidence": evidence_bundle_wrapper,
        "gap_ranker": coverage_gap_ranker,
        "spatial_join": point_to_boundary_spatial_join,
        "catchment": nearest_facility_catchment,
        "map": map_artifact_generation,
    }


def select_tasks() -> list[dict]:
    tasks = [json.loads(line) for line in
             (PACK_DIR / "benchmark_task_demands.jsonl").read_text(encoding="utf-8").splitlines()
             if line.strip()]
    selected = [t for t in tasks
                if t["task_family"] in RUNNABLE_FAMILIES
                and t["area_of_interest"]["aoi_id"] in AOI_FIXTURES]
    selected.sort(key=lambda t: t["task_id"])
    return selected


def proof_stats(receipts: list[dict]) -> tuple[int, int]:
    total = sum(len(r["proof_results"]) for r in receipts)
    passed = sum(1 for r in receipts for p in r["proof_results"] if p["passed"])
    return passed, total


def run_benchmark(write: bool) -> dict:
    run_id = "run-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = RUNS_ROOT / run_id
    artifacts_dir = run_dir / "artifacts" if write else None
    prims = import_primitives()
    tasks = select_tasks()
    locks = compile_plan_locks()

    scorecards: list[dict] = []
    all_receipts: list[dict] = []
    negative_memories: list[dict] = []
    primitives_seen: set[str] = set()

    for task in tasks:
        aoi_id = task["area_of_interest"]["aoi_id"]
        family = task["task_family"]
        lock = locks[family]
        ctx = TaskContext(run_id, artifacts_dir)
        t0 = time.perf_counter()
        error_note = ""
        try:
            success, note = FAMILY_RUNNERS[family](ctx, aoi_id, prims)
        except PrimitiveExecutionError as exc:
            ctx.receipts.append(exc.receipt)
            success, note = False, f"primitive failed: {exc}"
            error_note = str(exc)
        wall = time.perf_counter() - t0

        executed = [r["primitive_id"] for r in ctx.receipts]
        expected = [s["primitive_id"] for s in lock["route"]]
        sequence_ok = executed == expected
        if success and not sequence_ok:
            success = False
            error_note = (error_note + " | executed sequence does not match PlanLock "
                          f"{lock['lock_id']}").strip(" |")

        # Replay proof: a second execution of the same lock against the same
        # inputs must produce the identical output-hash sequence. Artifacts
        # are not re-persisted for the replay pass.
        replay_verified = False
        if success:
            replay_ctx = TaskContext(run_id, None)
            try:
                FAMILY_RUNNERS[family](replay_ctx, aoi_id, prims)
                replay_verified = (
                    [r["output_hash"] for r in ctx.receipts]
                    == [r["output_hash"] for r in replay_ctx.receipts])
            except PrimitiveExecutionError:
                replay_verified = False
            if not replay_verified:
                success = False
                error_note = (error_note + " | replay produced different output hashes"
                              ).strip(" |")

        if not success:
            negative_memories.append({
                "record_type": "negative_memory",
                "memory_id": ("negmem:place_discovery.task_failure."
                              f"{family}.{aoi_id.split(':')[1]}"),
                "failure_class": "benchmark_task_failure",
                "description": (f"Task {task['task_id']} failed under arm {ARM_ID}: "
                                + (error_note or note)),
                "affected_primitive_ids": sorted(set(executed)) or
                    [f"prim:place_discovery.{FAMILY_ROUTES[family][0]}"],
                "affected_task_families": [family],
                "evidence_refs": [run_id],
                "suppression_rule": (f"re-verify the {family} route against "
                                     f"{lock['lock_id']} before reusing it for this area"),
                "resolution_status": "open",
                "fixed_by": None,
                "version": "0.1.0",
                "candidate": True,
                "serves_truth": False,
            })

        reuse = sum(1 for p in set(executed) if p in primitives_seen)
        primitives_seen.update(executed)
        passed, total = proof_stats(ctx.receipts)

        scorecard = {
            "record_type": "place_discovery_benchmark_scorecard",
            "scorecard_id": "score:" + hashlib.sha256(
                f"{task['task_id']}|{ARM_ID}|{run_id}".encode()).hexdigest()[:16],
            "task_id": task["task_id"],
            "task_family": family,
            "arm_id": ARM_ID,
            "run_id": run_id,
            "measured": True,
            "execution_mode": "fixture_offline",
            "task_success": bool(success),
            "wall_clock_seconds": round(wall, 4),
            "depth_to_solution": DEPTH,
            "runtime_llm_tokens": 0,
            "primitives_executed": sorted(set(executed)),
            "primitive_reuse_count": reuse,
            "proof_coverage": round(passed / total, 4) if total else 0.0,
            "receipt_ids": [r["receipt_id"] for r in ctx.receipts],
            "artifacts_emitted": ctx.artifact_files,
            "plan_lock_id": lock["lock_id"],
            "route_hash": lock["route_hash"],
            "replay_verified": replay_verified,
            "notes": (note + (" | " + error_note if error_note else "")
                      + " | fixture_offline: synthetic fixtures measure route machinery, not real-world accuracy"
                      + " | arms A1/A2 not run (require model-in-loop harness)"),
            "candidate": True,
            "serves_truth": False,
        }
        scorecards.append(scorecard)
        all_receipts.extend(ctx.receipts)

    gap_records = [
        {
            "record_type": "place_discovery_gap_record",
            "gap_id": f"gap:{fam}",
            "task_family": fam,
            "reason": "family not runnable offline - missing components",
            "missing": missing,
            "signal": "benchmark_harness_coverage_hole",
            "candidate": True,
            "serves_truth": False,
        }
        for fam, missing in UNRUNNABLE_FAMILIES.items()
    ]

    summary = {
        "run_id": run_id,
        "arm_id": ARM_ID,
        "execution_mode": "fixture_offline",
        "tasks_executed": len(scorecards),
        "tasks_succeeded": sum(1 for s in scorecards if s["task_success"]),
        "replay_verified_count": sum(1 for s in scorecards if s["replay_verified"]),
        "plan_locks_compiled": len(locks),
        "total_receipts": len(all_receipts),
        "total_proofs_passed": sum(1 for r in all_receipts for p in r["proof_results"] if p["passed"]),
        "total_proofs": sum(len(r["proof_results"]) for r in all_receipts),
        "distinct_primitives_executed": sorted(primitives_seen),
        "runtime_llm_tokens_total": 0,
        "gap_records": len(gap_records),
        "negative_memories_created": len(negative_memories),
        "families_not_run": sorted(UNRUNNABLE_FAMILIES),
        "honesty_notes": [
            "fixture_offline run: synthetic fixtures, measures route machinery only",
            "baseline arms A1/A2 not run; no baseline comparison is claimed",
            "no token-savings claim can be made from this run alone",
            "replay_verified means a second execution reproduced identical output hashes",
        ],
    }

    if write:
        run_dir.mkdir(parents=True, exist_ok=True)
        files = {
            "scorecards.jsonl": "".join(json.dumps(s) + "\n" for s in scorecards),
            "receipts.jsonl": "".join(json.dumps(r) + "\n" for r in all_receipts),
            "gap_records.jsonl": "".join(json.dumps(g) + "\n" for g in gap_records),
            "plan_locks.jsonl": "".join(
                json.dumps(locks[fam]) + "\n" for fam in sorted(locks)),
            "negative_memory.jsonl": "".join(
                json.dumps(m) + "\n" for m in negative_memories),
            "run_summary.json": json.dumps(summary, indent=2) + "\n",
        }
        for name, content in files.items():
            (run_dir / name).write_text(content, encoding="utf-8")
        manifest = {
            "run_id": run_id,
            "generated_by": "scripts/run_place_discovery_benchmark.py",
            "files": {name: {"rows": content.count("\n") if name.endswith(".jsonl") else 1,
                             "content_sha256": hashlib.sha256(content.encode()).hexdigest()}
                      for name, content in files.items()},
            "artifact_files": sorted(p.name for p in (artifacts_dir.glob("*") if artifacts_dir and artifacts_dir.exists() else [])),
            "candidate": True,
            "serves_truth": False,
        }
        (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        summary["run_dir"] = str(run_dir.relative_to(REPO_ROOT))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="execute and persist the run")
    parser.add_argument("--self-test", action="store_true", help="execute in memory, persist nothing")
    args = parser.parse_args()
    if not (args.write or args.self_test):
        parser.print_help()
        return 2
    summary = run_benchmark(write=args.write)
    print(json.dumps(summary, indent=2))
    ok = summary["tasks_succeeded"] == summary["tasks_executed"] and summary["tasks_executed"] > 0
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
