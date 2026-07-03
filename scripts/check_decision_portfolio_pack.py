#!/usr/bin/env python3
"""Checker for the decision-portfolio pack.

Enforces, beyond schema validity + manifest hash gate + candidate boundary:
  - referential integrity: every path.decision_id names a real decision; every
    decision.default_path is one of its own paths;
  - a portfolio has >= 2 paths (one option is not a decision);
  - the default_path is cold-start-eligible: its applicability.requires_keys is
    empty, so it is always a valid fallback before any receipts exist;
  - every handler_ref resolves to a real callable;
  - unique ids; no forbidden claim language.

Usage:
    python3 scripts/check_decision_portfolio_pack.py --self-test
"""

import argparse
import hashlib
import importlib
import importlib.util
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "decision-portfolios"
SCHEMA_DIR = REPO_ROOT / "schemas"

FILE_TO_SCHEMA = {
    "decision_points.jsonl": "decision_point.schema.json",
    "execution_paths.jsonl": "execution_path.schema.json",
}
FORBIDDEN = [
    re.compile(r"\b\d+(\.\d+)?x\s+(faster|cheaper|reduction)", re.IGNORECASE),
    re.compile(r"\bproven to\b", re.IGNORECASE),
    re.compile(r"\btokens? saved\b", re.IGNORECASE),
]


def load_validator_class():
    spec = importlib.util.spec_from_file_location(
        "pack_checker", REPO_ROOT / "scripts" / "check_place_discovery_geospatial_pack.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.StructuralValidator


def iter_text(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for x in v.values():
            yield from iter_text(x)
    elif isinstance(v, list):
        for x in v:
            yield from iter_text(x)


def _resolves(ref: str) -> bool:
    try:
        mod_name, attr = ref.split(":", 1)
        mod = importlib.import_module(mod_name)
        return callable(getattr(mod, attr, None))
    except Exception:  # noqa: BLE001
        return False


def run_checks() -> dict:
    problems = []
    counts = {}
    SV = load_validator_class()

    mpath = PACK_DIR / "manifest.json"
    if not mpath.exists():
        return {"ok": False, "problems": [f"missing {mpath}"], "counts": {}}
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    problems += [f"manifest: {e}" for e in SV(
        json.loads((SCHEMA_DIR / "pack_manifest.schema.json").read_text())).validate(manifest)]

    data = {}
    for fname, schema_name in FILE_TO_SCHEMA.items():
        fpath = PACK_DIR / fname
        if not fpath.exists():
            problems.append(f"missing pack file {fname}")
            continue
        raw = fpath.read_bytes()
        rows = [json.loads(x) for x in raw.decode().splitlines() if x.strip()]
        data[fname] = rows
        counts[fname] = len(rows)
        mf = manifest.get("files", {}).get(fname, {})
        if mf.get("rows") != len(rows):
            problems.append(f"{fname}: manifest rows mismatch")
        if mf.get("content_sha256") != hashlib.sha256(raw).hexdigest():
            problems.append(f"{fname}: content hash mismatch - regenerate via the builder")
        validator = SV(json.loads((SCHEMA_DIR / schema_name).read_text()))
        for i, row in enumerate(rows):
            for e in validator.validate(row)[:4]:
                problems.append(f"{fname}[{i}]: {e}")
            if row.get("candidate") is not True or row.get("serves_truth") is not False:
                problems.append(f"{fname}[{i}]: boundary violated")
            for text in iter_text(row):
                for pat in FORBIDDEN:
                    if pat.search(text):
                        problems.append(f"{fname}[{i}]: forbidden claim {pat.pattern!r}")

    decisions = data.get("decision_points.jsonl", [])
    paths = data.get("execution_paths.jsonl", [])
    decision_ids = {d["decision_id"] for d in decisions}
    by_decision: dict[str, list] = {}
    for p in paths:
        by_decision.setdefault(p["decision_id"], []).append(p)
        if p["decision_id"] not in decision_ids:
            problems.append(f"path {p['path_id']}: unknown decision_id {p['decision_id']}")
        ref = p.get("handler_ref")
        if ref and not _resolves(ref):
            problems.append(f"path {p['path_id']}: handler_ref {ref} does not resolve")

    for d in decisions:
        dp = by_decision.get(d["decision_id"], [])
        ids = {p["path_id"] for p in dp}
        if len(dp) < 2:
            problems.append(f"{d['decision_id']}: portfolio needs >= 2 paths, has {len(dp)}")
        if d["default_path"] not in ids:
            problems.append(f"{d['decision_id']}: default_path {d['default_path']} not among its paths")
        else:
            default = next(p for p in dp if p["path_id"] == d["default_path"])
            if default["applicability"].get("requires_keys"):
                problems.append(f"{d['decision_id']}: default_path is not cold-start-eligible "
                                "(applicability.requires_keys must be empty)")
        if d["selection_policy"] == "epsilon_greedy" and "epsilon" not in d:
            problems.append(f"{d['decision_id']}: epsilon_greedy policy needs an epsilon")

    for fname, key in [("decision_points.jsonl", "decision_id"), ("execution_paths.jsonl", "path_id")]:
        ids = [r[key] for r in data.get(fname, [])]
        dupes = {x for x in ids if ids.count(x) > 1}
        if dupes:
            problems.append(f"{fname}: duplicate ids {sorted(dupes)}")

    return {"ok": not problems, "problems": problems[:60], "counts": counts,
            "total_rows": sum(counts.values())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test:
        parser.print_help()
        return 2
    result = run_checks()
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
