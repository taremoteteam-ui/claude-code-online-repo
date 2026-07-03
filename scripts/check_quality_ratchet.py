"""Quality ratchet: fail if a measured headline metric silently regresses.

The demos and benchmarks in this repo PRINT their headline numbers (compose
rate, route optimality, retrieval hit@k) and pass regardless of value. So a
change that quietly drops the compose rate from 0.89 to 0.60 - a real
regression - sails through the proof suite green, because every stage it touches
still "succeeds". This gate closes that hole.

It records each measured metric as a candidate FLOOR (for higher-is-better
metrics) or CEILING (for lower-is-better) in benchmarks/quality_baseline.json,
then fails a run whose freshly-measured value crosses that bound by more than a
tiny tolerance. The baseline is a candidate artifact, never a truth claim - it
is one measurement of THIS repo's own machinery in fixture mode, not a
real-world accuracy number. Moving the ratchet up is deliberate: run with
--update after an intended improvement to re-record the floor.

All probed values come from existing scripts' JSON output; this gate adds no new
measurement, only a no-regression assertion over numbers already computed and
already disclosed as fixture-mode / candidate.

Usage:
    python3 scripts/check_quality_ratchet.py --self-test   # measure vs baseline
    python3 scripts/check_quality_ratchet.py --update       # re-record baseline
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
BASELINE_PATH = REPO_ROOT / "benchmarks" / "quality_baseline.json"

# Absorbs float-repr jitter only; these probes are deterministic, so a real
# regression is always far larger than this.
_TOLERANCE = 1e-4


def _dig(doc: dict, path: str):
    """Fetch a nested value by dotted path, e.g. 'lexical_plus_typed_edge.hit_at_k'."""
    cur = doc
    for key in path.split("."):
        cur = cur[key]
    return cur


# Each probe runs a script once and pulls one already-measured number from its
# JSON. direction 'up' = higher is better (value must stay >= floor); 'down' =
# lower is better (value must stay <= ceiling).
PROBES = [
    {"metric": "route_compose_rate", "direction": "up",
     "cmd": [PY, "scripts/run_route_compiler_demo.py", "--self-test"],
     "path": "compose_rate",
     "note": "fraction of target contracts the edge compiler resolves with zero model calls"},
    {"metric": "route_optimal_fraction", "direction": "up",
     "cmd": [PY, "scripts/run_route_compiler_benchmark.py", "--self-test", "--trials", "120"],
     "path": "optimal_fraction",
     "note": "fraction of compiled routes that match the BFS shortest-path oracle"},
    {"metric": "route_valid_fraction", "direction": "up",
     "cmd": [PY, "scripts/run_route_compiler_benchmark.py", "--self-test", "--trials", "120"],
     "path": "valid_fraction",
     "note": "fraction of compiled routes whose every step has its inputs satisfied"},
    {"metric": "route_irredundant_fraction", "direction": "up",
     "cmd": [PY, "scripts/run_route_compiler_benchmark.py", "--self-test", "--trials", "120"],
     "path": "irredundant_fraction",
     "note": "fraction of compiled routes with no removable step"},
    {"metric": "route_mean_excess_steps", "direction": "down",
     "cmd": [PY, "scripts/run_route_compiler_benchmark.py", "--self-test", "--trials", "120"],
     "path": "mean_excess_steps",
     "note": "mean steps over the oracle's shortest route (0.0 = always shortest)"},
    {"metric": "graph_search_hit_at_k", "direction": "up",
     "cmd": [PY, "scripts/evaluate_graph_search.py", "--self-test"],
     "path": "lexical_plus_typed_edge.hit_at_k",
     "note": "cross-lane retrieval hit@k over the whole capability graph (lexical + typed edge)"},
    {"metric": "graph_search_mrr", "direction": "up",
     "cmd": [PY, "scripts/evaluate_graph_search.py", "--self-test"],
     "path": "lexical_plus_typed_edge.mrr",
     "note": "cross-lane retrieval mean reciprocal rank (lexical + typed edge)"},
    {"metric": "foundry_fixture_executable", "direction": "up",
     "cmd": [PY, "scripts/run_foundry_pipeline.py", "--self-test"],
     "path": "store.fixture_executable",
     "note": "count of mined primitives proven to actually run their edge transform"},
    {"metric": "policy_contextual_regret", "direction": "down",
     "cmd": [PY, "scripts/run_policy_selection_benchmark.py", "--self-test"],
     "path": "regimes.contextual.holdout_regret.argmax_contextual",
     "note": "holdout regret of the context-conditioned policy in the contextual regime "
             "(the data-selected winner; lower is better)"},
    {"metric": "ope_dr_bad_model_bias", "direction": "down",
     "cmd": [PY, "scripts/run_off_policy_evaluation_benchmark.py", "--self-test"],
     "path": "estimators.DR_bad_model.abs_bias",
     "note": "absolute bias of the doubly-robust estimator under a deliberately "
             "misspecified reward model (the robustness result; lower is better)"},
    {"metric": "coding_problems_solved", "direction": "up",
     "cmd": [PY, "scripts/run_coding_primitive_pipeline.py", "--self-test"],
     "path": "problems_solved",
     "note": "harvested coding problems whose solution passes all its fixture test cases "
             "(live run; must not silently drop)"},
    {"metric": "coding_test_cases_passed", "direction": "up",
     "cmd": [PY, "scripts/run_coding_primitive_pipeline.py", "--self-test"],
     "path": "test_cases_passed",
     "note": "total coding-problem fixture test cases passing across all solutions"},
]


def _measure() -> dict:
    """Run each probe once (caching by command so a script that feeds several
    metrics is only invoked once) and return {metric: value}."""
    cache: dict[tuple, dict] = {}
    values = {}
    for p in PROBES:
        key = tuple(p["cmd"])
        if key not in cache:
            proc = subprocess.run(p["cmd"], cwd=REPO_ROOT, capture_output=True,
                                  text=True, timeout=600)
            if proc.returncode != 0:
                raise RuntimeError(f"probe command failed: {' '.join(p['cmd'])}\n{proc.stderr[-400:]}")
            cache[key] = json.loads(proc.stdout)
        values[p["metric"]] = _dig(cache[key], p["path"])
    return values


def _regressed(direction: str, current: float, baseline: float) -> bool:
    if direction == "up":
        return current < baseline - _TOLERANCE
    return current > baseline + _TOLERANCE


def run(update: bool) -> dict:
    values = _measure()
    if update:
        payload = {
            "record_type": "quality_baseline",
            "note": ("candidate floors/ceilings for this repo's own machinery, "
                     "measured in fixture mode; NOT a real-world accuracy claim"),
            "candidate": True, "serves_truth": False,
            "metrics": {p["metric"]: {"baseline": values[p["metric"]],
                                      "direction": p["direction"], "note": p["note"]}
                        for p in PROBES},
        }
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return {"record_type": "quality_ratchet", "mode": "update",
                "baseline_path": str(BASELINE_PATH.relative_to(REPO_ROOT)),
                "metrics_recorded": len(values), "values": values,
                "candidate": True, "serves_truth": False}

    if not BASELINE_PATH.exists():
        return {"record_type": "quality_ratchet", "mode": "check", "ok": False,
                "error": "no baseline recorded; run --update first",
                "candidate": True, "serves_truth": False}
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))["metrics"]
    checks = []
    for p in PROBES:
        m = p["metric"]
        cur = values[m]
        if m not in baseline:
            checks.append({"metric": m, "ok": False, "current": cur,
                           "error": "metric absent from baseline (run --update)"})
            continue
        base = baseline[m]["baseline"]
        bad = _regressed(p["direction"], cur, base)
        checks.append({"metric": m, "ok": not bad, "direction": p["direction"],
                       "current": cur, "baseline": base,
                       "delta": round(cur - base, 6)})
    regressions = [c["metric"] for c in checks if not c["ok"]]
    return {"record_type": "quality_ratchet", "mode": "check",
            "ok": not regressions, "regressions": regressions, "checks": checks,
            "tolerance": _TOLERANCE, "candidate": True, "serves_truth": False,
            "note": "a regression means a measured metric dropped below its recorded floor"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true",
                        help="measure current metrics and compare to the baseline")
    parser.add_argument("--update", action="store_true",
                        help="re-record the baseline from current measurements")
    args = parser.parse_args()
    if not (args.self_test or args.update):
        parser.print_help()
        return 2
    result = run(update=args.update)
    print(json.dumps(result, indent=2))
    if args.update:
        return 0
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
