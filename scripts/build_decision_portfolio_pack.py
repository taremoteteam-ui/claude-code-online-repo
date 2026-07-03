#!/usr/bin/env python3
"""Builder for the decision-portfolio pack (the universal path-portfolio substrate).

Single source for catalog/knowledge-packs/data/decision-portfolios/. Never
hand-edit emitted pack files; edit scripts/seeds/decision_portfolio_seed.py.
Counts/hashes computed. Every row candidate=true / serves_truth=false.

Usage:
    python3 scripts/build_decision_portfolio_pack.py --self-test
    python3 scripts/build_decision_portfolio_pack.py --write
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SEEDS_DIR = REPO_ROOT / "scripts" / "seeds"
PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "decision-portfolios"

PACK_ID = "decision-portfolios"
PACK_VERSION = "0.1.0"
ROW_VERSION = "0.1.0"
GENERATED_BY = "scripts/build_decision_portfolio_pack.py"
SCHEMA_REFS = ["schemas/decision_point.schema.json", "schemas/execution_path.schema.json",
               "schemas/pack_manifest.schema.json"]


def load_seed(constant: str) -> list:
    path = SEEDS_DIR / "decision_portfolio_seed.py"
    ns: dict = {}
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), ns)  # noqa: S102
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


def build_pack() -> dict[str, bytes]:
    decisions = sorted((stamp(dict(r), "decision_point") for r in load_seed("DECISION_POINTS")),
                       key=lambda r: r["decision_id"])
    paths = sorted((stamp(dict(r), "execution_path") for r in load_seed("EXECUTION_PATHS")),
                   key=lambda r: r["path_id"])
    files = {"decision_points.jsonl": decisions, "execution_paths.jsonl": paths}
    payloads = {name: "".join(json.dumps(r, ensure_ascii=True) + "\n" for r in rows).encode()
                for name, rows in files.items()}
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
    payloads["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    return payloads


def self_test() -> int:
    payloads = build_pack()
    manifest = json.loads(payloads["manifest.json"])
    problems = []
    decisions = [json.loads(x) for x in payloads["decision_points.jsonl"].decode().splitlines()]
    paths = [json.loads(x) for x in payloads["execution_paths.jsonl"].decode().splitlines()]
    by_decision: dict[str, list] = {}
    for p in paths:
        by_decision.setdefault(p["decision_id"], []).append(p)
    for d in decisions:
        dp = by_decision.get(d["decision_id"], [])
        if len(dp) < 2:
            problems.append(f"{d['decision_id']}: a portfolio needs >= 2 paths")
        if d["default_path"] not in {p["path_id"] for p in dp}:
            problems.append(f"{d['decision_id']}: default_path not among its paths")
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
