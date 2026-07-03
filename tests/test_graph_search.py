"""Contract tests for the universal capability-graph search index."""

import unittest

from primitives.graph_search import GraphSearchIndex

NODES = [
    {"node_id": "prim:swe.generate_patch", "title": "Generate Patch", "lane": "coding_agent",
     "kind": "reusable_primitive_family", "input_edge": "CodeSlice",
     "output_edge": "PatchDraft",
     "required_input_ports": [{"name": "CodeSlice", "canonical_type": "CodeSlice"}],
     "output_ports": [{"name": "PatchDraft", "role": "data", "canonical_type": "PatchDraft"}]},
    {"node_id": "prim:geo.dedupe", "title": "Deduplicate Facilities", "lane": "geospatial",
     "kind": "reusable_primitive_family", "input_edge": "EntityRecordSet",
     "output_edge": "DedupedRecordSet",
     "required_input_ports": [{"name": "EntityRecordSet", "canonical_type": "EntityRecordSet"}],
     "output_ports": [{"name": "DedupedRecordSet", "role": "data", "canonical_type": "DedupedRecordSet"}]},
    {"node_id": "prim:other.noise", "title": "Something Unrelated", "lane": "misc",
     "kind": "reusable_primitive_family", "input_edge": "Foo", "output_edge": "Bar",
     "required_input_ports": [{"name": "Foo", "canonical_type": "Foo"}],
     "output_ports": [{"name": "Bar", "role": "data", "canonical_type": "Bar"}]},
]


class GraphSearchTests(unittest.TestCase):
    def setUp(self):
        self.index = GraphSearchIndex(nodes=NODES)

    def test_covers_all_nodes(self):
        self.assertEqual(self.index.coverage(), 3)

    def test_lexical_finds_cross_lane_target(self):
        hits = self.index.search("generate a patch for the code", top_k=2)
        self.assertEqual(hits[0]["node_id"], "prim:swe.generate_patch")

    def test_typed_plane_boosts_producer_of_wanted_type(self):
        hits = self.index.search("deduplicate", want="DedupedRecordSet", top_k=3)
        top = hits[0]
        self.assertEqual(top["node_id"], "prim:geo.dedupe")
        self.assertIn("produces_want", top["planes"])

    def test_blocking_index_built(self):
        self.assertIn("PatchDraft", self.index.producers_by_type)
        self.assertIn("prim:swe.generate_patch", self.index.producers_by_type["PatchDraft"])
        self.assertIn("EntityRecordSet", self.index.consumers_by_type)

    def test_no_match_returns_empty(self):
        self.assertEqual(self.index.search("zzzquux nonsense", top_k=5), [])


if __name__ == "__main__":
    unittest.main()
