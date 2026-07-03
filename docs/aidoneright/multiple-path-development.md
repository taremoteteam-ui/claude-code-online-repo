# AIDoneRight Standard 002 — Multiple-Path Development

Status: **candidate standard** · Reference impl: `primitives/multipath.py` ·
Demo: `scripts/run_multipath_demo.py` · Tests: `tests/test_multipath.py`

## The rule

When there is more than one reasonable way to do something, **do not decide up
front.** Build every reasonable path behind one contract, **benchmark** them,
**let the data choose**, and keep the losers as an ordered **fallback** chain. A
decision made by argument is a decision unmeasured; MPD replaces the argument with
a scorecard.

This is the non-commitment law as a *development* discipline (build/eval time),
complementary to the runtime decision engine (`decision-portfolio-substrate.md`).
All paths in a portfolio produce the same **Globally Unique Name** (Standard 001) —
MPD is what turns a "multi-path artifact" from a review note into a measured
choice.

## When it applies

Any point where you were about to write `if strategy == ...`, pick a library,
choose an algorithm, set a heuristic, or hardcode an order. If a competent
engineer could reasonably disagree about the choice, it is a portfolio, not a
constant.

## The loop (executable)

```python
from primitives.multipath import select_portfolio, run_with_fallback

paths = [ {"path_id": "p.a", "impl": fn_a, "produces": "task.gun", "cost_hint": 1.0},
          {"path_id": "p.b", "impl": fn_b, "produces": "task.gun", "cost_hint": 2.0} ]
cases = [ {"input": ..., "expected": ...}, ... ]      # or use a score_fn

receipt = select_portfolio(paths, cases)              # benchmark + choose
order = [receipt["decision"]["chosen"], *receipt["decision"]["fallback_chain"]]
result = run_with_fallback({p["path_id"]: p["impl"] for p in paths}, order, live_input)
```

- **`benchmark_paths`** scores every path on the same cases (exact-match or a
  `score_fn`); a path that crashes is *measured as a failure*, not fatal.
- **`choose`** ranks by correctness, then mean score, then cost, then id (a fully
  disclosed ranking) and returns the winner plus the fallback chain — never a
  silent pick.
- **`run_with_fallback`** runs the winner; on failure (an exception **or** a
  `None` "I can't") it falls through the chain and records who served, so a
  fallback is always visible.

The demo (`run_multipath_demo.py`) parses a messy int list three ways
(`comma_split` / `regex_delims` / `extract_ints`): measured correctness
0.25 / 0.75 / 1.0, winner `extract_ints`, and a fallback that *actually fires* —
`regex_delims` returns `None` on `x10y20` and `extract_ints` serves, recorded in
the attempt trail.

## Artifacts a portfolio produces

- a **scorecard per path** (correctness, errors, mean score, cost) — candidate;
- an **mpd_choice** receipt (chosen + fallback chain + disclosed ranking);
- at runtime, an **attempt trail** naming which path served.

## How it composes with the rest of the stack

- **Standard 001 (GUVN):** every path in a portfolio produces the same GUN; the
  tracer flags the multi-path artifact, MPD resolves it.
- **Decision engine:** a portfolio can graduate from build-time selection to a
  runtime `DecisionPoint` when the best path is *context-dependent* — the cases
  become logged receipts and a selection policy chooses per request.
- **Route compiler:** once chosen, the winning path is one node on the capability
  graph; the fallback chain is the compiler's degradation plan.
- **Off-policy evaluation / CRM:** when paths are compared on *logged* rather than
  held-out cases, use the OPE estimators so the comparison is unbiased.

## Discipline

- Enumerate paths that are genuinely *reasonable* — MPD is not brute force over
  nonsense; log what you excluded and why.
- The benchmark cases are the contract; grow them when a path fails in production
  (that failure becomes a new case, and the portfolio re-chooses).
- Never drop a path silently for cost — record it in the fallback chain. Every
  scorecard and choice is `candidate: true, serves_truth: false` until a real
  measurement backs it.
