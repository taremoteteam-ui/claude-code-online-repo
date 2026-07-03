"""Guardrails for the AIDoneRight project template + standards hub.

Keeps the scaffold well-formed: the required files exist, the skeleton proof
runner is valid Python, and the standards hub links every standard doc. Cheap; it
just protects the template from bit-rot.
"""

import ast
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = REPO_ROOT / "templates" / "aidoneright-project-template"
HUB = REPO_ROOT / "docs" / "aidoneright" / "README.md"

REQUIRED = [
    "README.md", "CLAUDE.md", "CONTEXT.md", "STANDARDS.md",
    ".github/workflows/proofs.yml", "scripts/run_proofs.py",
    "schemas/.gitkeep", "scripts/seeds/.gitkeep", "primitives/.gitkeep", "tests/.gitkeep",
]


class TemplateTests(unittest.TestCase):
    def test_required_files_exist(self):
        for rel in REQUIRED:
            self.assertTrue((TEMPLATE / rel).exists(), rel)

    def test_skeleton_run_proofs_is_valid_python(self):
        src = (TEMPLATE / "scripts" / "run_proofs.py").read_text(encoding="utf-8")
        ast.parse(src)   # raises SyntaxError if malformed

    def test_standards_docs_referenced_by_hub(self):
        hub = HUB.read_text(encoding="utf-8")
        for doc in ("globally-unique-naming-and-tracing.md", "multiple-path-development.md"):
            self.assertIn(doc, hub)
            self.assertTrue((HUB.parent / doc).exists(), doc)

    def test_standards_copy_states_invariants(self):
        text = (TEMPLATE / "STANDARDS.md").read_text(encoding="utf-8")
        for token in ("candidate", "Globally Unique", "Multiple-Path", "Verify the verifier"):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
