"""Contract tests for the route runtime (execute a compiled PlanLock).

route_runtime was previously exercised only indirectly (through the foundry
pipeline and coding-harness demos). These tests pin its two load-bearing
behaviours directly:

  1. it threads real values through a compiled chain, emits one receipt per step,
     and resolves the wanted artifact BY CANONICAL TYPE (the _merge canonical
     store - the exact seam a past bug lost); and
  2. a step with no registered handler is an honest stop (ran=False, the node
     reported as unimplemented), never a faked result.
"""

import unittest

from primitives.core import PrimitiveOutcome, ProofResult
from primitives.edges import canonical_type
from primitives.route_runtime import execute_route


def _emit(port, value):
    """A handler that produces {port: value} with a passing proof."""
    def handler(state):
        return PrimitiveOutcome(
            output={port: value},
            effects_observed=["none"],
            proof_results=[ProofResult("schema_validation", True, "ok")])
    return handler


class RouteRuntimeTests(unittest.TestCase):
    def test_runs_chain_and_resolves_want_by_canonical_type(self):
        # producing port is "RowSet" but the want is keyed by its canonical type
        # (TabularDataset); the runtime must resolve across that alias.
        self.assertNotEqual(canonical_type("RowSet"), "RowSet")
        route = {
            "compiled": True,
            "want": "RowSet",
            "want_canonical_type": canonical_type("RowSet"),
            "route_steps": [{"node_id": "n1"}],
        }
        handlers = {"n1": _emit("RowSet", [{"a": 1}])}
        result = execute_route(route, handlers, initial_state={}, run_id="t")
        self.assertTrue(result["ran"])
        self.assertEqual(result["want_value"], [{"a": 1}])
        self.assertEqual(result["steps_executed"], 1)
        self.assertEqual(len(result["step_receipts"]), 1)
        self.assertEqual(result["effects_union"], ["none"])
        self.assertEqual(result["unimplemented"], [])

    def test_two_step_chain_threads_state(self):
        route = {
            "compiled": True, "want": "RowSet",
            "want_canonical_type": canonical_type("RowSet"),
            "route_steps": [{"node_id": "n1"}, {"node_id": "n2"}],
        }
        handlers = {"n1": _emit("Parsed", {"k": 1}), "n2": _emit("RowSet", [{"k": 1}])}
        result = execute_route(route, handlers, initial_state={}, run_id="t")
        self.assertTrue(result["ran"])
        self.assertEqual(result["steps_executed"], 2)
        self.assertEqual(result["want_value"], [{"k": 1}])

    def test_missing_handler_is_an_honest_stop(self):
        route = {
            "compiled": True, "want": "RowSet",
            "want_canonical_type": canonical_type("RowSet"),
            "route_steps": [{"node_id": "n1"}, {"node_id": "n2"}],
        }
        handlers = {"n1": _emit("RowSet", [{"a": 1}])}   # n2 has no handler
        result = execute_route(route, handlers, initial_state={}, run_id="t")
        self.assertFalse(result["ran"])
        self.assertEqual(result["unimplemented"], ["n2"])
        self.assertEqual(result["steps_executed"], 1)

    def test_uncompiled_route_does_not_run(self):
        result = execute_route({"compiled": False}, {}, {}, run_id="t")
        self.assertFalse(result["ran"])
        self.assertEqual(result["step_receipts"], [])


if __name__ == "__main__":
    unittest.main()
