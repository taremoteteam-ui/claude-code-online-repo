# Document Extraction Lane Handoff

Last updated: 2026-07-02

Audience: Claude Code, Claude Code Fable, Codex, model lanes, and agents
building the document/contract schema-extraction lane of the Primitive Atlas.

Status: candidate lane handoff. All generated rows are candidate=true /
serves_truth=false. Fixtures are SYNTHETIC. No metric here is measured unless
produced by local scripts and manifests. This lane produces extraction and
evidence outputs for review workflows - it is NOT legal advice and does not
produce final legal conclusions.

## Core thesis

Contract and document extraction is a lattice, not a pile of bespoke
extractors. The reusable structure is:

```text
document_type  x  applicable_field_family  ->  extraction target
```

An employment agreement, a commercial lease, and an oil & gas lease all share
the universal field families (parties, dates, monetary, term/termination,
governing law, signatures) and each adds its specific family
(employment_specific, real_estate_specific + property_description,
oil_gas_specific). The builder crosses each document type ONLY with the
fields whose family that document type declares applicable - a principled
cross product, never a blind cartesian. That is how a few dozen document
types and a few hundred fields materialize into thousands of extraction-target
candidates, and how the lattice extends toward tens of thousands as the field
catalog, format overlays (pdf_native / pdf_scanned / docx / html), and
jurisdiction overlays grow - all recomputed from `manifest.json`, never typed.

## The honesty mechanism: source-span grounding

The lane invariant, enforced by the checker on every extraction target and
every field-emitting primitive:

```text
Every extracted field value carries a source span [start, end] into the
document text, and span_text must equal document_text[start:end] AND contain
the extracted value. An extraction that cannot point to a verifiable span is
a hallucination and fails its proof.
```

This is the DocILE / KILE (Key Information Localization and Extraction) idea:
localize before you extract. `source_span_verification` is a mandatory proof
on every field and every target. The standalone `source_span_verify`
primitive is the guardrail that a batch of extractions can be run through to
catch any ungrounded value.

## Canonical visible edge

```text
Document+DocumentTypeSpec+FieldSchema+ExtractionPolicy
  -> ExtractedFieldSet+SourceSpanBundle+UncertaintyReport
```

Hidden internal route:

```text
Document -> IngestedText+LayoutOffsets
IngestedText -> ClauseSectionSet
ClauseSectionSet+FieldSchema -> LocatedFieldCandidates
LocatedFieldCandidates -> ExtractedValues+SourceSpans
ExtractedValues+NormalizationPolicy -> NormalizedValues+LossinessReceipts
ExtractedValues -> SpanVerificationReceipt (hallucination guard)
NormalizedValues+SpanVerificationReceipt -> ExtractionEvidenceBundle
```

## Working primitives (deterministic, stdlib-only)

Canonical IDs (implemented under `primitives/documents/`):

```text
prim:document_extraction.document_ingest_and_layout   text + line offsets
prim:document_extraction.clause_section_segment       heading-based sectioning
prim:document_extraction.field_locate_and_extract     anchor/value regex + spans
prim:document_extraction.table_line_item_extract      card only (not yet built)
prim:document_extraction.value_normalize              dates/money/pct/duration/party
prim:document_extraction.source_span_verify           hallucination guard
prim:document_extraction.extraction_schema_validate   required + type coherence
prim:document_extraction.extraction_evidence_bundle   span-on-every-field bundle
```

Every field-emitting primitive proves `source_span_verification` /
`no_hallucinated_span`. `field_locate_and_extract` derives value and span
deterministically from anchor + value regexes provided in the field spec -
no model call in the runtime path.

## Field families

```text
universal:   parties, identifiers, dates, monetary, quantities, obligations,
             term_termination, governing_law_jurisdiction, signatures_execution,
             definitions, conditions, representations_warranties,
             indemnification_liability, confidentiality, dispute_resolution
specific:    property_description, real_estate_specific, oil_gas_specific,
             employment_specific, ip_specific, financial_specific,
             insurance_specific
```

## Document types (span all industries)

employment (executive / at-will / union / offer / severance / contractor /
MSA / SOW), real estate (office / retail / ground / residential leases,
purchase & sale, warranty / quitclaim deeds, easement), oil & gas (lease,
mineral deed, JOA, farmout, right-of-way, division order), financial
(loan / credit agreement, promissory note, security agreement, guaranty,
SAFE / convertible note, stock purchase), corporate (bylaws, operating
agreement), IP / tech (assignment, patent / trademark license, SaaS / DPA),
insurance (policy, certificate), government (contract / RFP, purchase order),
supply chain (bill of lading), construction (prime / subcontract, AIA-style).
Exact roster and each type's `applicable_field_families` live in the seed
pack; recompute counts from `manifest.json`.

## Benchmark plan

Five synthetic document families with ground-truth field specs (anchors +
value regexes + expected value + expected normalized form):

```text
employment_agreement, commercial_lease, oil_gas_lease, purchase_and_sale,
mutual_nda
```

The harness (`scripts/run_document_extraction_benchmark.py`) runs the
deterministic extraction route (arm A4) over each fixture and measures, per
document:

```text
field_recall            fields located out of ground truth
source_span_coverage    fraction of located values with a verified span
normalization_accuracy  normalized value matches expected_normalized
runtime_llm_tokens      0 for arm A4 (no model in the runtime path)
depth_to_solution       L-level reached
proof_coverage          passed / total proofs
```

Honesty rules mirror the place-discovery lane: only arms that run get
scorecards; fixture-mode runs measure route machinery, not real-world
extraction accuracy on real contracts; baseline arms A1/A2 (model reads the
whole document and extracts free-form) are not simulated - they require a
model-in-the-loop harness and no source-span-vs-baseline savings claim is
made until they run.

## Hard boundaries

- Extraction / evidence / review outputs only. Never a final legal
  conclusion, legal advice, or an assertion that a clause is enforceable.
- High-stakes families (indemnification / liability, dispute resolution,
  representations / warranties, obligations, conditions) and any hard-difficulty
  field force `human_review_required` on the materialized target.
- Fixtures are synthetic; real-contract extraction requires real source
  snapshots, per-document license/consent review, and PII handling before any
  promotion. Extracted party PII stays in the evidence bundle boundary and is
  never promoted to truth.
- The value is not "read the contract for me and decide." It is: turn a
  document into source-span-grounded, normalized, reviewable fields with an
  uncertainty report.

## Repo pointers

```text
schemas/document_type.schema.json
schemas/extraction_field.schema.json
schemas/extraction_target.schema.json
schemas/document_extraction_primitive.schema.json
scripts/seeds/document_types_seed.py               (edit content here)
scripts/seeds/extraction_field_families_seed.py    (edit content here)
scripts/seeds/extraction_primitives_seed.py        (edit content here)
scripts/build_document_extraction_pack.py          single source for pack files
scripts/check_document_extraction_pack.py --self-test
primitives/documents/                              working extractors
fixtures/document-extraction/                      synthetic fixtures
scripts/run_document_extraction_benchmark.py       measured extraction run
catalog/knowledge-packs/data/document-extraction-seeds/manifest.json
```

## Next build slices

1. `table_line_item_extract` real implementation (invoice / rent schedule /
   division-order tables) with cell-span grounding - the DocILE LIR track.
2. Format ingest adapters: real PDF (native + OCR), DOCX, HTML - each an
   injectable transport like the place-discovery adapters, so the same
   extraction route runs on real formats with `retrieved_mode` disclosed.
3. Jurisdiction and format overlays over the target lattice (materialize hot
   combinations only).
4. Baseline arms A1/A2 for the extraction benchmark - the first measured
   source-span-grounded-vs-free-form comparison.
5. Promotion gate run over the highest-reuse targets (party names, effective
   dates, monetary terms recur across nearly every document type).
