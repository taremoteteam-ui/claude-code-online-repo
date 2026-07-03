"""Tests for the route validator + ordering strategies (frameworks, LLM propose)."""

import unittest

from primitives.route_validator import validate_order
from primitives.orderers import deterministic_compile, framework_fill, llm_propose


def _node(nid, req, outp):
    return {"node_id": nid, "lane": "t", "kind": "primitive", "title": nid,
            "input_edge": "+".join(req) or "NoInput", "output_edge": outp,
            "required_input_ports": [{"name": r, "canonical_type": r} for r in req],
            "config_ports": [],
            "output_ports": [{"name": outp, "role": "data", "canonical_type": outp}]}


NODES = [
    _node("n:parse", ["GeoJsonDocument"], "PointFeatureCollection"),
    _node("n:flat", ["PointFeatureCollection"], "EntityRecordSet"),
    _node("n:tab", ["EntityRecordSet"], "RowTable"),
]
HAVE, WANT = ["GeoJsonDocument"], "RowTable"


class ValidatorTests(unittest.TestCase):
    def test_valid_chain(self):
        v = validate_order(["n:parse", "n:flat", "n:tab"], HAVE, WANT, NODES)
        self.assertTrue(v["valid"])
        self.assertTrue(v["produces_want"])

    def test_reversed_is_invalid(self):
        v = validate_order(["n:tab", "n:flat", "n:parse"], HAVE, WANT, NODES)
        self.assertFalse(v["valid"])
        self.assertEqual(v["first_unsatisfied"]["node_id"], "n:tab")

    def test_unknown_node_is_invalid(self):
        v = validate_order(["n:nope"], HAVE, WANT, NODES)
        self.assertFalse(v["valid"])

    def test_missing_want_is_invalid(self):
        v = validate_order(["n:parse"], HAVE, WANT, NODES)
        self.assertFalse(v["produces_want"])


class OrdererTests(unittest.TestCase):
    def test_deterministic_compile_valid(self):
        r = deterministic_compile(HAVE, WANT, NODES)
        self.assertTrue(validate_order(r["order"], HAVE, WANT, NODES)["valid"])

    def test_framework_fill_binds_and_validates(self):
        fw = {"framework_id": "framework:t", "slots": [
            {"role": "parse", "produces_type": "PointFeatureCollection"},
            {"role": "flat", "produces_type": "EntityRecordSet"},
            {"role": "tab", "produces_type": "RowTable"}]}
        r = framework_fill(fw, HAVE, WANT, NODES)
        self.assertTrue(r["filled"])
        self.assertTrue(validate_order(r["order"], HAVE, WANT, NODES)["valid"])

    def test_framework_unfillable_slot(self):
        fw = {"framework_id": "framework:t", "slots": [{"role": "x", "produces_type": "Nonexistent"}]}
        self.assertFalse(framework_fill(fw, HAVE, WANT, NODES)["filled"])

    def test_llm_propose_repairs_invalid_to_valid(self):
        r = llm_propose(HAVE, WANT, NODES)
        # the stub proposes a reversed (invalid) order; repair fixes it
        self.assertFalse(r["proposal_valid"])
        self.assertTrue(r["repaired"])
        self.assertTrue(validate_order(r["order"], HAVE, WANT, NODES)["valid"])


if __name__ == "__main__":
    unittest.main()
