"""Contract tests for the working document-extraction primitives.

Run from the repo root:
    python3 -m unittest tests.test_document_extraction -v

The load-bearing property under test is source-span grounding: every extracted
value must carry a span [start, end] such that document_text[start:end] equals
span_text and contains the value. A deliberate hallucination case proves the
guardrail fails when that property is violated.

All document text here is SYNTHETIC (clearly fictional parties, addresses, and
amounts). Nothing asserts real-world contract content.
"""

from __future__ import annotations

import unittest

from primitives.core import run_primitive
from primitives.documents.bundle import extraction_evidence_bundle
from primitives.documents.extract import (
    clause_section_segment,
    document_ingest_and_layout,
    field_locate_and_extract,
)
from primitives.documents.normalize import normalize_value, value_normalize
from primitives.documents.verify import (
    extraction_schema_validate,
    source_span_verify,
)

# A small synthetic contract snippet (clearly fictional).
SNIPPET = (
    "EMPLOYMENT AGREEMENT\n"
    "\n"
    "This Employment Agreement is made effective as of January 1, 2026, "
    "by and between Northwind Robotics, LLC (the Employer) and Dana "
    "Fictional (the Employee).\n"
    "\n"
    "1. COMPENSATION\n"
    "\n"
    "The Employer shall pay the Employee a base salary of $120,000.00 per "
    "year.\n"
    "\n"
    "2. TERM\n"
    "\n"
    "The term shall be for a period of two (2) years.\n"
)


def proofs(outcome) -> dict:
    return {p.proof: p for p in outcome.proof_results}


class TestDocumentIngestAndLayout(unittest.TestCase):
    def test_offset_integrity_slices_back_to_each_line(self):
        text = "Alpha line\r\nBeta line\rGamma line\n"
        oc = document_ingest_and_layout(
            {"document_text": text, "document_id": "doc:ingest01"}
        )
        out = oc.output
        norm = out["normalized_text"]
        # Newlines were normalized to LF and the change was recorded.
        self.assertNotIn("\r", norm)
        self.assertTrue(out["newline_normalization"]["changed"])
        self.assertEqual(out["newline_normalization"]["crlf_to_lf"], 1)
        self.assertEqual(out["newline_normalization"]["cr_to_lf"], 1)
        # Every recorded line offset slices back to exactly that line.
        lines = norm.split("\n")
        for i, (start, end) in enumerate(out["layout_offsets"]["lines"]):
            self.assertEqual(norm[start:end], lines[i])
        self.assertTrue(proofs(oc)["offset_integrity"].passed)
        self.assertEqual(out["char_count"], len(norm))

    def test_missing_document_id_raises(self):
        with self.assertRaises(ValueError):
            document_ingest_and_layout({"document_text": "x", "document_id": ""})


class TestClauseSectionSegment(unittest.TestCase):
    def test_segments_synthetic_contract(self):
        oc = clause_section_segment({"document_text": SNIPPET})
        pr = proofs(oc)
        self.assertTrue(pr["span_coverage"].passed)
        self.assertTrue(pr["heading_span_valid"].passed)
        sections = oc.output["sections"]
        headings = [s["heading"] for s in sections]
        self.assertIn("EMPLOYMENT AGREEMENT", headings)
        self.assertIn("1. COMPENSATION", headings)
        self.assertIn("2. TERM", headings)
        # Sections are contiguous, non-overlapping, and within bounds.
        prev_end = 0
        for s in sections:
            start, end = s["span"]
            self.assertLessEqual(prev_end, start)
            self.assertLess(start, end)
            self.assertLessEqual(end, len(SNIPPET))
            # The heading text really occurs inside its own span.
            self.assertIn(s["heading"], SNIPPET[start:end])
            prev_end = end

    def test_custom_heading_patterns(self):
        text = "Preamble.\n>>ALPHA\nbody a\n>>BETA\nbody b\n"
        oc = clause_section_segment(
            {"document_text": text, "heading_patterns": [r"^>>"]}
        )
        headings = [s["heading"] for s in oc.output["sections"]]
        self.assertIn(">>ALPHA", headings)
        self.assertIn(">>BETA", headings)


class TestFieldLocateAndExtract(unittest.TestCase):
    def build_specs(self):
        return [
            {
                "field_ref": "field:parties.employer_legal_name",
                "value_type": "party_entity",
                "cardinality": "one",
                "anchors": [r"between\s+([A-Z][A-Za-z0-9 ,.&]+?LLC)"],
                "value_pattern": None,
                "normalization": "party_canonical",
            },
            {
                "field_ref": "field:dates.effective_date",
                "value_type": "date",
                "cardinality": "one",
                "anchors": [r"effective as of"],
                "value_pattern": r"([A-Z][a-z]+ \d{1,2}, \d{4})",
                "normalization": "iso_date",
            },
            {
                "field_ref": "field:monetary.base_salary_amount",
                "value_type": "money_amount",
                "cardinality": "one",
                "anchors": [r"base salary of"],
                "value_pattern": r"(\$[\d,]+\.\d{2})",
                "normalization": "currency_decimal",
            },
        ]

    def test_extracts_party_date_amount_with_verified_spans(self):
        oc = field_locate_and_extract(
            {"document_text": SNIPPET, "field_specs": self.build_specs()}
        )
        pr = proofs(oc)
        self.assertTrue(pr["source_span_verification"].passed)
        self.assertTrue(pr["value_type_validation"].passed)
        self.assertTrue(pr["cardinality_check"].passed)
        self.assertEqual(oc.output["unmatched"], [])

        by_ref = {e["field_ref"]: e for e in oc.output["extractions"]}
        self.assertEqual(set(by_ref), {
            "field:parties.employer_legal_name",
            "field:dates.effective_date",
            "field:monetary.base_salary_amount",
        })
        # THE honesty invariant, asserted directly for every extraction.
        for e in oc.output["extractions"]:
            start, end = e["source_span"]
            self.assertEqual(SNIPPET[start:end], e["span_text"])
            self.assertIn(e["value"], e["span_text"])

        self.assertEqual(
            by_ref["field:parties.employer_legal_name"]["value"],
            "Northwind Robotics, LLC",
        )
        self.assertEqual(
            by_ref["field:parties.employer_legal_name"]["normalized_value"],
            "NORTHWIND ROBOTICS",
        )
        self.assertEqual(
            by_ref["field:dates.effective_date"]["value"], "January 1, 2026",
        )
        self.assertEqual(
            by_ref["field:dates.effective_date"]["normalized_value"],
            "2026-01-01",
        )
        self.assertEqual(
            by_ref["field:monetary.base_salary_amount"]["value"],
            "$120,000.00",
        )
        self.assertEqual(
            by_ref["field:monetary.base_salary_amount"]["normalized_value"],
            "120000.00",
        )

    def test_clean_receipt_through_core_runner(self):
        output, receipt = run_primitive(
            "prim:document_extraction.field_locate_and_extract",
            field_locate_and_extract,
            {"document_text": SNIPPET, "field_specs": self.build_specs()},
            run_id="test:document_extraction",
            declared_effects=["none"],
        )
        self.assertIsNone(receipt["error"])
        self.assertTrue(receipt["candidate"])
        self.assertFalse(receipt["serves_truth"])
        self.assertEqual(receipt["effects_observed"], ["none"])
        self.assertEqual(len(output["extractions"]), 3)
        self.assertEqual(
            {p["proof"] for p in receipt["proof_results"]},
            {
                "schema_validation",
                "source_span_verification",
                "value_type_validation",
                "cardinality_check",
            },
        )

    def test_unmatched_optional_field_is_reported_not_guessed(self):
        specs = [{
            "field_ref": "field:identifiers.contract_number",
            "value_type": "identifier",
            "cardinality": "zero_or_one",
            "anchors": [r"Contract\s+No\.\s*([A-Z0-9-]+)"],
            "value_pattern": None,
            "normalization": "none",
        }]
        oc = field_locate_and_extract(
            {"document_text": SNIPPET, "field_specs": specs}
        )
        self.assertEqual(oc.output["extractions"], [])
        self.assertEqual(
            oc.output["unmatched"], ["field:identifiers.contract_number"]
        )
        # Optional cardinality: an unmatched field is not a cardinality error.
        self.assertTrue(proofs(oc)["cardinality_check"].passed)


class TestSourceSpanVerifyGuardrail(unittest.TestCase):
    def test_clean_extractions_have_no_violation(self):
        # first three chars of SNIPPET are "EMP"
        clean = [{"value": "EMP", "source_span": [0, 3], "span_text": "EMP"}]
        oc = source_span_verify(
            {"document_text": SNIPPET, "extractions": clean}
        )
        self.assertEqual(oc.output["violations"], [])
        self.assertTrue(proofs(oc)["no_hallucinated_span"].passed)
        self.assertEqual(oc.output["span_coverage_ratio"], 1.0)

    def test_deliberate_hallucination_fails_proof(self):
        # span_text claims "GHOST" but document_text[0:5] is "EMPLO".
        hallucination = [
            {"value": "GHOST CORP", "source_span": [0, 5], "span_text": "GHOST"}
        ]
        oc = source_span_verify(
            {"document_text": SNIPPET, "extractions": hallucination}
        )
        self.assertEqual(len(oc.output["violations"]), 1)
        self.assertEqual(oc.output["violations"][0]["index"], 0)
        pr = proofs(oc)
        self.assertFalse(pr["no_hallucinated_span"].passed)
        # And the guardrail refuses to run clean through the core runner.
        with self.assertRaises(Exception):
            run_primitive(
                "prim:document_extraction.source_span_verify",
                source_span_verify,
                {"document_text": SNIPPET, "extractions": hallucination},
                run_id="test:hallucination",
                declared_effects=["none"],
            )

    def test_value_not_in_span_is_a_violation(self):
        # span slices back correctly but the claimed value is not inside it.
        bad = [{"value": "Zeta", "source_span": [0, 3], "span_text": "EMP"}]
        oc = source_span_verify({"document_text": SNIPPET, "extractions": bad})
        self.assertEqual(len(oc.output["violations"]), 1)
        self.assertIn("value_not_in_span_text",
                      oc.output["violations"][0]["reason"])


class TestExtractionSchemaValidate(unittest.TestCase):
    def test_missing_required_and_type_mismatch(self):
        extractions = [
            {"field_ref": "field:dates.effective_date", "value": "not a date"},
        ]
        oc = extraction_schema_validate({
            "extractions": extractions,
            "required_field_refs": [
                "field:dates.effective_date",
                "field:monetary.purchase_price",
            ],
            "field_types": {"field_ref_ignored": "date",
                            "field:dates.effective_date": "date"},
        })
        self.assertIn("field:monetary.purchase_price",
                      oc.output["missing_required"])
        self.assertEqual(len(oc.output["type_mismatches"]), 1)
        self.assertFalse(oc.output["ok"])
        self.assertFalse(proofs(oc)["required_coverage"].passed)
        self.assertFalse(proofs(oc)["type_coherence"].passed)

    def test_all_present_and_coherent_ok(self):
        extractions = [
            {"field_ref": "field:dates.effective_date",
             "value": "January 1, 2026"},
        ]
        oc = extraction_schema_validate({
            "extractions": extractions,
            "required_field_refs": ["field:dates.effective_date"],
            "field_types": {"field:dates.effective_date": "date"},
        })
        self.assertTrue(oc.output["ok"])
        self.assertTrue(proofs(oc)["required_coverage"].passed)
        self.assertTrue(proofs(oc)["type_coherence"].passed)


class TestValueNormalize(unittest.TestCase):
    def test_iso_date_formats(self):
        for raw in ("January 1, 2026", "01/01/2026", "2026-01-01"):
            nv, _ = normalize_value(raw, "iso_date", "date")
            self.assertEqual(nv, "2026-01-01")

    def test_currency_percentage_duration(self):
        self.assertEqual(
            normalize_value("$1,250.00", "currency_decimal", "money_amount")[0],
            "1250.00",
        )
        self.assertEqual(
            normalize_value("12.5%", "percentage_fraction", "percentage")[0],
            "0.125",
        )
        self.assertEqual(
            normalize_value("thirty (30) days", "duration_iso8601",
                            "duration")[0],
            "P30D",
        )
        self.assertEqual(
            normalize_value("2 years", "duration_iso8601", "duration")[0],
            "P2Y",
        )

    def test_lossy_disclosure_and_receipt(self):
        oc = value_normalize({
            "raw_value": "Acme Widgets, LLC",
            "normalization": "party_canonical",
            "value_type": "party_entity",
        })
        out = oc.output
        self.assertEqual(out["normalized_value"], "ACME WIDGETS")
        self.assertTrue(out["lossy"])
        self.assertTrue(out["receipt"]["reason"])  # a reason is disclosed
        self.assertEqual(out["receipt"]["suffix"], "LLC")
        pr = proofs(oc)
        self.assertTrue(pr["normalization_roundtrip"].passed)
        self.assertTrue(pr["value_type_coherent"].passed)

    def test_non_lossy_passthrough_of_canonical_input(self):
        oc = value_normalize({
            "raw_value": "2026-01-01",
            "normalization": "iso_date",
            "value_type": "date",
        })
        self.assertFalse(oc.output["lossy"])

    def test_unknown_normalization_rejected(self):
        with self.assertRaises(ValueError):
            value_normalize({
                "raw_value": "x", "normalization": "no_such_rule",
                "value_type": "none",
            })


class TestEvidenceBundle(unittest.TestCase):
    def build_extractions(self):
        oc = field_locate_and_extract({
            "document_text": SNIPPET,
            "field_specs": [{
                "field_ref": "field:dates.effective_date",
                "value_type": "date",
                "cardinality": "one",
                "anchors": [r"effective as of"],
                "value_pattern": r"([A-Z][a-z]+ \d{1,2}, \d{4})",
                "normalization": "iso_date",
            }],
        })
        return oc.output["extractions"]

    def test_span_on_every_field_and_stable_hash(self):
        oc = extraction_evidence_bundle({
            "document_id": "doc:emp_synth_01",
            "extractions": self.build_extractions(),
            "source_snapshots": ["snap:employment_agreement_synth_01"],
            "uncertainty_notes": ["effective date parsed under US convention"],
        })
        pr = proofs(oc)
        self.assertTrue(pr["source_span_present_on_every_field"].passed)
        self.assertTrue(pr["uncertainty_report_present"].passed)
        self.assertTrue(pr["bundle_hash_stable"].passed)
        bundle = oc.output["evidence_bundle"]
        self.assertTrue(bundle["bundle_hash"].startswith("sha256:"))
        for f in bundle["fields"]:
            self.assertIsInstance(f["source_span"], list)
            self.assertEqual(len(f["source_span"]), 2)
            self.assertTrue(f["span_text"])
        # Re-bundling identical inputs yields an identical hash.
        oc2 = extraction_evidence_bundle({
            "document_id": "doc:emp_synth_01",
            "extractions": self.build_extractions(),
            "source_snapshots": ["snap:employment_agreement_synth_01"],
            "uncertainty_notes": ["effective date parsed under US convention"],
        })
        self.assertEqual(
            bundle["bundle_hash"],
            oc2.output["evidence_bundle"]["bundle_hash"],
        )

    def test_field_missing_span_fails_proof(self):
        oc = extraction_evidence_bundle({
            "document_id": "doc:emp_synth_01",
            "extractions": [{"field_ref": "field:x", "value": "v",
                             "normalized_value": "v"}],
            "source_snapshots": [],
            "uncertainty_notes": [],
        })
        self.assertFalse(
            proofs(oc)["source_span_present_on_every_field"].passed
        )


if __name__ == "__main__":
    unittest.main()
