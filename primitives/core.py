"""Execution core for place-discovery primitives.

Every primitive implementation runs through :func:`run_primitive`, which
computes input/output hashes, times the execution, collects proof results,
and emits an ExecutionReceipt conforming to
``schemas/execution_receipt.schema.json``.

Receipts are measured artifacts: every field is computed at runtime.
All receipts carry ``candidate=True, serves_truth=False`` - executing a
primitive never promotes it.

Stdlib only. No third-party dependencies.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


def canonical_hash(obj: Any) -> str:
    """Deterministic sha256 over a JSON-serializable object."""
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@dataclass
class ProofResult:
    proof: str
    passed: bool
    detail: str = ""

    def to_dict(self) -> dict:
        d = {"proof": self.proof, "passed": self.passed}
        if self.detail:
            d["detail"] = self.detail
        return d


@dataclass
class ArtifactRef:
    artifact_type: str
    content_sha256: str
    path: str = ""

    def to_dict(self) -> dict:
        d = {"artifact_type": self.artifact_type, "content_sha256": self.content_sha256}
        if self.path:
            d["path"] = self.path
        return d


@dataclass
class PrimitiveOutcome:
    """What a primitive implementation returns to the runner.

    ``output`` is the visible output edge payload (JSON-serializable).
    ``proof_results`` are the proofs the primitive ran on its own output.
    ``effects_observed`` must honestly report what actually happened.
    """

    output: Any
    effects_observed: list[str] = field(default_factory=list)
    proof_results: list[ProofResult] = field(default_factory=list)
    source_snapshot_ids: list[str] = field(default_factory=list)
    artifacts: list[ArtifactRef] = field(default_factory=list)


class PrimitiveExecutionError(Exception):
    """Raised when a primitive fails; carries the receipt for the failure."""

    def __init__(self, message: str, receipt: dict):
        super().__init__(message)
        self.receipt = receipt


def run_primitive(
    primitive_id: str,
    fn: Callable[[Any], PrimitiveOutcome],
    payload: Any,
    run_id: str,
    declared_effects: list[str],
    execution_mode: str = "pure_local",
    runtime_target: str = "local.python",
) -> tuple[Any, dict]:
    """Execute ``fn(payload)`` and emit an ExecutionReceipt.

    Returns ``(outcome.output, receipt_dict)``. On failure raises
    :class:`PrimitiveExecutionError` whose ``receipt`` attribute records the
    error - failures produce receipts too.
    """
    input_hash = canonical_hash(payload)
    started_at = utc_now_iso()
    t0 = time.perf_counter()
    error: str | None = None
    outcome: PrimitiveOutcome | None = None
    try:
        outcome = fn(payload)
        if not isinstance(outcome, PrimitiveOutcome):
            raise TypeError(f"{primitive_id}: implementation must return PrimitiveOutcome")
    except Exception as exc:  # noqa: BLE001 - receipts must record any failure
        error = f"{type(exc).__name__}: {exc}"
    wall_clock_ms = (time.perf_counter() - t0) * 1000.0

    output = outcome.output if outcome else None
    receipt = {
        "record_type": "place_discovery_execution_receipt",
        "receipt_id": "rcpt:" + hashlib.sha256(
            f"{primitive_id}|{run_id}|{input_hash}|{started_at}".encode("utf-8")
        ).hexdigest()[:16],
        "primitive_id": primitive_id,
        "run_id": run_id,
        "input_hash": input_hash,
        "output_hash": canonical_hash(output) if output is not None else None,
        "runtime_target": runtime_target,
        "execution_mode": execution_mode,
        "effects_declared": list(declared_effects),
        "effects_observed": list(outcome.effects_observed) if outcome else [],
        "proof_results": [p.to_dict() for p in outcome.proof_results] if outcome else [],
        "source_snapshot_ids": list(outcome.source_snapshot_ids) if outcome else [],
        "artifacts": [a.to_dict() for a in outcome.artifacts] if outcome else [],
        "started_at_utc": started_at,
        "wall_clock_ms": round(wall_clock_ms, 3),
        "error": error,
        "candidate": True,
        "serves_truth": False,
    }
    if error is not None:
        raise PrimitiveExecutionError(f"{primitive_id} failed: {error}", receipt)
    failed_proofs = [p for p in (outcome.proof_results if outcome else []) if not p.passed]
    if failed_proofs:
        receipt["error"] = "proof_failure: " + ", ".join(p.proof for p in failed_proofs)
        raise PrimitiveExecutionError(f"{primitive_id} proof failure", receipt)
    return output, receipt
