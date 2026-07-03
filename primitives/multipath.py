"""Multiple-Path Development (MPD): don't decide HOW to do something up front -
build every reasonable path behind one contract, benchmark them, let the data
choose, and keep the losers as an ordered fallback chain.

This is the non-commitment law applied as a DEVELOPMENT technique (build/eval
time), complementary to the runtime decision engine. All paths in a portfolio
produce the same Globally Unique Name (Standard 001), i.e. the same substitutable
contract; MPD is exactly what turns a "multi-path artifact" from a review note
into a measured choice.

The loop:
  benchmark_paths(paths, cases)  -> a scorecard per path (correctness, errors)
  choose(scorecards)             -> winner + ranked fallback chain (disclosed)
  run_with_fallback(impls, order, value)
                                 -> run the winner; on failure (raise or None)
                                    fall through the chain; record who served

`select_portfolio` runs all three and returns one auditable receipt. Every path's
result is measured, never assumed; nothing is chosen silently. Pure and
deterministic; stdlib only; candidate material.
"""

from __future__ import annotations


def _call(impl, value):
    """Call an impl with a case value. A dict value is spread as kwargs, a tuple
    as positional args, anything else as a single positional arg."""
    if isinstance(value, dict):
        return impl(**value)
    if isinstance(value, tuple):
        return impl(*value)
    return impl(value)


def benchmark_paths(paths: list[dict], cases: list[dict], score_fn=None) -> list[dict]:
    """Score each path on the same cases. A path is {path_id, impl, produces,
    cost_hint?}. A case is {input, expected}. Without score_fn, a case passes iff
    the output equals `expected`; with score_fn(output, case) -> [0,1], the mean
    score is recorded and a case 'passes' at score >= 1.0. Exceptions are caught
    and counted as failures - a path that crashes is measured, not fatal."""
    n = len(cases) or 1
    scorecards = []
    for p in paths:
        passed = errors = 0
        score_sum = 0.0
        for case in cases:
            try:
                out = _call(p["impl"], case["input"])
            except Exception:  # noqa: BLE001 - a crash is a failed case, measured
                errors += 1
                continue
            s = float(score_fn(out, case)) if score_fn else (1.0 if out == case["expected"] else 0.0)
            score_sum += s
            if s >= 1.0:
                passed += 1
        scorecards.append({
            "path_id": p["path_id"], "produces": p.get("produces"),
            "cases": len(cases), "passed": passed, "errors": errors,
            "correctness": round(passed / n, 4), "mean_score": round(score_sum / n, 4),
            "cost_hint": p.get("cost_hint", 1.0),
            "candidate": True, "serves_truth": False,
        })
    return scorecards


def choose(scorecards: list[dict]) -> dict:
    """Rank the scorecards and return the winner plus the ordered fallback chain.
    Ranking (all disclosed): higher correctness, then higher mean_score, then lower
    cost_hint, then path_id for a deterministic tie-break."""
    ranked = sorted(scorecards, key=lambda s: (
        -s["correctness"], -s["mean_score"], s["cost_hint"], s["path_id"]))
    order = [s["path_id"] for s in ranked]
    return {
        "record_type": "mpd_choice",
        "chosen": order[0] if order else None,
        "fallback_chain": order[1:],
        "ranking": [{"path_id": s["path_id"], "correctness": s["correctness"],
                     "mean_score": s["mean_score"], "cost_hint": s["cost_hint"]}
                    for s in ranked],
        "reason": "max correctness, then mean_score, then min cost (disclosed ranking)",
        "candidate": True, "serves_truth": False,
    }


def run_with_fallback(impls: dict, order: list[str], value) -> dict:
    """Run paths in `order` until one succeeds. A path FAILS if it raises or
    returns None; then the next path is tried. Records every attempt and which
    path ultimately served - so a fallback is always visible, never silent."""
    attempts = []
    for pid in order:
        try:
            out = _call(impls[pid], value)
        except Exception as exc:  # noqa: BLE001
            attempts.append({"path_id": pid, "ok": False, "error": repr(exc)})
            continue
        if out is None:
            attempts.append({"path_id": pid, "ok": False, "error": "returned None"})
            continue
        attempts.append({"path_id": pid, "ok": True})
        return {"value": out, "served_by": pid, "attempts": attempts,
                "candidate": True, "serves_truth": False}
    return {"value": None, "served_by": None, "attempts": attempts,
            "candidate": True, "serves_truth": False}


def select_portfolio(paths: list[dict], cases: list[dict], score_fn=None) -> dict:
    """The whole MPD loop as one auditable receipt: benchmark every path, choose
    the winner + fallback chain, and return both plus the scorecards."""
    scorecards = benchmark_paths(paths, cases, score_fn=score_fn)
    decision = choose(scorecards)
    return {
        "record_type": "mpd_portfolio_receipt",
        "path_count": len(paths), "case_count": len(cases),
        "scorecards": scorecards, "decision": decision,
        "candidate": True, "serves_truth": False,
    }
