# Compiled Primitive AI — the 99% Programmatic Development Handoff

Last updated: 2026-07-02

Audience: Claude Code, Claude Code Fable, Codex, model lanes, and agents
building the Compiled Primitive AI route market.

Status: canonical framing handoff, imported 2026-07-02. External paper and
benchmark numbers are prior-art signals, not local measurements. The seed
bundle it references (1M-row compiled-primitive-AI ZIP) lives in the wider
ecosystem; treat missing local artifacts as future intake slices, not errors.
Precedence per docs/OPERATIONS-BIBLE.md section 12: the bibles win their
domains; this handoff carries the category framing and the coverage claim
language.

## The claim, phrased carefully

The right north-star architecture is Compiled AI for repeated programmatic
development, powered by a primitive database in the millions.

Phrase the claim carefully:

```text
Not "99% of all possible software invention."
Instead:
"99% of common, repeated, programmatic development work can be decomposed into
reusable primitive routes, wrappers, templates, proofs, and deployment
artifacts."
```

That includes app scaffolding, auth, CRUD, ETL, APIs, webhooks, tests, CI/CD,
deployments, observability, data cleaning, file conversion, document
extraction, RAG, browser automation, dashboards, data science pipelines,
guardrails, and common industry workflows. It does not mean every novel
algorithm, product decision, research breakthrough, or ambiguous design
problem becomes deterministic.

## The key upgrade from Compiled AI

Compiled AI proves the pattern:

```text
LLM at compile time
deterministic runtime
mandatory validation
zero or reduced runtime model calls
token amortization
auditability
```

The paper (arXiv:2604.05150) defines compiled AI as one-time LLM invocation,
zero-token deterministic execution, and mandatory multi-stage validation
before deployment. It reports 96% task completion on BFCL, break-even at
about 17 transactions, and 57x token reduction at 1,000 transactions —
prior-art numbers, never presented as local performance.

The generalization:

```text
Compiled AI:
  workflow spec -> generated code artifact -> validation -> deterministic run

Compiled Primitive AI:
  intent -> primitive search -> CandidateBundle -> route/remix/adapters
        -> PlanDelta -> PlanLock -> deterministic execution
        -> proof receipt -> promotion or negative memory
```

Generated code is only one possible compiled output; a compiled primitive
route may also lower into an OpenAPI call plan, MCP tool route, queue worker,
browser-extraction recipe, schema mapping, SQL transformation, guardrail
chain, Terraform plan, Kubernetes job, RAG proof route, or human-review
packet.

The product category is not "LLM-generated code artifacts." It is
**proof-aware compiled capability routes**.

## The six-layer "99% programmatic development" stack

### 1. Leaf primitives

Small deterministic capabilities:

```text
parse_json
validate_schema
normalize_email
hash_file
dedupe_by_key
convert_csv_to_parquet
extract_regex_group
call_openapi_endpoint
verify_webhook_signature
emit_audit_receipt
```

Useful, but not enough alone.

### 2. Primitive molecules

Small chains that appear everywhere:

```text
schema_safe_import:
  parse -> validate -> normalize -> quarantine_bad_rows -> receipt

safe_external_mutation:
  preview -> idempotency_key -> approval_gate -> execute -> audit -> rollback_ref

rag_grounded_answer:
  retrieve -> rerank -> cite -> answer -> support_check -> abstain_if_unsupported

cloud_deploy:
  build -> scan -> plan -> policy_check -> deploy -> healthcheck -> rollback_ref
```

### 3. Primitive groups

Larger reusable capabilities with one visible edge:

```text
RawCustomerCsv+ImportPolicy+CrmTarget -> CrmImportReceipt
PasswordResetRequest+TokenPolicy -> PasswordResetReceipt
RepoSnapshot+IssueDescription+TestHarness -> PatchArtifact+TestReceipt
BusinessDocumentPdf+ExtractionSchema -> StructuredDocumentJson+SourceSpanReceipt
OpenApiSpec+ToolPolicy -> McpServerArtifact+ToolSchemaReceipt
```

The group card is the key compression mechanism: the LLM sees the smallest
useful contract — visible input edge, visible output edge, blackbox behavior,
effects, and proof status — and hidden member edges stay behind drill-down.

### 4. Runtime wrappers

The same primitive group should lower into many execution shapes:

```text
local function · Python package · TypeScript function · REST endpoint ·
GraphQL resolver · MCP tool · CLI command · queue worker · cron job ·
Temporal activity · Airflow task · Dagster asset · dbt model · SQL view ·
browser automation script · Kubernetes job · serverless function ·
Terraform-deployed service · human-review checklist
```

This is how one primitive becomes many deployable products.

### 5. Package/deployment factories

Each route can be packaged:

```text
Docker / OCI image · Terraform module · Pulumi component · AWS CDK construct ·
Azure Bicep module · CloudFormation / SAM app · Helm chart ·
Kubernetes operator · GitHub Action · MCP server · Postman collection ·
Pipedream component · marketplace listing
```

Not just "generate code" — compile, prove, package, deploy, and observe.

### 6. Proof, telemetry, promotion, and negative memory

Every route needs receipts:

```text
contract test receipt · unit test receipt · schema validation receipt ·
security scan receipt · sandbox execution receipt · side-effect audit receipt ·
benchmark scorecard · human-review packet · deployment receipt ·
runtime telemetry · negative-memory record
```

Compile-time validation catches failures before deployment rather than
allowing silent runtime errors.

## Why a million-primitives database makes sense

A million rows should not mean one million hand-authored functions. It should
mean a lattice:

```text
primitive families
x schema standards
x data shapes
x industries
x runtimes
x proof types
x package targets
x failure modes
x implementation strategies
x jurisdiction/localization overlays
```

Example: base family `record_import` x object (customer/invoice/order/payment/
claim/ticket/product) x input shape (CSV/JSON/XML/PDF/API page/webhook/table)
x schema (JSON Schema/OpenAPI/FHIR/XBRL/GS1/Schema.org/custom) x runtime
(local/API/queue/cron/serverless/K8s) x proof (schema validation/fixture/
idempotency/audit/side-effect) — thousands of useful candidates from one
family without becoming random noise.

The registry stores structured objects, not a flat table:

```text
PrimitiveFamily · PrimitiveVariant · PrimitiveGroup · RoutePortfolio ·
RuntimeWrapper · PackageFactory · ProofObligation · BenchmarkTask ·
Scorecard · NegativeMemory · PromotionEvidence
```

## The 20 macro-domains that cover most development

```text
1. App scaffolding and project structure
2. Auth, identity, sessions, MFA, RBAC, ABAC
3. CRUD resources, forms, admin pages, dashboards
4. API endpoints, SDKs, webhooks, MCP tools
5. Database schema, migrations, cleanup, indexing
6. File conversion, media conversion, document parsing
7. Data import, validation, dedupe, export
8. ETL/ELT, data quality, lineage, semantic metrics
9. Search, retrieval, RAG, citations, vector indexes
10. Event-driven systems, queues, workers, cron jobs
11. Testing, fixtures, mocks, contract tests, evals
12. CI/CD, release automation, package publishing
13. Cloud/IaC deployment, Terraform, Helm, K8s, serverless
14. Security, guardrails, privacy, audit, policy-as-code
15. Observability, logs, metrics, traces, incidents
16. ML/data-science pipelines, Kaggle/OpenML-style workflows
17. Browser automation, scraping, website/entity extraction
18. Visualization, reports, charts, media generation
19. Industry workflows: healthcare, finance, insurance, logistics, retail, public sector
20. Meta-primitives: primitive search, route planning, compilation, proof, telemetry, promotion
```

## The compiler pipeline

```text
1. User asks for task.
2. System decomposes request into desired input/output edge.
3. Primitive search returns CandidateBundle.
4. Route planner chooses:
   - exact primitive group
   - near-match + deterministic mutators
   - template-slot fill
   - graph route
   - bounded model PlanDelta
   - source fallback
5. Compiler emits PlanLock.
6. Deterministic workers execute.
7. Proof harness runs.
8. Receipts are stored.
9. Successful route is cached/grouped/promoted.
10. Failed route writes negative memory.
```

## The "99%" route decision rule

For any development task:

```text
Can this be solved by an existing promoted group?
Can it be solved by a candidate group with proof?
Can a near-match be remixed with deterministic mutators?
Can a template be filled?
Can a source-backed API/schema/package generate the missing primitive?
Can a bounded model generate only the missing edge?
Does this require full source reading?
Does this require human review?
```

Most repeated programmatic work should stop before "full source reading."

Depth ladder:

```text
L1 edge card only
L2 contract card
L3 behavior card
L4 hidden route card
L5 proof card
L6 source slice
L7 full source/docs/repo
```

The benchmark claim shape (placeholders until measured):

```text
Primitive-first solved X% of tasks at L1-L3,
Y% at L4-L5,
Z% with source slices,
and only N% required full source/docs/repo.
```

That is a stronger story than "we used fewer tokens."

## Deterministic versus model-assisted

Compiled AI itself acknowledges the split: pure deterministic regex was fast
on DocILE but less accurate for semantic fields; the Code Factory variant
recovered accuracy using bounded LLM calls.

Deterministic whenever possible:

```text
schema validation · field mapping · file conversion · database cleanup ·
API request validation · idempotency keys · audit receipts · policy checks ·
RBAC/ABAC decisions · pagination · retry/backoff · cache lookup ·
data quality checks · unit tests · contract tests · deployment packaging
```

Bounded model use when needed:

```text
ambiguous document field extraction · field alias suggestion ·
task decomposition · route planning over uncertain candidates ·
natural-language-to-schema mapping · source summarization ·
error explanation · human-review packet drafting ·
visual/media interpretation · semantic code repair
```

The crucial rule:

```text
Use models as bounded slots inside compiled routes,
not as the whole runtime brain.
```

## The millions-primitives generation strategy

Do not ask a model to "invent a million primitives" and then trust them.
Use factories:

```text
OpenAPI -> endpoint primitive cards
MCP registry -> tool primitive cards
PyPI/npm -> package API surface cards
Terraform/Helm/CDK -> deployment primitive cards
GitHub Actions -> CI/CD primitive cards
Kaggle/OpenML/MLE-bench -> data-science primitive demands
SWE-bench/Terminal-Bench/AppWorld -> dev-agent primitive demands
DocILE/ParseBench -> document-extraction primitive demands
Schema.org/FHIR/XBRL/GS1 -> schema-specific primitive families
NAICS/public companies/websites -> industry/entity primitive overlays
```

OpenAPI lets humans and computers understand API capabilities without source
code; MCP tool schemas support structured input/output validation. Extract
contracts, ideas, source refs, and implementation opportunities — never
blindly copy code.

## The benchmark plan

Use benchmarks not just to score the system, but to generate primitives:

```text
BenchmarkTask -> TaskPrimitiveDemand -> CandidateBundle -> BaselineRun
-> PrimitiveFirstRun -> Scorecard -> PromotionEvidence or NegativeMemory
```

Paired comparisons: same task, fixtures, source refs, side-effect sandbox,
and scorecard fields; vary the route-generation/search/planning/compiler/
proof path.

Comparison arms:

```text
A1 baseline runtime agent
A2 baseline agent with search/RAG
A3 compiled-code/template generation
A4 primitive-first CandidateBundle + deterministic remix
A5 primitive-first CandidateBundle + PlanDelta
A6 source fallback + bounded micro-repair
A7 human-reviewed route for high-risk domains
```

Metrics:

```text
task_success · tokens_to_plan · tokens_to_pass · runtime_llm_tokens ·
source_context_tokens · source_files_read · depth_to_solution ·
compile_success · proof_success · route_reuse · new_group_created ·
negative_memory_created · cost_per_success · break_even_executions
```

## What the first real product should do

Not implement all million primitives. Implement the route market engine:

```text
primitive registry
CandidateBundle search
route portfolio planner
deterministic mutator engine
PlanLock compiler
proof harness
receipt ledger
negative memory
benchmark runner
deployment/package factories
```

The million-row database is fuel. The route market is the engine.

## The practical "99% coverage" roadmap

```text
Phase 1: common software structures (auth, CRUD, forms, migrations, upload,
         notifications, webhooks, queues, cron, CI/CD, observability, deploy)
Phase 2: data and document primitives (conversion, schema inference, cleaning,
         dedupe, outliers, invoice/contract/table extraction, RAG citation proof)
Phase 3: API/tool ecosystems (OpenAPI, AsyncAPI, GraphQL, gRPC, MCP, Postman,
         Pipedream/n8n/Zapier/Make)
Phase 4: cloud/deployment packaging (Docker, Terraform, Helm, K8s, serverless,
         CDK/Pulumi/Bicep, GitHub Actions, marketplace skeletons)
Phase 5: benchmark-driven expansion (BFCL, DocILE, SWE-bench, Terminal-Bench,
         AppWorld, Kaggle Benchmarks, MLE-bench, OpenML, BigCodeBench, WebArena)
Phase 6: local/geography/industry overlays (NAICS, jurisdictions, tax/payment/
         invoice standards, FHIR, XBRL/ISO 20022, GS1, ACORD, procurement)
Phase 7: self-improvement (telemetry, co-occurrence mining, cache warming,
         route sprouting, ranker/LoRA specialization, champion/challenger,
         promotion/retirement)
```

## The strongest internal design principle

```text
Generate only the missing edge.
Reuse everything else.
```

When a user asks for something, avoid: read whole repo · read whole package
docs · ask model to write whole solution · run agent loop until it stumbles
into success.

Instead: find existing primitive/group · find near-match · adapt with
deterministic mutators · compile PlanLock · run proof · fallback only where
the registry has a real gap.

## Bottom line

Compiled AI gives the proof-of-pattern: compile once, validate hard, run
deterministically, amortize tokens.

This system is the broader version:

```text
search once
compose from primitives
compile route
execute deterministically
prove with receipts
cache and promote
remember failures
deploy anywhere
```

Every common software task becomes reducible to:

```text
InputEdge + Policy
  -> PrimitiveRoute
  -> PlanLock
  -> OutputArtifact + ProofReceipt
```

That is the category: **Compiled Primitive AI — a proof-aware primitive route
market for software development.**

## Local status pointer

This repo's measured contribution to the claim lives in
`docs/OPERATIONS-BIBLE.md` Appendix A (dated local snapshot; recompute via
`scripts/run_proofs.py` and `scripts/check_benchmark_run.py --self-test`).
The depth-ladder claim shape is implemented in the local harness: arm A4
scorecards record `depth_to_solution` per task, and the run checker enforces
that no unrun arm gets a scorecard. Baseline arms A1/A2 have not run; no
token-savings percentage exists for this lane yet.
