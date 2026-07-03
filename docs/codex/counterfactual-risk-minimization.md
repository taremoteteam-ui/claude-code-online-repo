# Counterfactual risk minimization — learn a better policy from logs

**Closing the flywheel.** Off-policy *evaluation* (`off-policy-evaluation.md`) tells
you the value of a policy you never deployed. CRM/POEM goes one step further:
*learn* the policy — search a policy class for the one that maximizes a
variance-penalized off-policy value estimate from the logs alone.

## The objective

Over a deterministic `context -> action` policy class (enumerated exhaustively —
`|A|^|X|`, tiny for the intended use):

```
score(pi) = SNIPS(pi)  -  lambda * empirical_bernstein_radius(IPS_terms(pi))
```

`primitives/policy_learning.py`: `learn_policy(logs, contexts, actions, lam)`
returns the argmax; `learn_naive_policy` (lambda=0, SNIPS) and
`learn_naive_ips_policy` (raw IPS) are the unregularized baselines. It reuses the
real OPE estimators and the confidence radius from the trust layer, so it stays in
the same honesty regime: valid with genuine full-support propensities; the learned
policy's value must still be checked out of sample.

## What the benchmark measures (synthetic, seeded, replayable)

`scripts/run_policy_learning_benchmark.py` — 2 contexts, 3 actions, known `q`, and
a behavior policy with poor overlap on the good actions. It learns a policy from
partial-feedback logs and scores each learned policy's TRUE value.

**Gated (robustly true):**
- **CRM learns a policy far better than the behavior policy** that produced the
  logs — mean true value ≈ **0.775 (optimal) up from 0.4975 (behavior)**, a +0.28
  jump purely from off-policy learning.
- The naive learner also beats behavior — off-policy *learning* works; the penalty
  is a separate knob.
- With a large log CRM's value converges to the optimal policy's (consistency).

**Reported, NOT gated — an honest negative finding:** in this regime the variance
penalty did **not** reliably raise mean true value (`penalty_effect_on_mean ≈ 0`).
With SNIPS already self-normalizing and the good actions only mildly under-covered,
the extra empirical-Bernstein penalty mostly adds conservatism. `lambda` was
**not** tuned until a win appeared — that would be exactly the curated claim this
repo forbids. The penalty earns its keep when the logs *poorly* cover the good
actions (a low-support arm that gets lucky and fools raw IPS); that is a bias/
variance knob, disclosed rather than oversold.

This negative result is a feature, not a bug: it demonstrates the discipline —
measure what actually happens, report it, and refuse to dress a knob up as a
breakthrough.

## Honesty boundary

Synthetic so the learned policy's true value is knowable and used only to score
(never shown to the learner). Valid only with genuine full-support propensities.
Seeded → deterministic; zero model calls. A penalty-sign mutation is in the
mutation set (flipping the penalty to a bonus must fail the
penalty-never-increases-score test). candidate / serves_truth=false.

## Command

```bash
python3 scripts/run_policy_learning_benchmark.py --self-test
python3 -m unittest tests.test_policy_learning -v
```
