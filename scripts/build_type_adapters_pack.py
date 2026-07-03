#!/usr/bin/env python3
"""Builder for the type-adapter connector pack.

Single source for catalog/knowledge-packs/data/type-adapters/. Never hand-edit
the emitted pack file; edit scripts/seeds/type_adapters_seed.py or this builder,
then re-run with --write. Counts/hashes in manifest.json are computed. Every row
is candidate=true / serves_truth=false.

Usage:
    python3 scripts/build_type_adapters_pack.py --self-test
    python3 scripts/build_type_adapters_pack.py --write
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SEEDS_DIR = REPO_ROOT / "scripts" / "seeds"
PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "type-adapters"

PACK_ID = "type-adapters"
PACK_VERSION = "0.1.0"
ROW_VERSION = "0.1.0"
GENERATED_BY = "scripts/build_type_adapters_pack.py"
SCHEMA_REFS = ["schemas/type_adapter.schema.json", "schemas/pack_manifest.schema.json"]


def load_seed_constant(name: str, constant: str) -> list:
    path = SEEDS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"missing seed module: {path}")
    ns: dict = {}
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), ns)  # noqa: S102
    if constant not in ns:
        raise KeyError(f"{name}: expected top-level constant {constant}")
    return ns[constant]


def stamp(row: dict) -> dict:
    for forbidden in ("record_type", "version", "candidate", "serves_truth"):
        if forbidden in row:
            raise ValueError(f"seed row illegally sets builder-owned field {forbidden!r}")
    out = {"record_type": "type_adapter"}
    out.update(row)
    out["version"] = ROW_VERSION
    out["candidate"] = True
    out["serves_truth"] = False
    return out


def build_adapters() -> list[dict]:
    seen: set[str] = set()
    rows = []
    for r in load_seed_constant("type_adapters_seed.py", "ADAPTERS"):
        row = stamp(dict(r))
        aid = row["adapter_id"]
        if aid in seen:
            raise ValueError(f"duplicate adapter_id: {aid}")
        seen.add(aid)
        rows.append(row)
    return sorted(rows, key=lambda r: r["adapter_id"])


def jsonl_bytes(rows: list[dict]) -> bytes:
    return "".join(json.dumps(r, ensure_ascii=True) + "\n" for r in rows).encode("utf-8")


def build_pack() -> dict[str, bytes]:
    adapters = build_adapters()
    files = {"type_adapters.jsonl": adapters}
    payloads = {name: jsonl_bytes(rows) for name, rows in files.items()}
    manifest = {
        "pack_id": PACK_ID,
        "pack_version": PACK_VERSION,
        "generated_by": GENERATED_BY,
        "schema_refs": SCHEMA_REFS,
        "files": {name: {"rows": len(files[name]),
                         "content_sha256": hashlib.sha256(payloads[name]).hexdigest()}
                  for name in sorted(files)},
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
    rows = [json.loads(x) for x in payloads["type_adapters.jsonl"].decode().splitlines()]
    for r in rows:
        if r.get("candidate") is not True or r.get("serves_truth") is not False:
            problems.append(f"{r['adapter_id']}: boundary violated")
        if r["from_port"] == r["to_port"]:
            problems.append(f"{r['adapter_id']}: from_port == to_port (use a synonym, not an adapter)")
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
