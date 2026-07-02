# Universal Primitive Catalog Handoff

Last updated: 2026-07-02

Audience: Claude Code, Claude Code Fable, Codex, and agents growing the
reusable-primitive bank.

Status: candidate catalog lane. All rows are candidate=true /
serves_truth=false. These are CAPABILITY CONTRACTS, not implemented code -
each is a reusable-primitive family or a runtime-shaped resolved variant, with
a first-class problem-solution block. Nothing here is promoted; promotion
requires source refs, contract checks, effect declaration, proof receipts, and
fixture/benchmark evidence (operating manual section 12).

## What this lane is

The recurring building blocks of programmatic development, published as a
searchable candidate bank. It answers "generate thousands of reusable
primitives" without row-count padding: a base family is a genuinely distinct
capability, and each family is materialized into the runtime shapes it
actually supports.

```text
reusable_primitive_family  x  applicable_runtime_wrapper  ->  resolved_primitive
```

The same capability as a Python function, a FastAPI endpoint, an MCP tool, a
queue worker, or a Kubernetes job is genuinely different - different effects,
different proof obligations, different failure modes (operating manual section
8). So the multiplication is meaningful, not cosmetic. The builder crosses each
family with ONLY the wrappers it declares applicable (a password-reset flow
lowers to FastAPI/MCP/function/queue, never to a browser worker), so the
lattice stays principled.

## Domains covered

```text
auth_identity · security · crud_data_app · trackers · data_engineering ·
format_conversion · data_quality · integration_async · api_surface ·
messaging · devops_deploy · observability · guardrails_safety ·
entity_resolution · enrichment_verification · document_intelligence ·
rag_retrieval · geospatial · similarity_indexing
```

## The record shapes

Base family (`schemas/reusable_primitive_family.schema.json`): compact contract
(input_edge, output_edge, blackbox, effects, base_runtime_targets, proof
requirements) PLUS a mandatory `problem_solution` block - problem,
naive_agent_failure, solution, core_components, common_inputs, common_outputs,
known_pitfalls, success_signals. Problem-solution is first-class, not optional
prose (operating manual section 4): a primitive states which repeated problem
it solves and which naive-agent failure it prevents.

Runtime wrapper (`schemas/runtime_wrapper.schema.json`): lowers a core edge
into one execution shape, adding its own policy edge, effects, and proof
obligations. The 10-wrapper bank is `scripts/seeds/runtime_wrappers_seed.py`.

Resolved primitive (`schemas/resolved_primitive.schema.json`): a materialized
(family x wrapper) row with composed edges, unioned effects, unioned proof
obligations, and a back-reference to the family's problem-solution.

## Invariants the checker enforces

```text
- every row validates against its JSON schema
- manifest counts + content hashes match disk (hand-edit gate)
- referential integrity: family wrappers exist; resolved rows reference a real
  family + wrapper; resolved runtime_target matches its wrapper
- effect/proof UNION coherence: a resolved primitive's effects and proofs cover
  its family's AND its wrapper's declarations (no dropped side effect or proof)
- problem-solution completeness on every family
- candidate/serves_truth boundary; no unmeasured-claim language; unique ids
```

## Repo pointers

```text
schemas/reusable_primitive_family.schema.json
schemas/runtime_wrapper.schema.json
schemas/resolved_primitive.schema.json
scripts/seeds/runtime_wrappers_seed.py                (wrapper bank)
scripts/seeds/universal_families_*_seed.py            (6 domain modules, FAMILIES const each)
scripts/build_universal_primitive_pack.py             single source for pack files
scripts/check_universal_primitive_pack.py --self-test
catalog/knowledge-packs/data/universal-primitive-catalog/manifest.json   (recompute counts here)
```

## Next build slices

1. `primitives/search.py` already indexes place-discovery cards; extend the
   index to this catalog so a CandidateBundle can span lanes (operating manual
   section 10).
2. Deterministic mutators (`primitives/mutators.py`) are the remix layer for
   resolved primitives - wire a `contract_diff_remix` that adapts a near-match
   resolved primitive to a requested edge.
3. Promote a first family from candidate to implemented: pick a high-reuse,
   low-risk family (e.g. a format-conversion primitive), implement it under
   `primitives/`, attach fixtures, and run it through the promotion gate
   (L0->L10). The catalog is the demand map; implementation is the wedge.
4. Source-adapter extraction (operating manual section 21): mine OpenAPI / MCP
   / package registries to turn real contracts into families automatically,
   instead of hand-authoring.
