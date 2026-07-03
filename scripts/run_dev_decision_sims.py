#!/usr/bin/env python3
"""Realistic developer-decision simulations: the same engine driving everyday
engineering choices, picking correctly per CONTEXT - some by structural
applicability, some by learned receipts.

Each scenario is a decision an engineer normally hardcodes. Here it is a
portfolio; the engine chooses per context. Two mechanisms are exercised:
  - structural: applicability predicates alone settle a choice (retrying a
    non-idempotent call is simply not allowed);
  - learned: context-conditioned receipts settle a choice (protobuf wins for
    large stable-schema payloads; json wins for small evolving ones).

Every expected answer is asserted, so a regression flips the gate. Zero model
calls; deterministic.

Usage: python3 scripts/run_dev_decision_sims.py --self-test
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from primitives.decision_engine import LedgerStats, choose, context_signature  # noqa: E402


def _p(did, pid, requires=None, conds=None, cost_ms=10):
    return {"record_type": "execution_path", "path_id": pid, "decision_id": did, "title": pid,
            "method": "one interchangeable way to satisfy this engineering decision",
            "applicability": {"requires_keys": requires or [], "conditions": conds or []},
            "cost_model": {"tokens": 0, "latency_ms": cost_ms, "side_effect_risk": "none"},
            "reversibility": "reversible", "preference_rank": 0, "deterministic": True,
            "expected_receipts": ["win"], "version": "0", "candidate": True, "serves_truth": False}


def _d(did, keys, policy="argmax_receipts", default=None):
    return {"decision_id": did, "context_signature": keys,
            "contract": {"input": "x", "output": "y", "win_definition": "the choice performs best here",
                         "consumes": [], "produces": ["z"]},
            "selection_policy": policy, "default_path": default}


def _receipts(did, keys, ctx, path, wins, seq0):
    return [{"decision_id": did, "path_id": path, "context_signature": context_signature(did, ctx, keys),
             "sequence": seq0 + i, "applicable": True, "chosen": True, "proved": w > 0,
             "win_score": w, "cost_observed": 10, "candidate": True, "serves_truth": False}
            for i, w in enumerate(wins)]


def run() -> dict:
    scenarios = []

    # 1. Retry policy - STRUCTURAL: non-idempotent forbids retry paths.
    did = "decision:eng.retry_policy"
    keys = ["idempotent", "error_kind"]
    idem = [{"key": "idempotent", "op": "truthy"}]
    paths = [_p(did, "path:retry.none"),
             _p(did, "path:retry.fixed", ["idempotent"], idem),
             _p(did, "path:retry.exp_backoff", ["idempotent"], idem),
             _p(did, "path:retry.circuit_breaker", ["idempotent"], idem)]
    d = _d(did, keys, policy="deterministic_tier", default="path:retry.none")
    ctx_bad = {"idempotent": False, "error_kind": "transient"}
    c1 = choose(d, paths, ctx_bad)
    scenarios.append({"scenario": "retry / non-idempotent", "context": ctx_bad,
                      "chosen": c1["chosen_path"], "expected": "path:retry.none",
                      "why": "retry paths require idempotency; only no-retry is applicable"})

    # 2. Serialization - LEARNED per context.
    did = "decision:eng.serialization"
    keys = ["payload_size", "schema"]
    paths = [_p(did, "path:ser.json"), _p(did, "path:ser.msgpack"), _p(did, "path:ser.protobuf")]
    d = _d(did, keys, default="path:ser.json")
    led, seq = [], 0
    big = {"payload_size": "large", "schema": "stable"}
    small = {"payload_size": "small", "schema": "evolving"}
    for ctx, best in [(big, "path:ser.protobuf"), (small, "path:ser.json")]:
        for p in paths:
            w = [0.95] * 6 if p["path_id"] == best else [0.55] * 6
            led += _receipts(did, keys, ctx, p["path_id"], w, seq); seq += 6
    for ctx, best in [(big, "path:ser.protobuf"), (small, "path:ser.json")]:
        sig = context_signature(did, ctx, keys)
        c = choose(d, paths, ctx, LedgerStats.from_receipts(led, only_context=sig))
        scenarios.append({"scenario": f"serialization / {ctx['payload_size']}-{ctx['schema']}",
                          "context": ctx, "chosen": c["chosen_path"], "expected": best,
                          "why": "learned from context-conditioned receipts"})

    # 3. Concurrency - LEARNED per workload.
    did = "decision:eng.concurrency"
    keys = ["workload"]
    paths = [_p(did, "path:conc.sync"), _p(did, "path:conc.threadpool"),
             _p(did, "path:conc.async"), _p(did, "path:conc.multiprocess")]
    d = _d(did, keys, default="path:conc.sync")
    led, seq = [], 0
    io = {"workload": "io_bound"}
    cpu = {"workload": "cpu_bound"}
    for ctx, best in [(io, "path:conc.async"), (cpu, "path:conc.multiprocess")]:
        for p in paths:
            w = [0.9] * 6 if p["path_id"] == best else [0.5] * 6
            led += _receipts(did, keys, ctx, p["path_id"], w, seq); seq += 6
    for ctx, best in [(io, "path:conc.async"), (cpu, "path:conc.multiprocess")]:
        sig = context_signature(did, ctx, keys)
        c = choose(d, paths, ctx, LedgerStats.from_receipts(led, only_context=sig))
        scenarios.append({"scenario": f"concurrency / {ctx['workload']}", "context": ctx,
                          "chosen": c["chosen_path"], "expected": best,
                          "why": "learned from context-conditioned receipts"})

    correct = sum(1 for s in scenarios if s["chosen"] == s["expected"])
    return {"run_id": "devsims", "scenarios": scenarios,
            "correct": correct, "total": len(scenarios),
            "candidate": True, "serves_truth": False,
            "honesty_notes": [
                "structural choices are settled by applicability predicates (no receipts needed)",
                "learned choices are settled by context-conditioned receipts, not hardcoding",
                "one engine drives every scenario; the engineer declared only paths + context + win",
            ]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test:
        parser.print_help()
        return 2
    result = run()
    print(json.dumps(result, indent=2))
    return 0 if result["correct"] == result["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
