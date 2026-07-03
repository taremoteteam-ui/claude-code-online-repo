"""Off-policy / counterfactual policy evaluation: let logged data choose the
SELECTION POLICY itself, not just the path.

The decision engine offers several selection policies (deterministic_tier,
cheapest_that_proves, argmax_receipts, epsilon_greedy) plus a context-conditioned
variant. Which one to run is itself a decision - and the non-commitment law says
don't hardwire it: store every policy and let data choose. This module replays a
logged FULL-FEEDBACK history through each policy (using the REAL engine's
``choose``), measures the counterfactual regret each policy WOULD have accrued on
the same log, selects the best, and (in the benchmark) re-checks the winner on a
held-out segment so the choice is not overfit to the log it was picked on.

This is the flywheel: the system reads its own telemetry and improves its own
control policy from data, with the improvement MEASURED, not asserted.

Honesty boundary:
- Counterfactual regret is valid here only because the environment is a SIMULATED
  FULL-FEEDBACK log (every arm's outcome is recorded). On a partial-feedback
  production log you would need propensity weighting (IPS / doubly-robust); that
  is out of scope and flagged, never faked.
- The policy still LEARNS from partial feedback (only the arm it pulls updates its
  receipts) - the full-feedback log is used only to reveal the pulled arm's reward
  deterministically and to compute regret against a known oracle.
- Deterministic given a seed; every record is candidate=true / serves_truth=false.

Stdlib only.
"""

from __future__ import annotations

import random

from primitives.decision_engine import LedgerStats, choose, context_signature

# The policy portfolio: each is a thin descriptor over the engine's own
# selection machinery. 'contextual' conditions the receipt stats on the current
# learnable context (the engine's only_context seam); everything else is the
# stock engine policy named in 'engine_policy'.
POLICY_PORTFOLIO = [
    {"name": "deterministic_tier", "engine_policy": "deterministic_tier"},
    {"name": "cheapest_that_proves", "engine_policy": "cheapest_that_proves"},
    {"name": "argmax_receipts", "engine_policy": "argmax_receipts"},
    {"name": "epsilon_greedy", "engine_policy": "epsilon_greedy", "epsilon": 0.10},
    {"name": "argmax_contextual", "engine_policy": "argmax_receipts", "contextual": True},
]


def make_log(rounds: int, arms: list[str], means_fn, context_fn, seed: int) -> list[dict]:
    """Generate a full-feedback log. means_fn(t, context)->{arm: p} gives each
    arm's TRUE Bernoulli mean that round; context_fn(t, rng)->dict is the
    observable context. Every arm's outcome is drawn and recorded (full feedback),
    which is what makes counterfactual regret computable. Deterministic per seed."""
    rng = random.Random(seed)
    log = []
    for t in range(rounds):
        ctx = context_fn(t, rng)
        means = means_fn(t, ctx)
        outcomes = {a: (1.0 if rng.random() < means[a] else 0.0) for a in arms}
        log.append({"context": ctx, "true_means": means, "outcomes": outcomes})
    return log


def replay(policy: dict, base_decision: dict, paths: list[dict], log: list[dict],
           cost_observed: float = 10.0) -> dict:
    """Replay one policy over a log using the real engine. At round t the policy
    sees only receipts from rounds < t (no peeking); it pulls one arm; the log
    reveals that arm's outcome; regret accrues against the round's true best arm.
    Returns cumulative regret, reward, and the pull histogram."""
    did = base_decision["decision_id"]
    learn_keys = base_decision["learn_keys"]
    decision = dict(base_decision)
    decision["selection_policy"] = policy["engine_policy"]
    decision["epsilon"] = policy.get("epsilon", 0.0)
    # '+ t' nonce makes epsilon-greedy's deterministic-by-context exploration vary
    # round to round; the learnable signature (learn_keys only) drives learning.
    decision["context_signature"] = list(learn_keys) + ["_t"]
    decay = policy.get("decay", 0.9)

    receipts: list[dict] = []
    regret = reward = 0.0
    pulls: dict[str, int] = {}
    for t, rnd in enumerate(log):
        ctx = rnd["context"]
        ctx_full = dict(ctx)
        ctx_full["_t"] = t
        learn_sig = context_signature(did, ctx, learn_keys)
        if policy.get("contextual"):
            stats = LedgerStats.from_receipts(receipts, decay=decay, only_context=learn_sig)
        else:
            stats = LedgerStats.from_receipts(receipts, decay=decay)
        chosen = choose(decision, paths, ctx_full, stats)["chosen_path"]
        if chosen is None:
            continue
        pulls[chosen] = pulls.get(chosen, 0) + 1
        out = rnd["outcomes"][chosen]
        reward += out
        best = max(rnd["true_means"].values())
        regret += best - rnd["true_means"][chosen]
        receipts.append({
            "decision_id": did, "path_id": chosen, "context_signature": learn_sig,
            "sequence": t, "applicable": True, "chosen": True, "proved": out > 0,
            "win_score": out, "cost_observed": cost_observed,
            "candidate": True, "serves_truth": False})
    return {"policy": policy["name"], "rounds": len(log),
            "cumulative_regret": round(regret, 3), "total_reward": round(reward, 1),
            "mean_reward": round(reward / max(1, len(log)), 4), "pulls": pulls}


def evaluate(base_decision: dict, paths: list[dict], log: list[dict],
             policies: list[dict] | None = None) -> dict:
    """Replay every policy over the same log. Returns {policy_name: metrics}."""
    policies = policies or POLICY_PORTFOLIO
    return {p["name"]: replay(p, base_decision, paths, log) for p in policies}


def select_best(results: dict) -> str:
    """Pick the policy with the lowest cumulative regret (deterministic tie-break
    by name). This is the data choosing the control policy."""
    return min(results, key=lambda name: (results[name]["cumulative_regret"], name))
