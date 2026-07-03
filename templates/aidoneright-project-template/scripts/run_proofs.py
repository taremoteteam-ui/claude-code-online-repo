#!/usr/bin/env python3
"""Umbrella proof runner (AIDoneRight template).

Runs every proof stage in order and exits non-zero if any fails. Counts come from
each stage's own output. Add your stages to STAGES as the project grows; keep the
three verify-the-verifier gates (Standard 003) at the end.

Usage: python3 scripts/run_proofs.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Each stage is (name, argv). Uncomment / add as you implement them. The empty
# default makes a fresh project green from commit #1; do not leave it empty for
# long - a proof suite that proves nothing is Standard 000 rule 2 in spirit.
STAGES: list[tuple[str, list[str]]] = [
    # ("schema_checker",   [sys.executable, "scripts/check_pack.py", "--self-test"]),
    # ("unit_tests",       [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."]),
    # ("code_map",         [sys.executable, "scripts/build_code_map.py", "--self-test"]),
    # --- Standard 003: verify the verifier (keep last) ---
    # ("determinism_gate", [sys.executable, "scripts/check_determinism.py", "--self-test"]),
    # ("quality_ratchet",  [sys.executable, "scripts/check_quality_ratchet.py", "--self-test"]),
    # ("mutation_test",    [sys.executable, "scripts/mutation_test.py", "--self-test"]),
]


def run_stage(name: str, cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=600)
    return {"stage": name, "ok": proc.returncode == 0, "returncode": proc.returncode,
            "tail": (proc.stdout + proc.stderr).strip().splitlines()[-6:]}


def main() -> int:
    results = [run_stage(name, cmd) for name, cmd in STAGES]
    ok = all(r["ok"] for r in results)
    print(json.dumps({"ok": ok, "stages": results}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
