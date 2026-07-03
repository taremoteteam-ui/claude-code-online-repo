#!/usr/bin/env python3
"""Repo inventory / health report for the Primitive Atlas.

Scans the repository (never hardcodes counts) and emits a deterministic,
candidate JSON report describing packs, schemas, builders, checkers, tests,
proof stages, and structural orphans (schemas with no checker, pack dirs with
no manifest, builders with no matching checker).

Conventions: stdlib-only, deterministic (sorted outputs). Nothing here promotes
truth; the report is candidate material.

Usage:
    python3 scripts/repo_inventory.py --self-test   # print report, exit 0/1
    python3 scripts/repo_inventory.py --write        # also persist the report
"""

import argparse
import glob
import json
import os
import re
import sys

# Repo root is the parent of this script's directory (scripts/).
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PACKS_DIR = os.path.join(REPO_ROOT, "catalog", "knowledge-packs", "data")
SCHEMAS_DIR = os.path.join(REPO_ROOT, "schemas")
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
TESTS_DIR = os.path.join(REPO_ROOT, "tests")
RUN_PROOFS = os.path.join(SCRIPTS_DIR, "run_proofs.py")

OUTPUT_DIR = os.path.join(REPO_ROOT, "benchmarks", "repo_inventory")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "inventory.json")


def _rel(path):
    """Repo-relative POSIX path for stable, portable report output."""
    return os.path.relpath(path, REPO_ROOT).replace(os.sep, "/")


def scan_packs():
    """Scan pack dirs under catalog/knowledge-packs/data/.

    Returns (packs, total_pack_rows, pack_dirs_without_manifest, errors).

    ``packs`` maps pack name -> {total_rows, files}. ``total_rows`` comes from
    the manifest's ``total_rows`` field, falling back to the sum of
    ``row_counts`` (or per-file ``rows``). ``errors`` collects unreadable or
    malformed manifests so the caller can fail the self-test.
    """
    packs = {}
    total_pack_rows = 0
    without_manifest = []
    errors = []

    if not os.path.isdir(PACKS_DIR):
        return packs, total_pack_rows, without_manifest, errors

    for name in sorted(os.listdir(PACKS_DIR)):
        pack_dir = os.path.join(PACKS_DIR, name)
        if not os.path.isdir(pack_dir):
            continue
        manifest_path = os.path.join(pack_dir, "manifest.json")
        if not os.path.isfile(manifest_path):
            without_manifest.append(name)
            continue
        try:
            with open(manifest_path, "r", encoding="utf-8") as handle:
                manifest = json.load(handle)
        except (OSError, ValueError) as exc:
            errors.append("%s: %s" % (_rel(manifest_path), exc))
            continue
        if not isinstance(manifest, dict):
            errors.append("%s: manifest is not a JSON object" % _rel(manifest_path))
            continue

        row_counts = manifest.get("row_counts")
        files_field = manifest.get("files")

        total_rows = manifest.get("total_rows")
        if total_rows is None:
            if isinstance(row_counts, dict):
                total_rows = sum(v for v in row_counts.values() if isinstance(v, int))
            elif isinstance(files_field, dict):
                total_rows = sum(
                    v.get("rows", 0)
                    for v in files_field.values()
                    if isinstance(v, dict)
                )
            else:
                total_rows = 0

        # File list: prefer manifest's declared files, then row_counts keys,
        # else the actual data files on disk (sorted, deterministic).
        file_names = set()
        if isinstance(files_field, dict):
            file_names.update(files_field.keys())
        if isinstance(row_counts, dict):
            file_names.update(row_counts.keys())
        if not file_names:
            for entry in os.listdir(pack_dir):
                if entry != "manifest.json" and os.path.isfile(
                    os.path.join(pack_dir, entry)
                ):
                    file_names.add(entry)

        packs[name] = {
            "total_rows": total_rows,
            "files": sorted(file_names),
        }
        if isinstance(total_rows, int):
            total_pack_rows += total_rows

    return packs, total_pack_rows, sorted(without_manifest), errors


def _basenames(pattern):
    return sorted(os.path.basename(p) for p in glob.glob(pattern))


def count_proof_stages():
    """Count entries in run_proofs.py STAGES.

    Counts ``[sys.executable`` occurrences inside the ``STAGES = [ ... ]``
    block only (the OPTIONAL_STAGES block, if any, is excluded). Returns 0 if
    the file or the STAGES marker is absent.
    """
    if not os.path.isfile(RUN_PROOFS):
        return 0
    try:
        with open(RUN_PROOFS, "r", encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return 0

    start = text.find("STAGES = [")
    if start == -1:
        return 0
    segment = text[start:]
    # Stop at OPTIONAL_STAGES (or any second top-level *_STAGES assignment) so
    # only the primary STAGES list is counted.
    stop = segment.find("OPTIONAL_STAGES")
    if stop != -1:
        segment = segment[:stop]
    return len(re.findall(r"\[sys\.executable", segment))


def find_schema_orphans(schema_files):
    """Schemas referenced by no check_*.py file (by filename)."""
    checker_text = ""
    for checker in sorted(glob.glob(os.path.join(SCRIPTS_DIR, "check_*.py"))):
        try:
            with open(checker, "r", encoding="utf-8") as handle:
                checker_text += handle.read()
        except OSError:
            continue
    orphans = [name for name in schema_files if name not in checker_text]
    return sorted(orphans)


def find_builder_orphans():
    """Builders (build_X.py) with no matching checker (check_X.py)."""
    builders = _basenames(os.path.join(SCRIPTS_DIR, "build_*.py"))
    checker_stems = {
        name[len("check_"):] for name in _basenames(os.path.join(SCRIPTS_DIR, "check_*.py"))
    }
    orphans = []
    for builder in builders:
        stem = builder[len("build_"):]
        if stem not in checker_stems:
            orphans.append(builder)
    return sorted(orphans)


def build_report():
    """Build the inventory report dict plus a list of fatal scan errors."""
    packs, total_pack_rows, packs_without_manifest, errors = scan_packs()

    schema_files = _basenames(os.path.join(SCHEMAS_DIR, "*.schema.json"))
    builders = _basenames(os.path.join(SCRIPTS_DIR, "build_*.py"))
    checkers = _basenames(os.path.join(SCRIPTS_DIR, "check_*.py"))
    tests = _basenames(os.path.join(TESTS_DIR, "test_*.py"))

    schema_orphans = find_schema_orphans(schema_files)
    builder_orphans = find_builder_orphans()

    orphan_count = (
        len(schema_orphans) + len(packs_without_manifest) + len(builder_orphans)
    )

    report = {
        "record_type": "repo_inventory",
        "candidate": True,
        "serves_truth": False,
        "packs": packs,
        "total_pack_rows": total_pack_rows,
        "schemas": len(schema_files),
        "builders": len(builders),
        "checkers": len(checkers),
        "tests": len(tests),
        "proof_stages": count_proof_stages(),
        "orphans": {
            "schemas_without_checker": schema_orphans,
            "pack_dirs_without_manifest": packs_without_manifest,
            "builders_without_checker": builder_orphans,
        },
        "orphan_count": orphan_count,
    }
    return report, errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Print the inventory report; exit 1 if any manifest is malformed.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Persist the report to benchmarks/repo_inventory/inventory.json.",
    )
    args = parser.parse_args(argv)

    report, errors = build_report()

    output = json.dumps(report, indent=2, sort_keys=True)

    if args.write:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
            handle.write(output + "\n")

    print(output)

    if errors:
        for err in errors:
            sys.stderr.write("ERROR: %s\n" % err)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
