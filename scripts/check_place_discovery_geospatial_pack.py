#!/usr/bin/env python3
"""Checker for the place-discovery-geospatial seed pack.

Validates the emitted pack against the repo schemas and enforces the
lane invariants:

  - every row is candidate=true and serves_truth=false
  - every row validates against its JSON schema (structural validator,
    dependency-free)
  - manifest row counts and content hashes match the files on disk
    (a mismatch means someone hand-edited a generated file - regenerate
    with the builder instead)
  - referential integrity: primitive cards only reference source_ids
    that exist; groups and benchmark tasks only reference primitive_ids
    that exist
  - all 18 P0 primitives are present with build order 1..18 exactly once
  - benchmark pack contains 8 task families x 40 areas of interest
  - no forbidden claim language in descriptive fields (rows must not
    assert measured savings/results)

Usage:
    python3 scripts/check_place_discovery_geospatial_pack.py --self-test
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "place-discovery-geospatial-seeds"
SCHEMA_DIR = REPO_ROOT / "schemas"

FILE_TO_SCHEMA = {
    "source_surfaces.jsonl": "source_surface.schema.json",
    "primitive_cards.jsonl": "primitive_card.schema.json",
    "primitive_groups.jsonl": "primitive_group.schema.json",
    "variation_overlays.jsonl": "variation_overlay.schema.json",
    "benchmark_task_demands.jsonl": "benchmark_task_demand.schema.json",
}

CANONICAL_P0_IDS = [
    "prim:place_discovery.source_surface_registry",
    "prim:place_discovery.ckan_package_resource_harvester",
    "prim:place_discovery.socrata_soql_dataset_ingester",
    "prim:place_discovery.arcgis_featureserver_layer_ingester",
    "prim:place_discovery.hrsa_health_center_ingester",
    "prim:place_discovery.nppes_provider_identity_resolver",
    "prim:place_discovery.careeronestop_training_provider_adapter",
    "prim:place_discovery.college_scorecard_ipeds_program_adapter",
    "prim:place_discovery.osm_overpass_bounded_poi_query",
    "prim:place_discovery.overture_openaddresses_place_ingester",
    "prim:place_discovery.dataset_schema_fingerprint",
    "prim:place_discovery.entity_normalize_and_dedupe",
    "prim:place_discovery.geocode_policy_gate",
    "prim:place_discovery.point_to_boundary_spatial_join",
    "prim:place_discovery.nearest_facility_isochrone_catchment_analysis",
    "prim:place_discovery.map_artifact_generation",
    "prim:place_discovery.evidence_bundle_wrapper",
    "prim:place_discovery.portal_change_monitor",
]

TASK_FAMILIES = [
    "clinic_discovery",
    "training_provider_discovery",
    "care_desert_analysis",
    "portal_dataset_harvest",
    "osm_poi_extraction",
    "schema_drift_detection",
    "site_selection_ranking",
    "map_dashboard_generation",
]

# Rows are candidate seed material; descriptive text must not assert
# measured outcomes. These phrases indicate an unmeasured claim.
FORBIDDEN_CLAIM_PATTERNS = [
    re.compile(r"\b\d+(\.\d+)?x\s+(faster|cheaper|reduction)", re.IGNORECASE),
    re.compile(r"\bproven to\b", re.IGNORECASE),
    re.compile(r"\bguarantee[sd]?\b", re.IGNORECASE),
    re.compile(r"\btokens? saved\b", re.IGNORECASE),
]


class StructuralValidator:
    """Minimal dependency-free JSON Schema validator covering the subset
    used by this repo's schemas: type, enum, const, required, properties,
    additionalProperties(false), items, minItems, maxItems, minLength,
    minimum, maximum, pattern, and ["type","null"] unions."""

    def __init__(self, schema: dict):
        self.schema = schema

    def validate(self, instance, schema=None, path="$") -> list:
        schema = self.schema if schema is None else schema
        errors = []

        if "const" in schema:
            if instance != schema["const"]:
                errors.append(f"{path}: expected const {schema['const']!r}, got {instance!r}")
            return errors
        if "enum" in schema:
            if instance not in schema["enum"]:
                errors.append(f"{path}: {instance!r} not in enum")
            return errors

        stype = schema.get("type")
        if stype is not None:
            types = stype if isinstance(stype, list) else [stype]
            if not any(self._is_type(instance, t) for t in types):
                errors.append(f"{path}: expected type {types}, got {type(instance).__name__}")
                return errors

        if isinstance(instance, str):
            if "minLength" in schema and len(instance) < schema["minLength"]:
                errors.append(f"{path}: string shorter than minLength {schema['minLength']}")
            if "pattern" in schema and not re.search(schema["pattern"], instance):
                errors.append(f"{path}: does not match pattern {schema['pattern']!r}")
        if isinstance(instance, (int, float)) and not isinstance(instance, bool):
            if "minimum" in schema and instance < schema["minimum"]:
                errors.append(f"{path}: below minimum {schema['minimum']}")
            if "maximum" in schema and instance > schema["maximum"]:
                errors.append(f"{path}: above maximum {schema['maximum']}")
        if isinstance(instance, list):
            if "minItems" in schema and len(instance) < schema["minItems"]:
                errors.append(f"{path}: fewer than minItems {schema['minItems']}")
            if "maxItems" in schema and len(instance) > schema["maxItems"]:
                errors.append(f"{path}: more than maxItems {schema['maxItems']}")
            if "items" in schema:
                for i, item in enumerate(instance):
                    errors.extend(self.validate(item, schema["items"], f"{path}[{i}]"))
        if isinstance(instance, dict):
            for req in schema.get("required", []):
                if req not in instance:
                    errors.append(f"{path}: missing required field {req!r}")
            props = schema.get("properties", {})
            for key, value in instance.items():
                if key in props:
                    errors.extend(self.validate(value, props[key], f"{path}.{key}"))
                elif schema.get("additionalProperties") is False:
                    errors.append(f"{path}: unexpected field {key!r}")
                elif isinstance(schema.get("additionalProperties"), dict):
                    errors.extend(self.validate(value, schema["additionalProperties"], f"{path}.{key}"))
        return errors

    @staticmethod
    def _is_type(instance, t: str) -> bool:
        if t == "object":
            return isinstance(instance, dict)
        if t == "array":
            return isinstance(instance, list)
        if t == "string":
            return isinstance(instance, str)
        if t == "integer":
            return isinstance(instance, int) and not isinstance(instance, bool)
        if t == "number":
            return isinstance(instance, (int, float)) and not isinstance(instance, bool)
        if t == "boolean":
            return isinstance(instance, bool)
        if t == "null":
            return instance is None
        return False


def iter_text_fields(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from iter_text_fields(v)
    elif isinstance(value, list):
        for v in value:
            yield from iter_text_fields(v)


def load_jsonl(path: Path) -> list:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_checks() -> dict:
    problems: list[str] = []
    counts: dict[str, int] = {}

    manifest_path = PACK_DIR / "manifest.json"
    if not manifest_path.exists():
        return {"ok": False, "problems": [f"missing {manifest_path}"], "counts": {}}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    manifest_validator = StructuralValidator(
        json.loads((SCHEMA_DIR / "pack_manifest.schema.json").read_text(encoding="utf-8"))
    )
    problems += [f"manifest: {e}" for e in manifest_validator.validate(manifest)]

    data: dict[str, list] = {}
    for fname, schema_name in FILE_TO_SCHEMA.items():
        fpath = PACK_DIR / fname
        if not fpath.exists():
            problems.append(f"missing pack file {fname}")
            continue
        raw = fpath.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        rows = load_jsonl(fpath)
        data[fname] = rows
        counts[fname] = len(rows)

        mf = manifest.get("files", {}).get(fname)
        if not mf:
            problems.append(f"{fname}: not listed in manifest")
        else:
            if mf.get("rows") != len(rows):
                problems.append(f"{fname}: manifest rows={mf.get('rows')} but file has {len(rows)}")
            if mf.get("content_sha256") != digest:
                problems.append(
                    f"{fname}: content hash mismatch - generated file was hand-edited; "
                    "regenerate via the builder"
                )

        validator = StructuralValidator(
            json.loads((SCHEMA_DIR / schema_name).read_text(encoding="utf-8"))
        )
        for i, row in enumerate(rows):
            errs = validator.validate(row)
            for e in errs[:5]:
                problems.append(f"{fname}[{i}]: {e}")
            if row.get("candidate") is not True or row.get("serves_truth") is not False:
                problems.append(f"{fname}[{i}]: violates candidate/serves_truth boundary")
            for text in iter_text_fields(row):
                for pat in FORBIDDEN_CLAIM_PATTERNS:
                    if pat.search(text):
                        problems.append(f"{fname}[{i}]: forbidden claim language: {pat.pattern!r}")

    # Referential integrity.
    source_ids = {r["source_id"] for r in data.get("source_surfaces.jsonl", [])}
    primitive_ids = {r["primitive_id"] for r in data.get("primitive_cards.jsonl", [])}

    for i, card in enumerate(data.get("primitive_cards.jsonl", [])):
        for ref in card.get("source_surface_refs", []):
            if ref not in source_ids:
                problems.append(f"primitive_cards.jsonl[{i}]: unknown source ref {ref}")
    for i, grp in enumerate(data.get("primitive_groups.jsonl", [])):
        for ref in grp.get("member_primitive_refs", []):
            if ref not in primitive_ids:
                problems.append(f"primitive_groups.jsonl[{i}]: unknown primitive ref {ref}")
    for i, task in enumerate(data.get("benchmark_task_demands.jsonl", [])):
        for ref in task.get("primitive_demands", []):
            if ref not in primitive_ids:
                problems.append(f"benchmark_task_demands.jsonl[{i}]: unknown primitive ref {ref}")

    # P0 completeness: all 18 canonical ids, orders 1..18 exactly once.
    p0 = {c["primitive_id"]: c["p0_build_order"] for c in data.get("primitive_cards.jsonl", []) if c.get("p0_build_order")}
    for expected_order, pid in enumerate(CANONICAL_P0_IDS, start=1):
        if pid not in p0:
            problems.append(f"P0 primitive missing: {pid}")
        elif p0[pid] != expected_order:
            problems.append(f"{pid}: p0_build_order={p0[pid]}, expected {expected_order}")
    extra_p0 = set(p0) - set(CANONICAL_P0_IDS)
    if extra_p0:
        problems.append(f"unexpected primitives claim P0 build order: {sorted(extra_p0)}")

    # Benchmark shape: 8 families x 40 AOIs, unique task ids.
    tasks = data.get("benchmark_task_demands.jsonl", [])
    fam_counts: dict[str, int] = {}
    aoi_ids = set()
    task_ids = set()
    for t in tasks:
        fam_counts[t["task_family"]] = fam_counts.get(t["task_family"], 0) + 1
        aoi_ids.add(t["area_of_interest"]["aoi_id"])
        if t["task_id"] in task_ids:
            problems.append(f"duplicate task_id {t['task_id']}")
        task_ids.add(t["task_id"])
    for fam in TASK_FAMILIES:
        if fam_counts.get(fam, 0) != 40:
            problems.append(f"task family {fam}: expected 40 tasks, got {fam_counts.get(fam, 0)}")
    if tasks and len(aoi_ids) != 40:
        problems.append(f"expected 40 distinct areas of interest, got {len(aoi_ids)}")

    # Uniqueness of ids in every file.
    for fname, key in [
        ("source_surfaces.jsonl", "source_id"),
        ("primitive_cards.jsonl", "primitive_id"),
        ("primitive_groups.jsonl", "group_id"),
        ("variation_overlays.jsonl", "overlay_id"),
    ]:
        ids = [r[key] for r in data.get(fname, [])]
        dupes = {x for x in ids if ids.count(x) > 1}
        if dupes:
            problems.append(f"{fname}: duplicate ids {sorted(dupes)}")

    return {"ok": not problems, "problems": problems[:80], "counts": counts,
            "total_rows": sum(counts.values())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run all pack checks")
    args = parser.parse_args()
    if not args.self_test:
        parser.print_help()
        return 2
    result = run_checks()
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
