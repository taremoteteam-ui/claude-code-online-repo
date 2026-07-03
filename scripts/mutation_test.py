"""Mutation testing: verify the proof suite actually CATCHES bugs.

A green test suite proves nothing if the tests are toothless. This harness
injects a real defect into a core module (flips a comparison, a sign, a
predicate), runs the specific gate that SHOULD catch it, and confirms that gate
goes RED. A mutation that SURVIVES (the gate stays green) is a hole in the
verification - reported, not hidden. Every mutation restores the source in a
finally block, so the tree is always left clean even on error.

This is meta-verification: it tests the tests. Deterministic; stdlib only.

Usage: python3 scripts/mutation_test.py --self-test
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def _purge_pycache() -> None:
    """Remove all bytecode caches. Critical: a catcher imports the MUTATED
    module; if it wrote a .pyc, restoring the .py within the same second leaves
    Python using the stale mutated bytecode (matching mtimes). We run catchers
    with PYTHONDONTWRITEBYTECODE and purge caches to be doubly safe."""
    for d in REPO_ROOT.rglob("__pycache__"):
        shutil.rmtree(d, ignore_errors=True)

# Each mutation: a real defect in a core module + the fast gate that must catch
# it. `find` must occur exactly once. `catcher` should EXIT NON-ZERO on the
# mutated code (the bug is detected).
MUTATIONS = [
    {"name": "route_compiler_all_to_any",
     "file": "primitives/route_compiler.py",
     "find": "if all(ct in available for ct in reqs):",
     "replace": "if any(ct in available for ct in reqs):",
     "catcher": [PY, "scripts/verify_decision_engine.py", "--self-test", "--trials", "40"],
     "why": "an unsound compiler (fires nodes with unmet inputs) must fail P8 soundness"},
    {"name": "route_validator_never_missing",
     "file": "primitives/route_validator.py",
     "find": "missing = [r for r in reqs if r not in available]",
     "replace": "missing = []",
     "catcher": [PY, "-m", "unittest", "tests.test_orderers"],
     "why": "a validator that never reports missing inputs must fail the reversed-order test"},
    {"name": "planner_gate_order_sign_flip",
     "file": "primitives/decision_planner.py",
     "find": 'ordered = sorted(resolved, key=lambda g: (-g["ratio"], g["gate_id"]))',
     "replace": 'ordered = sorted(resolved, key=lambda g: (g["ratio"], g["gate_id"]))',
     "catcher": [PY, "scripts/verify_decision_engine.py", "--self-test", "--trials", "40"],
     "why": "reversing the fail-fast gate order must fail P2 optimality"},
    {"name": "planner_expected_cost_inverted",
     "file": "primitives/decision_planner.py",
     "find": "exp_cost = normalize_cost(path[\"cost_model\"]) / success   # amortised retry cost",
     "replace": "exp_cost = normalize_cost(path[\"cost_model\"]) * success   # amortised retry cost",
     "catcher": [PY, "scripts/verify_decision_engine.py", "--self-test", "--trials", "40"],
     "why": "inverting expected-cost must fail P1/P7 vs brute force"},
    {"name": "decision_graph_fire_any_fork",
     "file": "primitives/decision_graph.py",
     "find": "if consumes <= available:",
     "replace": "if True:",
     "catcher": [PY, "-m", "unittest", "tests.test_decision_graph"],
     "why": "firing forks whose contracts are unmet must break the ordering test"},
    {"name": "foundry_sanitize_disabled",
     "file": "primitives/foundry.py",
     "find": "    return \"\".join(p[:1].upper() + p[1:] for p in parts)",
     "replace": "    return raw",
     "catcher": [PY, "-m", "unittest", "tests.test_foundry"],
     "why": "disabling type sanitization must fail the messy-type robustness test"},
    {"name": "decision_engine_default_tiebreak_inverted",
     "file": "primitives/decision_engine.py",
     "find": "                base += 1e-6",
     "replace": "                base -= 1e-6",
     "catcher": [PY, "-m", "unittest", "tests.test_decision_engine"],
     "why": "inverting the cold-start default-path tie-break must fail the cold-start test"},
    {"name": "type_adapter_auth_gate_inverted",
     "file": "primitives/type_adapters.py",
     "find": "    allow = decision == \"allow\"",
     "replace": "    allow = decision != \"allow\"",
     "catcher": [PY, "scripts/check_type_adapters_pack.py", "--self-test"],
     "why": "an auth adapter that authenticates DENY decisions must fail its allow-gate proof"},
    {"name": "route_runtime_ran_always_true",
     "file": "primitives/route_runtime.py",
     "find": "    ran = not unimplemented and error is None",
     "replace": "    ran = True",
     "catcher": [PY, "-m", "unittest", "tests.test_route_runtime"],
     "why": "claiming a route ran when a step is unimplemented must fail the honest-stop test"},
    {"name": "policy_eval_regret_sign_flip",
     "file": "primitives/policy_evaluation.py",
     "find": "        regret += best - rnd[\"true_means\"][chosen]",
     "replace": "        regret += rnd[\"true_means\"][chosen] - best",
     "catcher": [PY, "-m", "unittest", "tests.test_policy_evaluation"],
     "why": "inverting the counterfactual regret sign must fail the learner-beats-baseline test"},
    {"name": "off_policy_dr_correction_dropped",
     "file": "primitives/off_policy_estimators.py",
     "find": "        total += baseline + w * (e[\"reward\"] - reward_model(x, a))",
     "replace": "        total += baseline",
     "catcher": [PY, "-m", "unittest", "tests.test_off_policy_estimators"],
     "why": "dropping the doubly-robust correction collapses DR to the biased direct method "
            "and must fail the misspecified-model robustness test"},
    {"name": "algo_union_find_counter_corrupted",
     "file": "primitives/algorithmic_primitives.py",
     "find": "        self.components -= 1",
     "replace": "        self.components += 1",
     "catcher": [PY, "-m", "unittest", "tests.test_coding_solutions"],
     "why": "corrupting the shared union-find component counter must fail every solution "
            "that reuses it (islands, provinces) - the decomposition has teeth"},
    {"name": "crm_variance_penalty_sign_flip",
     "file": "primitives/policy_learning.py",
     "find": "    return value - lam * penalty",
     "replace": "    return value + lam * penalty",
     "catcher": [PY, "-m", "unittest", "tests.test_policy_learning"],
     "why": "flipping the CRM variance penalty to a bonus (rewarding uncertainty) must fail "
            "the penalty-never-increases-score test"},
    {"name": "guvn_multipath_classification_broken",
     "file": "primitives/guvn.py",
     "find": "        \"multi_path_artifacts\": [a for a, m in classified.items() if m[\"kind\"] == \"multi_path\"],",
     "replace": "        \"multi_path_artifacts\": [a for a, m in classified.items() if m[\"kind\"] == \"internal\"],",
     "catcher": [PY, "-m", "unittest", "tests.test_guvn"],
     "why": "misclassifying multi-path artifacts in the code map must fail the tracer's "
            "classification test"},
]


def _run(catcher) -> int:
    # PYTHONDONTWRITEBYTECODE: the catcher imports the MUTATED module; without
    # this it would write a .pyc compiled from mutated source, and restoring the
    # .py within the same filesystem-mtime tick would leave Python loading the
    # stale mutated bytecode on the next run (poisoning every later stage).
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.run(catcher, cwd=REPO_ROOT, capture_output=True, text=True,
                          timeout=300, env=env)
    return proc.returncode


def run() -> dict:
    _purge_pycache()   # start from a clean cache so no stale .pyc leaks in
    results = []
    for m in MUTATIONS:
        path = REPO_ROOT / m["file"]
        original = path.read_text(encoding="utf-8")
        status = {"name": m["name"], "file": m["file"], "why": m["why"]}
        if original.count(m["find"]) != 1:
            status.update(caught=False, error=f"find-string appears {original.count(m['find'])} times (expected 1)")
            results.append(status)
            continue
        try:
            path.write_text(original.replace(m["find"], m["replace"], 1), encoding="utf-8")
            rc = _run(m["catcher"])
            status["caught"] = rc != 0   # gate went red => bug detected
            status["catcher_exit"] = rc
        except Exception as exc:  # noqa: BLE001
            status.update(caught=False, error=repr(exc))
        finally:
            path.write_text(original, encoding="utf-8")   # ALWAYS restore
            _purge_pycache()   # and drop any bytecode the catcher compiled
        results.append(status)

    survived = [r["name"] for r in results if not r.get("caught")]
    return {"record_type": "mutation_test", "mutations": len(MUTATIONS),
            "caught": sum(1 for r in results if r.get("caught")),
            "survived": survived, "results": results,
            "all_caught": not survived,
            "candidate": True, "serves_truth": False,
            "note": "a surviving mutation is a hole in the verification suite; source is always restored"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test:
        parser.print_help()
        return 2
    result = run()
    print(json.dumps(result, indent=2))
    return 0 if result["all_caught"] else 1


if __name__ == "__main__":
    sys.exit(main())
