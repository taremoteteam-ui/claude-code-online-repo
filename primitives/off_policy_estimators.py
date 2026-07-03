"""Off-policy estimators: evaluate a policy you never deployed from PARTIAL-
FEEDBACK logs of a different (behavior) policy.

This closes the honesty gap flagged in policy_evaluation.py. There, counterfactual
regret was valid only because the log was FULL feedback (every arm's outcome
recorded). Real production logs are partial: you observe the reward of the ONE
action the logging policy took, nothing about the others. To evaluate a target
policy from such logs you need importance weighting by the logging propensity.

Contextual-bandit setting. A logged sample is (context x, action a, reward r,
propensity p) where a was drawn by the behavior policy mu with p = mu(a|x) > 0
(full support is required), and r is observed for a only. A target policy pi maps
a context to an action distribution pi(.|x). We want its value
V(pi) = E_x E_{a~pi(.|x)} E[r | x, a].

Four estimators, in increasing sophistication:

- IPS (inverse propensity scoring): unbiased if mu has full support, but high
  variance when pi and mu disagree (weights pi/p blow up).
- SNIPS (self-normalized IPS): divide by the summed weights instead of N. Lower
  variance, consistent, slightly biased. Bounded to the reward range.
- DM (direct method): fit a reward model rhat(x,a) and average pi over it. Low
  variance, but biased by model error.
- DR (doubly robust): DM baseline plus an IPS-weighted correction of the model's
  residual. UNBIASED IF EITHER the propensities OR the reward model is correct -
  and lower variance than IPS when the model is any good. This is the headline:
  robustness to reward-model misspecification, proven by measurement.

Every estimator is a pure deterministic function of its inputs; the honesty of
the ESTIMATE depends on the propensities being real (logged at decision time),
never reconstructed after the fact. Stdlib only; candidate material.
"""

from __future__ import annotations

from typing import Callable

# A target policy: context -> {action: probability} (probabilities sum to ~1).
TargetPolicy = Callable[[object], dict]
# A reward model: (context, action) -> predicted reward.
RewardModel = Callable[[object, object], float]


def _check_support(propensity: float) -> None:
    if propensity <= 0.0:
        raise ValueError("logged propensity must be > 0 (behavior policy needs full "
                         "support over any action the target can take)")


def ips_value(logs: list[dict], target: TargetPolicy) -> float:
    """Inverse-propensity estimate of V(target). Unbiased under full support."""
    if not logs:
        return 0.0
    total = 0.0
    for e in logs:
        _check_support(e["propensity"])
        w = target(e["context"]).get(e["action"], 0.0) / e["propensity"]
        total += w * e["reward"]
    return total / len(logs)


def snips_value(logs: list[dict], target: TargetPolicy) -> float:
    """Self-normalized IPS: divide by summed weights. Lower variance, consistent."""
    if not logs:
        return 0.0
    num = den = 0.0
    for e in logs:
        _check_support(e["propensity"])
        w = target(e["context"]).get(e["action"], 0.0) / e["propensity"]
        num += w * e["reward"]
        den += w
    return num / den if den else 0.0


def dm_value(logs: list[dict], target: TargetPolicy, reward_model: RewardModel,
             actions: list) -> float:
    """Direct-method estimate: average the model's pi-weighted reward over the
    logged contexts. Ignores the logged actions/rewards entirely - so it is only
    as good as the reward model."""
    if not logs:
        return 0.0
    total = 0.0
    for e in logs:
        tp = target(e["context"])
        total += sum(tp.get(a, 0.0) * reward_model(e["context"], a) for a in actions)
    return total / len(logs)


def dr_value(logs: list[dict], target: TargetPolicy, reward_model: RewardModel,
             actions: list) -> float:
    """Doubly-robust estimate: DM baseline + IPS-weighted correction of the
    model residual on the logged action. Unbiased if EITHER the propensities or
    the reward model is right."""
    if not logs:
        return 0.0
    total = 0.0
    for e in logs:
        x, a = e["context"], e["action"]
        _check_support(e["propensity"])
        tp = target(x)
        baseline = sum(tp.get(aa, 0.0) * reward_model(x, aa) for aa in actions)
        w = tp.get(a, 0.0) / e["propensity"]
        total += baseline + w * (e["reward"] - reward_model(x, a))
    return total / len(logs)


def fit_reward_model(logs: list[dict], actions: list, fallback: float = 0.5) -> RewardModel:
    """Fit the direct-method reward model: the empirical mean logged reward per
    (context, action). Unseen (context, action) pairs fall back to a constant.
    Deterministic. Fit this on a log INDEPENDENT of the one you evaluate on (the
    benchmark uses a separate pilot log) so DR's correction stays honest."""
    sums: dict = {}
    counts: dict = {}
    for e in logs:
        key = (e["context"], e["action"])
        sums[key] = sums.get(key, 0.0) + e["reward"]
        counts[key] = counts.get(key, 0) + 1

    def model(context, action) -> float:
        key = (context, action)
        c = counts.get(key, 0)
        return sums[key] / c if c else fallback

    return model


def true_value(context_weights: dict, q: dict, target: TargetPolicy,
               actions: list) -> float:
    """Exact V(target) from a KNOWN environment (only possible in simulation):
    sum over contexts (weighted) of the target-weighted true reward means q[x][a].
    This is the oracle the estimators are checked against."""
    total_w = sum(context_weights.values())
    v = 0.0
    for x, wx in context_weights.items():
        tp = target(x)
        vx = sum(tp.get(a, 0.0) * q[x][a] for a in actions)
        v += (wx / total_w) * vx
    return v
