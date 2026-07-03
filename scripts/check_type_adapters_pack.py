#!/usr/bin/env python3
"""Checker for the type-adapter connector pack.

Enforces, beyond schema validity + manifest hash gate + candidate boundary:
  - from_port != to_port (a pure alias belongs in primitives/edges.py
    _SYNONYM_MAP, not here);
  - input_edge == from_port and output_edge starts with to_port (edge/port
    coherence so the capability-graph node produces the declared target type);
  - every implementation_ref resolves to a real callable in
    primitives/type_adapters.py REGISTRY, and running it on its self-test
    fixture passes EVERY proof (a declared adapter that does not actually work
    goes red);
  - unique adapter_ids; no forbidden claim language.

Usage:
    python3 scripts/check_type_adapters_pack.py --self-test
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
PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "type-adapters"
SCHEMA_DIR = REPO_ROOT / "schemas"

FORBIDDEN = [
    re.compile(r"\b\d+(\.\d+)?x\s+(faster|cheaper|reduction)", re.IGNORECASE),
    re.compile(r"\bproven to\b", re.IGNORECASE),
    re.compile(r"\btokens? saved\b", re.IGNORECASE),
    re.compile(r"\b\d+% (accura|faster|cheaper)", re.IGNORECASE),
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


def run_checks() -> dict:
    problems = []
    SV = load_validator_class()

    mpath = PACK_DIR / "manifest.json"
    if not mpath.exists():
        return {"ok": False, "problems": [f"missing {mpath}"], "counts": {}}
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    problems += [f"manifest: {e}" for e in SV(
        json.loads((SCHEMA_DIR / "pack_manifest.schema.json").read_text())).validate(manifest)]

    fpath = PACK_DIR / "type_adapters.jsonl"
    if not fpath.exists():
        return {"ok": False, "problems": [f"missing {fpath}"], "counts": {}}
    raw = fpath.read_bytes()
    rows = [json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]
    mf = manifest.get("files", {}).get("type_adapters.jsonl", {})
    if mf.get("rows") != len(rows):
        problems.append("type_adapters.jsonl: manifest rows mismatch")
    if mf.get("content_sha256") != hashlib.sha256(raw).hexdigest():
        problems.append("type_adapters.jsonl: content hash mismatch - regenerate via the builder")

    validator = SV(json.loads((SCHEMA_DIR / "type_adapter.schema.json").read_text()))

    # Backing implementations.
    ta = importlib.import_module("primitives.type_adapters")

    ids = [r.get("adapter_id") for r in rows]
    dupes = sorted({x for x in ids if ids.count(x) > 1})
    if dupes:
        problems.append(f"duplicate adapter_ids: {dupes}")

    for i, r in enumerate(rows):
        for e in validator.validate(r)[:4]:
            problems.append(f"type_adapters.jsonl[{i}]: {e}")
        if r.get("candidate") is not True or r.get("serves_truth") is not False:
            problems.append(f"type_adapters.jsonl[{i}]: boundary violated")
        if r.get("from_port") == r.get("to_port"):
            problems.append(f"{r.get('adapter_id')}: from_port == to_port")
        if r.get("input_edge") != r.get("from_port"):
            problems.append(f"{r.get('adapter_id')}: input_edge must equal from_port")
        if not str(r.get("output_edge", "")).startswith(str(r.get("to_port", ""))):
            problems.append(f"{r.get('adapter_id')}: output_edge must start with to_port")
        for text in iter_text(r):
            for pat in FORBIDDEN:
                if pat.search(text):
                    problems.append(f"{r.get('adapter_id')}: forbidden claim {pat.pattern!r}")

        # implementation_ref resolves and its fixture passes every proof.
        ref = r.get("implementation_ref", "")
        aid = r.get("adapter_id")
        if aid not in getattr(ta, "REGISTRY", {}):
            problems.append(f"{aid}: not in primitives.type_adapters.REGISTRY")
            continue
        expected_ref = "primitives.type_adapters:" + ta.REGISTRY[aid].__name__
        if ref != expected_ref:
            problems.append(f"{aid}: implementation_ref {ref!r} != {expected_ref!r}")
        fixture = getattr(ta, "SELF_TESTS", {}).get(aid)
        if fixture is None:
            problems.append(f"{aid}: no SELF_TESTS fixture")
            continue
        try:
            outcome = ta.REGISTRY[aid](fixture)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{aid}: implementation raised {exc!r}")
            continue
        failed = [p.proof for p in outcome.proof_results if not p.passed]
        if failed:
            problems.append(f"{aid}: fixture proofs failed {failed}")
        declared = set(r.get("proof_requirements", []))
        actual = {p.proof for p in outcome.proof_results}
        if declared - actual:
            problems.append(f"{aid}: declared proofs {sorted(declared - actual)} not emitted")

    return {"ok": not problems, "problems": problems[:60], "counts": {"type_adapters.jsonl": len(rows)},
            "total_rows": len(rows)}


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
