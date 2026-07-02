"""Seed rows: primitive cards for the document-extraction lane.

Pure-data module. One top-level constant EXTRACTION_PRIMITIVES (list of 8
dicts), one card per canonical extraction primitive id. Cards are the compact
contracts validated against schemas/document_extraction_primitive.schema.json.
Rows are candidate seed material; the builder script injects record_type,
version, candidate=True, and serves_truth=False -- this module must not set
them. input_edge/output_edge are compact AaaBbb+Ccc strings. Every card that
emits field values requires source_span_verification. table_line_item_extract
has no working implementation yet and is flagged human_review_required.
"""

EXTRACTION_PRIMITIVES = [
    {
        "primitive_id": "prim:document_extraction.document_ingest_and_layout",
        "kind": "ingest.worker",
        "title": "Document Ingest and Layout",
        "input_edge": "DocumentText+DocumentId",
        "output_edge": "NormalizedText+LayoutOffsets",
        "blackbox": {
            "does": "Ingests raw document text, normalizes line endings, and records a per-line character-offset layout so every later span indexes into a single canonical text. Reports whether any newline normalization changed the byte positions."
        },
        "effects": ["none"],
        "runtime_targets": ["local.python"],
        "proof_requirements": ["schema_validation", "offset_integrity"],
        "known_failure_modes": [
            "scanned PDF exported with hard-wrapped lines splits a clause across many short lines",
            "mixed CRLF and LF newlines shift character offsets if not normalized first",
            "a byte-order mark or non-breaking space at the head of the file offsets every span by one",
        ],
        "telemetry_signals": [
            "ingest.char_count",
            "ingest.line_count",
            "ingest.newline_normalization_changed",
        ],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "primitive_id": "prim:document_extraction.clause_section_segment",
        "kind": "segment.worker",
        "title": "Clause and Section Segmenter",
        "input_edge": "DocumentText+HeadingPatterns",
        "output_edge": "ClauseSections+SegmentReceipt",
        "blackbox": {
            "does": "Splits document text into non-overlapping clause and section spans by detecting headings (all-caps lines, Section N, Article N, numbered N.), so field location can be scoped to the operative clause instead of the whole document."
        },
        "effects": ["none"],
        "runtime_targets": ["local.python"],
        "proof_requirements": [
            "schema_validation", "span_coverage", "heading_span_valid",
        ],
        "known_failure_modes": [
            "a defined term written in all caps mid-paragraph is misread as a section heading",
            "an unnumbered recitals block merges into the first numbered section",
            "an exhibit or schedule uses a different heading style and is left unsegmented",
        ],
        "telemetry_signals": [
            "segment.section_count",
            "segment.heading_hit_count",
            "segment.preamble_present",
        ],
        "risk_class": "medium",
        "human_review_required": False,
    },
    {
        "primitive_id": "prim:document_extraction.field_locate_and_extract",
        "kind": "extract.worker",
        "title": "Field Locate and Extract",
        "input_edge": "DocumentText+FieldSpecs",
        "output_edge": "FieldExtractions+SpanReceipts",
        "blackbox": {
            "does": "Locates each requested field value by anchor regex and emits the value with a source span [start,end] into the document text, proving that document_text[start:end] equals span_text and contains the value. Fields with no verifiable match are reported as unmatched, never guessed."
        },
        "effects": ["none"],
        "runtime_targets": ["local.python"],
        "proof_requirements": [
            "schema_validation",
            "source_span_verification",
            "value_type_validation",
            "cardinality_check",
        ],
        "known_failure_modes": [
            "anchor matches a definition reference instead of the operative value",
            "span points at the right value in the wrong clause",
            "scanned PDF OCR noise breaks the anchor regex so the field goes unmatched",
            "value_pattern window is too short and truncates a multi-token amount or party name",
        ],
        "telemetry_signals": [
            "locate.extraction_count",
            "locate.unmatched_count",
            "locate.span_verification_failures",
        ],
        "risk_class": "high",
        "human_review_required": False,
    },
    {
        "primitive_id": "prim:document_extraction.table_line_item_extract",
        "kind": "extract.worker",
        "title": "Table and Line-Item Extractor",
        "input_edge": "DocumentText+TableSpecs",
        "output_edge": "LineItems+TableReceipt",
        "blackbox": {
            "does": "Extracts rows and cells from tabular blocks (rent schedules, payment schedules, exhibit line items) with a source span per cell. Not yet implemented as a working primitive; this card reserves the contract and routes extractions to human review until a checker-backed implementation lands."
        },
        "effects": ["human_review"],
        "runtime_targets": ["local.python"],
        "proof_requirements": [
            "schema_validation",
            "source_span_verification",
            "row_column_alignment",
        ],
        "known_failure_modes": [
            "not-yet-implemented: no working extractor exists, so every table routes to human review",
            "column boundaries inferred from whitespace collapse when a cell wraps to a second line",
            "a merged header cell misaligns every value in the row beneath it",
        ],
        "telemetry_signals": [
            "table.row_count",
            "table.cell_span_failures",
            "table.human_review_routed",
        ],
        "risk_class": "high",
        "human_review_required": True,
    },
    {
        "primitive_id": "prim:document_extraction.value_normalize",
        "kind": "normalize.worker",
        "title": "Value Normalizer",
        "input_edge": "RawValue+NormalizationRule",
        "output_edge": "NormalizedValue+NormalizeReceipt",
        "blackbox": {
            "does": "Normalizes a raw extracted value by rule (iso_date, currency_decimal, percentage_fraction, duration_iso8601, number_parse, boolean_normalize, party_canonical, none) and returns a receipt disclosing whether the transform was lossy and why. Every transform is idempotent."
        },
        "effects": ["none"],
        "runtime_targets": ["local.python"],
        "proof_requirements": [
            "schema_validation",
            "normalization_roundtrip",
            "value_type_coherent",
        ],
        "known_failure_modes": [
            "ambiguous day-month order in a numeric date is normalized under the wrong convention",
            "an entity suffix like LP is dropped from a party whose legal name genuinely ends in it",
            "a currency amount without a symbol is normalized as USD when the document denominates another currency",
        ],
        "telemetry_signals": [
            "normalize.lossy_rate",
            "normalize.rule_histogram",
            "normalize.roundtrip_failures",
        ],
        "risk_class": "medium",
        "human_review_required": False,
    },
    {
        "primitive_id": "prim:document_extraction.source_span_verify",
        "kind": "verify.worker",
        "title": "Source Span Verifier",
        "input_edge": "DocumentText+Extractions",
        "output_edge": "SpanVerdicts+ViolationSet",
        "blackbox": {
            "does": "The standalone honesty guardrail: re-derives every extraction span against the document text and flags any whose document_text[start:end] does not equal span_text or does not contain the value. The no_hallucinated_span proof fails whenever any violation is present."
        },
        "effects": ["none"],
        "runtime_targets": ["local.python", "api.endpoint"],
        "proof_requirements": ["schema_validation", "no_hallucinated_span"],
        "known_failure_modes": [
            "an extraction verified against a different text revision than the one it was located in",
            "span offsets computed on pre-normalization text no longer align after newline normalization",
            "a whitespace-only span slices back cleanly yet carries no real value",
        ],
        "telemetry_signals": [
            "verify.violation_count",
            "verify.span_coverage_ratio",
            "verify.checked_count",
        ],
        "risk_class": "medium",
        "human_review_required": False,
    },
    {
        "primitive_id": "prim:document_extraction.extraction_schema_validate",
        "kind": "policy.gate",
        "title": "Extraction Schema Validator",
        "input_edge": "Extractions+RequiredFieldRefs",
        "output_edge": "SchemaVerdict+MismatchSet",
        "blackbox": {
            "does": "Policy gate over an extraction set: confirms every required field_ref is present and each extracted value is shape-coherent with its declared value_type, returning the missing-required and type-mismatch sets so downstream steps never bundle an incomplete or mistyped result."
        },
        "effects": ["none"],
        "runtime_targets": ["local.python"],
        "proof_requirements": [
            "schema_validation", "required_coverage", "type_coherence",
        ],
        "known_failure_modes": [
            "a required field is marked present but its value is an empty or whitespace span",
            "value_type shape check is too loose and passes a number where a date was required",
            "required_field_refs drift out of sync with the field catalog after a schema change",
        ],
        "telemetry_signals": [
            "schema.missing_required_count",
            "schema.type_mismatch_count",
            "schema.ok_rate",
        ],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "primitive_id": "prim:document_extraction.extraction_evidence_bundle",
        "kind": "artifact.generator",
        "title": "Extraction Evidence Bundle",
        "input_edge": "DocumentId+Extractions",
        "output_edge": "EvidenceBundle+BundleHash",
        "blackbox": {
            "does": "Assembles verified extractions, source snapshots, and uncertainty notes into a single evidence bundle carrying a stable content hash, retaining the source span on every field so a reviewer can confirm each value is grounded in the document text."
        },
        "effects": ["none"],
        "runtime_targets": ["local.python"],
        "proof_requirements": [
            "source_span_present_on_every_field",
            "uncertainty_report_present",
            "bundle_hash_stable",
        ],
        "known_failure_modes": [
            "an extraction added to the bundle without its source span slips past a reviewer as ungrounded",
            "uncertainty notes are dropped so a low-confidence value looks as trusted as a clean one",
            "bundle hash changes across runs because a non-canonical key ordering leaks into the payload",
        ],
        "telemetry_signals": [
            "bundle.field_count",
            "bundle.uncertainty_note_count",
            "bundle.hash_recompute_stable",
        ],
        "risk_class": "low",
        "human_review_required": False,
    },
]
