"""Unit tests for the co-occurrence miner (scripts/build_cooccurrence_edges.py).

These tests build a synthetic mini-scorecards fixture in a temporary
directory; they never depend on real benchmark runs (the script's
--self-test covers the real runs).

Run from the repo root:
    python3 -m unittest tests.test_cooccurrence -v
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

P1 = "prim:place_discovery.alpha_ingester"
P2 = "prim:place_discovery.beta_dedupe"
P3 = "prim:place_discovery.gamma_mapper"
P4 = "prim:place_discovery.delta_solo"


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "cooc_builder", REPO_ROOT / "scripts" / "build_cooccurrence_edges.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BUILDER = load_builder()


def write_run(runs_root: Path, run_id: str, scorecards: list) -> None:
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True)
    payload = "".join(json.dumps(row) + "\n" for row in scorecards)
    (run_dir / "scorecards.jsonl").write_text(payload, encoding="utf-8")


def scorecard(run_id: str, task_id: str, primitives: list) -> dict:
    return {
        "record_type": "place_discovery_benchmark_scorecard",
        "task_id": task_id,
        "run_id": run_id,
        "arm_id": "A4",
        "primitives_executed": primitives,
    }


class CooccurrenceFixtureMixin:
    """Two synthetic runs with known primitive overlap.

    run-a: t1 executes {P1, P2, P3} (P2 listed twice to exercise dedupe),
           t2 executes {P1, P2}
    run-b: t3 executes {P2, P3},
           t4 executes {P4} alone (contributes no pairs)

    Expected task counts: P1=2, P2=3, P3=2, P4=1.
    Expected pairs: (P1,P2)=2, (P2,P3)=2, (P1,P3)=1.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.runs_root = Path(self._tmp.name) / "runs"
        write_run(self.runs_root, "run-a", [
            scorecard("run-a", "bench:x.t1", [P1, P2, P3, P2]),
            scorecard("run-a", "bench:x.t2", [P1, P2]),
        ])
        write_run(self.runs_root, "run-b", [
            scorecard("run-b", "bench:x.t3", [P2, P3]),
            scorecard("run-b", "bench:x.t4", [P4]),
        ])
        self.observations = BUILDER.load_observations(self.runs_root)
        self.edges = BUILDER.build_edges(self.observations)
        self.by_pair = {(e["a"], e["b"]): e for e in self.edges}


class TestCooccurrenceCounts(CooccurrenceFixtureMixin, unittest.TestCase):
    def test_observation_loading_dedupes_and_sorts_primitives(self):
        self.assertEqual(len(self.observations), 4)
        t1 = next(o for o in self.observations if o["task_id"] == "bench:x.t1")
        self.assertEqual(t1["primitives"], sorted([P1, P2, P3]))

    def test_expected_pairs_present_and_solo_primitive_excluded(self):
        self.assertEqual(set(self.by_pair), {(P1, P2), (P2, P3), (P1, P3)})
        for a, b in self.by_pair:
            self.assertLess(a, b)
        self.assertFalse(any(P4 in (e["a"], e["b"]) for e in self.edges))

    def test_counts_and_jaccard(self):
        e12 = self.by_pair[(P1, P2)]
        self.assertEqual(e12["used_together_count"], 2)
        self.assertEqual(e12["a_task_count"], 2)
        self.assertEqual(e12["b_task_count"], 3)
        self.assertEqual(e12["jaccard"], round(2 / 3, 4))

        e23 = self.by_pair[(P2, P3)]
        self.assertEqual(e23["used_together_count"], 2)
        self.assertEqual(e23["a_task_count"], 3)
        self.assertEqual(e23["b_task_count"], 2)
        self.assertEqual(e23["jaccard"], round(2 / 3, 4))

        e13 = self.by_pair[(P1, P3)]
        self.assertEqual(e13["used_together_count"], 1)
        self.assertEqual(e13["a_task_count"], 2)
        self.assertEqual(e13["b_task_count"], 2)
        self.assertEqual(e13["jaccard"], round(1 / 3, 4))

    def test_used_together_never_exceeds_endpoint_task_counts(self):
        for e in self.edges:
            self.assertLessEqual(
                e["used_together_count"], min(e["a_task_count"], e["b_task_count"]))
            self.assertGreater(e["jaccard"], 0)
            self.assertLessEqual(e["jaccard"], 1)

    def test_source_run_ids(self):
        self.assertEqual(self.by_pair[(P1, P2)]["source_run_ids"], ["run-a"])
        self.assertEqual(self.by_pair[(P1, P3)]["source_run_ids"], ["run-a"])
        self.assertEqual(self.by_pair[(P2, P3)]["source_run_ids"], ["run-a", "run-b"])

    def test_edge_ids_are_sha256_of_sorted_pair(self):
        for e in self.edges:
            digest = hashlib.sha256(f"{e['a']}|{e['b']}".encode("utf-8")).hexdigest()
            self.assertEqual(e["edge_id"], f"cooc:{digest[:16]}")
            self.assertRegex(e["edge_id"], r"^cooc:[0-9a-f]{16}$")

    def test_sorted_by_count_desc_then_edge_id(self):
        keys = [(-e["used_together_count"], e["edge_id"]) for e in self.edges]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(self.edges[-1]["used_together_count"], 1)

    def test_row_shape_and_candidate_boundary(self):
        expected_keys = [
            "record_type", "edge_id", "a", "b", "used_together_count",
            "a_task_count", "b_task_count", "jaccard", "source_run_ids",
            "candidate", "serves_truth",
        ]
        for e in self.edges:
            self.assertEqual(list(e.keys()), expected_keys)
            self.assertEqual(e["record_type"], "primitive_cooccurrence_edge")
            self.assertIs(e["candidate"], True)
            self.assertIs(e["serves_truth"], False)

    def test_verify_edges_passes_on_consistent_build(self):
        self.assertEqual(BUILDER.verify_edges(self.edges, self.observations), [])

    def test_verify_edges_flags_inconsistencies(self):
        broken = json.loads(json.dumps(self.edges))
        broken[0]["used_together_count"] = 99
        broken[1]["jaccard"] = 0.0
        problems = BUILDER.verify_edges(broken, self.observations)
        self.assertTrue(any("exceeds min" in p for p in problems))
        self.assertTrue(any("outside (0, 1]" in p for p in problems))


class TestCooccurrencePayloads(CooccurrenceFixtureMixin, unittest.TestCase):
    def test_manifest_counts_and_hash_are_computed(self):
        payloads = BUILDER.build_payloads(self.runs_root)
        manifest = json.loads(payloads["manifest.json"])
        edges_bytes = payloads["edges.jsonl"]
        rows = [json.loads(line) for line in edges_bytes.decode("utf-8").splitlines()]
        self.assertEqual(manifest["files"]["edges.jsonl"]["rows"], len(rows))
        self.assertEqual(
            manifest["files"]["edges.jsonl"]["content_sha256"],
            hashlib.sha256(edges_bytes).hexdigest())
        self.assertEqual(manifest["row_counts"]["edges.jsonl"], len(rows))
        self.assertEqual(manifest["total_rows"], len(rows))
        self.assertEqual(manifest["source_run_ids"], ["run-a", "run-b"])
        self.assertIs(manifest["candidate"], True)
        self.assertIs(manifest["serves_truth"], False)

    def test_two_builds_are_byte_identical(self):
        first = BUILDER.build_payloads(self.runs_root)
        second = BUILDER.build_payloads(self.runs_root)
        self.assertEqual(sorted(first), sorted(second))
        for name in first:
            self.assertEqual(first[name], second[name], f"{name} differs between builds")

    def test_empty_runs_root_yields_no_edges(self):
        empty_root = Path(self._tmp.name) / "empty-runs"
        empty_root.mkdir()
        payloads = BUILDER.build_payloads(empty_root)
        self.assertEqual(payloads["edges.jsonl"], b"")
        manifest = json.loads(payloads["manifest.json"])
        self.assertEqual(manifest["total_rows"], 0)
        self.assertEqual(manifest["source_run_ids"], [])


if __name__ == "__main__":
    unittest.main()
