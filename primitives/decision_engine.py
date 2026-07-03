"""Domain-agnostic decision engine: the universal "store all paths, let data
choose" substrate.

Nothing here is primitive-specific. A DecisionPoint owns a portfolio of
contract-substitutable ExecutionPaths; this module (1) filters paths by their
declarative applicability predicate over a context, (2) scores them by a
selection policy that fuses cost with accumulated, recency-decayed receipts, and
(3) returns a FULLY DISCLOSED ranking so every choice is auditable - never a
silent pick. Execution of a chosen path is the caller's job; the caller reports
a DecisionReceipt back to the ledger, which is the only memory the policy and
the supervisor learn from.

Determinism: ordering is by a monotonic receipt `sequence`, not wall-clock;
exploration (epsilon_greedy) is a deterministic function of the context hash, so
a run is reproducible. Stdlib only.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

# Cost normalization weights (lower normalized cost is better). Deterministic,
# documented, and the same for every domain - a path's domain lives in its
# numbers, not in the engine.
_RISK_RANK = {"none": 0.0, "low": 1.0, "medium": 2.0, "high": 4.0}
_W_TOKENS = 1.0 / 1000.0     # 1000 tokens ~= 1.0 cost unit
_W_LATENCY = 1.0 / 1000.0    # 1000 ms   ~= 1.0 cost unit
_W_RISK = 1.0
_COST_WEIGHT = 0.25          # how much cost pulls against receipt win-rate
_PRIOR_WIN = 0.5             # cold-start prior for a path with no receipts


def normalize_cost(cost_model: dict) -> float:
    return (_W_TOKENS * float(cost_model.get("tokens", 0))
            + _W_LATENCY * float(cost_model.get("latency_ms", 0))
            + _W_RISK * _RISK_RANK.get(cost_model.get("side_effect_risk", "none"), 0.0))


def context_signature(decision_id: str, context: dict, keys: list[str]) -> str:
    """Stable signature of the subset of context a decision keys on."""
    sub = {k: context.get(k) for k in sorted(keys)}
    blob = repr(sorted(sub.items()))
    return "ctx:" + hashlib.sha256((decision_id + "|" + blob).encode()).hexdigest()[:16]


def _cond_holds(cond: dict, context: dict) -> bool:
    key, op = cond["key"], cond["op"]
    present = key in context
    val = context.get(key)
    tgt = cond.get("value")
    if op == "exists":
        return present
    if op == "truthy":
        return bool(val)
    if op == "falsy":
        return not bool(val)
    if not present:
        return False
    if op == "eq":
        return val == tgt
    if op == "ne":
        return val != tgt
    if op == "in":
        return isinstance(tgt, list) and val in tgt
    try:
        if op == "gt":
            return val > tgt
        if op == "gte":
            return val >= tgt
        if op == "lt":
            return val < tgt
        if op == "lte":
            return val <= tgt
    except TypeError:
        return False
    return False


def is_applicable(path: dict, context: dict) -> bool:
    appl = path["applicability"]
    for k in appl.get("requires_keys", []):
        if k not in context:
            return False
    return all(_cond_holds(c, context) for c in appl.get("conditions", []))


@dataclass
class PathStats:
    count: int = 0
    wins: float = 0.0
    win_rate: float = 0.0
    decayed_win_rate: float = _PRIOR_WIN
    mean_cost: float = 0.0
    last_sequence: int = -1
    cold: bool = True


@dataclass
class LedgerStats:
    """Per (decision_id, path_id) aggregates with recency decay."""
    decay: float = 0.9
    by_path: dict = field(default_factory=dict)

    @classmethod
    def from_receipts(cls, receipts: list[dict], decay: float = 0.9,
                      only_context: str | None = None) -> "LedgerStats":
        """Aggregate receipts. Pass only_context to condition on a single
        context_signature (a CONTEXTUAL comparison - the fair way to compare
        paths whose applicability differs across contexts, and the seam for a
        contextual bandit)."""
        self = cls(decay=decay)
        grouped: dict[tuple, list[dict]] = {}
        for r in receipts:
            if not r.get("applicable", True):
                continue
            if only_context is not None and r.get("context_signature") != only_context:
                continue
            grouped.setdefault((r["decision_id"], r["path_id"]), []).append(r)
        for key, rs in grouped.items():
            rs = sorted(rs, key=lambda x: x["sequence"])
            max_seq = rs[-1]["sequence"]
            wnum = wden = 0.0
            cost_sum = 0.0
            wins = 0.0
            for r in rs:
                w = decay ** (max_seq - r["sequence"])
                wnum += w * float(r["win_score"])
                wden += w
                cost_sum += float(r["cost_observed"])
                wins += float(r["win_score"])
            self.by_path[key] = PathStats(
                count=len(rs), wins=wins, win_rate=wins / len(rs),
                decayed_win_rate=(wnum / wden) if wden else _PRIOR_WIN,
                mean_cost=cost_sum / len(rs), last_sequence=max_seq, cold=False)
        return self

    def get(self, decision_id: str, path_id: str) -> PathStats:
        return self.by_path.get((decision_id, path_id), PathStats())


def _explore_index(decision_id: str, context_sig: str, n: int, epsilon: float) -> int:
    """Deterministic pseudo-exploration: hash the context into [0,1); if it
    falls in the epsilon band, return an explore slot, else -1 (exploit)."""
    if n == 0 or epsilon <= 0:
        return -1
    h = int(hashlib.sha256((decision_id + "|" + context_sig).encode()).hexdigest(), 16)
    frac = (h % 10_000) / 10_000.0
    if frac < epsilon:
        return h % n
    return -1


def choose(decision: dict, paths: list[dict], context: dict,
           stats: LedgerStats | None = None) -> dict:
    """Return the chosen path plus a fully disclosed ranking.

    Never a silent pick: every applicable path's score, its cost, its
    (decayed) receipt win-rate, and the reason the winner won are returned.
    """
    stats = stats or LedgerStats()
    policy = decision["selection_policy"]
    did = decision["decision_id"]
    keys = decision["context_signature"]
    ctx_sig = context_signature(did, context, keys)

    ranked = []
    for p in paths:
        appl = is_applicable(p, context)
        st = stats.get(did, p["path_id"])
        ncost = normalize_cost(p["cost_model"])
        ranked.append({
            "path_id": p["path_id"], "applicable": appl,
            "preference_rank": p["preference_rank"], "norm_cost": round(ncost, 4),
            "count": st.count, "cold": st.cold,
            "win_rate": round(st.win_rate, 4),
            "decayed_win_rate": round(st.decayed_win_rate, 4),
        })
    applicable = [r for r in ranked if r["applicable"]]

    reason = ""
    chosen = None
    if not applicable:
        chosen = None
        reason = "no applicable path for this context"
    elif policy == "deterministic_tier":
        applicable.sort(key=lambda r: (r["preference_rank"], r["path_id"]))
        chosen = applicable[0]["path_id"]
        reason = "lowest-tier applicable path (receipts ignored by policy)"
    elif policy == "cheapest_that_proves":
        proven = [r for r in applicable if r["cold"] or r["win_rate"] > 0]
        pool = proven or applicable
        pool.sort(key=lambda r: (r["norm_cost"], r["preference_rank"], r["path_id"]))
        chosen = pool[0]["path_id"]
        reason = "cheapest applicable path that has not been disproven"
    else:  # argmax_receipts or epsilon_greedy
        def score(r):
            base = r["decayed_win_rate"] if not r["cold"] else _PRIOR_WIN
            # default-path prior bonus so cold ties resolve to the declared default
            if r["cold"] and r["path_id"] == decision["default_path"]:
                base += 1e-6
            return base - _COST_WEIGHT * r["norm_cost"]
        for r in applicable:
            r["score"] = round(score(r), 6)
        applicable.sort(key=lambda r: (-r["score"], r["preference_rank"], r["path_id"]))
        chosen = applicable[0]["path_id"]
        reason = "argmax(decayed_win_rate - cost) over applicable paths"
        if policy == "epsilon_greedy":
            eps = float(decision.get("epsilon", 0.0))
            slot = _explore_index(did, ctx_sig, len(applicable), eps)
            if slot >= 0:
                chosen = applicable[slot]["path_id"]
                reason = f"epsilon-greedy EXPLORE (eps={eps}) - deterministic by context hash"

    ranked.sort(key=lambda r: (not r["applicable"], r["preference_rank"], r["path_id"]))
    return {
        "decision_id": did, "context_signature": ctx_sig, "policy": policy,
        "chosen_path": chosen, "reason": reason,
        "n_applicable": len(applicable), "ranked": ranked,
    }
