#!/usr/bin/env python3
"""Umbrella proof runner for this repo.

Runs, in order:
  1. pack builder self-test
  2. pack checker self-test
  3. unit tests (tests/)
  4. benchmark harness self-test (in-memory, nothing persisted)
  5. benchmark run checker against the latest persisted run (if any)

Exit 0 only if every stage passes. Counts come from each stage's own output.

Usage:
    python3 scripts/run_proofs.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

STAGES = [
    ("builder_self_test",
     [sys.executable, "scripts/build_place_discovery_geospatial_pack.py", "--self-test"]),
    ("pack_checker",
     [sys.executable, "scripts/check_place_discovery_geospatial_pack.py", "--self-test"]),
    ("core_object_schemas",
     [sys.executable, "scripts/check_core_object_schemas.py", "--self-test"]),
    ("savings_formulas_self_test",
     [sys.executable, "scripts/eval/savings_formulas.py", "--self-test"]),
    ("unit_tests",
     [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-v"]),
    ("candidate_search_eval",
     [sys.executable, "scripts/evaluate_candidate_search.py", "--self-test"]),
    ("cooccurrence_self_test",
     [sys.executable, "scripts/build_cooccurrence_edges.py", "--self-test"]),
    ("benchmark_harness_self_test",
     [sys.executable, "scripts/run_place_discovery_benchmark.py", "--self-test"]),
]

OPTIONAL_STAGES = [
    ("benchmark_run_checker",
     [sys.executable, "scripts/check_benchmark_run.py", "--self-test"]),
]


def run_stage(name: str, cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=600)
    return {
        "stage": name,
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "tail": (proc.stdout + proc.stderr).strip().splitlines()[-6:],
    }


def main() -> int:
    results = [run_stage(name, cmd) for name, cmd in STAGES]
    runs_root = REPO_ROOT / "benchmarks" / "runs"
    if runs_root.exists() and any(p.is_dir() for p in runs_root.iterdir()):
        results.extend(run_stage(name, cmd) for name, cmd in OPTIONAL_STAGES)
    ok = all(r["ok"] for r in results)
    print(json.dumps({"ok": ok, "stages": results}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
