#!/usr/bin/env python3
"""Deterministic GUVN code-map builder.

Imports GUVN-annotated modules so their @unit declarations register, then builds
the whole-system code map (nodes = units + artifacts, edges = consume/produce)
purely from the Globally Unique Names - no function bodies are read. Also runs the
uniqueness linter. The map and its content hash are deterministic, so it diffs
cleanly in review and can gate a content-hash check.

By default it traces the sample pipeline fixture (fixtures/guvn/sample_pipeline.py);
pass module import paths to trace others.

Usage:
    python3 scripts/build_code_map.py --self-test          # trace the fixture
    python3 scripts/build_code_map.py --write              # persist map + mermaid
    python3 scripts/build_code_map.py --modules a.b c.d    # trace given modules
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from primitives.guvn import (build_code_map, lint,  # noqa: E402
                             registered_units, render_mermaid)

DEFAULT_MODULES = ["fixtures.guvn.sample_pipeline"]


def run(modules: list[str]) -> dict:
    for m in modules:
        importlib.import_module(m)
    units = registered_units()
    code_map = build_code_map(units)
    lints = lint(units)
    return {"modules": modules, "code_map": code_map, "lint": lints,
            "ok": lints["ok"], "candidate": True, "serves_truth": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--modules", nargs="*", default=None)
    args = parser.parse_args()
    if not (args.self_test or args.write):
        parser.print_help()
        return 2
    result = run(args.modules or DEFAULT_MODULES)
    cm = result["code_map"]
    summary = {"modules": result["modules"], "units": cm["unit_count"],
               "artifacts": cm["artifact_count"], "edges": cm["edge_count"],
               "sources": cm["sources"], "sinks": cm["sinks"],
               "multi_path_artifacts": cm["multi_path_artifacts"],
               "lint_ok": result["lint"]["ok"], "lint_errors": result["lint"]["errors"],
               "content_sha256": cm["content_sha256"]}
    print(json.dumps(summary, indent=2))
    if args.write:
        out = REPO_ROOT / "benchmarks" / "code_maps"
        out.mkdir(parents=True, exist_ok=True)
        (out / "sample_pipeline.map.json").write_text(json.dumps(cm, indent=2) + "\n", encoding="utf-8")
        (out / "sample_pipeline.mmd").write_text(render_mermaid(cm) + "\n", encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
