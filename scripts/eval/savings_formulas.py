#!/usr/bin/env python3
"""Single source for every savings/impact formula in this repo.

Formulas only. This module computes nothing until fed MEASURED inputs from
receipts and scorecards. No default values, no example numbers, no
projections live here.

Formulas mirror docs/codex/primitive-atlas-northstar.md, section
"Savings And Impact Formulas". Any other script that needs one of these
numbers MUST import from this module instead of re-deriving the arithmetic.

Every function:
  - takes explicit measured inputs (no globals, no config, no defaults),
  - is deterministic and pure,
  - returns a float,
  - raises ValueError on invalid inputs (zero denominators, negative values
    where a negative measurement is impossible, probabilities outside [0, 1],
    non-integer counts, NaN/inf, booleans).

Inputs named ``*_saved_per_task`` / ``*_saved_per_reuse`` are measured
deltas: a negative value is a valid measurement (a regression) and is NOT
rejected. Everything else that cannot physically be negative is rejected
when negative.

MEASUREMENT_STATUS maps each formula name to its required input sources so
callers know exactly which inputs exist today and which do not. As of this
writing only arm A4 (deterministic route replay, fixture_offline) has ever
run; baseline arms A1/A2 have NOT run, so no savings comparison can be
computed yet.

Usage:
    python3 scripts/eval/savings_formulas.py --self-test   # synthetic checks
    python3 scripts/eval/savings_formulas.py --status      # measurement status

Stdlib only. ASCII only.
"""

from __future__ import annotations

import argparse
import json
import math
import sys

PER_100K_MULTIPLIER = 100000
SECONDS_PER_HOUR = 3600.0


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------

def _finite(name: str, value) -> float:
    """A real, finite number (bool is rejected: it is not a measurement)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a real number, got {type(value).__name__}")
    v = float(value)
    if math.isnan(v) or math.isinf(v):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return v


def _non_negative(name: str, value) -> float:
    v = _finite(name, value)
    if v < 0:
        raise ValueError(f"{name} cannot be negative, got {value!r}")
    return v


def _positive(name: str, value) -> float:
    v = _finite(name, value)
    if v <= 0:
        raise ValueError(f"{name} must be > 0 (zero denominators are invalid), got {value!r}")
    return v


def _count(name: str, value) -> int:
    """A non-negative integer count. Floats are rejected: counts are exact."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer count, got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{name} cannot be negative, got {value!r}")
    return value


def _probability(name: str, value) -> float:
    v = _finite(name, value)
    if v < 0.0 or v > 1.0:
        raise ValueError(f"{name} must be within [0, 1], got {value!r}")
    return v


def _measured_delta(name: str, value) -> float:
    """A measured saved-amount delta; negative means a measured regression."""
    return _finite(name, value)


# ---------------------------------------------------------------------------
# Per task
# ---------------------------------------------------------------------------

def token_savings_pct(primitive_first_total_tokens, baseline_total_tokens) -> float:
    """1 - primitive_first_total_tokens / baseline_total_tokens."""
    pf = _non_negative("primitive_first_total_tokens", primitive_first_total_tokens)
    base = _positive("baseline_total_tokens", baseline_total_tokens)
    return 1.0 - pf / base


def source_context_avoidance_pct(
    primitive_first_source_context_tokens, baseline_source_context_tokens
) -> float:
    """1 - primitive_first_source_context_tokens / baseline_source_context_tokens."""
    pf = _non_negative(
        "primitive_first_source_context_tokens", primitive_first_source_context_tokens
    )
    base = _positive("baseline_source_context_tokens", baseline_source_context_tokens)
    return 1.0 - pf / base


def cost_savings_pct(primitive_first_total_cost, baseline_total_cost) -> float:
    """1 - primitive_first_total_cost / baseline_total_cost."""
    pf = _non_negative("primitive_first_total_cost", primitive_first_total_cost)
    base = _positive("baseline_total_cost", baseline_total_cost)
    return 1.0 - pf / base


def speedup_factor(baseline_wall_clock_seconds, primitive_first_wall_clock_seconds) -> float:
    """baseline_wall_clock_seconds / primitive_first_wall_clock_seconds."""
    base = _positive("baseline_wall_clock_seconds", baseline_wall_clock_seconds)
    pf = _positive("primitive_first_wall_clock_seconds", primitive_first_wall_clock_seconds)
    return base / pf


def proof_coverage(passed_proof_requirements, total_proof_requirements) -> float:
    """passed_proof_requirements / total_proof_requirements."""
    passed = _count("passed_proof_requirements", passed_proof_requirements)
    total = _count("total_proof_requirements", total_proof_requirements)
    if total == 0:
        raise ValueError(
            "total_proof_requirements must be > 0 (coverage of zero requirements is undefined)"
        )
    if passed > total:
        raise ValueError(
            f"passed_proof_requirements ({passed}) cannot exceed "
            f"total_proof_requirements ({total})"
        )
    return passed / total


def reuse_ratio(reused_route_steps, total_route_steps) -> float:
    """reused_route_steps / total_route_steps."""
    reused = _count("reused_route_steps", reused_route_steps)
    total = _count("total_route_steps", total_route_steps)
    if total == 0:
        raise ValueError("total_route_steps must be > 0 (ratio over zero steps is undefined)")
    if reused > total:
        raise ValueError(
            f"reused_route_steps ({reused}) cannot exceed total_route_steps ({total})"
        )
    return reused / total


# ---------------------------------------------------------------------------
# Per developer
# ---------------------------------------------------------------------------

def weekly_tokens_saved_per_developer(
    average_tasks_per_week, average_tokens_saved_per_task
) -> float:
    """average_tasks_per_week * average_tokens_saved_per_task."""
    tasks = _non_negative("average_tasks_per_week", average_tasks_per_week)
    saved = _measured_delta("average_tokens_saved_per_task", average_tokens_saved_per_task)
    return tasks * saved


def weekly_cost_saved_per_developer(average_tasks_per_week, average_cost_saved_per_task) -> float:
    """average_tasks_per_week * average_cost_saved_per_task."""
    tasks = _non_negative("average_tasks_per_week", average_tasks_per_week)
    saved = _measured_delta("average_cost_saved_per_task", average_cost_saved_per_task)
    return tasks * saved


def weekly_hours_saved_per_developer(
    average_tasks_per_week, average_wall_clock_seconds_saved_per_task
) -> float:
    """average_tasks_per_week * average_wall_clock_seconds_saved_per_task / 3600."""
    tasks = _non_negative("average_tasks_per_week", average_tasks_per_week)
    saved = _measured_delta(
        "average_wall_clock_seconds_saved_per_task", average_wall_clock_seconds_saved_per_task
    )
    return tasks * saved / SECONDS_PER_HOUR


# ---------------------------------------------------------------------------
# Per 100K developers / users
# ---------------------------------------------------------------------------

def per_100k_developers(weekly_per_developer_value) -> float:
    """weekly_per_developer_value * 100000 (generic per-100K multiplier)."""
    value = _measured_delta("weekly_per_developer_value", weekly_per_developer_value)
    return value * PER_100K_MULTIPLIER


# ---------------------------------------------------------------------------
# Route amortization
# ---------------------------------------------------------------------------

def break_even_tasks(primitive_creation_cost, average_future_cost_saved_per_task) -> float:
    """primitive_creation_cost / average_future_cost_saved_per_task."""
    creation = _non_negative("primitive_creation_cost", primitive_creation_cost)
    saved = _positive("average_future_cost_saved_per_task", average_future_cost_saved_per_task)
    return creation / saved


def route_reuse_value(
    route_reuse_count, average_tokens_saved_per_reuse, proof_success_rate
) -> float:
    """route_reuse_count * average_tokens_saved_per_reuse * proof_success_rate."""
    count = _count("route_reuse_count", route_reuse_count)
    saved = _measured_delta("average_tokens_saved_per_reuse", average_tokens_saved_per_reuse)
    rate = _probability("proof_success_rate", proof_success_rate)
    return count * saved * rate


def promotion_value(
    future_tokens_avoided_estimate, proof_success_rate, reuse_probability
) -> float:
    """future_tokens_avoided_estimate * proof_success_rate * reuse_probability."""
    avoided = _non_negative("future_tokens_avoided_estimate", future_tokens_avoided_estimate)
    rate = _probability("proof_success_rate", proof_success_rate)
    prob = _probability("reuse_probability", reuse_probability)
    return avoided * rate * prob


# ---------------------------------------------------------------------------
# Registry and measurement status
# ---------------------------------------------------------------------------

FORMULAS = {
    "token_savings_pct": token_savings_pct,
    "source_context_avoidance_pct": source_context_avoidance_pct,
    "cost_savings_pct": cost_savings_pct,
    "speedup_factor": speedup_factor,
    "proof_coverage": proof_coverage,
    "reuse_ratio": reuse_ratio,
    "weekly_tokens_saved_per_developer": weekly_tokens_saved_per_developer,
    "weekly_cost_saved_per_developer": weekly_cost_saved_per_developer,
    "weekly_hours_saved_per_developer": weekly_hours_saved_per_developer,
    "per_100k_developers": per_100k_developers,
    "break_even_tasks": break_even_tasks,
    "route_reuse_value": route_reuse_value,
    "promotion_value": promotion_value,
}

# Which real inputs exist today, and which do not. "NOT YET RUN" /
# "NOT YET MEASURED" entries mean the formula CANNOT be honestly computed
# yet; do not feed it estimates and present the result as measured.
MEASUREMENT_STATUS = {
    "token_savings_pct": [
        "baseline arm scorecard (A1/A2): NOT YET RUN",
        "primitive-first arm scorecard (A4): benchmarks/runs/*/scorecards.jsonl"
        " (runtime_llm_tokens; measured 0 in fixture_offline replay)",
    ],
    "source_context_avoidance_pct": [
        "baseline source-context token telemetry (A1/A2): NOT YET RUN",
        "primitive-first source-context token telemetry: NOT YET MEASURED"
        " (A4 scorecards record runtime_llm_tokens only)",
    ],
    "cost_savings_pct": [
        "baseline arm cost telemetry (A1/A2): NOT YET RUN",
        "primitive-first cost telemetry: NOT YET MEASURED"
        " (no cost fields recorded in current scorecards)",
    ],
    "speedup_factor": [
        "baseline arm wall clock (A1/A2): NOT YET RUN",
        "primitive-first wall clock (A4): benchmarks/runs/*/scorecards.jsonl"
        " (wall_clock_seconds, fixture_offline)",
    ],
    "proof_coverage": [
        "execution receipts: benchmarks/runs/*/receipts.jsonl (proof_results, measured)",
        "per-task scorecards (A4): benchmarks/runs/*/scorecards.jsonl"
        " (proof_coverage, measured)",
    ],
    "reuse_ratio": [
        "route step reuse telemetry: NOT YET MEASURED"
        " (scorecards record primitive_reuse_count, currently 0; no reused-step"
        " provenance exists yet)",
    ],
    "weekly_tokens_saved_per_developer": [
        "average_tasks_per_week: NOT YET MEASURED (no developer telemetry exists)",
        "average_tokens_saved_per_task: NOT YET MEASURED"
        " (requires baseline arms A1/A2 to run)",
    ],
    "weekly_cost_saved_per_developer": [
        "average_tasks_per_week: NOT YET MEASURED (no developer telemetry exists)",
        "average_cost_saved_per_task: NOT YET MEASURED"
        " (requires baseline arms A1/A2 to run)",
    ],
    "weekly_hours_saved_per_developer": [
        "average_tasks_per_week: NOT YET MEASURED (no developer telemetry exists)",
        "average_wall_clock_seconds_saved_per_task: NOT YET MEASURED"
        " (requires baseline arms A1/A2 to run)",
    ],
    "per_100k_developers": [
        "weekly_per_developer_value: NOT YET MEASURED"
        " (derived from the weekly_*_saved_per_developer formulas above,"
        " none of which have measured inputs yet)",
    ],
    "break_even_tasks": [
        "primitive_creation_cost: NOT YET MEASURED (no build-cost telemetry exists)",
        "average_future_cost_saved_per_task: NOT YET MEASURED"
        " (requires baseline arms A1/A2 to run)",
    ],
    "route_reuse_value": [
        "route_reuse_count: NOT YET MEASURED"
        " (scorecards primitive_reuse_count is currently 0)",
        "average_tokens_saved_per_reuse: NOT YET MEASURED"
        " (requires baseline arms A1/A2 to run)",
        "proof_success_rate: benchmarks/runs/*/receipts.jsonl (proof_results, measured)",
    ],
    "promotion_value": [
        "future_tokens_avoided_estimate: NOT YET MEASURED"
        " (no promotion has occurred; nothing in this repo serves truth)",
        "proof_success_rate: benchmarks/runs/*/receipts.jsonl (proof_results, measured)",
        "reuse_probability: NOT YET MEASURED (no reuse telemetry exists)",
    ],
}


# ---------------------------------------------------------------------------
# Self test (synthetic inputs only - these numbers verify algebra, they are
# not measurements and must never be quoted as results)
# ---------------------------------------------------------------------------

def _self_test() -> dict:
    failures: list[str] = []
    exercised: set[str] = set()

    def eq(formula_name: str, actual: float, expected: float, label: str) -> None:
        exercised.add(formula_name)
        if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12):
            failures.append(f"{label}: expected {expected!r}, got {actual!r}")

    def raises(formula_name: str, fn, args: tuple, label: str) -> None:
        exercised.add(formula_name)
        try:
            fn(*args)
        except ValueError:
            return
        failures.append(f"{label}: expected ValueError, none raised")

    # Algebra checks (synthetic inputs).
    eq("token_savings_pct", token_savings_pct(50, 100), 0.5, "token_savings_pct(50,100)")
    eq("token_savings_pct", token_savings_pct(100, 100), 0.0, "token_savings_pct(100,100)")
    eq("token_savings_pct", token_savings_pct(150, 100), -0.5,
       "token_savings_pct(150,100) measured regression")
    eq("source_context_avoidance_pct", source_context_avoidance_pct(25, 100), 0.75,
       "source_context_avoidance_pct(25,100)")
    eq("cost_savings_pct", cost_savings_pct(1.0, 4.0), 0.75, "cost_savings_pct(1,4)")
    eq("speedup_factor", speedup_factor(10, 2), 5.0, "speedup_factor(10,2)")
    eq("proof_coverage", proof_coverage(3, 4), 0.75, "proof_coverage(3,4)")
    eq("reuse_ratio", reuse_ratio(2, 8), 0.25, "reuse_ratio(2,8)")
    eq("weekly_tokens_saved_per_developer",
       weekly_tokens_saved_per_developer(10, 500), 5000.0,
       "weekly_tokens_saved_per_developer(10,500)")
    eq("weekly_cost_saved_per_developer",
       weekly_cost_saved_per_developer(10, 0.25), 2.5,
       "weekly_cost_saved_per_developer(10,0.25)")
    eq("weekly_hours_saved_per_developer",
       weekly_hours_saved_per_developer(10, 360), 1.0,
       "weekly_hours_saved_per_developer(10,360)")
    eq("per_100k_developers", per_100k_developers(2.0), 200000.0, "per_100k_developers(2.0)")
    eq("break_even_tasks", break_even_tasks(100.0, 4.0), 25.0, "break_even_tasks(100,4)")
    eq("route_reuse_value", route_reuse_value(10, 500, 0.9), 4500.0,
       "route_reuse_value(10,500,0.9)")
    eq("promotion_value", promotion_value(10000, 0.9, 0.5), 4500.0,
       "promotion_value(10000,0.9,0.5)")

    # Error paths (synthetic inputs).
    raises("token_savings_pct", token_savings_pct, (50, 0), "token_savings_pct zero baseline")
    raises("token_savings_pct", token_savings_pct, (-1, 100),
           "token_savings_pct negative tokens")
    raises("source_context_avoidance_pct", source_context_avoidance_pct, (10, 0),
           "source_context_avoidance_pct zero baseline")
    raises("cost_savings_pct", cost_savings_pct, (1.0, 0.0), "cost_savings_pct zero baseline")
    raises("speedup_factor", speedup_factor, (10, 0), "speedup_factor zero denominator")
    raises("speedup_factor", speedup_factor, (0, 10), "speedup_factor zero baseline")
    raises("proof_coverage", proof_coverage, (1, 0), "proof_coverage zero total")
    raises("proof_coverage", proof_coverage, (5, 4), "proof_coverage passed > total")
    raises("proof_coverage", proof_coverage, (-1, 4), "proof_coverage negative count")
    raises("reuse_ratio", reuse_ratio, (1, 0), "reuse_ratio zero total")
    raises("reuse_ratio", reuse_ratio, (9, 8), "reuse_ratio reused > total")
    raises("weekly_tokens_saved_per_developer", weekly_tokens_saved_per_developer,
           (-1, 500), "weekly_tokens negative tasks_per_week")
    raises("weekly_cost_saved_per_developer", weekly_cost_saved_per_developer,
           (-1, 0.25), "weekly_cost negative tasks_per_week")
    raises("weekly_hours_saved_per_developer", weekly_hours_saved_per_developer,
           (-1, 360), "weekly_hours negative tasks_per_week")
    raises("per_100k_developers", per_100k_developers, (float("nan"),),
           "per_100k_developers NaN")
    raises("break_even_tasks", break_even_tasks, (100.0, 0.0),
           "break_even_tasks zero savings denominator")
    raises("break_even_tasks", break_even_tasks, (-1.0, 4.0),
           "break_even_tasks negative creation cost")
    raises("route_reuse_value", route_reuse_value, (-1, 500, 0.9),
           "route_reuse_value negative count")
    raises("route_reuse_value", route_reuse_value, (10, 500, 1.5),
           "route_reuse_value probability > 1")
    raises("promotion_value", promotion_value, (10000, -0.1, 0.5),
           "promotion_value probability < 0")
    raises("promotion_value", promotion_value, (-1, 0.9, 0.5),
           "promotion_value negative estimate")

    # Registry invariants.
    if exercised != set(FORMULAS):
        failures.append(
            "self-test coverage mismatch: "
            f"missing={sorted(set(FORMULAS) - exercised)}, "
            f"unknown={sorted(exercised - set(FORMULAS))}"
        )
    if set(MEASUREMENT_STATUS) != set(FORMULAS):
        failures.append(
            "MEASUREMENT_STATUS keys do not match FORMULAS: "
            f"missing={sorted(set(FORMULAS) - set(MEASUREMENT_STATUS))}, "
            f"extra={sorted(set(MEASUREMENT_STATUS) - set(FORMULAS))}"
        )
    for name, sources in MEASUREMENT_STATUS.items():
        if not sources or not all(isinstance(s, str) and s for s in sources):
            failures.append(f"MEASUREMENT_STATUS[{name!r}] must be a non-empty list of strings")

    return {
        "ok": not failures,
        "formulas_checked": len(FORMULAS),
        "self_test_inputs": "synthetic",
        "failures": failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true",
                        help="verify formula algebra and error paths with synthetic inputs")
    parser.add_argument("--status", action="store_true",
                        help="print MEASUREMENT_STATUS (which inputs exist today)")
    args = parser.parse_args(argv)

    if args.self_test:
        result = _self_test()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 1
    if args.status:
        print(json.dumps({
            "note": ("formulas only; nothing here is a measurement -"
                     " feed measured inputs from receipts and scorecards"),
            "measurement_status": MEASUREMENT_STATUS,
        }, indent=2, sort_keys=True))
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
