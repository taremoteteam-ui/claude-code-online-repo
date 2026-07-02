#!/usr/bin/env python3
"""Benchmark harness for the document-extraction lane.

Runs the DETERMINISTIC extraction route (arm A4) over each synthetic contract
fixture and writes MEASURED scorecards, execution receipts, and a computed
manifest under benchmarks/doc_runs/<run_id>/.

Route per document: ingest -> segment -> field_locate_and_extract (with the
benchmark ground-truth field specs, minus the answer keys) -> source_span_verify
-> extraction_evidence_bundle. Every located value is checked against its
source span; the run's headline is source-span coverage and field recall, not
just pass/fail.

Honesty rules:
  - Arm A4 invokes no model in the runtime path, so runtime_llm_tokens is 0
    (a measured fact of this arm).
  - Fixtures are synthetic contracts: this measures the extraction route, not
    real-world accuracy on real documents.
  - Baseline arms A1/A2 (a model reads the whole document and extracts
    free-form) are NOT simulated. No source-span-vs-baseline claim is made.

Usage:
    python3 scripts/run_document_extraction_benchmark.py --self-test
    python3 scripts/run_document_extraction_benchmark.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from primitives.core import PrimitiveExecutionError, run_primitive  # noqa: E402

SEEDS_DIR = REPO_ROOT / "scripts" / "seeds"
RUNS_ROOT = REPO_ROOT / "benchmarks" / "doc_runs"

ARM_ID = "A4"
DEPTH = "L4"


def load_benchmark_documents() -> list[dict]:
    ns: dict = {}
    path = SEEDS_DIR / "document_extraction_benchmark_seed.py"
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), ns)  # noqa: S102
    return ns["BENCHMARK_DOCUMENTS"]


def import_primitives() -> dict:
    from primitives.documents.extract import (
        clause_section_segment, document_ingest_and_layout, field_locate_and_extract,
    )
    from primitives.documents.verify import source_span_verify
    from primitives.documents.bundle import extraction_evidence_bundle
    return {
        "ingest": document_ingest_and_layout,
        "segment": clause_section_segment,
        "extract": field_locate_and_extract,
        "verify": source_span_verify,
        "bundle": extraction_evidence_bundle,
    }


class DocContext:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.receipts: list[dict] = []

    def exec(self, primitive_id: str, fn, payload):
        output, receipt = run_primitive(
            primitive_id, fn, payload, run_id=self.run_id,
            declared_effects=["none"], execution_mode="fixture_offline")
        self.receipts.append(receipt)
        return output, receipt


def spec_for_extractor(field_specs: list[dict]) -> list[dict]:
    """Strip the answer keys (expected_value/expected_normalized) before the
    extractor sees them - it must locate values from anchors alone."""
    stripped = []
    for s in field_specs:
        stripped.append({
            "field_ref": s["field_ref"],
            "value_type": s["value_type"],
            "cardinality": s.get("cardinality", "one"),
            "anchors": s["anchors"],
            "value_pattern": s.get("value_pattern"),
            "normalization": s.get("normalization", "none"),
        })
    return stripped


def score_document(doc: dict, prims: dict, ctx: DocContext) -> dict:
    text = (REPO_ROOT / doc["fixture_path"]).read_text(encoding="utf-8")
    doc_id = doc["document_family"]

    ctx.exec("prim:document_extraction.document_ingest_and_layout", prims["ingest"],
             {"document_text": text, "document_id": doc_id})
    ctx.exec("prim:document_extraction.clause_section_segment", prims["segment"],
             {"document_text": text})
    extract_out, _ = ctx.exec(
        "prim:document_extraction.field_locate_and_extract", prims["extract"],
        {"document_text": text, "field_specs": spec_for_extractor(doc["field_specs"])})
    extractions = extract_out["extractions"]
    by_ref = {e["field_ref"]: e for e in extractions}

    ctx.exec("prim:document_extraction.source_span_verify", prims["verify"],
             {"document_text": text,
              "extractions": [{"value": e["value"], "source_span": e["source_span"],
                               "span_text": e["span_text"]} for e in extractions]})
    ctx.exec("prim:document_extraction.extraction_evidence_bundle", prims["bundle"],
             {"document_id": doc_id, "extractions": extractions,
              "source_snapshots": [{"snapshot_id": f"snap:{doc_id}",
                                    "source_id": "fixture_synthetic",
                                    "retrieved_mode": "fixture_offline"}],
              "uncertainty_notes": ["synthetic fixture; anchors are ground-truth locators"]})

    expected = doc["field_specs"]
    located = 0
    span_ok = 0
    value_ok = 0
    norm_ok = 0
    for spec in expected:
        e = by_ref.get(spec["field_ref"])
        if e is None:
            continue
        located += 1
        if text[e["source_span"][0]:e["source_span"][1]] == e["span_text"] and e["value"] in e["span_text"]:
            span_ok += 1
        if e["value"] == spec["expected_value"]:
            value_ok += 1
        if str(e.get("normalized_value")) == str(spec.get("expected_normalized")):
            norm_ok += 1

    n = len(expected)
    passed = sum(1 for r in ctx.receipts for p in r["proof_results"] if p["passed"])
    total = sum(len(r["proof_results"]) for r in ctx.receipts)
    success = (located == n and span_ok == located and value_ok == located)
    missed = [s["field_ref"] for s in expected if s["field_ref"] not in by_ref]
    return {
        "fields_expected": n,
        "fields_located": located,
        "field_recall": round(located / n, 4) if n else 0.0,
        "source_span_coverage": round(span_ok / located, 4) if located else 0.0,
        "value_exact_match_ratio": round(value_ok / located, 4) if located else 0.0,
        "normalization_accuracy": round(norm_ok / located, 4) if located else 0.0,
        "proof_coverage": round(passed / total, 4) if total else 0.0,
        "task_success": success,
        "missed": missed,
    }


def run_benchmark(write: bool) -> dict:
    run_id = "docrun-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = RUNS_ROOT / run_id
    prims = import_primitives()
    docs = load_benchmark_documents()

    scorecards: list[dict] = []
    all_receipts: list[dict] = []
    for idx, doc in enumerate(docs):
        ctx = DocContext(run_id)
        t0 = time.perf_counter()
        error_note = ""
        try:
            metrics = score_document(doc, prims, ctx)
        except PrimitiveExecutionError as exc:
            ctx.receipts.append(exc.receipt)
            metrics = {"fields_expected": len(doc["field_specs"]), "fields_located": 0,
                       "field_recall": 0.0, "source_span_coverage": 0.0,
                       "value_exact_match_ratio": 0.0, "normalization_accuracy": 0.0,
                       "proof_coverage": 0.0, "task_success": False, "missed": []}
            error_note = str(exc)
        wall = time.perf_counter() - t0

        scorecard = {
            "record_type": "document_extraction_scorecard",
            "scorecard_id": "docscore:" + hashlib.sha256(
                f"{doc['document_family']}|{ARM_ID}|{run_id}".encode()).hexdigest()[:16],
            "document_family": doc["document_family"],
            "fixture_path": doc["fixture_path"],
            "arm_id": ARM_ID,
            "run_id": run_id,
            "measured": True,
            "execution_mode": "fixture_offline",
            "task_success": bool(metrics["task_success"]),
            "wall_clock_seconds": round(wall, 4),
            "depth_to_solution": DEPTH,
            "runtime_llm_tokens": 0,
            "fields_expected": metrics["fields_expected"],
            "fields_located": metrics["fields_located"],
            "field_recall": metrics["field_recall"],
            "source_span_coverage": metrics["source_span_coverage"],
            "value_exact_match_ratio": metrics["value_exact_match_ratio"],
            "normalization_accuracy": metrics["normalization_accuracy"],
            "proof_coverage": metrics["proof_coverage"],
            "receipt_ids": [r["receipt_id"] for r in ctx.receipts],
            "notes": ((f"missed={metrics['missed']} " if metrics["missed"] else "")
                      + (error_note + " " if error_note else "")
                      + "fixture_offline: synthetic contracts measure the extraction route, "
                      "not real-world accuracy | arms A1/A2 not run"),
            "candidate": True,
            "serves_truth": False,
        }
        scorecards.append(scorecard)
        all_receipts.extend(ctx.receipts)

    summary = {
        "run_id": run_id,
        "arm_id": ARM_ID,
        "execution_mode": "fixture_offline",
        "documents_run": len(scorecards),
        "documents_succeeded": sum(1 for s in scorecards if s["task_success"]),
        "mean_field_recall": round(
            sum(s["field_recall"] for s in scorecards) / len(scorecards), 4) if scorecards else 0.0,
        "mean_source_span_coverage": round(
            sum(s["source_span_coverage"] for s in scorecards) / len(scorecards), 4) if scorecards else 0.0,
        "total_receipts": len(all_receipts),
        "total_proofs_passed": sum(1 for r in all_receipts for p in r["proof_results"] if p["passed"]),
        "total_proofs": sum(len(r["proof_results"]) for r in all_receipts),
        "runtime_llm_tokens_total": 0,
        "honesty_notes": [
            "fixture_offline: synthetic contracts, extraction-route machinery only",
            "baseline arms A1/A2 not run; no source-span-vs-baseline claim is made",
        ],
    }

    if write:
        run_dir.mkdir(parents=True, exist_ok=True)
        files = {
            "scorecards.jsonl": "".join(json.dumps(s) + "\n" for s in scorecards),
            "receipts.jsonl": "".join(json.dumps(r) + "\n" for r in all_receipts),
            "run_summary.json": json.dumps(summary, indent=2) + "\n",
        }
        for name, content in files.items():
            (run_dir / name).write_text(content, encoding="utf-8")
        manifest = {
            "run_id": run_id,
            "generated_by": "scripts/run_document_extraction_benchmark.py",
            "files": {name: {"rows": content.count("\n") if name.endswith(".jsonl") else 1,
                             "content_sha256": hashlib.sha256(content.encode()).hexdigest()}
                      for name, content in files.items()},
            "candidate": True,
            "serves_truth": False,
        }
        (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        summary["run_dir"] = str(run_dir.relative_to(REPO_ROOT))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not (args.write or args.self_test):
        parser.print_help()
        return 2
    summary = run_benchmark(write=args.write)
    print(json.dumps(summary, indent=2))
    ok = (summary["documents_succeeded"] == summary["documents_run"]
          and summary["documents_run"] > 0)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
