#!/usr/bin/env python3
"""Checker for benchmark run artifacts under benchmarks/runs/<run_id>/.

Enforces:
  - scorecards and receipts validate against their JSON schemas
  - manifest row counts and content hashes match files on disk
  - every receipt referenced by a scorecard exists in receipts.jsonl
  - arm A4 scorecards report runtime_llm_tokens == 0 (deterministic replay
    honesty: no model ran, so no tokens may be reported)
  - execution receipts declare fixture_offline or pure_local mode unless a
    live run is explicitly marked
  - scorecard notes disclose fixture mode and unrun baseline arms

Usage:
    python3 scripts/check_benchmark_run.py --self-test          (latest run)
    python3 scripts/check_benchmark_run.py --run-dir benchmarks/runs/<id>
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_ROOT = REPO_ROOT / "benchmarks" / "runs"
SCHEMA_DIR = REPO_ROOT / "schemas"
sys.path.insert(0, str(REPO_ROOT))


def load_validator_class():
    spec = importlib.util.spec_from_file_location(
        "pack_checker", REPO_ROOT / "scripts" / "check_place_discovery_geospatial_pack.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.StructuralValidator


def load_jsonl(path: Path) -> list:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_checks(run_dir: Path) -> dict:
    problems: list[str] = []
    StructuralValidator = load_validator_class()

    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        return {"ok": False, "problems": [f"missing {manifest_path}"], "run_dir": str(run_dir)}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    for name, meta in manifest.get("files", {}).items():
        fpath = run_dir / name
        if not fpath.exists():
            problems.append(f"manifest lists {name} but file missing")
            continue
        content = fpath.read_text(encoding="utf-8")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if digest != meta["content_sha256"]:
            problems.append(f"{name}: content hash mismatch - run artifacts were edited after the run")
        if name.endswith(".jsonl") and content.count("\n") != meta["rows"]:
            problems.append(f"{name}: row count mismatch vs manifest")

    receipt_validator = StructuralValidator(
        json.loads((SCHEMA_DIR / "execution_receipt.schema.json").read_text(encoding="utf-8")))
    scorecard_validator = StructuralValidator(
        json.loads((SCHEMA_DIR / "benchmark_scorecard.schema.json").read_text(encoding="utf-8")))

    receipts = load_jsonl(run_dir / "receipts.jsonl") if (run_dir / "receipts.jsonl").exists() else []
    scorecards = load_jsonl(run_dir / "scorecards.jsonl") if (run_dir / "scorecards.jsonl").exists() else []

    receipt_ids = set()
    for i, r in enumerate(receipts):
        for e in receipt_validator.validate(r)[:3]:
            problems.append(f"receipts[{i}]: {e}")
        receipt_ids.add(r["receipt_id"])
        if r["execution_mode"] == "live_network":
            pass  # allowed, but disclosed by mode field itself
        if r.get("candidate") is not True or r.get("serves_truth") is not False:
            problems.append(f"receipts[{i}]: candidate/serves_truth boundary violated")

    # PlanLocks: schema-valid, recomputable route hashes, referenced by
    # scorecards. Locks are optional for runs persisted before the PlanLock
    # layer existed; scorecards carrying plan_lock_id make them mandatory.
    locks: dict[str, dict] = {}
    locks_path = run_dir / "plan_locks.jsonl"
    if locks_path.exists():
        from primitives.core import canonical_hash
        lock_validator = StructuralValidator(
            json.loads((SCHEMA_DIR / "plan_lock.schema.json").read_text(encoding="utf-8")))
        for i, lock in enumerate(load_jsonl(locks_path)):
            for e in lock_validator.validate(lock)[:3]:
                problems.append(f"plan_locks[{i}]: {e}")
            recomputed = canonical_hash(lock["route"])
            if lock["route_hash"] != recomputed:
                problems.append(
                    f"plan_locks[{i}]: route_hash does not recompute - lock was edited")
            locks[lock["lock_id"]] = lock

    negmem_path = run_dir / "negative_memory.jsonl"
    if negmem_path.exists():
        negmem_validator = StructuralValidator(
            json.loads((SCHEMA_DIR / "negative_memory.schema.json").read_text(encoding="utf-8")))
        for i, mem in enumerate(load_jsonl(negmem_path)):
            for e in negmem_validator.validate(mem)[:3]:
                problems.append(f"negative_memory[{i}]: {e}")

    for i, s in enumerate(scorecards):
        for e in scorecard_validator.validate(s)[:3]:
            problems.append(f"scorecards[{i}]: {e}")
        if s["arm_id"] == "A4" and s["runtime_llm_tokens"] != 0:
            problems.append(
                f"scorecards[{i}]: arm A4 is deterministic replay but reports "
                f"runtime_llm_tokens={s['runtime_llm_tokens']}")
        for rid in s["receipt_ids"]:
            if rid not in receipt_ids:
                problems.append(f"scorecards[{i}]: references unknown receipt {rid}")
        if "plan_lock_id" in s:
            lock = locks.get(s["plan_lock_id"])
            if lock is None:
                problems.append(f"scorecards[{i}]: unknown plan lock {s['plan_lock_id']}")
            elif s.get("route_hash") != lock["route_hash"]:
                problems.append(f"scorecards[{i}]: route_hash does not match its plan lock")
            if s["arm_id"] == "A4" and s["task_success"] and not s.get("replay_verified"):
                problems.append(
                    f"scorecards[{i}]: successful A4 task without verified replay - "
                    "deterministic replay arm requires replay proof")
        notes = s.get("notes", "")
        if s["execution_mode"] == "fixture_offline" and "fixture" not in notes.lower():
            problems.append(f"scorecards[{i}]: fixture mode not disclosed in notes")
        if "A1" not in notes and "not run" not in notes:
            problems.append(f"scorecards[{i}]: unrun baseline arms not disclosed in notes")

    counts = {
        "scorecards": len(scorecards),
        "receipts": len(receipts),
        "tasks_succeeded": sum(1 for s in scorecards if s["task_success"]),
        "proofs_total": sum(len(r["proof_results"]) for r in receipts),
        "proofs_passed": sum(1 for r in receipts for p in r["proof_results"] if p["passed"]),
    }
    return {"ok": not problems, "problems": problems[:60], "counts": counts,
            "run_dir": str(run_dir.relative_to(REPO_ROOT))}


def latest_run_dir() -> Path | None:
    if not RUNS_ROOT.exists():
        return None
    runs = sorted(p for p in RUNS_ROOT.iterdir() if p.is_dir())
    return runs[-1] if runs else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=str, help="specific run directory to check")
    parser.add_argument("--self-test", action="store_true", help="check the latest run")
    args = parser.parse_args()
    if args.run_dir:
        run_dir = REPO_ROOT / args.run_dir if not Path(args.run_dir).is_absolute() else Path(args.run_dir)
    elif args.self_test:
        run_dir = latest_run_dir()
        if run_dir is None:
            print(json.dumps({"ok": False, "problems": ["no benchmark runs found"]}))
            return 1
    else:
        parser.print_help()
        return 2
    result = run_checks(run_dir)
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
