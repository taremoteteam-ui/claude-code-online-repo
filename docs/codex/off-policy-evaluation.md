# Off-policy evaluation — evaluate a policy you never deployed

**The gap this closes.** `policy-selection-off-policy.md` could only compare
policies on a **full-feedback** log (every arm's outcome recorded), which real
production logs never have. This lane evaluates a target policy from
**partial-feedback** logs of a *different* behavior policy — the setting you
actually face when you want to know "would policy B have done better than the
policy A we were running?" without deploying B.

## The method

Contextual bandit. A logged sample is `(context x, action a, reward r,
propensity p)` where the behavior policy `mu` drew `a` with `p = mu(a|x) > 0`
(full support required) and `r` was observed **for `a` only**. We estimate the
value of a target policy `pi` four ways:

| Estimator | Idea | Bias | Variance |
|-----------|------|------|----------|
| **IPS** | importance-weight rewards by `pi/p` | unbiased (full support) | high when `pi`≠`mu` |
| **SNIPS** | IPS normalized by summed weights | slight | lower than IPS |
| **DM** | fit `rhat(x,a)`, average `pi` over it | biased by model error | low |
| **DR** | DM baseline + IPS-weighted residual correction | **unbiased if EITHER propensities OR model is right** | ≤ IPS when model is any good |

`primitives/off_policy_estimators.py` implements all four plus `fit_reward_model`
(empirical per-`(x,a)` mean) and `true_value` (the oracle, computable only in
simulation). Every estimator is a pure deterministic function; the honesty of the
estimate rests on the propensities being **logged at decision time**, never
reconstructed after the fact.

## What the benchmark measures (fully synthetic, seeded, replayable)

`scripts/run_off_policy_evaluation_benchmark.py` — known env (`q` fixed), uniform
behavior policy, greedy target (never deployed), Bernoulli rewards, 20 independent
evaluation logs. The DM/DR reward model is fit on an **independent pilot log** so
DR's correction stays honest. True value `V(pi) = 0.75`. Measured:

- **IPS is ~unbiased** — mean estimate ≈ 0.75 (bias < 0.001).
- **DR is robust to a misspecified reward model** — with a deliberately wrong
  model (constant 0.5), **DM is off by 0.25** but **DR recovers to bias ≈ 0.001**.
  That is the doubly-robust property, measured rather than asserted, and it is the
  reason to prefer DR in practice: your reward model *will* be wrong.
- **DR variance ≤ IPS variance** — the control-variate payoff (≈0.011 vs ≈0.018).

## Honesty boundary

- Fully synthetic so the estimators can be checked against the **known** true
  value; this measures the estimators' statistics, not any real-world value.
- Requires **full support** (`mu(a|x) > 0` wherever `pi` puts mass); the code
  raises on a zero propensity rather than silently dividing.
- On real logs the propensities must be genuine (logged when the action was
  chosen). Reconstructing them after the fact would void the guarantee — flagged,
  never faked. Every record is `candidate: true, serves_truth: false`. The DR
  robustness result is protected by the quality ratchet.

## Why it matters to the atlas

This is the estimator the self-improvement flywheel needs to run on **real
telemetry**: it lets the decision engine ask "what would switching to policy B
have earned?" from the logs it already has, with a bias/variance profile that
survives an imperfect reward model. It is the honest bridge from the synthetic
policy-selection benchmark to a production self-tuning loop.

## Commands

```bash
python3 scripts/run_off_policy_evaluation_benchmark.py --self-test   # measured
python3 scripts/run_off_policy_evaluation_benchmark.py --write       # persist
python3 -m unittest tests.test_off_policy_estimators -v              # exact math
```
