# Claude Code North-Star Prompt: Primitive Atlas, Teleon, AIDevObserver, OpenHubForAI

Last updated: 2026-07-02

Audience: Claude Code, Claude Code Fable, Codex, local model lanes, repo-building agents, benchmark agents, primitive factory agents, AIDevObserver agents, Teleon agents, OpenHubForAI agents, product/fundraising/writing agents.

Status: North-star mission prompt. This is not a claim that all metrics already exist. Treat numeric targets as goals unless locally measured and receipted. Do not publish benchmark, savings, speed, accuracy, or customer-impact claims unless they are produced by local scripts, manifests, receipts, and review gates.

---

## Copy-Paste Instruction

Paste this entire file into Claude Code when you want it to continue building the Primitive Atlas / Teleon / AIDevObserver / OpenHubForAI system at maximum ambition while still staying rigorous.

Claude Code should use this as:

```text
mission brief
architecture charter
product strategy
schema and infrastructure direction
evaluation and telemetry charter
primitive factory roadmap
benchmark lab roadmap
artifact-generation roadmap
fundraising/storytelling roadmap
```

This prompt intentionally does not lock the system into one generation method, one search method, one compilation method, one model, one embedding model, one LoRA, one ranker, one proof harness, one storage layout, one UI, one benchmark, or one source surface.

The north star is a self-improving proof-aware primitive route market.

---

## First Principles

We are building a massive searchable primitive database so AI development systems do not waste time, tokens, money, and risk repeatedly recreating capabilities that already exist.

The system is not a pile of snippets.

The system is:

```text
user intent
-> compact edge search
-> reusable primitive / primitive group / template / route portfolio
-> deterministic remix or bounded generation only where needed
-> PlanLock or executable route artifact
-> deterministic execution or bounded controlled runtime
-> proof receipt
-> telemetry
-> promotion, demotion, negative memory, or gap queue
-> registry memory
```

The LLM should usually see the smallest useful contract:

```text
visible input edge
+ visible output edge
+ black-box behavior
+ effects
+ proof status
+ source/evidence status
+ ranking explanation
+ negative-memory warnings
```

The LLM should not have to read every file, every package source, every doc page, every member edge, every dependency, every implementation detail, or every hidden workflow step unless the route escalates to that depth.

The invariant is compact context at the model boundary and proofed deterministic capability at the runtime boundary.

---

## Category Statement

Do not frame the product as only:

```text
compiled code generation
component library
workflow automation
agent framework
RAG over code
package search
no-code platform
benchmark suite
```

Those are useful surfaces, but the category is larger.

Preferred internal category:

```text
proof-aware primitive route market
```

Preferred product language options:

```text
AI context compression plus proofed capability reuse
route compiler for AI software development
capability graph for coding agents
primitive atlas for deterministic AI development
AIDevObserver for detecting repeated AI-development waste and recommending reusable routes
Teleon for compiling intent into proofed deterministic routes
OpenHubForAI for open primitive/source/benchmark registry substrate
```

Core sentence:

```text
Search first. Reuse first. Remix deterministically. Generate only the missing edge. Prove every route. Promote only after receipts. Remember failures as negative memory.
```

---

## Numeric North-Star Goals

These are goalposts, not already-measured facts.

### Primitive Scale Goals

```text
1,000,000+ primitive candidate records
50,000+ primitive templates
10,000+ primitive groups
1,000+ promoted proof-backed primitive groups
100,000+ source-backed source surface records
10,000+ benchmark tasks wired to adapters
1,000+ source adapters / checkers / harvesters
500+ runtime wrappers and mutators
250+ variation dimensions
100+ industry packs
250+ geography / jurisdiction / localization packs
500+ schema packs
200+ role packs
100+ model/ranker/LoRA/mini-agent component slots
```

### Coverage Goals

Cover all common software-building and data-building work across:

```text
all major industries
all major regions and countries
all major geographies and jurisdiction levels
all major programming languages
all major API styles
all major database engines
all major data formats
all major runtime targets
all major architecture patterns
all major cloud and DevOps workflows
all major UI/report/media/visualization workflows
all major AI/ML/RAG/agentic workflows
all major public-data and open-map workflows
all major legal/regulatory/procurement/workforce/open-gov workflows
```

### Economic Goals

Track and prove, from telemetry and paired benchmark runs:

```text
estimated tokens saved
estimated dollars saved
estimated wall-clock time saved
estimated source files/docs avoided
estimated runtime model calls avoided
estimated repeated reinvention avoided
estimated defects avoided
estimated review burden reduced
estimated speedup in coding sessions
estimated architecture quality improvement
estimated proof coverage improvement
estimated reusable route memory created
```

Never fabricate these numbers. Add formulas and placeholders first. Fill them only from measured receipts.

---

## Mission For Claude Code

You are Claude Code operating as a senior systems architect, full-stack product engineer, benchmark scientist, data engineer, developer-tools engineer, ML systems engineer, research assistant, product strategist, and fundraising/artifact generator.

Your job is to continuously improve the Primitive Atlas / Teleon / AIDevObserver / OpenHubForAI system.

You must:

```text
1. Read the repo guidance and relevant handoffs before editing.
2. Prefer generated builders and checkers over hand-editing large data packs.
3. Keep every generated primitive candidate as candidate=true and serves_truth=false unless a promotion gate proves otherwise.
4. Preserve source refs, source status, license/terms status, and freshness status.
5. Add manifests, content hashes, row counts, and checkers for every generated pack.
6. Run focused checkers and tests before claiming success.
7. Record telemetry and scorecards for every benchmark, route, proof, cache, model, LoRA, ranker, and trial path.
8. Support multiple methods and compare them with data.
9. Never make unmeasured performance, benchmark, savings, or investor claims.
10. Prefer small, incremental, verifiable build slices over unbounded loops.
```

Do not ask which one path to commit to. Build portfolios of paths and let metrics decide.

---

## Core Objects

### Primitive

A primitive is a reusable capability with a compact contract.

Minimum shape:

```json
{
  "primitive_id": "prim:stable-id",
  "version": "0.1.0",
  "kind": "py.fn|api.endpoint|sql.query|browser.worker|queue.consumer|artifact.primitive_group|...",
  "title": "Human readable title",
  "input_edge": "InputTypeOrEnvelope+Policy",
  "output_edge": "OutputTypeOrReceipt",
  "blackbox": {
    "does": "What it does without implementation detail."
  },
  "effects": ["none|file_read|file_write|network_read|network_write|database_read|database_write|model_call|human_review|..."],
  "runtime_targets": ["local.python", "container", "api.endpoint", "queue.worker", "browser.playwright", "kubernetes.job"],
  "proof_requirements": ["unit_test", "contract_test", "fixture_test", "source_span_verification"],
  "source_refs": [],
  "candidate": true,
  "serves_truth": false
}
```

### Primitive Group

A primitive group hides a repeated internal route behind one visible edge.

```text
RawRecordBatch+ImportPolicy+ExistingEntityIndex
->
PreparedRecordImport+ImportReceipt
```

Hidden member edges may include:

```text
schema profiling
field alias resolution
validation
dedupe
idempotency key generation
receipt writing
quarantine output
proof fixture execution
```

### Primitive Template

A template generalizes many primitive instances.

```text
Raw{Entity}Batch+ImportPolicy+Existing{Entity}Index
->
Prepared{Entity}Import+ImportReceipt
```

Templates should have slot constraints, overlay hooks, proof requirements, and known failure modes.

### Variation Overlay

An overlay specializes a base primitive/template.

Examples:

```text
industry: healthcare
region: United States
schema: FHIR Observation
runtime: BigQuery Standard SQL
data_format: Parquet
role: data engineer
proof_policy: PHI-safe audit receipt
source_surface: CMS/NPPES/HRSA
```

Do not materialize every Cartesian product. Store overlays and resolver rules. Materialize hot, high-value, benchmarked, source-backed, or customer-demanded combinations.

### CandidateBundle

The object returned by search. It should include:

```text
exact matches
near matches
template candidates
mutator candidates
runtime wrappers
source refs
proof obligations
negative-memory warnings
fallback options
ranking explanation
cost/speed/proof estimates
```

### PlanDelta

A compact candidate plan proposed by a model or deterministic planner over a CandidateBundle.

It is not truth.

### PlanLock

Canonical locked route artifact after validation and compilation.

It should be stable, hashable, replayable, and versioned.

### ExecutionReceipt

A record of what actually ran.

Should include:

```text
input hash
output hash
route id
primitive ids
model/ranker/adapter ids
runtime target
effects observed
proof results
artifacts emitted
latency
cost
tokens
source snapshot ids
error/failure details
```

### PromotionEvidence

A record proving a primitive or route deserves a higher trust level.

Should include:

```text
source refs
license/terms review
schema validation
input/output validation
side-effect declaration
proof receipts
benchmark scorecards
regression history
human review if required
freshness policy
rollback path
```

### NegativeMemory

A durable record of failed, unsafe, stale, wrong, too-expensive, or misleading paths.

Use it to suppress repeated waste.

---

## Lifecycle

Use a staged lifecycle:

```text
L0 discovered candidate
L1 source-backed candidate
L2 contract extracted
L3 effects declared
L4 proof obligations generated
L5 route compiled
L6 PlanLock emitted
L7 deterministic execution tested
L8 receipt recorded
L9 benchmark score recorded
L10 promoted, deprecated, retired, or negative-memory only
```

Default state:

```json
{
  "candidate": true,
  "serves_truth": false
}
```

No model, no LoRA, no agent, and no benchmark row can promote truth by itself.

---

## Primitive Data Format Flexibility

Many primitives perform the same conceptual transformation across different data representations.

The system must support variation across input and output data formats:

```text
JSON object
JSON array
JSONL
CSV
TSV
Excel/XLSX
row record
batch of rows
wide table
long/tidy table
normalized relational tables
denormalized table
star schema
snowflake schema
event log
ledger table
feature table
Parquet
Arrow
ORC
Avro
Protobuf
gRPC message
GraphQL object
OpenAPI schema
AsyncAPI message
XML
HTML
Markdown
PDF
image
video
audio
GeoJSON
WKT/WKB
Shapefile
KML
OSM PBF
SQL table
BigQuery table
Snowflake table
Postgres table
DuckDB table
Spark DataFrame
pandas DataFrame
Polars DataFrame
vector embedding matrix
HDF5/Zarr/scientific arrays
```

A primitive should not be duplicated just because data moves from JSON to Parquet or rows to BigQuery.

Use deterministic format mutators:

```text
json_to_row
row_to_json
jsonl_to_table
csv_to_table
table_to_parquet
parquet_to_arrow
arrow_to_dataframe
dataframe_to_sql_table
sql_table_to_feature_table
wide_to_long
long_to_wide
normalized_to_denormalized
denormalized_to_normalized
geojson_to_feature_table
feature_table_to_h3_cells
xml_to_dataclass
protobuf_to_json
openapi_schema_to_json_schema
json_schema_to_validator
```

Each mutator needs:

```text
preconditions
lossiness policy
schema fingerprint
field mapping receipt
null handling policy
type coercion policy
roundtrip test where possible
proof obligation
```

---

## Variation Dimensions To Support

Support variation dimensions for:

```text
primitive kind
granularity
algorithm family
data structure
data type
data semantics
schema standard
file format
message format
database engine
SQL dialect
BigQuery version/features
Snowflake version/features
Postgres version/features
Spark/Databricks version/features
cloud provider
runtime target
programming language
language version
framework
package manager
API style
auth style
pagination style
rate limit style
idempotency policy
eventing protocol
workflow engine
source surface
website/platform
industry
business process
role/seniority
country
state/province
county/city/locality
jurisdiction
language/locale
timezone
currency
tax/regulatory regime
geography/geospatial reference system
privacy class
security class
legal/compliance regime
risk class
proof policy
benchmark family
artifact type
response format
frontend/UI surface
visualization/media surface
model/ranker/LoRA component
embedding profile
search profile
cache policy
freshness policy
marketplace/product surface
human-review policy
```

Do not hard-code dimensions as a fixed closed list. Store dimensions in extensible tables and typed overlays.

---

## Generation Paths

Keep all primitive-generation paths available and measurable.

### Source Adapter Extraction

Mine structured source surfaces into primitive candidates.

Sources:

```text
OpenAPI
AsyncAPI
MCP tool schemas
GraphQL schemas
protobuf/gRPC
JSON Schema
FHIR
XBRL
GS1
EDI X12
HL7
DICOM
GTFS
GeoJSON
Kubernetes API objects
Terraform modules
OpenTelemetry semantic conventions
OpenLineage
Data Catalog APIs
CKAN
Socrata
ArcGIS FeatureServer
OGC API Records
```

### Package / Repo Capability Mining

Mine public and internal packages/repos for:

```text
public APIs
CLI commands
function signatures
type hints
examples
README usage
unit tests
integration tests
GitHub Actions workflows
Dockerfiles
Helm charts
Terraform modules
schemas
configuration surfaces
common helper utilities
repeated local routes
```

Sources:

```text
GitHub
GH Archive
GitHub BigQuery
The Stack
PyPI
npm
Maven
NuGet
Cargo
Go packages
RubyGems
Packagist
Conda
Hugging Face Hub
```

Do not copy restricted code. Extract contracts, source refs, proof plans, and implementation opportunities.

### Benchmark Task Demand Extraction

Convert benchmark tasks into primitive demands.

Benchmark families:

```text
SWE-bench
SWE-bench Verified
SWE-bench Lite
SWE-bench Multilingual
SWE-bench Multimodal
SWE-bench Live
Terminal-Bench
BigCodeBench
LiveCodeBench
EvalPlus
HumanEval
MBPP
MultiPL-E
CodeXGLUE
Project CodeNet
Defects4J
BugsInPy
QuixBugs
BugSwarm
BFCL
API-Bank
ToolBench
ToolSandbox
AppWorld
tau-bench
WebArena
VisualWebArena
BrowserGym
OSWorld
GAIA
AgentBench
DocILE
MLE-bench
DSBench
MLAgentBench
OpenML benchmark suites
Kaggle competitions
DrivenData competitions
Zindi competitions
AIcrowd competitions
BEIR
HELM
lm-evaluation-harness
OpenCompass
Inspect Evals
Codabench
```

Each benchmark adapter should output:

```text
BenchmarkTask
PrimitiveDemand
ExpectedInputEdge
ExpectedOutputEdge
CandidateRoutes
ProofRequirements
BaselineRun schema
PrimitiveFirstRun schema
Scorecard schema
PromotionEvidence candidate
```

### Workflow Template Mining

Mine workflow ecosystems:

```text
n8n templates
Zapier integrations
Make templates
Pipedream components
GitHub Actions workflows
Airflow DAGs
Dagster assets
Prefect flows
Temporal workflows
Argo workflows
CI/CD templates
runbooks
SOPs
Apple Shortcuts-like automations
low-code/no-code marketplaces
```

### Trace-to-Workflow Mining

Turn successful agent, developer, browser, terminal, tool, and coding-session traces into route candidates.

```text
successful trace
-> action extraction
-> primitive sequence
-> hidden member edges
-> route skeleton
-> proof obligations
-> group candidate
```

### Query Lattice Discovery

Generate search queries from typed dimensions:

```text
person
company
country
region
time period
industry
job title
job level
seniority
problem
solution
architecture
diagram
code language
schema
file format
database dialect
legal/regulatory term
public dataset term
website/source
benchmark
competition
movement/methodology
publication medium
advantages/disadvantages
cost/ROI
```

Generate millions of possible queries, but do not execute a blind Cartesian explosion. Use scheduler scoring:

```text
expected primitive yield
source authority
novelty
coverage gap
benchmark relevance
monetary/risk value
freshness need
license/terms safety
cost budget
diversity
```

### Model-Drafted Candidates

Models may draft primitive candidates, but model drafts remain unpromoted candidates until source/proof gates pass.

Use for:

```text
gap filling
variant generation
problem-solution card drafting
input/output edge suggestions
proof obligation suggestions
mutator suggestions
benchmark task synthesis
use-case expansion
pitch/storyline drafting
```

### Negative Memory to Gap Generation

Repeated failures produce new primitive demands.

```text
wrong route selected repeatedly
source stale repeatedly
schema mismatch repeatedly
manual glue repeatedly written
same helper regenerated repeatedly
same package docs reread repeatedly
same benchmark failure mode appears repeatedly
```

Create:

```text
GapRecord
PrimitiveDemand
PriorityScore
SourceSearchPlan
BenchmarkPlan
Owner/queue status
```

---

## Search Paths

Never assume one search method is best.

Support and compare:

```text
exact edge search
type-compatible edge search
schema/contract search
lexical BM25 search
dense embedding search
multi-vector search
hybrid lexical+dense search
reciprocal rank fusion
ColBERT/late interaction retrieval
SPLADE/sparse expansion retrieval
HyDE/hypothetical primitive card search
GraphRAG/community search
graph route search
known-chain search
route-template search
source-ref search
benchmark-task search
marketplace-source search
negative-memory search
freshness-aware search
official-source search
jurisdiction-aware search
industry/schema overlay search
runtime-shape search
proof-requirement search
co-occurrence/bundle search
cache-aware search
```

Search must produce a CandidateBundle, not one overconfident answer.

Record:

```text
search_path_id
query representation
embedding profiles used
lexical fields used
graph expansion used
ranker used
candidate count
winner source
false positives
false negatives if known
latency
cost
fallbacks
```

---

## Embeddings And Indexing

Do not use one embedding per primitive.

Use named embedding profiles:

```text
edge_io_embedding
blackbox_embedding
problem_statement_embedding
trigger_phrase_embedding
solution_route_embedding
hidden_member_edges_embedding
schema_semantics_embedding
algorithm_pattern_embedding
runtime_stack_embedding
industry_domain_embedding
jurisdiction_embedding
source_context_embedding
proof_requirements_embedding
failure_mode_embedding
negative_memory_embedding
code_signature_embedding
diagram_topology_embedding
legal_policy_embedding
visual_media_embedding
benchmark_task_embedding
```

Store embeddings in long form:

```text
primitive_id
primitive_version
embedding_profile_id
model_id
dimensions
vector
source_field_hash
created_at
```

Materialize wide search views for hot paths:

```text
primitive_search_doc
primitive_route_search_view
primitive_prompt_card_view
primitive_template_search_view
source_surface_yield_view
benchmark_task_search_view
negative_memory_search_view
```

Support different dimensions and models per embedding profile. Some profiles may be 384-d local embeddings; others may be 768, 1024, 1536, 3072, or domain-specific vectors. Track the model, dimensions, normalization, input fields, and source-field hash.

---

## Ranking And Affinity

Rank routes contextually by:

```text
contract fit
input/output edge compatibility
schema compatibility
runtime fit
stack fit
industry fit
jurisdiction fit
source authority
freshness confidence
proof strength
benchmark success
negative memory risk
side-effect risk
privacy/security risk
cost
latency
source escalation depth
route reuse count
cache hit probability
human-review burden
user/project affinity
```

Use transparent scoring first.

Later test:

```text
learning-to-rank
contextual bandits
Bayesian optimization
multi-armed bandits
MCTS route search
evolutionary route search
human feedback ranking
local rerankers
cross-encoder rerankers
LoRA-enhanced rerankers
```

Every ranking decision should produce a receipt.

---

## Route Planning Paths

Treat planning as a portfolio:

```text
exact_route_lookup
template_slot_fill
deterministic_graph_search
contract_diff_remix
known_chain_completion
cooccurrence_bundle_completion
LLM PlanDelta over CandidateBundle
tree of routes
graph of routes
MCTS route search
evolutionary route search
symbolic planner route
trace replay compile
human-reviewed route
source fallback route
```

Compare planners per task family. Do not declare one universal winner.

---

## Remixing And Mutating

### Deterministic Remix Mutators

Prioritize deterministic mutators because they save tokens and reduce risk:

```text
map_sequence
input_envelope_wrapper
output_wrapper
field_rename
field_project
field_default
field_merge
field_split
schema_validator_inserter
type_cast
path_to_bytes
bytes_to_text
json_to_dataclass
dataclass_to_json
json_to_row
row_to_json
csv_to_table
table_to_parquet
parquet_to_arrow
long_to_wide
wide_to_long
pagination_expander
retry_wrapper
cache_wrapper
idempotency_wrapper
auth_scope_binding
rate_limit_wrapper
artifact_materialize
artifact_reference
api_endpoint_wrapper
cloud_function_wrapper
kubernetes_job_wrapper
queue_worker_wrapper
cron_job_wrapper
cli_command_wrapper
mcp_tool_wrapper
browser_replay_wrapper
human_review_wrapper
route_to_group_card
```

Each mutator needs:

```text
preconditions
postconditions
proof obligations
lossiness policy
side-effect policy
failure modes
telemetry fields
```

### Non-Deterministic / Model-Assisted Remix

Allowed only in bounded roles:

```text
field alias suggestion
ambiguous schema mapping suggestion
code micro-repair
proof-case suggestion
source query rewriting
error explanation
human-review packet summarization
visual scene variant suggestion
entity-resolution threshold explanation
```

Do not let open-ended model text become runtime truth.

---

## Compilation Targets

Routes may compile into:

```text
PlanLock canonical JSON
Python callable
TypeScript function
Rust function
Go function
Java method
SQL query
SQL view
SQL stored procedure
dbt model
DuckDB query
BigQuery SQL
Snowflake SQL
Spark job
FastAPI endpoint
Express endpoint
GraphQL resolver
gRPC method
MCP tool wrapper
CLI command
queue consumer
cron job
Temporal activity/workflow
Airflow DAG/task
Dagster asset
Prefect flow
browser automation script
OpenAPI client wrapper
SDK package
mock server
contract test suite
Terraform module
Kubernetes job/deployment/service
Helm values/chart
GitHub Actions workflow
policy-as-code bundle
RAG pipeline
vector-index build job
dashboard/report artifact
Vega-Lite spec
Graphviz/Mermaid diagram
Manim scene
Three.js scene
FFmpeg/ImageMagick media pipeline
human-review checklist
```

Compilation methods to compare:

```text
deterministic template fill
schema-driven codegen
AST transform
typed graph lowering
grammar-constrained generation
model-generated bounded function
source-backed wrapper generation
policy-as-code compilation
manual approval and lock
```

---

## Runtime Targets

Runtime selected by effects, risk, latency, scale, and proof:

```text
local pure function
local file worker
container job
serverless function
API middleware
MCP prehook/tool
queue worker
browser worker
workflow engine
Kubernetes job
Kubernetes deployment
CI/CD action
database job
analytics warehouse query
vector search service
GPU media/render worker
human-review queue
```

Execution patterns:

```text
strict deterministic execution
bounded LLM subcall under schema/policy
parallel tool execution
future/asynchronous tool execution
retry with idempotency key
compensation/rollback route
dry-run preview before mutation
human approval before side effect
shadow execution before promotion
canary execution
```

Every runtime emits ExecutionReceipt.

---

## Proof And Validation

Use layered proof; match rigor to risk.

Proof types:

```text
schema validation
contract tests
unit tests
golden fixtures
roundtrip tests
property-based tests
metamorphic tests
differential tests
fuzzing
idempotency tests
side-effect audit
privacy/PII/PHI/PCI boundary test
source-span verification
citation support check
license/terms gate
security/static-analysis scan
sandbox execution
benchmark scorecard
freshness/effective-date check
visual regression
artifact hash check
performance budget check
human review
regression replay
shadow production comparison
```

Promotion requirements vary by domain.

Examples:

```text
zero-side-effect string formatter: light proof
API endpoint wrapper: contract/auth/idempotency proof
healthcare data route: privacy/source/audit/human-review proof
legal/regulatory route: jurisdiction/effective-date/citation/human-review proof
cloud deploy route: dry-run/security/policy/rollback proof
data export route: privacy/license/row-count/schema proof
financial route: audit/idempotency/reconciliation proof
```

---

## Model, LoRA, Ranker, And Mini-Agent Control Plane

Models are components, not global magic.

Use model slots:

```text
intent_classifier_model
request_decomposer_model
primitive_candidate_generator_model
edge_signature_infer_model
schema_mapper_model
search_query_rewriter_model
local_embedding_model
cross_encoder_reranker_model
route_planner_model
PlanDelta_writer_model
compiler_error_repair_model
proof_obligation_generator_model
negative_memory_classifier_model
source_fragility_detector_model
legal_geography_escalation_model
visual_scene_generator_model
code_micro_patch_model
receipt_summarizer_model
human_review_packet_writer
```

Each slot can be served by:

```text
deterministic rule
SQL query
graph query
local classifier
embedding model
cross-encoder ranker
small local language model
domain LoRA adapter
vision-language model
cloud frontier model
human review queue
```

LoRA / adapter lanes:

```text
entity_resolution_explain_adapter
healthcare_fhir_mapper_adapter
legal_effective_date_detector_adapter
geography_source_ranker_adapter
visual_threejs_scene_adapter
shader_error_repair_adapter
sql_bigquery_optimizer_adapter
primitive_problem_solution_card_adapter
route_failure_classifier_adapter
source_fragility_detector_adapter
api_contract_extraction_adapter
benchmark_task_mapper_adapter
```

Adapter records must include:

```text
base_model_ref
adapter_ref
training_data_lineage
eval_task_set
allowed_slots
disallowed_slots
latency_profile
memory_profile
cost_profile
calibration_profile
known_failure_modes
promotion_receipts
rollback_receipts
```

Mini-agents must be bounded:

```text
source_surface_scout
fragile_context_scout
geography_source_scout
legal_source_scout
api_version_scout
primitive_bundle_curator
route_portfolio_builder
negative_memory_writer
benchmark_case_synthesizer
visual_render_debugger
entity_resolution_threshold_tuner
repo_reuse_scout
package_surface_scout
```

Each mini-agent envelope:

```text
input_budget
source_allowlist
tool_allowlist
max_steps
max_tokens
max_wall_time
max_cost
stop_conditions
artifact_outputs
receipt_outputs
human_review_trigger
```

A mini-agent only survives if it improves proofed outcomes, not if it sounds better.

---

## Simultaneous Runs And Sprouting

The system must support simultaneous experiments:

```text
shadow
canary
paired_offline
tournament
sprout
```

Examples:

```text
exact_edge_search vs hybrid_search vs graph_route_search
rule_decomposer vs local_model_decomposer vs frontier_model_decomposer
template_slot_fill vs PlanDelta_compile vs source_fallback
brute_force_entity_resolution vs Splink_route vs BigQuery_managed_route
Three.js_scene_template vs Manim_scene_template vs WebGPU_shader_route
```

Sprout parameters:

```text
retriever weights
embedding profile mix
candidate bundle size
context depth limit
model slot assignment
LoRA adapter choice
ranker type
route member order
proof gate order
cache policy
blocking rule
matching threshold
freshness threshold
source authority threshold
visual render settings
shader precision
SQL dialect strategy
runtime wrapper target
```

Exploration policies:

```text
random search
grid search for small spaces
Bayesian optimization
successive halving
population-based training
evolutionary mutation
multi-armed bandit
contextual bandit
MCTS route search
novelty search
active learning
human-review sampling
```

Sprouts remain candidate-isolated. Promote only after held-out wins.

---

## Telemetry North Star

Every request, search, route, compile, proof, model call, cache event, and promotion decision should produce telemetry.

Use OpenTelemetry-like spans:

```text
request_intake
decompose_request
classify_task_family
detect_fragile_context
retrieve_candidates
rerank_candidates
construct_candidate_bundle
select_model_slot
run_mini_agent
write_plan_delta
compile_route
emit_plan_lock
execute_runtime
run_proofs
check_side_effects
emit_artifact
emit_receipt
update_cache
record_negative_memory
update_cooccurrence_graph
run_experiment_arm
compare_trial_paths
promote_or_demote
queue_gap
render_report
```

Core metrics:

```text
task_success
proof_success
compile_success
first_pass_success
tokens_to_plan
tokens_to_pass
runtime_llm_tokens
source_context_tokens
source_files_read
source_docs_read
context_depth_reached
latency_p50
latency_p95
cost_per_success
model_calls_by_slot
adapter_calls_by_slot
cache_hit_rate
cache_miss_rate
primitive_reuse_count
route_reuse_count
primitive_group_reuse_count
false_match_rate
false_block_rate
repair_attempts
negative_memory_created
human_review_rate
artifact_quality_score
downstream_regression_rate
source_ref_coverage
proof_coverage
freshness_risk
privacy_risk
side_effect_risk
```

Telemetry records must carry:

```text
trace_id
run_id
experiment_id
arm_id
route_id
primitive_ids
component_ids
model_ids
adapter_ids
ranker_ids
input_hash
output_hash
source_refs
source_snapshot_ids
artifact_hashes
privacy_classification
risk_class
metrics
error details
winner/loser reason
```

---

## Savings And Impact Formulas

Do not make unmeasured claims. Implement formulas first, fill with real telemetry later.

### Per Task

```text
token_savings_pct = 1 - primitive_first_total_tokens / baseline_total_tokens

source_context_avoidance_pct = 1 - primitive_first_source_context_tokens / baseline_source_context_tokens

cost_savings_pct = 1 - primitive_first_total_cost / baseline_total_cost

speedup_factor = baseline_wall_clock_seconds / primitive_first_wall_clock_seconds

proof_coverage = passed_proof_requirements / total_proof_requirements

reuse_ratio = reused_route_steps / total_route_steps
```

### Per Developer

```text
weekly_tokens_saved_per_developer = average_tasks_per_week * average_tokens_saved_per_task

weekly_cost_saved_per_developer = average_tasks_per_week * average_cost_saved_per_task

weekly_hours_saved_per_developer = average_tasks_per_week * average_wall_clock_seconds_saved_per_task / 3600
```

### Per 100K Developers / Users

```text
tokens_saved_per_100k_developers_per_week = weekly_tokens_saved_per_developer * 100000

cost_saved_per_100k_developers_per_week = weekly_cost_saved_per_developer * 100000

hours_saved_per_100k_developers_per_week = weekly_hours_saved_per_developer * 100000
```

### Route Amortization

```text
break_even_tasks = primitive_creation_cost / average_future_cost_saved_per_task

route_reuse_value = route_reuse_count * average_tokens_saved_per_reuse * proof_success_rate

promotion_value = future_tokens_avoided_estimate * proof_success_rate * reuse_probability
```

### AIDevObserver-Specific

```text
reinvention_detected_count
existing_helper_reuse_recommendations
accepted_reuse_recommendations
dismissed_reuse_recommendations
estimated_source_files_not_read
estimated_docs_not_read
estimated_duplicate_code_avoided
estimated_review_comments_avoided
estimated_test_failures_avoided
```

Reports must distinguish:

```text
measured
estimated from measured local baseline
projected scenario
hypothesis
```

---

## Gap Detection And Primitive Queueing

Automatically identify areas needing more primitives.

Signals:

```text
frequent source fallback
high token usage
high source escalation depth
repeated benchmark failures
repeated repair loops
high human-review rate
negative-memory clusters
low primitive recall@k
low proof coverage
low route reuse
high false-match rate
coverage holes by industry/region/schema/runtime
new API/package version detected
schema drift detected
law/regulation/source freshness changed
manual developer glue repeated
```

Output:

```text
GapRecord
PrimitiveDemand
SourceSearchPlan
BenchmarkPlan
PriorityScore
Owner/Queue
ExpectedValue
RiskClass
```

Priority formula:

```text
priority =
  frequency
+ dollar_or_risk_impact
+ LLM_context_waste_avoided
+ cross_industry_reuse
+ proofability
+ freshness_or_fragile_context_risk
+ source_surface_availability
+ deterministic_implementation_potential
- license_or_policy_risk
- ambiguity_without_human_review
```

---

## Primitive Co-Occurrence Learning

Build a graph of which primitives often go together.

Nodes:

```text
primitive
primitive group
template
mutator
runtime wrapper
proof pack
model slot
LoRA adapter
ranker
source surface
schema
industry
region
benchmark task
cache layer
negative memory class
```

Edges:

```text
used_after
used_before
used_together
fixed_by
failed_with
cached_with
compiled_to
proved_by
retrieved_by
ranked_by
improved_by_lora
supersedes
anti_affinity
```

Derived records:

```text
primitive_pair_affinity
primitive_group_affinity
route_skeleton
frequent_subroute
anti_affinity
missing_middle_edge
cache_candidate
promotion_candidate
decomposition_template
```

Use these for:

```text
better request decomposition
better CandidateBundle construction
route autocomplete
primitive group discovery
proof plan inference
cache key selection
negative-memory suppression
benchmark task generation
```

---

## Cache And Materialization

Cache at multiple levels:

```text
source_surface_card_cache
source_snapshot_cache
schema_fingerprint_cache
edge_signature_cache
embedding_cache
candidate_bundle_cache
route_skeleton_cache
PlanLock_cache
proof_fixture_cache
proof_result_cache
execution_receipt_cache
negative_memory_cache
render_asset_cache
entity_resolution_block_cache
benchmark_result_cache
```

Cache policies:

```text
never_cache_sensitive_data
cache_source_refs_not_raw_private_payloads
cache_promoted_routes_longer
cache_candidate_routes_shorter
invalidate_on_schema_change
invalidate_on_api_version_change
invalidate_on_legal_effective_date_change
invalidate_on_source_snapshot_change
invalidate_on_benchmark_regression
invalidate_on_model_or_adapter_change
invalidate_on_license_or_terms_change
```

Cache value metrics:

```text
tokens_saved
latency_saved
source_reads_avoided
proofs_reused
regressions_caused
stale_cache_hits
privacy_risk
```

---

## Infrastructure North Star

Build flexible infrastructure, not one rigid table.

### Storage

Use a mix of:

```text
Postgres for core truth and transactional registry
pgvector or vector DB for embeddings
graph store or graph tables for routes/co-occurrence
object store for source snapshots, artifacts, receipts, manifests
lakehouse tables for large telemetry/benchmark/source data
search engine for BM25 and hybrid retrieval
queue/event bus for ingestion and experiments
workflow engine for long-running pipelines
```

### Database Shapes

Use all three:

```text
normalized truth tables
long flexible attribute tables
wide denormalized search/materialized views
```

Core tables:

```text
primitive
primitive_version
primitive_contract
primitive_effect
primitive_runtime_target
primitive_source_ref
primitive_proof_requirement
primitive_template
primitive_overlay
primitive_group
primitive_group_member_edge
mutator
route_portfolio
candidate_bundle
plan_delta
plan_lock
execution_receipt
promotion_evidence
negative_memory
source_surface
source_document
source_snapshot
source_chunk
benchmark_source
benchmark_task
benchmark_run
scorecard
model_component
adapter_component
ranker_component
strategy_genome
experiment_arm
experiment_run
telemetry_event
cache_entry
gap_record
cooccurrence_edge
marketplace_listing
user_feedback
```

### APIs

Backend APIs should support:

```text
search primitives
resolve specialized primitive
construct CandidateBundle
compile PlanLock
execute route
run proof
record receipt
submit source surface
run source adapter
run benchmark
query telemetry
generate report
queue gap
promote/demote primitive
browse marketplace
integrate with AIDevObserver
integrate with IDE/CLI/MCP/GitHub/CI
```

### Frontend

UI surfaces:

```text
Primitive Explorer
Route Portfolio Viewer
CandidateBundle Inspector
PlanLock Viewer
Telemetry Trace Viewer
Savings Dashboard
Benchmark Dashboard
Coverage Heatmap
Gap Queue
Source Surface Registry
Promotion Review Queue
Negative Memory Browser
Model/LoRA/Ranker Leaderboard
Marketplace
AIDevObserver Coding Session Review
Pitch/Report Generator
```

### Integrations

Integrate with:

```text
Claude Code
Codex
VS Code / JetBrains / IDEs
GitHub / GitLab / Bitbucket
CI/CD
MCP servers
OpenAPI/AsyncAPI registries
package registries
benchmark harnesses
Kaggle/OpenML/DrivenData
public data portals
cloud providers
Slack/Jira/Linear/Notion
browser automation
local CLI
```

---

## Source Surfaces To Expand

Prioritize source-backed public surfaces and machine-readable surfaces.

### Software/API/Package

```text
OpenAPI directories
AsyncAPI directories
MCP tool registries
GraphQL schemas
protobuf/gRPC schemas
PyPI
npm
Maven
NuGet
Cargo
Go packages
RubyGems
Packagist
Conda
GitHub
GH Archive
The Stack
CodeSearchNet
Hugging Face Hub
Terraform Registry
Docker Hub
Helm charts
GitHub Actions marketplace
```

### Workflow/Automation

```text
n8n
Zapier
Make
Pipedream
Airflow
Dagster
Prefect
Temporal
Argo
Flyte
runbooks
SOPs
CI/CD templates
```

### Benchmarks

```text
SWE-bench family
Terminal-Bench
BigCodeBench
LiveCodeBench
EvalPlus
BFCL
API-Bank
ToolBench
ToolSandbox
AppWorld
tau-bench
WebArena
OSWorld
GAIA
DocILE
MLE-bench
DSBench
MLAgentBench
OpenML
Kaggle
DrivenData
Zindi
AIcrowd
BEIR
HELM
Inspect Evals
Codabench
```

### Public Data / Geospatial / Open Gov

```text
Data.gov / CKAN
Socrata
ArcGIS Hub / FeatureServer
OGC API Records
BigQuery public datasets
OpenStreetMap / Overpass
Overture Maps
OpenAddresses
GeoNames
Natural Earth
TIGER/Line
HIFLD
HRSA
NPPES
CMS Provider Data
CareerOneStop
College Scorecard
IPEDS
BLS
O*NET
OPM
USAJOBS
SAM.gov
USASpending
Grants.gov
Federal Register
eCFR
GovInfo
CourtListener
USPTO / PatentsView
Google Patents discovery
EPO OPS
WIPO PATENTSCOPE
Lens
SEC EDGAR
OFAC
OpenSanctions
```

### Media/Visualization/Graphics

```text
Matplotlib
Plotly
Vega-Lite
D3
Observable
Graphviz
Mermaid
Manim
Three.js
WebGL/WebGPU
Babylon.js
Phaser
PixiJS
Unity docs
Unreal docs
Godot docs
FFmpeg
ImageMagick
Pillow
OpenCV
MoviePy
Remotion
Blender
ComfyUI workflow graphs
Diffusers pipelines
```

### Algorithms/Math/Data Structures

```text
The Algorithms
CP-Algorithms
Rosetta Code
Project CodeNet
MIT OCW algorithms
NIST DLMF
Ray Tracing in One Weekend
PBRT
scientific computing docs
numeric libraries
```

---

## High-Value Primitive Families

P0 families:

```text
entity resolution
entity enrichment
source-backed verification
official-source verification
temporal staleness / fragile context detection
data quality and schema validation
source discovery and related-data search
geography-specific search and spatial analysis
legal/regulatory search and citation resolution
sanctions/PEP/watchlist screening
open-data portal discovery and harvesting
website browsing/extraction/monitoring/evidence receipts
repo/package/API capability extraction
reuse recommendation and route ranking
contract-test and proof-pack generation
document intelligence with source-span grounding
vendor/supplier risk intelligence
opportunity matching and deadline ranking
privacy/PII/PHI/PCI detection and redaction
negative memory and failed-route suppression
```

Developer/software families:

```text
API endpoint generation
resource API groups
webhook handlers
queue workers
cron/scheduled jobs
CLI tools
SDK generation
mock server generation
contract test generation
OpenAPI/AsyncAPI extraction
MCP tool wrapping
Kubernetes/Terraform wrappers
GitHub Actions workflows
cloud-function wrappers
repo helper detection
package capability mining
code migration primitives
security scanning
secrets detection
license/SBOM generation
```

Data/ML families:

```text
CSV/Parquet/SQL data load
schema fingerprint
data validation
long/wide conversion
feature table generation
leakage scan
train/validation split
metric parse
baseline model
hyperparameter search
submission validation
leaderboard comparison
model card
RAG chunking/indexing/retrieval/citation validation
embedding index build
reranker evaluation
```

Business/public-sector families:

```text
procurement opportunity ingestion
NAICS/PSC extraction
deadline ranking
bid/no-bid packet
grant discovery
job posting ingestion
skill extraction
role taxonomy mapping
training provider discovery
clinic/provider discovery
site selection
open-data map/report generation
legal/regulatory monitoring
patent prior-art evidence bundle
```

Media/visual families:

```text
chart artifact generation
diagram layout
map artifact generation
formula visualization
Manim scene generation
Three.js/WebGPU scene generation
image transform
GIF generation
video transform
subtitle generation
render proof receipts
canvas nonblank checks
visual regression checks
```

---

## Benchmark Lab North Star

Every benchmark task should compare multiple arms:

```text
A1 baseline LLM/agent, no primitive search
A2 baseline LLM/agent + repo/docs/search/RAG
A3 AIDevObserver review-only recommendation
A4 deterministic template fill
A5 primitive-first CandidateBundle + compact PlanDelta + PlanLock
A6 deterministic remix repair
A7 LLM micro-repair on failed edge
A8 source-level codegen fallback
A9 human-reviewed route for high-risk domain
```

Minimum fields:

```text
task_success
unit_test_pass
benchmark_metric
compile_success
proof_success
tokens_to_plan
tokens_to_pass
runtime_llm_tokens
source_context_tokens
source_files_read
source_docs_read
context_depth_reached
wall_clock_seconds
cost_usd
route_reuse_count
primitive_reuse_count
proof_coverage
source_ref_coverage
negative_memory_created
new_group_created
human_review_required
```

Depth-to-solution ladder:

```text
L1 edge card only
L2 contract card
L3 behavior card
L4 route card
L5 proof card
L6 source slice
L7 full source/docs/repo
```

Benchmark story:

```text
Primitive-first solved X% of tasks before full source escalation.
Primitive-first reduced tokens by Y%.
Primitive-first reduced source context by Z%.
Primitive-first reused promoted routes N times.
Primitive-first created M reusable group candidates.
Primitive-first generated K negative-memory records that prevent repeated waste.
```

Use placeholders until measured.

---

## AIDevObserver North Star

AIDevObserver observes AI-assisted development sessions and identifies waste, reuse, risk, and improvement opportunities.

It should detect:

```text
agent reread huge docs when compact contract existed
agent regenerated helper that existed in repo
agent wrote glue that a deterministic mutator could handle
agent used stale package/API/version info
agent skipped proof obligations
agent made unsafe side effects
agent failed to reuse primitive group
agent needed source fallback because primitive coverage was missing
agent discovered a new route worth distilling into a primitive
```

Outputs:

```text
session summary
reuse recommendations
token savings estimate
source context avoided estimate
primitive gap queue
negative memory
route candidate
proof coverage report
engineering manager report
team trend dashboard
```

Simulate real engineer coding sessions:

```text
baseline AI coding session
AI coding session with repo/docs RAG
AIDevObserver review-only session
AIDevObserver active route recommendation session
primitive-first session
```

Compare:

```text
time to patch
tokens used
source files read
tests passed
review comments
reuse count
route memory created
```

---

## Product / Fundraising / Writing Artifacts

Claude Code should also help generate product and business artifacts from measured data and clear hypotheses.

Artifact families:

```text
research papers
technical whitepapers
system design papers
benchmark reports
primitive atlas coverage reports
AIDevObserver case studies
coding-session simulations
real engineer workflow examples
pitch decks
one-pagers
investor memos
website copy
landing pages
pricing pages
product docs
API docs
marketplace docs
blog posts
demo scripts
sales engineering scripts
customer ROI calculators
security/compliance docs
architecture diagrams
roadmaps
release notes
```

Rules:

```text
Separate measured results from hypotheses.
Use local manifests and receipts for any metric.
Show formulas when projecting savings.
Keep external papers as prior art, not proof of local product performance.
Avoid overstating legal/medical/security outcomes.
Preserve candidate/truth status in all claims.
```

---

## Marketplace North Star

Build a marketplace for:

```text
promoted primitives
candidate primitives
primitive templates
industry packs
schema packs
region/jurisdiction packs
runtime wrappers
mutators
proof packs
benchmark adapters
source adapters
model slots
LoRA adapters
rankers
workflow imports
report templates
```

Marketplace metadata:

```text
capability title
input/output edges
supported formats
supported runtimes
supported industries
supported regions
source refs
license/terms status
proof status
benchmark status
usage count
reuse value
tokens saved estimate
cost saved estimate
failure modes
freshness policy
owner/maintainer
version
rollback path
```

Marketplace should allow:

```text
search
compare
install
fork
specialize
benchmark
promote
retire
report issue
request primitive
submit source surface
publish proof pack
```

---

## Claude Code Operating Loop

For each work session:

```text
1. Read AGENTS.md, CLAUDE.md, README.md, taxonomy/SPEC.md, and relevant handoffs.
2. Identify current repo source of truth and generated-pack patterns.
3. Select a bounded build slice.
4. Add or update schemas before data.
5. Write generator scripts for large packs.
6. Write checker scripts for generated packs.
7. Generate candidate rows with manifests, hashes, and row counts.
8. Add focused docs/handoffs.
9. Run self-tests and relevant repo checkers.
10. Record what changed, what passed, what failed, and what remains candidate.
11. Do not promote truth without receipts.
12. Suggest next bounded slices.
```

Do not start unbounded scraping, crawling, model generation, or benchmark runs without:

```text
stop file
ledger
budget
rate limits
source policy
privacy policy
dry run
manifest
checker
```

---

## Initial Build Slices To Ask Claude Code To Do

Use these as concrete next tasks.

### Build Slice 1: North-Star Docs And Repo Alignment

```text
Create docs/codex/primitive-atlas-northstar.md from this prompt.
Create docs/codex/primitive-atlas-telemetry-and-savings-model.md.
Create docs/codex/primitive-atlas-million-primitive-roadmap.md.
Add references from README/CLAUDE/AGENTS only if repo conventions allow.
Run docs/checkers.
```

### Build Slice 2: Schema Foundation

```text
Add schema files for Primitive, PrimitiveTemplate, PrimitiveGroup, VariationOverlay, CandidateBundle, PlanDelta, PlanLock, ExecutionReceipt, PromotionEvidence, NegativeMemory, StrategyGenome, ModelRouteReceipt, BenchmarkScorecard, GapRecord.
Add self-test checker.
```

### Build Slice 3: Telemetry Pack

```text
Generate telemetry signal catalog.
Generate metric dictionary.
Generate savings formula spec.
Generate OpenTelemetry span naming spec.
Generate dashboard requirements.
Add checker.
```

### Build Slice 4: Multi-Path Portfolio Pack

```text
Generate generation_paths.jsonl.
Generate search_paths.jsonl.
Generate route_planning_paths.jsonl.
Generate compilation_paths.jsonl.
Generate runtime_paths.jsonl.
Generate proof_paths.jsonl.
Generate repair_paths.jsonl.
Generate experiment_arms.jsonl.
Add checker.
```

### Build Slice 5: Source Surface Expansion Pack

```text
Generate source_surface_registry.jsonl with official/source-backed metadata.
Generate source_adapter_backlog.md.
Generate query_lattice_dimension_bank.yaml.
Generate scheduler policy.
Add checker.
```

### Build Slice 6: Primitive Template Seed Pack

```text
Generate 1,000 template candidates across software, data, ML, public data, geospatial, legal, procurement, healthcare, visualization, media, algorithms, DevOps, security, and business operations.
Each candidate must include input/output edges, variation slots, effects, proof requirements, failure modes, source search plan, candidate=true, serves_truth=false.
Add checker.
```

### Build Slice 7: Benchmark Lab Pack

```text
Generate benchmark source atlas.
Generate benchmark adapter schema.
Generate initial 100-task offline benchmark plan.
Generate A1-A9 comparison arms.
Generate scorecard schema.
Generate report template.
Add checker.
```

### Build Slice 8: AIDevObserver Simulation Pack

```text
Generate 100 realistic AI coding session simulations.
For each, define baseline session, primitive-first route, expected reuse opportunity, telemetry fields, savings formula, and proof plan.
Add checker.
```

### Build Slice 9: Marketplace Pack

```text
Generate marketplace listing schema.
Generate pack install/fork/specialize/benchmark/promote lifecycle.
Generate UI requirements.
Generate API endpoints.
Generate sample listings.
Add checker.
```

### Build Slice 10: Product And Fundraising Artifacts

```text
Draft research paper outline.
Draft technical whitepaper outline.
Draft investor memo.
Draft pitch deck outline.
Draft website copy.
Draft ROI calculator spec.
Draft demo script.
Keep measured/hypothesis labels explicit.
```

---

## Acceptance Criteria For Any Claude Code Output

A good output should include:

```text
files changed
new generated files
new schemas
new builders
new checkers
tests run
counts from manifests only
known limitations
candidate/truth status
next build slice
```

A bad output:

```text
handwaves metrics
claims savings without receipts
promotes generated candidates to truth
hardcodes a single method as final
creates large data manually without a generator/checker
ignores source licensing/freshness
forgets telemetry
forgets negative memory
forgets benchmarks
forgets format/runtime variation
```

---

## Final North-Star Instruction To Claude Code

Build toward a system where 100,000 developers or users can have their AI assistants solve repeated software, data, research, business, legal, public-data, geospatial, media, and operational tasks with far less context, far fewer tokens, fewer repeated mistakes, stronger proof, better routing, and compounding reuse.

Do this by creating:

```text
1,000,000+ source-backed primitive candidates
50,000+ primitive templates
multi-path generation/search/planning/compilation/proof portfolios
model/LoRA/ranker/mini-agent component control plane
advanced hybrid search and multi-embedding infrastructure
complete telemetry and savings accounting
benchmarks across coding, agentic, data, ML, browser, terminal, public-data, and document tasks
AIDevObserver coding-session analysis
front end + backend + API + marketplace + integrations
papers, reports, pitch decks, websites, demo scripts, and use cases
```

But never forget:

```text
Metrics decide.
Proof decides.
Receipts decide.
Candidate remains candidate until promoted.
Search first.
Reuse first.
Remix deterministically.
Generate only the missing edge.
```
