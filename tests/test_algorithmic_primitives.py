"""Contract tests for the working algorithmic kernels.

Every kernel must pass its declared self-test fixture, plus a few explicit
edge cases the fixtures don't cover (impossible / unreachable / cyclic inputs).
"""

import unittest

from primitives.algorithmic_primitives import (PRIMITIVES, bfs_shortest_path,
                                               dp_coin_change, kadane_max_subarray,
                                               run_self_test, topological_order,
                                               two_pointer_pair_sum)


class KernelSelfTests(unittest.TestCase):
    def test_every_kernel_self_test_passes(self):
        for pid in PRIMITIVES:
            self.assertTrue(run_self_test(pid), pid)

    def test_registry_shape(self):
        for pid, meta in PRIMITIVES.items():
            self.assertTrue(pid.startswith("algo:"))
            self.assertTrue(callable(meta["fn"]))
            for field in ("does", "pattern", "input_edge", "output_edge"):
                self.assertTrue(meta[field])


class KernelEdgeCases(unittest.TestCase):
    def test_pair_sum_no_answer(self):
        self.assertEqual(two_pointer_pair_sum([1, 2, 3], 100), [])

    def test_coin_change_impossible(self):
        self.assertEqual(dp_coin_change([2], 3), -1)

    def test_bfs_unreachable(self):
        self.assertEqual(bfs_shortest_path({0: [1], 1: [], 2: []}, 0, 2), -1)

    def test_bfs_self(self):
        self.assertEqual(bfs_shortest_path({0: []}, 0, 0), 0)

    def test_topological_order_detects_cycle(self):
        self.assertEqual(topological_order(2, [[0, 1], [1, 0]]), [])

    def test_kadane_all_negative(self):
        self.assertEqual(kadane_max_subarray([-5, -2, -9]), -2)


if __name__ == "__main__":
    unittest.main()
