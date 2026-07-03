#!/usr/bin/env python3
"""Builder for the warehouse-analytics lane.

Single source for catalog/knowledge-packs/data/warehouse-analytics-catalog/.
Emits reusable primitive families (dbt / warehouse modeling / data-engineering /
analytics / semantic-layer / multi-set ops), their runtime-shaped resolved
primitives, parameterized templates, and MULTI-WAVE pipeline templates. The
families share a warehouse port vocabulary so they compose on the edge graph;
the pipelines are ordered waves whose typed layering the checker verifies.

Counts/hashes in manifest.json are computed. Every row candidate/serves_truth=false.

Usage:
    python3 scripts/build_warehouse_analytics_pack.py --self-test
    python3 scripts/build_warehouse_analytics_pack.py --write
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SEEDS_DIR = REPO_ROOT / "scripts" / "seeds"
PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "warehouse-analytics-catalog"

PACK_ID = "warehouse-analytics-catalog"
PACK_VERSION = "0.1.0"
ROW_VERSION = "0.1.0"
GENERATED_BY = "scripts/build_warehouse_analytics_pack.py"

SCHEMA_REFS = [
    "schemas/reusable_primitive_family.schema.json",
    "schemas/runtime_wrapper.schema.json",
    "schemas/resolved_primitive.schema.json",
    "schemas/primitive_template.schema.json",
    "schemas/pipeline_wave_template.schema.json",
    "schemas/pack_manifest.schema.json",
]

FAMILY_MODULES = [
    "wh_families_dbt_seed.py",
    "wh_families_modeling_seed.py",
    "wh_families_dataeng_seed.py",
    "wh_families_analytics_seed.py",
    "wh_families_semantic_multiset_seed.py",
]

WRAPPER_SHORT = {
    "wrap:python_function": "pyfn",
    "wrap:fastapi_endpoint": "fastapi",
    "wrap:mcp_tool": "mcp",
    "wrap:queue_worker": "queue",
    "wrap:cron_job": "cron",
    "wrap:cloud_function": "cloudfn",
    "wrap:kubernetes_job": "k8sjob",
    "wrap:cli_command": "cli",
    "wrap:github_action": "ghaction",
    "wrap:browser_worker": "browser",
}


def load_seed_constant(name: str, constant: str, required: bool = True) -> list:
    path = SEEDS_DIR / name
    if not path.exists():
        if required:
            raise FileNotFoundError(f"missing seed module: {path}")
        return []
    ns: dict = {}
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), ns)  # noqa: S102
    return ns.get(constant, [])


def stamp(row: dict, record_type: str) -> dict:
    for forbidden in ("record_type", "version", "candidate", "serves_truth"):
        if forbidden in row:
            raise ValueError(f"seed row illegally sets builder-owned field {forbidden!r}")
    out = {"record_type": record_type}
    out.update(row)
    out["version"] = ROW_VERSION
    out["candidate"] = True
    out["serves_truth"] = False
    return out


def dedup(seq):
    out = []
    for x in seq:
        if x not in out:
            out.append(x)
    return out


def build_wrappers() -> list[dict]:
    rows = [stamp(dict(r), "runtime_wrapper")
            for r in load_seed_constant("runtime_wrappers_seed.py", "WRAPPERS")]
    return sorted(rows, key=lambda r: r["wrapper_id"])


def build_families() -> list[dict]:
    seen: dict[str, dict] = {}
    for module in FAMILY_MODULES:
        for r in load_seed_constant(module, "FAMILIES"):
            row = stamp(dict(r), "reusable_primitive_family")
            if row["family_id"] in seen:
                raise ValueError(f"duplicate family_id across modules: {row['family_id']}")
            seen[row["family_id"]] = row
    return sorted(seen.values(), key=lambda r: r["family_id"])


def build_resolved(families, wrappers) -> list[dict]:
    wrap_by_id = {w["wrapper_id"]: w for w in wrappers}
    out = []
    for fam in families:
        fa, fb = fam["family_id"].split(":", 1)[1].split(".", 1)
        for wid in fam["applicable_runtime_wrappers"]:
            wrap = wrap_by_id[wid]
            short = WRAPPER_SHORT[wid]
            effects = dedup([e for e in fam["effects"] if e != "none"]
                            + [e for e in wrap["added_effects"] if e != "none"]) or ["none"]
            proofs = dedup(list(fam["proof_requirements"]) + list(wrap["added_proof_requirements"]))
            in_edge = fam["input_edge"] + (("+" + wrap["input_policy_edge"]) if wrap["input_policy_edge"] else "")
            out.append({
                "record_type": "resolved_primitive",
                "resolved_id": f"resolved:{fa}.{fb}.{short}",
                "base_family_ref": fam["family_id"], "runtime_wrapper_ref": wid,
                "domain": fam["domain"],
                "title": f"{fam['title']} ({wrap['title']})",
                "input_edge": in_edge,
                "output_edge": fam["output_edge"] + "+" + wrap["output_receipt_edge"],
                "runtime_target": wrap["runtime_target"], "effects": effects,
                "proof_requirements": proofs, "problem_solution_ref": fam["family_id"],
                "risk_class": fam["risk_class"], "human_review_required": bool(fam["human_review_required"]),
                "version": ROW_VERSION, "candidate": True, "serves_truth": False,
            })
    out.sort(key=lambda r: r["resolved_id"])
    return out


def build_templates() -> list[dict]:
    rows = [stamp(dict(r), "primitive_template")
            for r in load_seed_constant("wh_templates_seed.py", "TEMPLATES", required=False)]
    return sorted(rows, key=lambda r: r["template_id"])


def build_pipelines() -> list[dict]:
    rows = [stamp(dict(r), "pipeline_wave_template")
            for r in load_seed_constant("wh_pipelines_seed.py", "PIPELINES", required=False)]
    return sorted(rows, key=lambda r: r["pipeline_id"])


def jsonl_bytes(rows) -> bytes:
    return "".join(json.dumps(r, ensure_ascii=True) + "\n" for r in rows).encode("utf-8")


def build_pack() -> dict[str, bytes]:
    wrappers = build_wrappers()
    families = build_families()
    resolved = build_resolved(families, wrappers)
    templates = build_templates()
    pipelines = build_pipelines()
    files = {
        "primitive_families.jsonl": families,
        "resolved_primitives.jsonl": resolved,
        "primitive_templates.jsonl": templates,
        "pipeline_wave_templates.jsonl": pipelines,
    }
    payloads = {name: jsonl_bytes(rows) for name, rows in files.items()}
    manifest = {
        "pack_id": PACK_ID, "pack_version": PACK_VERSION, "generated_by": GENERATED_BY,
        "schema_refs": SCHEMA_REFS,
        "files": {name: {"rows": len(files[name]),
                         "content_sha256": hashlib.sha256(payloads[name]).hexdigest()}
                  for name in sorted(files)},
        "row_counts": {name: len(rows) for name, rows in sorted(files.items())},
        "total_rows": sum(len(rows) for rows in files.values()),
        "candidate": True, "serves_truth": False,
    }
    payloads["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
    return payloads


def self_test() -> int:
    payloads = build_pack()
    manifest = json.loads(payloads["manifest.json"])
    print(json.dumps({"ok": True, "self_test": "builder",
                      "row_counts": manifest["row_counts"], "total_rows": manifest["total_rows"]}))
    return 0


def write_pack() -> int:
    payloads = build_pack()
    PACK_DIR.mkdir(parents=True, exist_ok=True)
    for name, data in sorted(payloads.items()):
        (PACK_DIR / name).write_bytes(data)
    manifest = json.loads(payloads["manifest.json"])
    print(json.dumps({"ok": True, "pack_dir": str(PACK_DIR.relative_to(REPO_ROOT)),
                      "row_counts": manifest["row_counts"], "total_rows": manifest["total_rows"]},
                     indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.write:
        return write_pack()
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
