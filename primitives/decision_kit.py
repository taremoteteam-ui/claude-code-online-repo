"""Drop-in decision kit: instrument any codebase's decision in ~3 lines.

The engine/planner are pure functions over (portfolio, context, ledger). This
facade wires them to a codebase with the least ceremony: register a decision +
its paths (in code or from the pack), point at a pluggable ledger sink, and call
`decide()` at the call site. No engineering decision about selection, ordering,
or combination is left to the caller - the kit derives it from data.

    kit = DecisionKit(ledger=JsonlLedger("ledger.jsonl"))
    kit.register(decision_dict, paths_list)                  # or kit.load_pack()
    choice = kit.decide("decision:retry.policy", {"idempotent": True})
    result = run(choice["chosen_path"])                      # your code
    kit.record("decision:retry.policy", choice["chosen_path"], ctx, win=1.0, cost=12)

The ledger sink is the storage seam (in-memory / JSONL / any callable), so the
same kit runs on files today and a database tomorrow without touching call
sites. Stdlib only.
"""

from __future__ import annotations

import json
from pathlib import Path

from primitives.decision_engine import LedgerStats, choose, context_signature
from primitives.decision_planner import optimal_gate_order, plan_combination

REPO_ROOT = Path(__file__).resolve().parent.parent
PACK_DIR = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "decision-portfolios"


class InMemoryLedger:
    def __init__(self):
        self.rows: list[dict] = []
        self._seq = 0

    def append(self, row: dict) -> None:
        row.setdefault("sequence", self._seq)
        self._seq = max(self._seq, row["sequence"]) + 1
        self.rows.append(row)

    def all(self) -> list[dict]:
        return list(self.rows)


class JsonlLedger:
    """Append-only file ledger - durable, still just an event log."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._seq = 0
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self._seq = max(self._seq, json.loads(line).get("sequence", 0) + 1)

    def append(self, row: dict) -> None:
        row.setdefault("sequence", self._seq)
        self._seq = max(self._seq, row["sequence"]) + 1
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")

    def all(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(x) for x in self.path.read_text(encoding="utf-8").splitlines() if x.strip()]


class DecisionKit:
    def __init__(self, ledger=None, decay: float = 0.9):
        self.ledger = ledger if ledger is not None else InMemoryLedger()
        self.decay = decay
        self.decisions: dict[str, dict] = {}
        self.paths: dict[str, list[dict]] = {}

    # --- registration -------------------------------------------------------
    def register(self, decision: dict, paths: list[dict]) -> "DecisionKit":
        self.decisions[decision["decision_id"]] = decision
        self.paths[decision["decision_id"]] = list(paths)
        return self

    def load_pack(self, pack_dir: Path | None = None) -> "DecisionKit":
        pack_dir = pack_dir or PACK_DIR
        for d in (json.loads(l) for l in (pack_dir / "decision_points.jsonl").read_text().splitlines() if l.strip()):
            self.decisions[d["decision_id"]] = d
            self.paths.setdefault(d["decision_id"], [])
        for p in (json.loads(l) for l in (pack_dir / "execution_paths.jsonl").read_text().splitlines() if l.strip()):
            self.paths.setdefault(p["decision_id"], []).append(p)
        return self

    # --- selection ----------------------------------------------------------
    def _stats(self, only_context: str | None = None) -> LedgerStats:
        return LedgerStats.from_receipts(self.ledger.all(), decay=self.decay, only_context=only_context)

    def decide(self, decision_id: str, context: dict, contextual: bool = True) -> dict:
        d = self.decisions[decision_id]
        sig = context_signature(decision_id, context, d["context_signature"]) if contextual else None
        return choose(d, self.paths[decision_id], context, self._stats(only_context=sig))

    def record(self, decision_id: str, path_id: str, context: dict, win: float,
               cost: float, proved: bool | None = None) -> None:
        d = self.decisions[decision_id]
        self.ledger.append({
            "record_type": "decision_receipt", "decision_id": decision_id, "path_id": path_id,
            "context_signature": context_signature(decision_id, context, d["context_signature"]),
            "applicable": True, "chosen": True,
            "proved": bool(win > 0) if proved is None else proved,
            "win_score": float(win), "cost_observed": float(cost),
            "candidate": True, "serves_truth": False,
        })

    # --- planning (combination + gate order) --------------------------------
    def plan(self, decision_ids: list[str], context: dict, min_reliability: float = 0.0,
             budget: float | None = None, compatible=None) -> dict:
        decisions = [self.decisions[i] for i in decision_ids]
        return plan_combination(decisions, self.paths, context, self._stats(),
                                min_reliability=min_reliability, budget=budget, compatible=compatible)

    def order_gates(self, gates: list[dict], decision_id: str = "gates") -> dict:
        return optimal_gate_order(gates, self._stats(), decision_id=decision_id)
