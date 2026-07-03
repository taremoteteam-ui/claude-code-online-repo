"""Counterfactual risk minimization (CRM/POEM): LEARN a better policy from logged
bandit data, don't just evaluate a fixed one.

Off-policy evaluation (primitives/off_policy_estimators.py) tells you the value of
a policy you never deployed. CRM closes the loop: search a policy CLASS for the
policy that maximizes a VARIANCE-PENALIZED off-policy value estimate

    score(pi) = SNIPS(pi)  -  lambda * confidence_radius(pi)

The penalty is the whole point (Swaminathan & Joachims' POEM): a naive
value-maximizer (lambda = 0) will happily pick a policy whose apparent value rests
on a handful of huge importance weights - a lucky, poorly-covered arm - and then
generalize badly. Penalizing the estimate's own uncertainty steers CRM toward
policies the logs actually SUPPORT.

Policy class here: deterministic context -> action maps over a finite context and
action set, enumerated exhaustively (|A|^|X|, tiny for the intended use). The
objective and estimators are the real ones from the OPE lane, so this is the same
honesty regime: valid on logs with genuine, full-support propensities; the value
of the learned policy must still be checked out of sample. Deterministic; stdlib
only; candidate / serves_truth=false.
"""

from __future__ import annotations

import itertools

from primitives.off_policy_estimators import ips_value, snips_value
from primitives.ope_confidence import empirical_bernstein_radius, ips_per_sample


def _as_target(policy_map: dict):
    """Turn a deterministic {context: action} map into a TargetPolicy callable."""
    def target(context):
        return {policy_map[context]: 1.0}
    return target


def crm_score(logs: list[dict], policy_map: dict, lam: float, delta: float = 0.1) -> float:
    """Variance-penalized off-policy value of a deterministic policy: the SNIPS
    estimate minus lambda times an empirical-Bernstein confidence radius on the
    per-sample IPS terms. lambda = 0 recovers the naive value-maximizer."""
    target = _as_target(policy_map)
    value = snips_value(logs, target)
    if lam <= 0:
        return value
    penalty = empirical_bernstein_radius(ips_per_sample(logs, target), delta=delta)
    return value - lam * penalty


def learn_policy(logs: list[dict], contexts: list, actions: list, lam: float,
                 delta: float = 0.1) -> dict:
    """Search all deterministic context->action policies for the one maximizing the
    CRM objective. Returns the policy map, its score, and lambda. Deterministic:
    ties keep the first policy in itertools.product order."""
    best_map, best_score = None, float("-inf")
    for combo in itertools.product(actions, repeat=len(contexts)):
        pmap = dict(zip(contexts, combo))
        s = crm_score(logs, pmap, lam=lam, delta=delta)
        if s > best_score:
            best_map, best_score = pmap, s
    return {"policy": best_map, "score": round(best_score, 4), "lambda": lam,
            "candidate": True, "serves_truth": False}


def learn_naive_policy(logs: list[dict], contexts: list, actions: list) -> dict:
    """The unpenalized SNIPS value-maximizer (lambda = 0)."""
    return learn_policy(logs, contexts, actions, lam=0.0)


def learn_naive_ips_policy(logs: list[dict], contexts: list, actions: list) -> dict:
    """The textbook unregularized ERM baseline: maximize the raw IPS value estimate
    (no self-normalization, no penalty). Higher variance than CRM; included so the
    benchmark can compare against the variance-regularized objective honestly."""
    best_map, best_score = None, float("-inf")
    for combo in itertools.product(actions, repeat=len(contexts)):
        pmap = dict(zip(contexts, combo))
        s = ips_value(logs, _as_target(pmap))
        if s > best_score:
            best_map, best_score = pmap, s
    return {"policy": best_map, "score": round(best_score, 4), "lambda": 0.0,
            "estimator": "ips", "candidate": True, "serves_truth": False}
