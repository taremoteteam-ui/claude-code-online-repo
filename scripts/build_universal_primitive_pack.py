#!/usr/bin/env python3
"""Builder for the universal reusable-primitive catalog.

Single source for every file under
catalog/knowledge-packs/data/universal-primitive-catalog/. Never hand-edit
emitted pack files; edit the seed modules under scripts/seeds/ or this
builder, then re-run with --write.

Loads the base primitive families (across several domain seed modules) and the
runtime-wrapper bank, then materializes resolved primitives by crossing each
family with ONLY the wrappers it declares applicable - a principled lattice,
never a blind cartesian. Counts/hashes in manifest.json are computed, never
typed. Every row is candidate=true / serves_truth=false.

Usage:
    python3 scripts/build_universal_primitive_pack.py --self-test
    python3 scripts/build_universal_primitive_pack.py --write
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SEEDS_DIR = REPO_ROOT / "scripts" / "seeds"
PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "universal-primitive-catalog"

PACK_ID = "universal-primitive-catalog"
PACK_VERSION = "0.1.0"
ROW_VERSION = "0.1.0"
GENERATED_BY = "scripts/build_universal_primitive_pack.py"

SCHEMA_REFS = [
    "schemas/reusable_primitive_family.schema.json",
    "schemas/runtime_wrapper.schema.json",
    "schemas/resolved_primitive.schema.json",
    "schemas/pack_manifest.schema.json",
]

# Domain family seed modules. Each exports a top-level constant FAMILIES.
FAMILY_SEED_MODULES = [
    "universal_families_auth_security_seed.py",
    "universal_families_crud_trackers_seed.py",
    "universal_families_data_seed.py",
    "universal_families_integration_seed.py",
    "universal_families_devops_seed.py",
    "universal_families_intelligence_seed.py",
    "universal_families_media_vision_seed.py",
    "universal_families_coding_agent_seed.py",
    "universal_families_similarity_er_seed.py",
]

# Short tags used in resolved ids, keyed by wrapper_id.
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


def load_seed_constant(name: str, constant: str) -> list:
    path = SEEDS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"missing seed module: {path}")
    ns: dict = {}
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), ns)  # noqa: S102
    if constant not in ns:
        raise KeyError(f"{name}: expected top-level constant {constant}")
    return ns[constant]


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


def build_wrappers() -> list[dict]:
    rows = [stamp(dict(r), "runtime_wrapper")
            for r in load_seed_constant("runtime_wrappers_seed.py", "WRAPPERS")]
    return sorted(rows, key=lambda r: r["wrapper_id"])


def build_families() -> list[dict]:
    seen: dict[str, dict] = {}
    for module in FAMILY_SEED_MODULES:
        for r in load_seed_constant(module, "FAMILIES"):
            row = stamp(dict(r), "reusable_primitive_family")
            fid = row["family_id"]
            if fid in seen:
                raise ValueError(f"duplicate family_id across seed modules: {fid}")
            seen[fid] = row
    return sorted(seen.values(), key=lambda r: r["family_id"])


def dedup_preserve(seq: list) -> list:
    out: list = []
    for x in seq:
        if x not in out:
            out.append(x)
    return out


def build_resolved(families: list[dict], wrappers: list[dict]) -> list[dict]:
    wrap_by_id = {w["wrapper_id"]: w for w in wrappers}
    resolved: list[dict] = []
    for fam in families:
        fam_a, fam_b = fam["family_id"].split(":", 1)[1].split(".", 1)
        for wid in fam["applicable_runtime_wrappers"]:
            wrap = wrap_by_id[wid]  # referential integrity enforced by checker too
            short = WRAPPER_SHORT[wid]
            effects = dedup_preserve(
                [e for e in fam["effects"] if e != "none"]
                + [e for e in wrap["added_effects"] if e != "none"]) or ["none"]
            proofs = dedup_preserve(list(fam["proof_requirements"])
                                    + list(wrap["added_proof_requirements"]))
            in_edge = fam["input_edge"]
            if wrap["input_policy_edge"]:
                in_edge = in_edge + "+" + wrap["input_policy_edge"]
            resolved.append({
                "record_type": "resolved_primitive",
                "resolved_id": f"resolved:{fam_a}.{fam_b}.{short}",
                "base_family_ref": fam["family_id"],
                "runtime_wrapper_ref": wid,
                "domain": fam["domain"],
                "title": f"{fam['title']} ({wrap['title']})",
                "input_edge": in_edge,
                "output_edge": fam["output_edge"] + "+" + wrap["output_receipt_edge"],
                "runtime_target": wrap["runtime_target"],
                "effects": effects,
                "proof_requirements": proofs,
                "problem_solution_ref": fam["family_id"],
                "risk_class": fam["risk_class"],
                "human_review_required": bool(fam["human_review_required"]),
                "version": ROW_VERSION,
                "candidate": True,
                "serves_truth": False,
            })
    resolved.sort(key=lambda r: r["resolved_id"])
    return resolved


def jsonl_bytes(rows: list[dict]) -> bytes:
    return "".join(json.dumps(r, ensure_ascii=True) + "\n" for r in rows).encode("utf-8")


def build_pack() -> dict[str, bytes]:
    wrappers = build_wrappers()
    families = build_families()
    resolved = build_resolved(families, wrappers)

    files = {
        "primitive_families.jsonl": families,
        "runtime_wrappers.jsonl": wrappers,
        "resolved_primitives.jsonl": resolved,
    }
    payloads = {name: jsonl_bytes(rows) for name, rows in files.items()}
    manifest = {
        "pack_id": PACK_ID,
        "pack_version": PACK_VERSION,
        "generated_by": GENERATED_BY,
        "schema_refs": SCHEMA_REFS,
        "files": {
            name: {"rows": len(files[name]),
                   "content_sha256": hashlib.sha256(payloads[name]).hexdigest()}
            for name in sorted(files)
        },
        "row_counts": {name: len(rows) for name, rows in sorted(files.items())},
        "total_rows": sum(len(rows) for rows in files.values()),
        "candidate": True,
        "serves_truth": False,
    }
    payloads["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
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
            problems.append(f"{name}: row count mismatch")
        for row in rows:
            if row.get("candidate") is not True or row.get("serves_truth") is not False:
                problems.append(f"{name}: candidate/serves_truth boundary violated")
                break
    if problems:
        print(json.dumps({"ok": False, "problems": problems}, indent=2))
        return 1
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
