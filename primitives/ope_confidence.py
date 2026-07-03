"""Trust the estimate: confidence intervals and an overlap diagnostic for
off-policy evaluation.

A point estimate of a policy's value is not enough to act on - IPS/DR can be
noisy or, worse, based on almost no effective data when the behavior policy
barely covered the target's actions. This module answers "and can I believe it?"
two ways:

- CONFIDENCE INTERVALS on the estimate:
  * bootstrap percentile CI over the per-sample estimator terms (well calibrated
    empirically), and
  * an empirical-Bernstein radius (distribution-free, uses the sample variance and
    range) as a conservative companion.
- an OVERLAP / EFFECTIVE-SAMPLE-SIZE diagnostic: the importance weights' ESS
  = (sum w)^2 / sum(w^2). When the behavior policy rarely took the target's
  actions, a few huge weights dominate, ESS collapses, and the estimate is not
  trustworthy no matter how tight the point value looks. The diagnostic flags this
  BEFORE you act on the number.

Every function is a pure, deterministic function of its inputs (the bootstrap
takes an explicit seed). Stdlib only; candidate material. Honesty: a CI is only as
valid as the propensities behind the estimate; this quantifies sampling
uncertainty, not model or logging error.
"""

from __future__ import annotations

import math
import random

from primitives.off_policy_estimators import TargetPolicy, RewardModel, _check_support


def importance_weights(logs: list[dict], target: TargetPolicy) -> list[float]:
    """The per-sample importance weights w_i = pi(a_i|x_i) / p_i."""
    ws = []
    for e in logs:
        _check_support(e["propensity"])
        ws.append(target(e["context"]).get(e["action"], 0.0) / e["propensity"])
    return ws


def ips_per_sample(logs: list[dict], target: TargetPolicy) -> list[float]:
    """Per-sample IPS terms; their mean is the IPS estimate."""
    return [w * e["reward"] for w, e in zip(importance_weights(logs, target), logs)]


def dr_per_sample(logs: list[dict], target: TargetPolicy, reward_model: RewardModel,
                  actions: list) -> list[float]:
    """Per-sample DR terms; their mean is the DR estimate."""
    out = []
    for e in logs:
        x, a = e["context"], e["action"]
        _check_support(e["propensity"])
        tp = target(x)
        baseline = sum(tp.get(aa, 0.0) * reward_model(x, aa) for aa in actions)
        w = tp.get(a, 0.0) / e["propensity"]
        out.append(baseline + w * (e["reward"] - reward_model(x, a)))
    return out


def effective_sample_size(weights: list[float]) -> dict:
    """ESS = (sum w)^2 / sum(w^2): the number of equally-weighted samples the log
    is 'worth' for importance weighting. Low ESS (relative to n, or in absolute
    terms) means a few samples carry all the weight - poor overlap, untrustworthy.
    """
    n = len(weights)
    s1 = sum(weights)
    s2 = sum(w * w for w in weights)
    ess = (s1 * s1 / s2) if s2 > 0 else 0.0
    return {"n": n, "ess": round(ess, 2), "ess_fraction": round(ess / n, 4) if n else 0.0,
            "max_weight": round(max(weights), 4) if weights else 0.0,
            "sum_weight": round(s1, 4)}


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def bootstrap_ci(values: list[float], alpha: float = 0.05, n_boot: int = 400,
                 seed: int = 0) -> dict:
    """Percentile bootstrap CI for the MEAN of `values` (the per-sample estimator
    terms). Deterministic given seed. Returns the point mean and [lo, hi] at the
    (1-alpha) level."""
    n = len(values)
    if n == 0:
        return {"mean": 0.0, "lo": 0.0, "hi": 0.0, "alpha": alpha, "n_boot": n_boot}
    rng = random.Random(f"boot:{seed}:{n}")
    means = []
    for _ in range(n_boot):
        resample = rng.choices(values, k=n)
        means.append(sum(resample) / n)
    means.sort()
    lo_idx = max(0, int((alpha / 2) * n_boot) - 1)
    hi_idx = min(n_boot - 1, int((1 - alpha / 2) * n_boot) - 1)
    return {"mean": round(_mean(values), 4), "lo": round(means[lo_idx], 4),
            "hi": round(means[hi_idx], 4), "alpha": alpha, "n_boot": n_boot}


def empirical_bernstein_radius(values: list[float], delta: float = 0.05,
                               value_range: float | None = None) -> float:
    """Two-sided empirical-Bernstein radius: with prob >= 1-delta the true mean is
    within this radius of the sample mean. Distribution-free; uses the sample
    variance and the range of `values`. Conservative vs the bootstrap. If
    value_range is None it is taken as max-min of the sample."""
    n = len(values)
    if n < 2:
        return float("inf")
    m = _mean(values)
    var = sum((v - m) ** 2 for v in values) / (n - 1)
    rng = value_range if value_range is not None else (max(values) - min(values))
    ln = math.log(2.0 / delta)
    return math.sqrt(2.0 * var * ln / n) + 3.0 * rng * ln / n


def dr_confidence(logs: list[dict], target: TargetPolicy, reward_model: RewardModel,
                  actions: list, alpha: float = 0.05, n_boot: int = 400,
                  seed: int = 0, min_ess: float = 200.0) -> dict:
    """Full trust report for a DR estimate: the point value, a bootstrap CI, an
    empirical-Bernstein radius, the overlap/ESS diagnostic, and a single
    `trustworthy` flag (enough effective samples AND a finite CI)."""
    terms = dr_per_sample(logs, target, reward_model, actions)
    ci = bootstrap_ci(terms, alpha=alpha, n_boot=n_boot, seed=seed)
    eb = empirical_bernstein_radius(terms, delta=alpha)
    overlap = effective_sample_size(importance_weights(logs, target))
    trustworthy = overlap["ess"] >= min_ess and math.isfinite(eb)
    return {
        "estimator": "DR", "value": ci["mean"], "ci_lo": ci["lo"], "ci_hi": ci["hi"],
        "ci_width": round(ci["hi"] - ci["lo"], 4),
        "empirical_bernstein_radius": round(eb, 4),
        "overlap": overlap, "min_ess": min_ess, "trustworthy": trustworthy,
        "candidate": True, "serves_truth": False,
    }
