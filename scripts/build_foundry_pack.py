#!/usr/bin/env python3
"""Builder for the foundry-mined-primitives pack: the STORAGE stage of the
ingestion pipeline. Runs acquire -> form -> verify over the synthetic fixture
sources and writes the edge-typed mined primitives + manifest. Deterministic and
offline. Never hand-edit pack files; edit the fixture sources under
fixtures/foundry/ or primitives/foundry.py, then regenerate.

Usage:
    python3 scripts/build_foundry_pack.py --self-test
    python3 scripts/build_foundry_pack.py --write
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from primitives.foundry import acquire, form, verify  # noqa: E402

FIXTURES_DIR = REPO_ROOT / "fixtures" / "foundry"
PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "foundry-mined-primitives"
PACK_ID = "foundry-mined-primitives"
PACK_VERSION = "0.1.0"
GENERATED_BY = "scripts/build_foundry_pack.py"
SCHEMA_REFS = ["schemas/mined_primitive.schema.json", "schemas/pack_manifest.schema.json"]


def build_rows() -> list[dict]:
    rows: list[dict] = []
    for src_path in sorted(FIXTURES_DIR.glob("*.json")):
        source = json.loads(src_path.read_text(encoding="utf-8"))
        snapshot, _receipt = acquire(source, path="cached_snapshot")
        for mined in form(snapshot):
            vr = verify(mined)
            mined["verification_status"] = vr["verification_status"]
            rows.append(mined)
    return sorted(rows, key=lambda r: r["mined_primitive_id"])


def build_pack() -> dict[str, bytes]:
    rows = build_rows()
    payload = "".join(json.dumps(r, ensure_ascii=True) + "\n" for r in rows).encode()
    manifest = {
        "pack_id": PACK_ID, "pack_version": PACK_VERSION, "generated_by": GENERATED_BY,
        "schema_refs": SCHEMA_REFS,
        "files": {"mined_primitives.jsonl": {"rows": len(rows),
                  "content_sha256": hashlib.sha256(payload).hexdigest()}},
        "row_counts": {"mined_primitives.jsonl": len(rows)},
        "total_rows": len(rows), "candidate": True, "serves_truth": False,
    }
    return {"mined_primitives.jsonl": payload,
            "manifest.json": (json.dumps(manifest, indent=2) + "\n").encode()}


def self_test() -> int:
    payloads = build_pack()
    rows = [json.loads(x) for x in payloads["mined_primitives.jsonl"].decode().splitlines()]
    problems = []
    for r in rows:
        if r.get("candidate") is not True or r.get("serves_truth") is not False:
            problems.append(f"{r['mined_primitive_id']}: boundary violated")
    verified = sum(1 for r in rows if r["verification_status"] == "fixture_verified")
    blocked = sum(1 for r in rows if r["verification_status"] == "license_blocked")
    if problems:
        print(json.dumps({"ok": False, "problems": problems}, indent=2))
        return 1
    print(json.dumps({"ok": True, "self_test": "foundry_builder", "mined": len(rows),
                      "fixture_verified": verified, "license_blocked": blocked}))
    return 0


def write_pack() -> int:
    payloads = build_pack()
    PACK_DIR.mkdir(parents=True, exist_ok=True)
    for name, data in sorted(payloads.items()):
        (PACK_DIR / name).write_bytes(data)
    manifest = json.loads(payloads["manifest.json"])
    print(json.dumps({"ok": True, "pack_dir": str(PACK_DIR.relative_to(REPO_ROOT)),
                      "total_rows": manifest["total_rows"]}, indent=2))
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
