#!/usr/bin/env python3
"""Builder for the solution-frameworks pack (reusable problem-solving wiring
scaffolds). Single source for catalog/knowledge-packs/data/solution-frameworks/.
Edit scripts/seeds/solution_frameworks_seed.py, then regenerate.

Usage: python3 scripts/build_solution_frameworks_pack.py --self-test | --write
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SEEDS_DIR = REPO_ROOT / "scripts" / "seeds"
PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "solution-frameworks"
PACK_ID = "solution-frameworks"
ROW_VERSION = "0.1.0"


def _load():
    ns: dict = {}
    exec(compile((SEEDS_DIR / "solution_frameworks_seed.py").read_text(), "s", "exec"), ns)  # noqa: S102
    return ns["FRAMEWORKS"]


def build_pack() -> dict[str, bytes]:
    rows = []
    seen = set()
    for r in _load():
        for forbidden in ("record_type", "version", "candidate", "serves_truth"):
            if forbidden in r:
                raise ValueError(f"seed sets builder-owned field {forbidden}")
        if r["framework_id"] in seen:
            raise ValueError(f"duplicate framework_id {r['framework_id']}")
        seen.add(r["framework_id"])
        rows.append({"record_type": "solution_framework", **r, "version": ROW_VERSION,
                     "candidate": True, "serves_truth": False})
    rows.sort(key=lambda x: x["framework_id"])
    payload = "".join(json.dumps(r, ensure_ascii=True) + "\n" for r in rows).encode()
    manifest = {
        "pack_id": PACK_ID, "pack_version": ROW_VERSION,
        "generated_by": "scripts/build_solution_frameworks_pack.py",
        "schema_refs": ["schemas/solution_framework.schema.json", "schemas/pack_manifest.schema.json"],
        "files": {"solution_frameworks.jsonl": {"rows": len(rows),
                  "content_sha256": hashlib.sha256(payload).hexdigest()}},
        "row_counts": {"solution_frameworks.jsonl": len(rows)}, "total_rows": len(rows),
        "candidate": True, "serves_truth": False,
    }
    return {"solution_frameworks.jsonl": payload,
            "manifest.json": (json.dumps(manifest, indent=2) + "\n").encode()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not (args.write or args.self_test):
        parser.print_help()
        return 2
    payloads = build_pack()
    rows = [json.loads(x) for x in payloads["solution_frameworks.jsonl"].decode().splitlines()]
    if args.write:
        PACK_DIR.mkdir(parents=True, exist_ok=True)
        for name, data in payloads.items():
            (PACK_DIR / name).write_bytes(data)
    print(json.dumps({"ok": True, "frameworks": len(rows),
                      "mode": "write" if args.write else "self_test"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
