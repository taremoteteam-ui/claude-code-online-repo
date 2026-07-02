#!/usr/bin/env python3
"""Checker for the route-market core-object schema foundation slice.

Covers the six core objects from the Operations Bible build slices:
PrimitiveTemplate, NegativeMemory, CandidateBundle, PlanDelta, PlanLock,
StrategyGenome.

Enforces:
  - every schema file parses and its example instance under
    examples/core_objects/ validates against it (StructuralValidator from
    scripts/check_place_discovery_geospatial_pack.py - dependency-free)
  - every example honors the candidate=true / serves_truth=false boundary
    and contains no forbidden claim language
  - the plan_lock example route_hash equals
    primitives.core.canonical_hash(route) - recomputed, never trusted
  - the negative_memory example evidence_refs point at things that exist:
    path-shaped refs must exist on disk; commit:<sha> refs must resolve in
    the local git object store when git is available

Usage:
    python3 scripts/check_core_object_schemas.py --self-test
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = REPO_ROOT / "schemas"
EXAMPLE_DIR = REPO_ROOT / "examples" / "core_objects"

sys.path.insert(0, str(REPO_ROOT))
from primitives.core import canonical_hash  # noqa: E402

SCHEMA_TO_EXAMPLE = {
    "primitive_template.schema.json": "primitive_template.json",
    "negative_memory.schema.json": "negative_memory.json",
    "candidate_bundle.schema.json": "candidate_bundle.json",
    "plan_delta.schema.json": "plan_delta.json",
    "plan_lock.schema.json": "plan_lock.json",
    "strategy_genome.schema.json": "strategy_genome.json",
}


def load_pack_checker_module():
    spec = importlib.util.spec_from_file_location(
        "pack_checker", REPO_ROOT / "scripts" / "check_place_discovery_geospatial_pack.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def commit_exists_locally(sha: str) -> bool | None:
    """True/False when git can answer; None when git is unavailable."""
    try:
        proc = subprocess.run(
            ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
            cwd=REPO_ROOT, capture_output=True, timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return proc.returncode == 0


def check_evidence_refs(refs: list, problems: list, checked: list) -> None:
    for ref in refs:
        if ref.startswith("commit:"):
            sha = ref.split(":", 1)[1]
            exists = commit_exists_locally(sha)
            if exists is None:
                checked.append(f"evidence ref {ref}: git unavailable, commit check skipped")
            elif not exists:
                problems.append(f"negative_memory evidence ref {ref}: commit not in local git store")
            else:
                checked.append(f"evidence ref {ref}: commit exists locally")
        elif "/" in ref:
            if not (REPO_ROOT / ref).exists():
                problems.append(f"negative_memory evidence ref {ref}: path does not exist")
            else:
                checked.append(f"evidence ref {ref}: path exists")
        else:
            checked.append(f"evidence ref {ref}: opaque id, existence not path-checkable")


def run_checks() -> dict:
    problems: list[str] = []
    checked: list[str] = []
    pack_checker = load_pack_checker_module()
    StructuralValidator = pack_checker.StructuralValidator

    examples: dict[str, dict] = {}
    for schema_name, example_name in SCHEMA_TO_EXAMPLE.items():
        schema_path = SCHEMA_DIR / schema_name
        example_path = EXAMPLE_DIR / example_name
        if not schema_path.exists():
            problems.append(f"missing schema {schema_name}")
            continue
        if not example_path.exists():
            problems.append(f"missing example {example_name}")
            continue
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"{schema_name}: not valid JSON ({exc})")
            continue
        try:
            instance = json.loads(example_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"{example_name}: not valid JSON ({exc})")
            continue
        examples[example_name] = instance

        errors = StructuralValidator(schema).validate(instance)
        for err in errors[:10]:
            problems.append(f"{example_name} vs {schema_name}: {err}")
        if not errors:
            checked.append(f"{example_name} validates against {schema_name}")

        if instance.get("candidate") is not True or instance.get("serves_truth") is not False:
            problems.append(f"{example_name}: violates candidate/serves_truth boundary")
        for text in pack_checker.iter_text_fields(instance):
            for pat in pack_checker.FORBIDDEN_CLAIM_PATTERNS:
                if pat.search(text):
                    problems.append(f"{example_name}: forbidden claim language: {pat.pattern!r}")

    lock = examples.get("plan_lock.json")
    if lock is not None:
        expected = canonical_hash(lock.get("route", []))
        if lock.get("route_hash") != expected:
            problems.append(
                f"plan_lock.json: route_hash {lock.get('route_hash')} != "
                f"canonical_hash(route) {expected} - hash was typed, not computed")
        else:
            checked.append("plan_lock.json: route_hash matches canonical_hash(route)")

    negmem = examples.get("negative_memory.json")
    if negmem is not None:
        check_evidence_refs(list(negmem.get("evidence_refs", [])), problems, checked)

    return {"ok": not problems, "problems": problems[:60], "checked": checked}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true",
                        help="validate all six core-object schemas and examples")
    args = parser.parse_args()
    if not args.self_test:
        parser.print_help()
        return 2
    result = run_checks()
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
