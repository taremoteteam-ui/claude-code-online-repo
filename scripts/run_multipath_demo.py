#!/usr/bin/env python3
"""Multiple-Path Development demo: three ways to parse an int list, benchmarked,
chosen, and with a fallback that actually fires.

The task (GUN: demo.parse.int_list): turn a messy string into a list of ints.
Three reasonable paths - NONE picked up front - all producing the same contract:

  demo.path.comma_split  - split on commas only        (narrow)
  demo.path.regex_delims - split on ,/space/semicolon   (wider; None if it can't)
  demo.path.extract_ints - pull every integer substring (widest)

MPD benchmarks all three on the same cases, chooses by measured correctness, and
keeps the rest as an ordered fallback chain. Then it shows the fallback firing:
feeding an embedded-letter input to a chain led by the narrower regex path, which
returns None and hands off to extract_ints - visibly, in the receipt.

Deterministic; zero model calls; candidate / serves_truth=false.

Usage: python3 scripts/run_multipath_demo.py --self-test
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from primitives.multipath import run_with_fallback, select_portfolio  # noqa: E402


def comma_split(s):
    return [int(x) for x in s.split(",")]


def regex_delims(s):
    parts = [p for p in re.split(r"[,\s;]+", s.strip()) if p]
    try:
        return [int(p) for p in parts]
    except ValueError:
        return None   # honest "I can't parse this" -> triggers fallback


def extract_ints(s):
    return [int(x) for x in re.findall(r"-?\d+", s)]


PATHS = [
    {"path_id": "demo.path.comma_split", "impl": comma_split,
     "produces": "demo.parse.int_list", "cost_hint": 1.0},
    {"path_id": "demo.path.regex_delims", "impl": regex_delims,
     "produces": "demo.parse.int_list", "cost_hint": 1.5},
    {"path_id": "demo.path.extract_ints", "impl": extract_ints,
     "produces": "demo.parse.int_list", "cost_hint": 2.0},
]

CASES = [
    {"input": "1,2,3", "expected": [1, 2, 3]},
    {"input": "4 5 6", "expected": [4, 5, 6]},
    {"input": "7; 8; 9", "expected": [7, 8, 9]},
    {"input": "x10y20", "expected": [10, 20]},
]


def run() -> dict:
    portfolio = select_portfolio(PATHS, CASES)
    impls = {p["path_id"]: p["impl"] for p in PATHS}

    # fallback demonstration: lead with the narrower regex path on an input it
    # cannot parse; it returns None and hands off down the chain.
    fb_order = ["demo.path.regex_delims", "demo.path.extract_ints"]
    fallback = run_with_fallback(impls, fb_order, "x10y20")

    return {
        "run_id": "mpddemo", "task": "demo.parse.int_list",
        "portfolio": portfolio,
        "chosen": portfolio["decision"]["chosen"],
        "fallback_chain": portfolio["decision"]["fallback_chain"],
        "fallback_demo": {"input": "x10y20", "order": fb_order,
                          "served_by": fallback["served_by"],
                          "value": fallback["value"],
                          "attempts": fallback["attempts"]},
        "candidate": True, "serves_truth": False,
        "honesty_notes": [
            "all three paths are measured on the same cases; the winner is chosen by "
            "correctness, not assumed",
            "the fallback fires visibly: regex_delims returns None on 'x10y20' and "
            "extract_ints serves - recorded in attempts",
            "deterministic; zero model calls",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if not (args.self_test or args.write):
        parser.print_help()
        return 2
    result = run()
    print(json.dumps(result, indent=2))
    if args.write:
        out = REPO_ROOT / "benchmarks" / "mpd_runs"
        out.mkdir(parents=True, exist_ok=True)
        (out / "int_list_portfolio.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    d = result["portfolio"]["decision"]
    fb = result["fallback_demo"]
    ok = (d["chosen"] == "demo.path.extract_ints"
          and fb["served_by"] == "demo.path.extract_ints"
          and fb["value"] == [10, 20])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
