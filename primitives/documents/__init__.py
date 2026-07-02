"""Working document-extraction primitives (source-span-grounded).

Every primitive here is a deterministic, stdlib-only worker behind a primitive
card in the document-extraction pack. The lane's honesty mechanism runs through
these modules: an extracted field value is only trusted when it carries a source
span [start, end] such that ``document_text[start:end] == span_text`` and the
value is contained in that span. Extractions that cannot prove their span are
hallucinations and fail the ``source_span_verification`` /
``no_hallucinated_span`` proofs.

Modules:

- ``extract``   -- document_ingest_and_layout, clause_section_segment,
                   field_locate_and_extract
- ``normalize`` -- value_normalize (and the shared ``normalize_value`` helper)
- ``verify``    -- source_span_verify, extraction_schema_validate
- ``bundle``    -- extraction_evidence_bundle

Implementations stay candidate=true / serves_truth=false. Every execution goes
through ``primitives/core.py`` and emits an ExecutionReceipt.
"""
