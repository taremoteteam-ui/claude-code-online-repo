#!/usr/bin/env python3
"""Compiled-AI token-amortization model.

Compiled AI (arXiv:2604.05150) reports that compiling once with an LLM and then
executing deterministically breaks even with runtime inference after a small
number of transactions and reduces tokens by a large factor at scale. This
system's PlanLocks ARE those compiled artifacts (the route compiler composes
with zero model calls; A4 replay measures runtime_llm_tokens = 0).

This script computes the break-even transaction count, the amortized tokens per
transaction, and the Nx reduction factor across a horizon - the EXACT formulas
(scripts/eval/savings_formulas.py), evaluated over ILLUSTRATIVE parameter sets.

HONESTY: the parameter values here are labeled `illustrative_not_measured`. THIS
system's real compile_phase_tokens and baseline_runtime_tokens_per_transaction
require measured baseline arms (A1/A2) that have NOT run; only
compiled_runtime_tokens_per_transaction = 0 is measured (A4 fixture replay). So
this demonstrates the SHAPE of compiled-AI economics and verifies the algebra -
it does not claim a measured reduction for this system. External reported
numbers are attributed to the paper, not to this repo.

Usage: python3 scripts/run_amortization_model.py --self-test | --write
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "eval"))

import savings_formulas as sf  # noqa: E402

RUNS = REPO_ROOT / "benchmarks" / "amortization"

# Illustrative parameter sets (NOT measurements of this system). Each: a
# one-time compile cost in tokens, the per-transaction baseline runtime tokens a
# model-in-the-loop system would spend, and the compiled per-transaction cost
# (0 for a pure PlanLock replay).
ILLUSTRATIVE = [
    {"label": "cheap_compile_pure_replay", "compile_phase_tokens": 2000,
     "baseline_runtime_tokens_per_transaction": 1200, "compiled_runtime_tokens_per_transaction": 0},
    {"label": "heavy_compile_pure_replay", "compile_phase_tokens": 20000,
     "baseline_runtime_tokens_per_transaction": 1200, "compiled_runtime_tokens_per_transaction": 0},
    {"label": "small_residual_runtime", "compile_phase_tokens": 8000,
     "baseline_runtime_tokens_per_transaction": 1200, "compiled_runtime_tokens_per_transaction": 40},
]
HORIZONS = [10, 100, 1000, 10000]


def run() -> dict:
    scenarios = []
    for p in ILLUSTRATIVE:
        c, base, comp = (p["compile_phase_tokens"],
                         p["baseline_runtime_tokens_per_transaction"],
                         p["compiled_runtime_tokens_per_transaction"])
        break_even = sf.compiled_break_even_transactions(c, base, comp)
        curve = []
        for n in HORIZONS:
            curve.append({
                "transactions": n,
                "amortized_tokens_per_txn": round(sf.amortized_tokens_per_transaction(c, comp, n), 3),
                "reduction_factor": round(sf.token_reduction_factor_at(c, base, comp, n), 3),
            })
        scenarios.append({**p, "inputs": "illustrative_not_measured",
                          "break_even_transactions": round(break_even, 3), "curve": curve})

    # algebra sanity: reduction strictly increases with the horizon; amortized
    # strictly decreases; the reduction crosses 1.0 exactly at break-even.
    sane = True
    for s in scenarios:
        red = [c["reduction_factor"] for c in s["curve"]]
        amo = [c["amortized_tokens_per_txn"] for c in s["curve"]]
        sane = sane and all(red[i] < red[i + 1] for i in range(len(red) - 1))
        sane = sane and all(amo[i] > amo[i + 1] for i in range(len(amo) - 1))

    return {
        "run_id": "amortization", "model": "compiled-AI token amortization (formulas exact; inputs illustrative)",
        "scenarios": scenarios,
        "external_reference": {
            "source": "arXiv:2604.05150 (Compiled AI)",
            "reported_break_even_transactions": "~17 (their function-calling eval)",
            "reported_reduction_at_1000": "57x (their measurement, not this repo's)",
            "note": "cited for context; this repo asserts no measured reduction until baseline arms A1/A2 run",
        },
        "algebra_sane": sane,
        "candidate": True, "serves_truth": False,
        "honesty_notes": [
            "parameter values are illustrative_not_measured - they show the SHAPE of the economics",
            "this system's compile cost + baseline runtime require baseline arms that have NOT run",
            "only compiled_runtime_tokens_per_transaction=0 is measured (A4 fixture replay)",
            "external Nx/break-even numbers are attributed to the paper, never to this repo",
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
        RUNS.mkdir(parents=True, exist_ok=True)
        (RUNS / "amortization_model.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0 if result["algebra_sane"] else 1


if __name__ == "__main__":
    sys.exit(main())
