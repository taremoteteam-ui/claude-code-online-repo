"""Contract tests for the GUVN system + deterministic tracer."""

import unittest

from primitives.guvn import (build_code_map, is_valid_gun, lint,
                             render_mermaid)


def _u(gun, consumes=(), produces=(), qualname=None):
    return {"gun": gun, "kind": "unit", "consumes": list(consumes),
            "produces": list(produces), "effects": ["none"],
            "qualname": qualname or gun}


# a -> [b] -> c , plus a second producer of b (multi-path), plus external input x
UNITS = [
    _u("lane.comp.make_b", consumes=["lane.in.x"], produces=["lane.mid.b"]),
    _u("lane.comp.make_b_alt", consumes=["lane.in.y"], produces=["lane.mid.b"]),
    _u("lane.comp.make_c", consumes=["lane.mid.b"], produces=["lane.out.c"]),
]


class GrammarTests(unittest.TestCase):
    def test_valid_and_invalid_guns(self):
        self.assertTrue(is_valid_gun("geo.records.entity_record_set"))
        self.assertTrue(is_valid_gun("a.b"))
        self.assertFalse(is_valid_gun("single"))          # needs >=2 segments
        self.assertFalse(is_valid_gun("Geo.Records.X"))    # no uppercase
        self.assertFalse(is_valid_gun("a..b"))
        self.assertFalse(is_valid_gun("a.b."))


class CodeMapTests(unittest.TestCase):
    def test_classification(self):
        cm = build_code_map(UNITS)
        self.assertEqual(cm["unit_count"], 3)
        self.assertEqual(set(cm["sources"]), {"lane.in.x", "lane.in.y"})
        self.assertEqual(cm["sinks"], ["lane.out.c"])
        self.assertEqual(cm["multi_path_artifacts"], ["lane.mid.b"])

    def test_hash_is_deterministic_and_order_independent(self):
        a = build_code_map(UNITS)["content_sha256"]
        b = build_code_map(list(reversed(UNITS)))["content_sha256"]
        self.assertEqual(a, b)

    def test_mermaid_renders_all_nodes(self):
        mmd = render_mermaid(build_code_map(UNITS))
        self.assertIn("flowchart LR", mmd)
        self.assertIn("lane.mid.b", mmd)


class LintTests(unittest.TestCase):
    def test_clean_units_pass(self):
        self.assertTrue(lint(UNITS)["ok"])

    def test_multi_path_is_info_not_error(self):
        res = lint(UNITS)
        self.assertTrue(res["ok"])
        self.assertTrue(any("multi-path artifact lane.mid.b" in i for i in res["info"]))

    def test_invalid_grammar_is_error(self):
        self.assertFalse(lint([_u("BadName", produces=["lane.out.c"])])["ok"])

    def test_unit_artifact_name_clash_is_error(self):
        bad = [_u("lane.comp.thing", produces=["lane.comp.thing"])]
        res = lint(bad)
        self.assertFalse(res["ok"])
        self.assertTrue(any("both a unit and an artifact" in e for e in res["errors"]))

    def test_duplicate_unit_gun_is_error(self):
        dup = [_u("lane.comp.x", produces=["lane.out.a"], qualname="f"),
               _u("lane.comp.x", produces=["lane.out.b"], qualname="g")]
        res = lint(dup)
        self.assertFalse(res["ok"])
        self.assertTrue(any("duplicate unit GUN" in e for e in res["errors"]))


class FixtureTraceTests(unittest.TestCase):
    def test_sample_pipeline_traces_clean(self):
        import importlib
        importlib.import_module("fixtures.guvn.sample_pipeline")
        from primitives.guvn import registered_units
        cm = build_code_map(registered_units())
        self.assertTrue(lint(registered_units())["ok"])
        self.assertIn("geo.records.entity_record_set", cm["multi_path_artifacts"])


if __name__ == "__main__":
    unittest.main()
