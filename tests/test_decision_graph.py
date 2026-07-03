"""Tests for the decision graph: forks compose by state contracts."""

import unittest

from primitives.decision_graph import (build_decision_edges, compile_decision_order,
                                       validate_decision_dag)


def _d(did, consumes, produces):
    return {"decision_id": did, "contract": {"input": "x", "output": "y", "win_definition": "wins",
                                             "consumes": consumes, "produces": produces}}


DECISIONS = [
    _d("decision:a.retrieve", ["intent"], ["candidates"]),
    _d("decision:b.order", ["candidates"], ["plan"]),
    _d("decision:c.exec", ["plan"], ["result"]),
    _d("decision:z.unrelated", ["nothing_here"], ["orphan"]),
]


class DecisionGraphTests(unittest.TestCase):
    def test_edges_derived_from_contracts(self):
        edges = {(e["from"], e["to"]) for e in build_decision_edges(DECISIONS)}
        self.assertIn(("decision:a.retrieve", "decision:b.order"), edges)
        self.assertIn(("decision:b.order", "decision:c.exec"), edges)
        self.assertNotIn(("decision:c.exec", "decision:a.retrieve"), edges)

    def test_compile_orders_the_chain(self):
        plan = compile_decision_order(DECISIONS, ["intent"], ["result"])
        self.assertTrue(plan["compiled"])
        self.assertEqual(plan["order"],
                         ["decision:a.retrieve", "decision:b.order", "decision:c.exec"])
        # the orphan fork is not on the path to the goal
        self.assertNotIn("decision:z.unrelated", plan["order"])

    def test_gap_when_goal_unreachable(self):
        plan = compile_decision_order(DECISIONS, ["intent"], ["orphan"])
        self.assertFalse(plan["compiled"])
        self.assertEqual(plan["unmet_keys"], ["orphan"])

    def test_validate_dag_valid_order(self):
        v = validate_decision_dag(
            ["decision:a.retrieve", "decision:b.order", "decision:c.exec"], DECISIONS, ["intent"])
        self.assertTrue(v["valid"])
        self.assertIn("result", v["final_state_keys"])

    def test_validate_dag_rejects_out_of_order(self):
        v = validate_decision_dag(
            ["decision:c.exec", "decision:b.order", "decision:a.retrieve"], DECISIONS, ["intent"])
        self.assertFalse(v["valid"])
        self.assertEqual(v["first_unsatisfied"]["decision_id"], "decision:c.exec")


if __name__ == "__main__":
    unittest.main()
