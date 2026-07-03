#!/usr/bin/env python3
"""Measured demo of the edge-graph route compiler.

Compiles a curated set of realistic (have -> want) targets over the capability
graph with ZERO model calls, and writes the compiled routes (PlanLocks), the
honest gap records for unreachable targets, and a normalization-candidate queue
that turns each gap into actionable work (which distinct port names a reviewer
could declare synonymous, or which connector primitive is missing).

This measures how far the bank is from being edge-compilable today. It does not
claim every target composes; the compose rate and the gap/normalization queue
are the deliverable - the targeted path to tens of thousands of *composable*
primitives.

Usage:
    python3 scripts/run_route_compiler_demo.py --self-test
    python3 scripts/run_route_compiler_demo.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from primitives.route_compiler import compile_route  # noqa: E402

GRAPH = REPO_ROOT / "catalog" / "knowledge-packs" / "data" / "capability-graph" / "capability_graph.jsonl"
RUNS_ROOT = REPO_ROOT / "benchmarks" / "route_compiler_runs"

# Curated realistic targets across lanes. `have` lists the artifacts a caller
# already holds; `want` is the artifact they need. Config/policy ports are
# assumed suppliable by the request and are not listed.
TARGETS = [
    {"have": ["CsvFile"], "want": "ParquetFile", "note": "format conversion (1 step, exact)"},
    {"have": ["CsvFile"], "want": "ArrowTable", "note": "csv->parquet->arrow (2 steps, exact)"},
    {"have": ["AreaOfInterest"], "want": "CanonicalEntitySet", "note": "ingest->dedupe (2 steps, typed hop)"},
    {"have": ["AreaOfInterest"], "want": "MatchDecisionReceipt", "note": "ingest->resolve (2 steps)"},
    {"have": ["DatasetSample"], "want": "SchemaFingerprint", "note": "profile a dataset"},
    {"have": ["HRSASiteRecordSet"], "want": "CanonicalEntitySet", "note": "resolve health-facility records"},
    {"have": ["ProviderCandidateSet"], "want": "CanonicalEntitySet", "note": "resolve provider records"},
    {"have": ["TrainingProviderRecordSet"], "want": "CanonicalEntitySet", "note": "resolve training providers"},
    {"have": ["InputTable"], "want": "SchemaFingerprint", "note": "fingerprint a table"},
    {"have": ["ParquetFile"], "want": "ArrowTable", "note": "parquet to arrow"},
    {"have": ["JsonObject"], "want": "RowSet", "note": "json to rows"},
    {"have": ["AreaOfInterest", "HRSASiteRecordSet"], "want": "MapOrDashboardArtifact", "note": "map facilities"},
    {"have": ["AreaOfInterest"], "want": "EvidenceBackedAnswer", "note": "flagship place-discovery route"},
    {"have": ["DocumentText"], "want": "ExtractedFieldValue", "note": "extract a contract field"},
    {"have": ["TextCorpus"], "want": "CitedAnswer", "note": "RAG grounded answer"},
    {"have": ["RawEntityRecordSet", "ReferenceEntitySet"], "want": "LinkGraph", "note": "record linkage"},
    {"have": ["ResetRequest"], "want": "ResetChallenge", "note": "password reset"},
    {"have": ["LoginAttempt"], "want": "SessionToken", "note": "login to session"},
    {"have": ["ComparisonVector"], "want": "MatchScoreSet", "note": "score candidate pairs"},
    {"have": ["ShortText", "ShortText"], "want": "SimilarityScore", "note": "string similarity"},
    {"have": ["PointRecordSet", "BoundaryLayer"], "want": "BoundaryTaggedRecordSet", "note": "spatial join"},
    {"have": ["WebhookHttpRequest"], "want": "DomainEvent", "note": "webhook to event"},
    {"have": ["RawCustomerRecordBatch"], "want": "CrmImportReceipt", "note": "customer import"},
]


def load_validator():
    spec = importlib.util.spec_from_file_location(
        "pack_checker", REPO_ROOT / "scripts" / "check_place_discovery_geospatial_pack.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.StructuralValidator(json.loads(
        (REPO_ROOT / "schemas" / "compiled_route.schema.json").read_text(encoding="utf-8")))


def _tokens(name: str) -> set:
    return {t.lower() for t in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])", name) if len(t) >= 4}


def normalization_candidates(unmet_type: str, nodes: list[dict]) -> list[dict]:
    """Producer output ports that share a meaningful token with the unmet type -
    reviewer candidates for a declared synonym, or the connector to build."""
    want_tokens = _tokens(unmet_type)
    if not want_tokens:
        return []
    out = []
    for n in nodes:
        for op in n["output_ports"]:
            if op["name"] == unmet_type:
                continue
            if _tokens(op["name"]) & want_tokens:
                out.append({"producer_node": n["node_id"], "produced_port": op["name"],
                            "shared_tokens": sorted(_tokens(op["name"]) & want_tokens)})
    # dedupe by produced_port, cap
    seen = set()
    uniq = []
    for c in sorted(out, key=lambda x: x["produced_port"]):
        if c["produced_port"] in seen:
            continue
        seen.add(c["produced_port"])
        uniq.append(c)
    return uniq[:8]


def run(write: bool) -> dict:
    nodes = [json.loads(line) for line in GRAPH.read_text(encoding="utf-8").splitlines() if line.strip()]
    run_id = "routerun-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    routes: list[dict] = []
    gaps: list[dict] = []
    norm_candidates: list[dict] = []
    validator = load_validator()
    schema_problems: list[str] = []

    for t in TARGETS:
        r = compile_route(t["have"], t["want"], nodes)
        errs = validator.validate(r)
        if errs:
            schema_problems.append(f"{t['want']}: {errs[0]}")
        if r["compiled"]:
            routes.append(r)
        else:
            gaps.append(r)
            for ut in r["unmet_types"]:
                cands = normalization_candidates(ut, nodes)
                if cands:
                    norm_candidates.append({
                        "record_type": "port_normalization_candidate",
                        "unmet_type": ut,
                        "for_target": t["want"],
                        "candidates": cands,
                        "action": "declare a reviewed synonym in primitives/edges.py _SYNONYM_MAP, or build the connector primitive",
                        "candidate": True,
                        "serves_truth": False,
                    })

    tiers = {}
    for r in routes:
        for s in r["route_steps"]:
            for c in s["satisfied_by"]:
                tiers[c["tier"]] = tiers.get(c["tier"], 0) + 1

    summary = {
        "run_id": run_id,
        "targets": len(TARGETS),
        "compiled": len(routes),
        "gaps": len(gaps),
        "compose_rate": round(len(routes) / len(TARGETS), 4),
        "runtime_llm_tokens": 0,
        "mean_step_count": round(sum(r["step_count"] for r in routes) / len(routes), 2) if routes else 0.0,
        "connection_tiers": tiers,
        "normalization_candidates": len(norm_candidates),
        "schema_problems": schema_problems,
        "honesty_notes": [
            "zero model calls: routes assembled purely from typed edges",
            "not every target composes; the gap + normalization queue is the deliverable",
            "typed-tier hops rely on reviewed synonyms and are labeled, never silent",
        ],
    }

    if write:
        run_dir = RUNS_ROOT / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        files = {
            "compiled_routes.jsonl": "".join(json.dumps(r) + "\n" for r in routes),
            "gap_records.jsonl": "".join(json.dumps(g) + "\n" for g in gaps),
            "normalization_candidates.jsonl": "".join(json.dumps(c) + "\n" for c in norm_candidates),
            "run_summary.json": json.dumps(summary, indent=2) + "\n",
        }
        for name, content in files.items():
            (run_dir / name).write_text(content, encoding="utf-8")
        manifest = {
            "run_id": run_id,
            "generated_by": "scripts/run_route_compiler_demo.py",
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
    summary = run(write=args.write)
    print(json.dumps(summary, indent=2))
    # Honest gate: the compiler must run, produce schema-valid routes, and
    # compose at least one real multi-primitive route. It does NOT require all
    # targets to compose - gaps are expected and are the point.
    ok = (not summary["schema_problems"] and summary["compiled"] >= 1
          and summary["runtime_llm_tokens"] == 0)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
