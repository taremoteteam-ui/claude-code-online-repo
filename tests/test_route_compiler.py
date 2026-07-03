"""Contract tests for the edge model and deterministic route compiler."""

import unittest

from primitives.edges import (
    canonical_type,
    config_ports,
    output_ports,
    port_role,
    required_input_ports,
)
from primitives.route_compiler import compile_route


def node(node_id, in_edge, out_edge):
    return {
        "node_id": node_id,
        "required_input_ports": [{"name": p.name, "canonical_type": p.canonical_type}
                                 for p in required_input_ports(in_edge)],
        "config_ports": [{"name": p.name, "canonical_type": p.canonical_type}
                         for p in config_ports(in_edge)],
        "output_ports": [{"name": p.name, "role": p.role, "canonical_type": p.canonical_type}
                         for p in output_ports(out_edge)],
    }


class EdgeModelTests(unittest.TestCase):
    def test_config_ports_excluded_from_requirements(self):
        reqs = required_input_ports("CsvFile+ImportPolicy+SchemaSpec")
        names = {p.name for p in reqs}
        self.assertIn("CsvFile", names)
        self.assertNotIn("ImportPolicy", names)
        self.assertNotIn("SchemaSpec", names)

    def test_roles(self):
        self.assertEqual(port_role("ImportPolicy"), "config")
        self.assertEqual(port_role("ImportReceipt"), "receipt")
        self.assertEqual(port_role("CsvFile"), "data")

    def test_conservative_typing_no_lossy_bucket(self):
        # Distinct artifacts must NOT collapse to one type.
        self.assertNotEqual(canonical_type("MapOrDashboardArtifact"),
                            canonical_type("MockServerArtifact"))

    def test_reviewed_synonym_applies(self):
        self.assertEqual(canonical_type("HRSASiteRecordSet"),
                         canonical_type("RawEntityRecordSet"))


class CompilerTests(unittest.TestCase):
    def setUp(self):
        self.nodes = [
            node("prim:a.to_b", "AArtifact+APolicy", "BArtifact+StepReceipt"),
            node("prim:b.to_c", "BArtifact", "CArtifact+StepReceipt"),
            node("prim:x.to_y", "XArtifact", "YArtifact"),
        ]

    def test_single_step(self):
        r = compile_route(["AArtifact"], "BArtifact", self.nodes)
        self.assertTrue(r["compiled"])
        self.assertEqual(r["step_count"], 1)
        self.assertEqual(r["route_steps"][0]["node_id"], "prim:a.to_b")

    def test_multi_step_chain(self):
        r = compile_route(["AArtifact"], "CArtifact", self.nodes)
        self.assertTrue(r["compiled"])
        self.assertEqual([s["node_id"] for s in r["route_steps"]],
                         ["prim:a.to_b", "prim:b.to_c"])
        # step 2's input satisfied by step 1 (exact tier, same port name).
        conn = r["route_steps"][1]["satisfied_by"][0]
        self.assertEqual(conn["source"], "step:1")
        self.assertEqual(conn["tier"], "exact")

    def test_config_ports_do_not_block(self):
        # APolicy is config; only AArtifact is required.
        r = compile_route(["AArtifact"], "BArtifact", self.nodes)
        self.assertTrue(r["compiled"])

    def test_unreachable_is_gap(self):
        r = compile_route(["AArtifact"], "YArtifact", self.nodes)
        self.assertFalse(r["compiled"])
        self.assertEqual(r["step_count"], 0)
        self.assertEqual(r["want_canonical_type"], "YArtifact")
        # nearest producer of YArtifact is reported.
        self.assertIn("prim:x.to_y", r["nearest_producers"])

    def test_already_available_empty_route(self):
        r = compile_route(["BArtifact"], "BArtifact", self.nodes)
        self.assertTrue(r["compiled"])
        self.assertEqual(r["step_count"], 0)

    def test_deterministic_route_hash(self):
        a = compile_route(["AArtifact"], "CArtifact", self.nodes)
        b = compile_route(["AArtifact"], "CArtifact", self.nodes)
        self.assertEqual(a["route_hash"], b["route_hash"])
        self.assertTrue(a["route_hash"].startswith("sha256:"))


if __name__ == "__main__":
    unittest.main()
