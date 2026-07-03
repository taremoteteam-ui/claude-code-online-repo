"""Contract tests: every harvested problem's solution actually solves it, and the
stored decomposition matches the solution's real kernel usage.

Data-driven over fixtures/coding-problems/problems.json so adding a problem
automatically extends coverage.
"""

import json
import unittest
from pathlib import Path

from primitives.coding_solutions import SOLUTIONS

REPO_ROOT = Path(__file__).resolve().parent.parent
PROBLEMS = json.loads(
    (REPO_ROOT / "fixtures" / "coding-problems" / "problems.json").read_text())["problems"]


class CodingSolutionTests(unittest.TestCase):
    def test_every_problem_has_a_solution(self):
        for p in PROBLEMS:
            self.assertIn(p["problem_id"], SOLUTIONS, p["problem_id"])

    def test_every_solution_passes_all_test_cases(self):
        for p in PROBLEMS:
            fn = SOLUTIONS[p["problem_id"]]["fn"]
            for i, tc in enumerate(p["test_cases"]):
                self.assertEqual(fn(**tc["args"]), tc["expected"],
                                 f"{p['problem_id']}[{i}]")

    def test_decomposition_matches_declared_uses(self):
        for p in PROBLEMS:
            self.assertEqual(SOLUTIONS[p["problem_id"]]["uses"], p["primitive_uses"],
                             p["problem_id"])

    def test_sources_span_all_four_styles(self):
        sources = {p["source"] for p in PROBLEMS}
        self.assertEqual(sources, {"leetcode", "codeforces", "interview", "hackathon"})


if __name__ == "__main__":
    unittest.main()
