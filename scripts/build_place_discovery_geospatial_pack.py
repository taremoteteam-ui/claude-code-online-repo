#!/usr/bin/env python3
"""Builder for the place-discovery-geospatial seed pack.

This script is the SINGLE SOURCE for every file under
catalog/knowledge-packs/data/place-discovery-geospatial-seeds/.
Never hand-edit emitted pack files; edit the seed modules under
scripts/seeds/ or this builder, then re-run with --write.

Usage:
    python3 scripts/build_place_discovery_geospatial_pack.py --self-test
    python3 scripts/build_place_discovery_geospatial_pack.py --write

Every emitted row is candidate seed material:
    candidate=true, serves_truth=false
No row may be promoted to truth by this builder. Counts and hashes in
manifest.json are computed, never typed.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SEEDS_DIR = REPO_ROOT / "scripts" / "seeds"
PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "place-discovery-geospatial-seeds"

PACK_ID = "place-discovery-geospatial-seeds"
PACK_VERSION = "0.1.0"
ROW_VERSION = "0.1.0"
GENERATED_BY = "scripts/build_place_discovery_geospatial_pack.py"

SCHEMA_REFS = [
    "schemas/source_surface.schema.json",
    "schemas/primitive_card.schema.json",
    "schemas/primitive_group.schema.json",
    "schemas/variation_overlay.schema.json",
    "schemas/benchmark_task_demand.schema.json",
    "schemas/pack_manifest.schema.json",
]

TASK_FAMILY_ORDER = [
    "clinic_discovery",
    "training_provider_discovery",
    "care_desert_analysis",
    "portal_dataset_harvest",
    "osm_poi_extraction",
    "schema_drift_detection",
    "site_selection_ranking",
    "map_dashboard_generation",
]

DEPTH_LADDER = ["L1", "L2", "L3", "L4", "L5", "L6", "L7"]
DIFFICULTY_CYCLE = ["easy", "medium", "hard"]


def load_seed_module(name: str) -> dict:
    """Load a pure-data seed module by exec'ing it into a namespace."""
    path = SEEDS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"missing seed module: {path}")
    namespace: dict = {}
    code = compile(path.read_text(encoding="utf-8"), str(path), "exec")
    exec(code, namespace)  # noqa: S102 - pure-data modules, repo-controlled
    return namespace


def stamp(row: dict, record_type: str) -> dict:
    """Inject builder-owned fields. Seed rows must not set these."""
    for forbidden in ("record_type", "version", "candidate", "serves_truth"):
        if forbidden in row:
            raise ValueError(
                f"seed row illegally sets builder-owned field {forbidden!r}: "
                f"{row.get('source_id') or row.get('primitive_id') or row.get('group_id') or row.get('overlay_id')}"
            )
    out = {"record_type": record_type}
    out.update(row)
    out["version"] = ROW_VERSION
    out["candidate"] = True
    out["serves_truth"] = False
    return out


def build_source_surfaces() -> list[dict]:
    ns = load_seed_module("source_surfaces_seed.py")
    rows = [stamp(dict(r), "place_discovery_source_surface") for r in ns["SOURCE_SURFACES"]]
    return sorted(rows, key=lambda r: r["source_id"])


def build_primitive_cards() -> list[dict]:
    ns = load_seed_module("primitive_families_seed.py")
    rows = [stamp(dict(r), "place_discovery_primitive_card") for r in ns["PRIMITIVE_FAMILIES"]]
    rows.sort(key=lambda r: (r["p0_build_order"] is None, r["p0_build_order"] or 0, r["primitive_id"]))
    return rows


def build_primitive_groups() -> list[dict]:
    ns = load_seed_module("primitive_groups_seed.py")
    rows = [stamp(dict(r), "place_discovery_primitive_group") for r in ns["PRIMITIVE_GROUPS"]]
    return sorted(rows, key=lambda r: r["group_id"])


def build_variation_overlays() -> list[dict]:
    ns = load_seed_module("variation_overlays_seed.py")
    rows = [stamp(dict(r), "place_discovery_variation_overlay") for r in ns["VARIATION_OVERLAYS"]]
    return sorted(rows, key=lambda r: r["overlay_id"])


def build_benchmark_tasks() -> list[dict]:
    """Cross 8 task families x 40 areas of interest deterministically."""
    ns = load_seed_module("benchmark_dimensions_seed.py")
    families = {f["family_id"]: f for f in ns["TASK_FAMILIES"]}
    aois = ns["AREAS_OF_INTEREST"]
    arms = [a["arm_id"] for a in ns["COMPARISON_ARMS"]]

    missing = [f for f in TASK_FAMILY_ORDER if f not in families]
    if missing:
        raise ValueError(f"benchmark seed missing task families: {missing}")
    if len(aois) != 40:
        raise ValueError(f"expected exactly 40 areas of interest, got {len(aois)}")

    tasks: list[dict] = []
    for family_id in TASK_FAMILY_ORDER:
        fam = families[family_id]
        for idx, aoi in enumerate(aois):
            seq = idx + 1
            question = fam["directed_question_template"].format(aoi=aoi["name"])
            row = {
                "record_type": "place_discovery_benchmark_task_demand",
                "task_id": f"bench:place_discovery.{family_id}.{seq:04d}",
                "task_family": family_id,
                "title": f"{fam['title']} - {aoi['name']}",
                "area_of_interest": {
                    "aoi_id": aoi["aoi_id"],
                    "name": aoi["name"],
                    "aoi_type": aoi["aoi_type"],
                    "state": aoi["state"],
                    "context_tags": list(aoi["context_tags"]),
                },
                "directed_question": question,
                "source_policy": fam["default_source_policy"],
                "expected_artifacts": list(fam["expected_artifacts"]),
                "primitive_demands": list(fam["primitive_demands"]),
                "comparison_arms": list(arms),
                "scorecard_fields": list(fam["scorecard_fields"]),
                "depth_ladder": list(DEPTH_LADDER),
                "difficulty": DIFFICULTY_CYCLE[idx % len(DIFFICULTY_CYCLE)],
                "version": ROW_VERSION,
                "candidate": True,
                "serves_truth": False,
            }
            tasks.append(row)
    return tasks


def jsonl_bytes(rows: list[dict]) -> bytes:
    return "".join(json.dumps(r, ensure_ascii=True, sort_keys=False) + "\n" for r in rows).encode("utf-8")


def build_pack() -> dict[str, bytes]:
    files: dict[str, list[dict]] = {
        "source_surfaces.jsonl": build_source_surfaces(),
        "primitive_cards.jsonl": build_primitive_cards(),
        "primitive_groups.jsonl": build_primitive_groups(),
        "variation_overlays.jsonl": build_variation_overlays(),
        "benchmark_task_demands.jsonl": build_benchmark_tasks(),
    }
    payloads = {name: jsonl_bytes(rows) for name, rows in files.items()}

    manifest = {
        "pack_id": PACK_ID,
        "pack_version": PACK_VERSION,
        "generated_by": GENERATED_BY,
        "schema_refs": SCHEMA_REFS,
        "files": {
            name: {
                "rows": len(files[name]),
                "content_sha256": hashlib.sha256(payloads[name]).hexdigest(),
            }
            for name in sorted(files)
        },
        "row_counts": {name: len(rows) for name, rows in sorted(files.items())},
        "total_rows": sum(len(rows) for rows in files.values()),
        "candidate": True,
        "serves_truth": False,
    }
    payloads["manifest.json"] = (json.dumps(manifest, indent=2, sort_keys=False) + "\n").encode("utf-8")
    return payloads


def self_test() -> int:
    payloads = build_pack()
    manifest = json.loads(payloads["manifest.json"])
    problems = []
    for name, data in payloads.items():
        if name == "manifest.json":
            continue
        rows = [json.loads(line) for line in data.decode("utf-8").splitlines()]
        if manifest["files"][name]["rows"] != len(rows):
            problems.append(f"{name}: manifest row count mismatch")
        for row in rows:
            if row.get("candidate") is not True or row.get("serves_truth") is not False:
                problems.append(f"{name}: row missing candidate/serves_truth boundary")
                break
    if problems:
        print(json.dumps({"ok": False, "problems": problems}, indent=2))
        return 1
    print(json.dumps({"ok": True, "self_test": "builder", "total_rows": manifest["total_rows"]}))
    return 0


def write_pack() -> int:
    payloads = build_pack()
    PACK_DIR.mkdir(parents=True, exist_ok=True)
    for name, data in sorted(payloads.items()):
        (PACK_DIR / name).write_bytes(data)
    manifest = json.loads(payloads["manifest.json"])
    print(
        json.dumps(
            {
                "ok": True,
                "pack_dir": str(PACK_DIR.relative_to(REPO_ROOT)),
                "files_written": sorted(payloads),
                "row_counts": manifest["row_counts"],
                "total_rows": manifest["total_rows"],
            },
            indent=2,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the pack to disk")
    parser.add_argument("--self-test", action="store_true", help="build in memory and verify invariants")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.write:
        return write_pack()
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
