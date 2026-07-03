#!/usr/bin/env python3
"""Optimality benchmark for the route compiler, against a brute-force oracle.

The compiler claims to find A route by edge composition. This measures HOW GOOD
that route is: over random typed graphs it compares the compiler's route length
to the TRUE minimal length (shortest number of node applications to produce the
wanted type), computed by BFS over the type-set state space (tractable because
the type alphabet is small). It also checks every compiled route is VALID and
IRREDUNDANT (no step can be removed without breaking reachability).

Honest: the compiler does not claim shortest-route optimality, so the optimality
fraction is REPORTED, not gated; the gate is on validity + irredundancy (a
compiler that emitted an invalid or padded route would fail). Deterministic
seeded PRNG. Zero model calls.

Usage: python3 scripts/run_route_compiler_benchmark.py --self-test [--trials N]
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import deque
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from primitives.route_compiler import compile_route  # noqa: E402
from primitives.route_validator import validate_order  # noqa: E402


def _rand_graph(rng):
    types = [f"T{i}" for i in range(rng.randint(3, 6))]
    nodes = []
    for i in range(rng.randint(3, 9)):
        ins = rng.sample(types, rng.randint(0, 2))
        out = rng.choice(types)
        nodes.append({"node_id": f"n{i}", "lane": "b", "kind": "primitive", "title": f"n{i}",
                      "input_edge": "+".join(ins) or "NoInput", "output_edge": out,
                      "required_input_ports": [{"name": t, "canonical_type": t} for t in ins],
                      "config_ports": [],
                      "output_ports": [{"name": out, "role": "data", "canonical_type": out}]})
    return types, nodes


def _optimal_len(have, want, nodes):
    """Min number of node applications to make `want` available, via BFS over
    frozenset(available-types). Returns None if unreachable."""
    start = frozenset(have)
    if want in start:
        return 0
    seen = {start}
    q = deque([(start, 0)])
    while q:
        state, d = q.popleft()
        for n in nodes:
            reqs = {p["canonical_type"] for p in n["required_input_ports"]}
            if reqs <= state:
                outs = {op["canonical_type"] for op in n["output_ports"]}
                new = state | outs
                if new == state:
                    continue
                if want in new:
                    return d + 1
                if new not in seen:
                    seen.add(new)
                    q.append((new, d + 1))
    return None


def _irredundant(order, have, want, nodes):
    """True if no single step can be dropped while still producing want."""
    for i in range(len(order)):
        reduced = order[:i] + order[i + 1:]
        if validate_order(reduced, have, want, nodes)["valid"]:
            return False   # step i was removable -> route was padded
    return True


def run(trials: int) -> dict:
    optimal = total = valid = irredundant = 0
    excess = []
    problems = []
    for t in range(trials):
        rng = random.Random(1000 + t)
        types, nodes = _rand_graph(rng)
        have = rng.sample(types, rng.randint(1, 2))
        want = rng.choice(types)
        opt = _optimal_len(have, want, nodes)
        route = compile_route(have, want, nodes)
        if not route["compiled"]:
            if opt is not None and opt > 0:
                problems.append({"trial": t, "issue": "reachable but not compiled"})
            continue
        total += 1
        order = [s["node_id"] for s in route["route_steps"]]
        v = validate_order(order, have, want, nodes)
        if v["valid"] and v["produces_want"]:
            valid += 1
        else:
            problems.append({"trial": t, "issue": "compiled route invalid"})
        if _irredundant(order, have, want, nodes):
            irredundant += 1
        else:
            problems.append({"trial": t, "issue": "route has a removable step"})
        lc = route["step_count"]
        if opt is not None:
            excess.append(lc - opt)
            if lc == opt:
                optimal += 1
    n = max(total, 1)
    return {
        "run_id": "routebench", "trials": trials, "compiled": total,
        "valid_fraction": round(valid / n, 4),
        "irredundant_fraction": round(irredundant / n, 4),
        "optimal_fraction": round(optimal / n, 4),
        "mean_excess_steps": round(sum(excess) / len(excess), 4) if excess else 0.0,
        "max_excess_steps": max(excess) if excess else 0,
        "problems": problems[:10],
        "candidate": True, "serves_truth": False,
        "honesty_notes": [
            "optimal length = min node applications to produce want, via BFS over the type-set state space (exact for small graphs)",
            "the compiler does not claim shortest-route optimality; optimal_fraction is reported, not gated",
            "the gate is validity + irredundancy: every compiled route must type-check and contain no removable step",
            "seeded PRNG - replayable",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--trials", type=int, default=400)
    args = parser.parse_args()
    if not (args.self_test or args.write):
        parser.print_help()
        return 2
    result = run(args.trials)
    print(json.dumps(result, indent=2))
    if args.write:
        out = REPO_ROOT / "benchmarks" / "route_compiler_runs"
        out.mkdir(parents=True, exist_ok=True)
        (out / "optimality_benchmark.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    # Gate: every compiled route valid + irredundant; no reachable-but-uncompiled.
    ok = (result["valid_fraction"] == 1.0 and result["irredundant_fraction"] == 1.0
          and not result["problems"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
