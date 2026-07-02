#!/usr/bin/env python3
"""Co-occurrence miner over measured benchmark runs.

Reads every benchmarks/runs/*/scorecards.jsonl and, for each scorecard,
treats the deduplicated primitives_executed set as one observed task
execution. For every unordered pair of primitives that appear in the same
execution it emits a primitive_cooccurrence_edge row with:

  - used_together_count: executions containing both primitives
  - a_task_count / b_task_count: executions containing each primitive
  - jaccard: used_together / (a_task_count + b_task_count - used_together)
  - source_run_ids: run ids in which the pair co-occurred

Edges are mined from measured scorecards only; they describe what actually
ran together in fixture-mode replays, not real-world affinity. Every row is
candidate=true, serves_truth=false. Counts and hashes in manifest.json are
computed, never typed.

Usage:
    python3 scripts/build_cooccurrence_edges.py --self-test
    python3 scripts/build_cooccurrence_edges.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_ROOT = REPO_ROOT / "benchmarks" / "runs"
OUT_DIR = REPO_ROOT / "benchmarks" / "cooccurrence"

GENERATED_BY = "scripts/build_cooccurrence_edges.py"
RECORD_TYPE = "primitive_cooccurrence_edge"
JACCARD_DECIMALS = 4


def edge_id_for_pair(a: str, b: str) -> str:
    """Stable edge id: sha256 over the sorted pair, first 16 hex chars."""
    lo, hi = sorted((a, b))
    digest = hashlib.sha256(f"{lo}|{hi}".encode("utf-8")).hexdigest()
    return f"cooc:{digest[:16]}"


def load_observations(runs_root: Path) -> list[dict]:
    """One observation per scorecard: run id + deduplicated primitive set.

    Run directories and scorecard rows are read in sorted, stable order so
    two builds over the same inputs are byte-identical.
    """
    observations: list[dict] = []
    if not runs_root.exists():
        return observations
    for run_dir in sorted(p for p in runs_root.iterdir() if p.is_dir()):
        scorecards_path = run_dir / "scorecards.jsonl"
        if not scorecards_path.exists():
            continue
        for line in scorecards_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            primitives = sorted(set(row.get("primitives_executed", [])))
            observations.append({
                "run_id": row.get("run_id", run_dir.name),
                "task_id": row.get("task_id", ""),
                "primitives": primitives,
            })
    return observations


def build_edges(observations: list[dict]) -> list[dict]:
    task_counts: dict[str, int] = {}
    pair_counts: dict[tuple[str, str], int] = {}
    pair_runs: dict[tuple[str, str], set] = {}

    for obs in observations:
        primitives = obs["primitives"]
        for pid in primitives:
            task_counts[pid] = task_counts.get(pid, 0) + 1
        for i, a in enumerate(primitives):
            for b in primitives[i + 1:]:
                pair = (a, b)  # primitives list is sorted, so a < b
                pair_counts[pair] = pair_counts.get(pair, 0) + 1
                pair_runs.setdefault(pair, set()).add(obs["run_id"])

    edges: list[dict] = []
    for (a, b), together in pair_counts.items():
        union = task_counts[a] + task_counts[b] - together
        edges.append({
            "record_type": RECORD_TYPE,
            "edge_id": edge_id_for_pair(a, b),
            "a": a,
            "b": b,
            "used_together_count": together,
            "a_task_count": task_counts[a],
            "b_task_count": task_counts[b],
            "jaccard": round(together / union, JACCARD_DECIMALS),
            "source_run_ids": sorted(pair_runs[(a, b)]),
            "candidate": True,
            "serves_truth": False,
        })
    edges.sort(key=lambda e: (-e["used_together_count"], e["edge_id"]))
    return edges


def jsonl_bytes(rows: list[dict]) -> bytes:
    return "".join(json.dumps(r, ensure_ascii=True, sort_keys=False) + "\n" for r in rows).encode("utf-8")


def build_payloads(runs_root: Path) -> dict[str, bytes]:
    observations = load_observations(runs_root)
    edges = build_edges(observations)
    payloads = {"edges.jsonl": jsonl_bytes(edges)}

    manifest = {
        "dataset_id": "place-discovery-cooccurrence-edges",
        "generated_by": GENERATED_BY,
        "source_run_ids": sorted({obs["run_id"] for obs in observations}),
        "files": {
            "edges.jsonl": {
                "rows": len(edges),
                "content_sha256": hashlib.sha256(payloads["edges.jsonl"]).hexdigest(),
            },
        },
        "row_counts": {"edges.jsonl": len(edges)},
        "total_rows": len(edges),
        "candidate": True,
        "serves_truth": False,
    }
    payloads["manifest.json"] = (json.dumps(manifest, indent=2, sort_keys=False) + "\n").encode("utf-8")
    return payloads


def verify_edges(edges: list[dict], observations: list[dict]) -> list[str]:
    """Invariant checks shared by --self-test and unit tests."""
    problems: list[str] = []
    seen_primitives = {pid for obs in observations for pid in obs["primitives"]}
    seen_runs = {obs["run_id"] for obs in observations}

    for i, e in enumerate(edges):
        label = f"edges[{i}] ({e.get('edge_id')})"
        for endpoint in (e["a"], e["b"]):
            if endpoint not in seen_primitives:
                problems.append(f"{label}: references primitive {endpoint} absent from scorecards")
        if e["a"] >= e["b"]:
            problems.append(f"{label}: endpoints not in sorted order")
        if e["edge_id"] != edge_id_for_pair(e["a"], e["b"]):
            problems.append(f"{label}: edge_id does not match sha256 of sorted pair")
        if not (0 < e["jaccard"] <= 1):
            problems.append(f"{label}: jaccard {e['jaccard']} outside (0, 1]")
        if e["used_together_count"] < 1:
            problems.append(f"{label}: used_together_count below 1")
        if e["used_together_count"] > min(e["a_task_count"], e["b_task_count"]):
            problems.append(f"{label}: used_together_count exceeds min of endpoint task counts")
        if not e["source_run_ids"]:
            problems.append(f"{label}: no source_run_ids")
        for rid in e["source_run_ids"]:
            if rid not in seen_runs:
                problems.append(f"{label}: references unknown run {rid}")
        if e.get("candidate") is not True or e.get("serves_truth") is not False:
            problems.append(f"{label}: candidate/serves_truth boundary violated")
    return problems


def self_test() -> int:
    observations = load_observations(RUNS_ROOT)
    problems: list[str] = []
    if not observations:
        problems.append(f"no scorecards found under {RUNS_ROOT.relative_to(REPO_ROOT)}")

    edges = build_edges(observations)
    problems += verify_edges(edges, observations)

    first = build_payloads(RUNS_ROOT)
    second = build_payloads(RUNS_ROOT)
    for name in sorted(set(first) | set(second)):
        if first.get(name) != second.get(name):
            problems.append(f"{name}: two builds are not byte-identical")

    manifest = json.loads(first["manifest.json"])
    if manifest["files"]["edges.jsonl"]["rows"] != len(edges):
        problems.append("manifest row count does not match built edges")

    result = {
        "ok": not problems,
        "problems": problems[:60],
        "scorecards_read": len(observations),
        "primitives_seen": len({p for o in observations for p in o["primitives"]}),
        "edges": len(edges),
        "source_run_ids": manifest["source_run_ids"],
    }
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


def write_edges() -> int:
    payloads = build_payloads(RUNS_ROOT)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, data in sorted(payloads.items()):
        (OUT_DIR / name).write_bytes(data)
    manifest = json.loads(payloads["manifest.json"])
    print(json.dumps({
        "ok": True,
        "out_dir": str(OUT_DIR.relative_to(REPO_ROOT)),
        "files_written": sorted(payloads),
        "row_counts": manifest["row_counts"],
        "total_rows": manifest["total_rows"],
    }, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true",
                        help="write edges.jsonl and manifest.json to benchmarks/cooccurrence/")
    parser.add_argument("--self-test", action="store_true",
                        help="build in memory from real runs and verify invariants")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.write:
        return write_edges()
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
