"""Determinism gate: a 'deterministic' system must build byte-identically twice.

For each pack builder, run its in-memory self-test twice and assert the emitted
row counts + content hashes are identical. Any hidden nondeterminism (dict order,
set iteration, a stray timestamp) shows up as a diff here, before it poisons a
content-hash gate intermittently. Cheap and stdlib only.

Usage: python3 scripts/check_determinism.py --self-test
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

BUILDERS = [
    "scripts/build_place_discovery_geospatial_pack.py",
    "scripts/build_universal_primitive_pack.py",
    "scripts/build_warehouse_analytics_pack.py",
    "scripts/build_type_adapters_pack.py",
    "scripts/build_decision_portfolio_pack.py",
    "scripts/build_foundry_pack.py",
    "scripts/build_capability_graph.py",
    "scripts/build_solution_frameworks_pack.py",
    "scripts/build_decision_frameworks_pack.py",
    "scripts/build_coding_primitive_pack.py",
]


def _out(cmd) -> str:
    proc = subprocess.run([PY, cmd, "--self-test"], cwd=REPO_ROOT,
                          capture_output=True, text=True, timeout=300)
    return proc.stdout + proc.stderr


def run() -> dict:
    results = []
    for b in BUILDERS:
        a = _out(b)
        c = _out(b)
        results.append({"builder": b, "deterministic": a == c})
    nondet = [r["builder"] for r in results if not r["deterministic"]]
    return {"record_type": "determinism_check", "builders": len(BUILDERS),
            "deterministic": sum(1 for r in results if r["deterministic"]),
            "nondeterministic": nondet, "all_deterministic": not nondet,
            "candidate": True, "serves_truth": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test:
        parser.print_help()
        return 2
    result = run()
    print(json.dumps(result, indent=2))
    return 0 if result["all_deterministic"] else 1


if __name__ == "__main__":
    sys.exit(main())
