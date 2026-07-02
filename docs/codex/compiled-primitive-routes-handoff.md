# Claude Fable Compiled Primitive Routes Handoff

Last updated: 2026-07-02

Audience: Claude Code Fable 5, Claude Code, Codex, and model/tool lanes
continuing the Compiled AI / primitive-route compiler work.

Status: research-and-build handoff. External paper and benchmark claims are
prior-art signals, not promoted truth for this repo. Verify live sources before
publishing metrics, screenshots, benchmark claims, product copy, or investor
claims.

## Read First

Before editing, read:

```text
AGENTS.md
CLAUDE.md
README.md
taxonomy/SPEC.md
docs/codex/claude-5-fable-all-surfaces-primitives-tools-handoff.md
docs/codex/primitive-family-expansion-handoff.md
docs/codex/primitive-problem-solution-details-handoff.md
docs/codex/high-priority-primitive-opportunity-rankings-handoff.md
docs/codex/marketplace-primitive-source-surfaces-handoff.md
docs/codex/aidevobserver-compiled-ai-evaluation-plan.md
docs/codex/primitive-registry-operational-schema.md
```

If these disagree, prefer the canonical repo source and recompute counts from
the owning manifests or checkers.

Note for this repo: this handoff was imported as canonical mission context on
2026-07-02. Some files in the read-first list describe the wider ecosystem and
may not exist locally yet; treat missing files as future build slices, not
errors.

## Core Thesis

Compiled AI is useful validation, but it is not the whole product category.

The broader AI Done Right / Teleon / AIDevObserver opportunity is:

```text
LLMs as primitive-route compilers
deterministic workers as runtime
proof receipts as trust
benchmarks as evidence
registry memory as compounding advantage
```

The important distinction:

```text
Compiled AI:
  workflow spec -> generated code artifact -> validation -> deterministic run

Compiled Primitive AI:
  intent -> primitive search -> CandidateBundle -> route/remix/adapters
        -> PlanDelta -> PlanLock -> deterministic execution
        -> proof receipt -> promotion or negative memory
```

Generated code is only one possible compiled output. A compiled primitive route
may also lower into an OpenAPI call plan, MCP tool route, queue worker,
browser-extraction recipe, schema mapping, SQL transformation, guardrail chain,
Terraform plan, Kubernetes job, RAG proof route, or human-review packet.

## Current Research Signals

Use these as prior art and benchmark inspiration:

- [Compiled AI: Deterministic Code Generation for LLM-Based Workflow Automation](https://arxiv.org/abs/2604.05150)
  frames one-time LLM generation, zero-token deterministic execution, and
  mandatory validation gates for high-stakes workflows.
- [PlanCompiler](https://arxiv.org/abs/2604.13092) is especially adjacent:
  typed node registry, static graph validation, deterministic compilation, and
  executable plans over primitives.
- [DSPy](https://arxiv.org/abs/2310.03714) validates the idea of compiling
  declarative language-model programs against metrics.
- [LLM+P](https://arxiv.org/abs/2304.11477) validates the split where an LLM
  translates intent and a deterministic planner solves the plan.
- [Blueprint First, Model Second](https://arxiv.org/abs/2508.02721) validates
  deterministic workflow logic with bounded model use, not free-form runtime
  agent control.
- [LLMCompiler](https://arxiv.org/abs/2312.04511) validates planning function
  calls once, then dispatching independent tool calls in parallel for lower
  latency and cost.
- [LLM-Tool Compiler](https://arxiv.org/abs/2405.17438) suggests a path for
  fusing similar tool operations so the model sees fewer, higher-level tool
  tasks.
- [AsyncFC](https://arxiv.org/abs/2605.15077) suggests an execution-layer path
  where unresolved tool results are represented as futures and model decoding
  overlaps with tool work.
- [WorkflowLLM](https://arxiv.org/abs/2411.05451) validates workflow data as a
  training/source surface: collected workflows, APIs, and generated variants can
  teach orchestration patterns.
- [FlowMind](https://arxiv.org/abs/2602.11782) validates a trace-first path:
  execute a task with tools, then reconstruct a structured workflow from the
  execution trace.
- [SynCode](https://arxiv.org/abs/2403.01632) validates grammar-constrained
  output paths for JSON, code, and other formal languages.
- [ReAct](https://arxiv.org/abs/2210.03629), [Tree of Thoughts](https://arxiv.org/abs/2305.10601),
  and [Graph of Thoughts](https://arxiv.org/abs/2308.09687) validate search
  over alternative reasoning/action paths, which maps to route-portfolio
  search.
- [Toolformer](https://arxiv.org/abs/2302.04761) validates the idea that tool
  use can be learned or induced from examples, not only hand-authored.
- [Self-RAG](https://arxiv.org/abs/2310.11511), [HyDE](https://arxiv.org/abs/2212.10496),
  [RAG-Fusion](https://arxiv.org/abs/2402.03367), and [GraphRAG](https://arxiv.org/abs/2404.16130)
  validate multiple retrieval and grounding paths; no single retriever should
  be assumed best.
- [SWE-agent](https://arxiv.org/abs/2405.15793) validates agent-computer
  interface design as a performance lever; primitive routes may need better
  tools and surfaces, not only better models.
- [Terminal-Bench](https://arxiv.org/abs/2601.11868), [AppWorld](https://arxiv.org/abs/2407.18901),
  and [MLE-bench](https://arxiv.org/abs/2410.07095) validate richer benchmark
  environments for terminal, API-state, and ML-engineering workflows.
- MLE-bench follow-on work on search policies and operator sets suggests that
  greedy, MCTS, and evolutionary search can be compared as route-discovery
  policies instead of arguing for one up front.
- [LoRA](https://arxiv.org/abs/2106.09685) and
  [Hugging Face PEFT](https://huggingface.co/docs/peft/en/index) validate a
  cheap-specialization lane: train or swap small adapters for extraction,
  ranking, decomposition, repair, and domain-specific scoring instead of
  assuming one general model must handle every primitive step.
- [vLLM LoRA adapter serving](https://docs.vllm.ai/en/latest/features/lora/)
  and [Ray Serve multi-adapter deployment patterns](https://docs.ray.io/en/latest/serve/llm/user-guides/multi-lora.html)
  suggest that model/adapter selection itself should be a runtime primitive
  with receipts, not hidden infrastructure.
- [Ray Tune](https://docs.ray.io/en/latest/tune/index.html) and
  [Optuna](https://optuna.readthedocs.io/en/stable/) validate systematic
  exploration of path parameters, search spaces, pruning rules, and competing
  trial arms.
- [MLflow tracking](https://mlflow.org/docs/latest/tracking/) and
  [Weights & Biases experiment tracking](https://docs.wandb.ai/models/track)
  are useful prior-art anchors for run metadata, metric history, artifacts,
  parameter comparisons, and leaderboard-style experiment review.
- [OpenTelemetry](https://opentelemetry.io/docs/) should be the default
  telemetry shape for execution traces, metrics, logs, and cross-runtime
  observability receipts.

Do not copy these systems. Use them to sharpen the category:

```text
They compile artifacts or plans.
We compile proof-aware capability routes over a primitive universe.
```

## Expanded Primitive Topic Branches

Do not limit primitive growth to coding-agent, document, API, and data-pipeline
tasks. The same route-market architecture should cover visual, mathematical,
game, graphics, algorithmic, and entity-resolution work.

Treat these as candidate research branches:

```text
universal app/software skeleton primitives
auth, sessions, identity, password reset, and account lifecycle
security, authorization, encryption, secrets, and audit controls
CRUD, admin, data trackers, customer trackers, and workflow trackers
notifications, uploads, imports, exports, webhooks, jobs, and schedulers
deployment, configuration, healthchecks, observability, and incident readiness
math visualization generation
three.js and WebGPU visualizations
web game development
game-engine game development
shader and rendering tricks
ray tracing and path tracing
GPU/CPU memory management tricks
classical algorithms and data structures
formula extraction and symbolic/numeric validation
distance metrics and similarity search
LSH, MinHash, sketches, and approximate nearest neighbor search
entity resolution, record linkage, and clustering
BigQuery-style managed entity resolution
Splink-style probabilistic/tunable entity resolution
leaf/block based record processing
place and facility discovery (clinics, health centers, training providers)
open-government data portal harvesting (CKAN, Socrata, ArcGIS, OGC Records)
open-map enrichment (OSM, Overture, OpenAddresses, TIGER)
geospatial analysis (spatial joins, isochrones, catchments, site selection)
```

The rule is the same as everywhere else:

```text
many source surfaces
many generation paths
many search paths
many compile/runtime targets
many proof receipts
metrics decide winners
```

## Universal App And Software Structure Primitive Branches

The most reusable primitive families are not exotic AI features. They are the
software structures nearly every real app rebuilds:

```text
project scaffold
environment configuration
dependency bootstrap
healthcheck endpoint
structured logging
feature flag
secret loading
database connection
database migration
seed data
user registration
login
logout
session refresh
password reset
email verification
MFA setup and challenge
OAuth/OIDC login
API keys
service accounts
RBAC
ABAC
tenant isolation
CSRF protection
rate limiting
input validation
output sanitization
encryption at rest
encryption in transit
audit logging
security headers
CRUD resource
admin CRUD page
customer tracker
lead tracker
support ticket tracker
subscription tracker
order tracker
inventory tracker
notification center
file upload
data import
data export
webhook handler
queue worker
cron job
background job
search index
analytics event tracker
billing or checkout flow
settings page
onboarding checklist
error boundary
accessibility audit
CI/CD workflow
container build
Terraform deploy
Kubernetes deploy
logs, metrics, traces
alerts
incident runbook
```

These should become common app skeleton primitive groups. The route compiler
should not rediscover password reset, audit logging, session refresh, CRUD
scaffolding, customer timelines, webhook verification, queue workers, or deploy
manifests every time a user asks for an app.

Source surfaces to mine:

```text
OWASP ASVS requirements
NIST digital identity guidance
OpenID Connect and OAuth specs
The Twelve-Factor App
framework starters and official templates
Rails, Django, Laravel, Spring, ASP.NET, FastAPI, Express, Next.js, Remix
Supabase, Firebase, Auth0, Clerk, WorkOS, Keycloak docs
Stripe, Shopify, HubSpot, Salesforce integration docs
Terraform Registry modules
Kubernetes workload and job docs
OpenTelemetry docs
GitHub Actions marketplace workflows
SaaS admin/dashboard templates
open-source app starter repos
```

Useful references:

- [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/)
  provides a basis for testing web application technical security controls and
  secure-development requirements.
- [NIST SP 800-63 Digital Identity Guidelines](https://pages.nist.gov/800-63-4/)
  covers identity proofing, authentication, federation, security, privacy, and
  customer-experience requirements.
- [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html)
  defines an identity layer on top of OAuth that lets clients verify user
  identity and obtain profile claims.
- [The Twelve-Factor App](https://12factor.net/) is a compact source for
  portable SaaS structure: codebase, dependencies, config, backing services,
  build/release/run, processes, port binding, concurrency, disposability,
  dev/prod parity, logs, and admin processes.

### Universal App Primitive Families

Identity and account lifecycle:

```text
registration_request_validate
user_account_create
email_verification_issue
email_verification_confirm
password_login_verify
session_issue
session_refresh
session_revoke
logout_all_devices
password_reset_request
password_reset_token_issue
password_reset_confirm
MFA_enrollment_start
MFA_challenge_verify
OIDC_auth_code_callback
user_profile_update
account_deactivate
account_delete_request
```

Authorization and tenant controls:

```text
role_assign
role_policy_eval
permission_matrix_extract
ABAC_policy_eval
tenant_scope_resolve
tenant_boundary_gate
resource_owner_check
service_account_issue
api_key_issue
api_key_rotate
api_key_revoke
admin_impersonation_gate
privileged_action_approval
```

Security and compliance controls:

```text
csrf_token_validate
rate_limit_apply
request_schema_validate
output_sanitize
security_headers_apply
secret_redact
secret_scan
password_hash
token_sign
token_verify
encryption_key_load
field_encrypt
field_decrypt
audit_event_emit
security_event_emit
data_retention_policy_apply
privacy_export_packet
delete_request_workflow
```

Core data and CRUD:

```text
db_connection_init
db_migration_apply
db_seed_apply
business_object_schema_bind
crud_endpoint_generate
crud_form_generate
admin_table_generate
soft_delete
archive_record
restore_record
record_version_write
record_history_read
import_csv_validate
export_csv_emit
search_index_update
cache_get_or_fill
```

Trackers that appear in many industries:

```text
customer_tracker_update
customer_timeline_emit
lead_tracker_update
support_ticket_tracker_update
subscription_tracker_update
order_tracker_update
inventory_tracker_update
project_tracker_update
asset_tracker_update
employee_tracker_update
vendor_tracker_update
contract_tracker_update
claim_tracker_update
case_tracker_update
analytics_event_track
```

Messaging, async, and integration:

```text
email_send
sms_send
push_notification_send
notification_preference_apply
webhook_signature_verify
webhook_event_dedupe
webhook_event_to_domain_event
queue_message_validate
queue_worker_execute
dead_letter_route
cron_schedule_execute
transactional_outbox_write
outbox_dispatch
idempotency_key_check
retry_policy_apply
```

Frontend and product surfaces:

```text
landing_page_shell
signup_form
login_form
password_reset_form
settings_page
profile_page
admin_dashboard
crud_admin_page
table_filter_sort_page
empty_state
error_state
toast_notification
onboarding_checklist
checkout_page
accessibility_check
responsive_layout_check
```

Ops, deployment, and observability:

```text
healthcheck_endpoint
readiness_probe
liveness_probe
structured_log_emit
metric_emit
trace_span_emit
alert_rule_generate
incident_runbook_emit
container_build
docker_compose_service
github_action_workflow
terraform_plan
kubernetes_deployment
kubernetes_job
cloud_function_deploy
rollback_plan
backup_job
restore_test
```

### Common App Primitive Groups

Password reset group:

```text
visible edge:
  PasswordResetRequest+TokenPolicy+DeliveryPolicy
    -> PasswordResetReceipt

hidden member edges:
  PasswordResetRequest -> IdentityLookupResult
  IdentityLookupResult -> AccountEnumerationSafeResponse
  IdentityLookupResult+TokenPolicy -> ResetToken
  ResetToken+DeliveryPolicy -> ResetEmailReceipt
  ResetToken+NewPassword -> PasswordUpdateReceipt
  PasswordUpdateReceipt -> SessionRevocationReceipt
  PasswordUpdateReceipt -> AuditEvent

proof requirements:
  token expiry test
  one-time-use test
  no account enumeration test
  rate-limit test
  session revocation test
  audit receipt schema test
```

Login and session group:

```text
visible edge:
  LoginAttempt+AuthPolicy+SessionPolicy
    -> SessionOrChallenge+AuthReceipt

hidden member edges:
  LoginAttempt -> CredentialValidationResult
  CredentialValidationResult -> RiskSignalSet
  RiskSignalSet+AuthPolicy -> MFARequiredDecision
  CredentialValidationResult+SessionPolicy -> SessionToken
  SessionToken -> SessionCookieOrBearerToken
  AuthDecision -> AuditEvent

proof requirements:
  bad password test
  locked account test
  MFA required test
  session expiry test
  secure cookie attribute test
  audit event test
```

Customer tracker group:

```text
visible edge:
  CustomerEventOrRecord+CustomerPolicy
    -> CustomerTimeline+CustomerReceipt

hidden member edges:
  CustomerEventOrRecord -> NormalizedCustomerRecord
  NormalizedCustomerRecord -> IdentityLinkedRecord
  IdentityLinkedRecord -> TimelineEvent
  TimelineEvent -> CustomerStateUpdate
  CustomerStateUpdate -> CustomerTimeline
  CustomerTimeline -> CustomerReceipt

proof requirements:
  identity resolution fixture
  duplicate event idempotency test
  timeline ordering test
  privacy boundary test
  deletion or retention policy test
```

CRUD resource group:

```text
visible edge:
  BusinessObjectSchema+CrudPolicy+RuntimePolicy
    -> CrudEndpointSet+CrudUiSpec+ContractReceipt

hidden member edges:
  BusinessObjectSchema -> ValidationSchema
  ValidationSchema -> CreateUpdateRequestSchemas
  CrudPolicy -> AuthorizationPolicy
  CreateUpdateRequestSchemas+AuthorizationPolicy -> EndpointSet
  EndpointSet -> OpenApiSpec
  EndpointSet+UiPolicy -> AdminCrudPage
  EndpointSet+ProofPolicy -> ContractReceipt

proof requirements:
  create/read/update/delete contract tests
  authorization tests
  invalid input tests
  soft-delete or archive tests
  OpenAPI schema test
```

Webhook ingestion group:

```text
visible edge:
  WebhookHttpRequest+WebhookPolicy
    -> DomainEvent+WebhookReceipt

hidden member edges:
  WebhookHttpRequest -> SignatureValidationReceipt
  SignatureValidationReceipt -> ParsedWebhookPayload
  ParsedWebhookPayload -> IdempotencyDecision
  IdempotencyDecision -> DomainEvent
  DomainEvent -> OutboxEvent
  OutboxEvent -> WebhookReceipt

proof requirements:
  signature verification test
  replay attack test
  malformed payload test
  idempotency test
  dead-letter route test
```

### Runtime Shapes

Each universal app primitive should be wrappable as:

```text
local function
REST endpoint
GraphQL resolver
MCP tool
queue worker
cron job
cloud function
Kubernetes job
GitHub Action
Terraform module
Helm chart
frontend component
admin page
test harness
```

### Why This Branch Is High Value

These primitives have unusually high reuse because they are:

```text
common across nearly every app
security-sensitive
easy to benchmark with fixtures
expensive when implemented badly
good candidates for deterministic assembly
good candidates for code generation only at the final wrapper layer
easy to convert into route portfolios
easy to sell as app accelerator packs
```

This branch should become a dedicated app skeleton primitive pack:

```text
base app skeleton families
+ language/framework overlays
+ auth/provider overlays
+ database overlays
+ industry overlays
+ compliance overlays
+ runtime wrappers
+ proof packs
= resolved app-build primitive routes
```

## Human, Staff, And Engineer Action Primitive Branches

Common human actions are also primitive candidates. Treat them as work-intent
routes that can be drafted, checked, queued, approved, executed, and receipted.
The important distinction is that many human-action primitives have externally
visible or irreversible side effects, so they need approval thresholds,
before/after state, rollback or compensation plans, and audit receipts.

The million-row seed bundle generated for this handoff includes explicit
`human_action_core` fields for this branch:

```text
actor_role
work_channel
action_intent
target_object
handoff_boundary
guardrails
receipt_expectation
```

High-value human-action primitive families:

```text
inbox_triage
email_check
email_reply
newsletter_send
calendar_schedule
staff_task_queue
approval_workflow
double_check_review
audit_review
complaint_management
refund_management
subscription_management
renewal_management
cancellation_management
customer_success_playbook
support_case_resolution
engineer_oncall_action
code_review_action
incident_response_action
admin_backoffice_action
finance_ops_action
sales_ops_action
hr_ops_action
legal_ops_action
data_merge_review
search_operation
crud_operation
staff_handoff
manager_approval
human_agent_collaboration
```

Representative visible edges:

```text
InboxState+TriagePolicy+UserRole
  -> PrioritizedMessageQueue+TriageReceipt

EmailThread+ReplyPolicy+CustomerContext
  -> ReplyDraft+SourceEvidenceReceipt

NewsletterDraft+AudiencePolicy+SendPolicy
  -> SendPreviewOrScheduledCampaign+NewsletterReceipt

ComplaintThread+ResolutionPolicy+AccountContext
  -> ResolutionPlan+ComplaintReceipt

RefundRequest+RefundPolicy+PaymentContext
  -> RefundDecisionOrApprovalRequest+RefundReceipt

SubscriptionChangeRequest+PlanPolicy+BillingContext
  -> SubscriptionMutationPlan+ApprovalOrExecutionReceipt

CrudMutationRequest+AuthorizationPolicy+RecordSchema
  -> RecordMutationPreview+CrudReceipt

SearchIntent+SourcePolicy+ResultSchema
  -> RankedResultSet+SearchReceipt

MergeCandidatePair+IdentityPolicy+HumanReviewPolicy
  -> MergeDecisionOrReviewPacket+MergeReceipt
```

Common guardrails:

```text
human approval required for irreversible actions
draft before send
preview before mutation
rollback or compensation plan
audit receipt required
customer notice policy
role scope check
tenant boundary check
amount limit check
rate limit and abuse check
no account enumeration
data minimization
```

Example group: complaint to refund decision.

```text
visible edge:
  ComplaintThread+RefundPolicy+CustomerAccountContext
    -> ResolutionPlan+RefundApprovalReceipt

hidden member edges:
  ComplaintThread -> ComplaintSummary
  ComplaintSummary+CustomerAccountContext -> EntitlementAndHistoryDigest
  EntitlementAndHistoryDigest+RefundPolicy -> RefundEligibilityDecision
  RefundEligibilityDecision -> DraftCustomerResponse
  RefundEligibilityDecision -> ApprovalRequestOrNoRefundReceipt
  ApprovalRequestOrNoRefundReceipt -> AuditReceipt

proof requirements:
  policy fixture test
  role authorization test
  amount threshold test
  draft-before-send test
  before/after state receipt test
  audit receipt schema test
```

Example group: data merge review.

```text
visible edge:
  MergeCandidateSet+IdentityPolicy+ReviewPolicy
    -> ApprovedMergePlanOrReviewQueue+MergeReceipt

hidden member edges:
  MergeCandidateSet -> SimilarityFeatureSet
  SimilarityFeatureSet -> MatchClusterCandidate
  MatchClusterCandidate+IdentityPolicy -> MergeRiskDecision
  MergeRiskDecision -> AutoMergePlanOrHumanReviewPacket
  AutoMergePlanOrHumanReviewPacket -> MergeReceipt

proof requirements:
  duplicate fixture test
  false-positive guard test
  survivorship rule test
  rollback plan test
  human-review threshold test
```

This branch is especially valuable because it turns daily staff work into
agentic, checkpointable work without pretending the agent should autonomously do
everything. The primitive should know whether it is allowed to draft, preview,
execute, schedule, or only prepare a human review packet.

## Visual, Math, And Animation Primitive Branches

Source surfaces to mine:

```text
Manim docs and examples
LLM-to-Manim research tasks
Three.js docs and examples
WebGL and WebGPU specs/docs
Babylon.js, PixiJS, D3, Observable, Vega-Lite
NIST DLMF formulas and plots
OpenStax / MIT OCW / textbook examples
research paper figures and equations
notebook visualizations
```

Useful references:

- [Manim Community docs](https://docs.manim.community/en/stable/)
- [Three.js docs](https://threejs.org/docs/)
- [Khronos WebGL specification](https://registry.khronos.org/webgl/specs/latest/1.0/)
- [MDN WebGPU API](https://developer.mozilla.org/en-US/docs/Web/API/WebGPU_API)
- [NIST Digital Library of Mathematical Functions](https://dlmf.nist.gov/)
- [MIT OpenCourseWare 6.006 Introduction to Algorithms](https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/)
- [Introduction to Algorithms, MIT Press](https://mitpress.mit.edu/9780262046305/introduction-to-algorithms/)

Candidate primitives:

```text
formula_to_manim_scene
formula_to_threejs_surface
latex_expression_to_svg
symbol_ledger_build
equation_step_visualize
parametric_curve_render
vector_field_render
phase_portrait_render
matrix_transform_animation
graph_algorithm_animation
geometry_construction_animation
probability_distribution_visualize
optimization_landscape_render
proof_step_to_visual_sequence
notebook_plot_to_interactive_scene
paper_figure_to_reproducible_spec
```

Compile targets:

```text
Manim Python scene
Three.js component
WebGPU shader pipeline
SVG/Canvas artifact
Vega-Lite or Observable notebook
HTML interactive explainer
video render job
image frame sequence
```

Proof receipts:

```text
symbol_consistency_receipt
formula_parse_receipt
render_smoke_test
frame_sequence_receipt
visual_diff_receipt
canvas_nonblank_receipt
axis_label_check
unit_scale_check
accessibility_alt_text_receipt
pedagogy_review_optional
```

Known failure modes:

```text
symbol drift between text, formula, and narration
incorrect domain or units
axis/scale mismatch
overlapping labels
blank canvas
wrong dimensional projection
animation timing hides the concept
generated code renders but teaches the wrong thing
```

## Three.js, Web Game, And Engine Primitive Branches

Source surfaces to mine:

```text
Three.js official examples and docs
Babylon.js docs
Phaser docs for 2D web games
PixiJS docs for high-performance 2D rendering
Unity render pipeline and profiler docs
Unreal Nanite, Lumen, ray tracing, and Unreal Insights docs
Godot rendering and performance docs
game templates, sample projects, shaders, asset pipelines
```

Useful references:

- [Phaser docs](https://docs.phaser.io/phaser/getting-started/what-is-phaser)
- [Unity render pipelines](https://docs.unity3d.com/Manual/render-pipelines.html)
- [Unity memory profiler docs](https://docs.unity3d.com/Manual/profiler-memory.html)
- [Unreal Nanite](https://dev.epicgames.com/documentation/en-us/unreal-engine/nanite-virtualized-geometry-in-unreal-engine)
- [Unreal Lumen](https://dev.epicgames.com/documentation/en-us/unreal-engine/lumen-global-illumination-and-reflections-in-unreal-engine)
- [Unreal hardware ray tracing](https://dev.epicgames.com/documentation/en-us/unreal-engine/hardware-ray-tracing-in-unreal-engine)
- [Unreal Insights](https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-insights-in-unreal-engine)
- [Godot rendering docs](https://docs.godotengine.org/en/stable/tutorials/rendering/index.html)
- [Godot performance docs](https://docs.godotengine.org/en/stable/tutorials/performance/index.html)

Candidate primitive families:

```text
scene_graph_create
camera_controls_bind
orbit_controls_attach
asset_loader_pipeline
gltf_optimize_and_load
texture_atlas_pack
sprite_sheet_animation
tilemap_collision_layer
ecs_component_emit
physics_body_bind
input_mapping_generate
game_loop_tick_compile
state_machine_for_player
level_streaming_plan
lod_strategy_select
instancing_strategy_select
object_pool_insert
shader_material_generate
postprocessing_chain_build
webgl_context_loss_handler
canvas_pixel_health_check
fps_budget_receipt_emit
memory_budget_receipt_emit
```

Rendering and performance primitive families:

```text
frustum_culling
occlusion_culling
batching_and_instancing
texture_compression_select
mipmap_policy_select
render_target_lifecycle
deferred_vs_forward_path_select
shadow_map_budget
screen_space_effect_gate
gpu_particle_system
compute_shader_dispatch
webgpu_buffer_layout
shader_compile_validate
draw_call_profile
frame_time_breakdown
gpu_memory_profile
```

Compile targets:

```text
Three.js scene module
Phaser scene
PixiJS renderer component
Unity prefab or script
Unreal Blueprint/C++ task spec
Godot scene/script
GLSL/WGSL shader module
asset import recipe
profiling checklist
```

Proof receipts:

```text
canvas_nonblank_receipt
asset_load_receipt
shader_compile_receipt
frame_budget_receipt
draw_call_count_receipt
memory_peak_receipt
input_response_receipt
physics_collision_fixture
mobile_viewport_receipt
visual_regression_receipt
```

## Ray Tracing And Rendering-Systems Branches

Source surfaces to mine:

```text
Ray Tracing in One Weekend
Physically Based Rendering
renderer source repos
shader toy examples
GPU path tracing examples
engine rendering docs
graphics course assignments
```

Useful references:

- [Ray Tracing in One Weekend](https://raytracing.github.io/)
- [Physically Based Rendering, fourth edition](https://pbr-book.org/4ed/contents)

Candidate primitives:

```text
ray_sphere_intersection
ray_triangle_intersection
aabb_intersection
bvh_build
bvh_traverse
material_bsdf_eval
importance_sampling_select
camera_ray_generate
path_trace_sample
denoise_pass_apply
tonemap_apply
gamma_correct
normal_map_decode
texture_sample_bilinear
monte_carlo_integrator
stratified_sampler
sobol_sampler
reservoir_sampling
```

Proof receipts:

```text
known_scene_pixel_fixture
intersection_numeric_tolerance
sampling_distribution_check
energy_conservation_check
render_hash_or_perceptual_diff
performance_profile
memory_profile
```

## Algorithm, Formula, And Textbook Primitive Branches

Treat textbooks and formula libraries as source surfaces for deterministic
primitive families, examples, proofs, and visualizations.

Candidate source surfaces:

```text
MIT Press CLRS
MIT OCW algorithm courses
NIST DLMF
Ray Tracing in One Weekend
PBRT
Open-source algorithm libraries
CP-Algorithms
The Algorithms repositories
Rosetta Code
Project CodeNet
```

Candidate primitive families:

```text
sort
search
heap
priority_queue
union_find
graph_traversal_bfs_dfs
shortest_path
topological_sort
flow_matching
dynamic_programming
segment_tree
fenwick_tree
trie
suffix_array
rolling_hash
fft_convolution
matrix_factorization
root_find
numeric_integrate
symbolic_simplify
formula_latex_parse
formula_to_test_fixture
algorithm_trace_emit
algorithm_visualize
```

Proof receipts:

```text
known_input_output_fixture
property_based_test
complexity_receipt
numeric_tolerance_receipt
algorithm_trace_receipt
cross_implementation_diff
source_reference_receipt
```

Important note: textbook-derived rows must not copy protected text. Extract
concept names, contracts, public examples where licensed, implementation
requirements, and proof obligations. Keep `source_refs` and license status
explicit.

## Distance, Similarity, LSH, And Indexing Branches

Distance and indexing methods are primitive families because they decide how
search, dedupe, clustering, and entity resolution scale.

Useful references:

- [datasketch MinHash LSH](https://ekzhu.com/datasketch/lsh.html)
- [scikit-learn nearest neighbors](https://scikit-learn.org/stable/modules/neighbors.html)
- [scikit-learn Manhattan distances](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.manhattan_distances.html)
- [Faiss documentation](https://faiss.ai/)

Candidate distance primitives:

```text
l1_manhattan_distance
l2_euclidean_distance
cosine_distance
jaccard_similarity
weighted_jaccard
hamming_distance
levenshtein_distance
jaro_winkler_similarity
phonetic_encode
haversine_distance
mahalanobis_distance
date_window_distance
money_amount_distance
address_similarity
name_similarity
embedding_distance
```

Candidate indexing primitives:

```text
brute_force_knn
kd_tree_index
ball_tree_index
leaf_size_tune
minhash_signature
minhash_lsh_index
simhash_signature
hnsw_index
faiss_index_select
product_quantization
inverted_file_index
blocking_key_generate
canopy_cluster
nearest_neighbor_graph_emit
ann_benchmark_score
```

Path-selection rule:

```text
small N or high precision -> brute force can win
low-dimensional structured data -> KDTree/BallTree can win
set/string shingles -> MinHash/LSH can win
embedding vectors at scale -> HNSW/Faiss/PQ can win
entity resolution -> blocking plus probabilistic comparison often wins
```

Proof receipts:

```text
recall_at_k
precision_at_k
candidate_pair_reduction
latency_p50_p95
memory_peak
false_positive_rate
false_negative_rate
threshold_sensitivity
index_rebuild_receipt
```

## Entity Resolution And Record Linkage Branches

Entity resolution should be a first-class primitive family. It sits at the
intersection of source search, matching, clustering, proof, privacy, and human
review.

Useful references:

- [BigQuery entity resolution framework](https://docs.cloud.google.com/bigquery/docs/entity-resolution-intro)
- [Splink docs](https://moj-analytical-services.github.io/splink/index.html)
- [Splink blocking rules](https://moj-analytical-services.github.io/splink/topic_guides/blocking/blocking_rules.html)

Candidate primitive families:

```text
record_standardize
name_normalize
address_normalize
phone_normalize
email_normalize
date_of_birth_normalize
blocking_rule_generate
blocking_rule_analyze
candidate_pair_generate
comparison_vector_emit
fellegi_sunter_score
term_frequency_adjust
probabilistic_match_train
threshold_tune
match_explain
cluster_links
canonical_entity_assign
clerical_review_packet
unlinkable_record_detect
entity_graph_emit
identity_resolution_receipt
```

BigQuery-style managed ER route:

```text
InputDataset+ProviderIdentityGraph+MatchParameters
  -> MatchedOutputDataset+JobStatusReceipt
```

This route is useful when matching should occur in-place through a provider
remote function or service boundary, with explicit read/write permissions,
output dataset, job status, and identity-provider logic.

Splink-style tunable ER route:

```text
RawRecordTable+BlockingRules+ComparisonSettings+ThresholdPolicy
  -> ClusteredEntityTable+MatchWeights+DiagnosticsReceipt
```

This route is useful when the project needs transparent probabilistic linkage,
blocking analysis, match weights, threshold tuning, and interactive diagnostics.

Leaf/block based record processing routes:

```text
RecordBatch -> NormalizedLeaves -> BlockingKeys -> CandidatePairs
CandidatePairs -> ComparisonVectors -> MatchScores -> LinkGraph
LinkGraph -> ConnectedComponents -> CanonicalEntities
```

The "leaf" idea should be tested in two senses:

```text
tree leaves:
  KDTree/BallTree leaf_size controls where tree search switches to local brute force.

record leaves:
  split records into comparable atomic leaves such as name token, address token,
  date part, phone segment, email domain, source-system key, geohash, or entity
  attribute shard; compare and aggregate leaf receipts.
```

Proof receipts:

```text
labeled_pair_precision_recall
cluster_precision_recall
pairwise_f1
threshold_curve
blocking_reduction_ratio
false_merge_review
false_split_review
explainability_packet
privacy_boundary_receipt
human_clerical_review_receipt
```

Known failure modes:

```text
loose blocking creates too many pairs
tight blocking misses true matches
common names over-link
missing fields under-link
household/family records merge incorrectly
source-system IDs are reused or dirty
address normalization changes over time
threshold tuned on one population fails on another
probabilistic score is mistaken for truth
```

## Place, Facility, Open-Data, And Geospatial Branches

Places are evidence-backed entities: resolve providers/facilities across
sources, attach provenance, geocoding confidence, freshness, coverage gaps,
uncertainty, and catchment/context signals. The reusable capability is:

```text
place/entity discovery
+ source-backed evidence
+ entity resolution
+ open-map enrichment
+ spatial analysis
+ public-dataset ingestion
+ map/dashboard/report output
+ replayable proof receipt
```

Canonical visible edge:

```text
AreaOfInterest+DirectedQuestion+SourcePolicy+ExtractionSchema
  -> EvidenceBackedAnswer+SourceBundle+SpatialArtifacts+UncertaintyReport
```

Source surfaces to mine (official-first):

```text
HRSA health center datasets
CMS NPPES/NPI registry + CMS provider data catalog
OSM healthcare tags / Healthsites / WHO GHFD
CareerOneStop training-provider APIs + state ETPL lists
College Scorecard API + NCES IPEDS
OSM Overpass / Nominatim (usage-policy gated) / Overture / OpenAddresses
Census TIGER/TIGERweb + ArcGIS Hub layers
CKAN (Data.gov), Socrata SODA, ArcGIS FeatureServer, OGC API Records
GeoPandas / DuckDB Spatial / PostGIS / OSMnx / OSRM / openrouteservice / H3 / S2
```

Candidate primitive families (P0 build order lives in the intake briefs):

```text
source_surface_registry
ckan_package_resource_harvester
socrata_soql_dataset_ingester
arcgis_featureserver_layer_ingester
hrsa_health_center_ingester
nppes_provider_identity_resolver
careeronestop_training_provider_adapter
college_scorecard_ipeds_program_adapter
osm_overpass_bounded_poi_query
overture_openaddresses_place_ingester
dataset_schema_fingerprint
entity_normalize_and_dedupe
geocode_policy_gate
point_to_boundary_spatial_join
nearest_facility_isochrone_catchment_analysis
map_artifact_generation
evidence_bundle_wrapper
portal_change_monitor
```

Proof receipts:

```text
entity_match_precision
official-vs-open coverage comparison
geocode confidence + boundary vintage receipts
attribution_complete + license status
freshness_recorded
spatial join / isochrone method receipts
map_artifact_correctness (non-blank, labeled, attributed)
```

Hard boundaries: directory/access/planning outputs only — never patient-level
data, diagnosis, treatment advice, or final legal/compliance conclusions;
respect source usage policies (e.g. Nominatim) and record attribution.

## Non-Commitment Principle

Do not commit the system to one way of generating primitives, one way of
searching for them, one way of compiling routes, or one way of proving them.

The product should maintain a portfolio of paths:

```text
generation paths
search paths
route-planning paths
compilation paths
runtime-lowering paths
proof paths
repair paths
promotion paths
negative-memory paths
```

Every path should produce comparable receipts. Data, metrics, policy, and
logic decide which path wins for a given task.

The route compiler should ask:

```text
Which path solves this task with the least source escalation, least runtime
model use, strongest proof, lowest side-effect risk, and best reuse value?
```

## Problem-Solution As A Primitive Core

Do not limit a primitive to a function description plus input and output
description. A primitive needs two layers:

```text
compact contract:
  search/routing card shown first

problem-solution contract:
  deeper operational card used for planning, implementation, proof, repair,
  ranking, caching, and promotion
```

The compact contract stays small:

```text
id
version metadata
title
input_edge
output_edge
blackbox behavior
effects
runtime targets
proof status
candidate/truth boundary
links to problem_solution, route, proof, telemetry, and source records
```

The problem-solution contract is a first-class component of the primitive:

```text
problem statement
user trigger
affected actor or role
industry/domain/context
country/region/jurisdiction when relevant
stakes and cost of failure
current bad workaround
non-goals
fragile context that may change
solution hypothesis
deterministic route summary
model-assisted route summary
data transformations
required source evidence
acceptance criteria
proof obligations
failure modes
troubleshooting hooks
negative-memory queries
cache and materialization hints
telemetry metrics
promotion and retirement rules
```

This means a primitive answers all of these, not just "what function can be
called?":

```text
What real problem does this solve?
Who asks for it and why?
What input shape starts the problem?
What output artifact proves the problem was handled?
What transformations happen?
What should be deterministic?
Where may a model, LoRA, mini-agent, or ranker help?
What data and source snapshots did it rely on?
What proof says it works?
What usually fails?
What telemetry should improve the next route?
What should be cached, grouped, or suppressed?
```

Example shape:

```json
{
  "primitive_card": {
    "id": "primitive/customer-record-import",
    "version": "0.2.0",
    "lifecycle": "candidate",
    "title": "Customer record import",
    "input_edge": "RawCustomerRecordBatch+ImportPolicy+ExistingCustomerIndex",
    "output_edge": "PreparedCustomerImport+ImportReceipt",
    "blackbox": {
      "does": "Validates, normalizes, deduplicates, and prepares customer records for a target system."
    },
    "effects": [
      "artifact_write"
    ],
    "candidate": true,
    "serves_truth": false,
    "detail_refs": {
      "problem_solution": "problem-solution/customer-record-import",
      "route_portfolio": "route-portfolio/customer-record-import",
      "telemetry_family": "telemetry/customer-record-import",
      "negative_memory": "negative-memory/customer-record-import"
    }
  },
  "problem_solution": {
    "id": "problem-solution/customer-record-import",
    "version": "0.2.0",
    "problem": {
      "statement": "Teams repeatedly need to import customer records from messy external files without dropping identifiers, merging the wrong people, or creating non-idempotent writes.",
      "user_triggers": [
        "upload customer CSV",
        "sync CRM contacts",
        "migrate account records",
        "dedupe customer export"
      ],
      "stakes": [
        "duplicate customer records",
        "lost source identifiers",
        "wrong account association",
        "unsafe retry behavior"
      ],
      "non_goals": [
        "do not infer legal identity from weak evidence",
        "do not write to production CRM without an execution policy"
      ],
      "fragile_context": [
        "target CRM schema changes",
        "source export columns drift",
        "identity rules vary by region and industry"
      ]
    },
    "solution": {
      "route_summary": [
        "profile input records",
        "infer or bind schema",
        "normalize identity fields",
        "generate candidate duplicates",
        "score likely matches",
        "emit import preview",
        "write receipt"
      ],
      "deterministic_steps": [
        "schema validation",
        "field mapping",
        "idempotency key generation",
        "receipt emission"
      ],
      "model_assisted_steps": [
        "field alias suggestion",
        "ambiguous match explanation",
        "troubleshooting summary"
      ],
      "acceptance_criteria": [
        "line count preserved unless quarantined with reason",
        "source record id preserved",
        "dedupe threshold recorded",
        "dry-run receipt available before mutation"
      ]
    },
    "candidate": true,
    "serves_truth": false
  }
}
```

Important: this repo allows versioning through the `version` metadata field and
lineage fields. Do not put versions in the immutable ID, slug, or file name.

### Problem-Solution Fields To Index

The problem-solution layer should be searchable and rankable, not just prose.

Index these fields separately:

```text
problem_statement_embedding
trigger_phrase_embedding
industry_domain_embedding
jurisdiction_embedding
input_edge_embedding
output_edge_embedding
solution_route_embedding
failure_mode_embedding
troubleshooting_embedding
negative_memory_embedding
proof_requirement_embedding
```

Use lexical search too:

```text
exact business object names
website/platform names
schema names
error messages
legal/jurisdiction terms
country/region names
algorithm names
database dialect names
metric names
```

This lets the system match both:

```text
"dedupe messy customer CSV before CRM import"
```

and:

```text
RawCustomerRecordBatch+ImportPolicy+ExistingCustomerIndex
  -> PreparedCustomerImport+ImportReceipt
```

### Version, Lineage, And Data Tracking

Versioning is required, but keep it metadata-only:

```text
primitive version
problem-solution version
route portfolio version
strategy genome version
model component version
LoRA adapter version
ranker version
embedding model version
schema version
source snapshot version
dataset version
proof harness version
cache policy version
telemetry schema version
```

Every meaningful change should record:

```text
changed fields
reason for change
source evidence
backward compatibility
affected routes
affected caches
affected proofs
benchmark replay required
supersedes
superseded_by
deprecation window
rollback path
```

For data-bearing primitives, track:

```text
dataset_id
dataset_version
source_snapshot_hash
schema_hash
row_count
column_count
sample_policy
privacy_boundary
license_or_terms_status
freshness_timestamp
run_date
commit_sha
producer_strategy
validation_receipts
```

A primitive is not only "latest description." It is:

```text
description
+ problem_solution
+ data lineage
+ model lineage
+ route lineage
+ proof lineage
+ telemetry history
+ promotion state
```

### Strategy Genome Records

Make every search, model, ranker, compiler, proof, cache, and fallback choice
explicit in a strategy record:

```json
{
  "strategy_genome": {
    "id": "strategy/customer-record-import",
    "version": "0.4.0",
    "task_family": "customer_record_import",
    "components": {
      "decomposer": "model-slot/request-decomposer",
      "retriever": "search/hybrid-edge-schema-vector",
      "reranker": "ranker/primitive-cross-encoder",
      "planner": "model-slot/route-planner",
      "compiler": "compiler/plan-delta-to-plan-lock",
      "proof_policy": "proof-policy/contract-fixture-smoke",
      "cache_policy": "cache-policy/source-contract-route"
    },
    "parameters": {
      "candidate_bundle_size": 12,
      "max_context_depth": "behavior-card",
      "source_fallback_threshold": 0.62,
      "exploration_rate": 0.05
    },
    "candidate": true,
    "serves_truth": false
  }
}
```

This gives the system something concrete to mutate, compare, replay, promote,
or retire.

## Model, Adapter, Ranker, And Telemetry Layer

Models, LoRA adapters, mini agents, local rankers, and heuristic scorers must
be first-class path components. They should be selected, tested, swapped, and
ranked just like primitives.

Do not treat the "model" as a single global dependency. Treat it as a portfolio
of task-specific slots:

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
```

Each slot can be served by multiple kinds of model or scorer:

```text
deterministic rule
SQL or graph query
local classifier
embedding model
cross-encoder ranker
small local language model
domain LoRA adapter
vision-language model
cloud frontier model
human review queue
```

The system should record which model path was used and why:

```json
{
  "model_route_receipt": {
    "slot": "request_decomposer_model",
    "selected_model_path": "local_small_model",
    "adapter": "primitive_decomposition_adapter",
    "fallbacks_considered": [
      "rule_based_decomposer",
      "frontier_model_decomposer"
    ],
    "selection_reason": [
      "low_risk_task",
      "cached_schema_available",
      "latency_budget_tight"
    ],
    "metrics_recorded": [
      "decomposition_accuracy_proxy",
      "tokens",
      "latency_ms",
      "compile_success",
      "downstream_proof_pass"
    ],
    "candidate": true,
    "serves_truth": false
  }
}
```

### LoRA And Adapter Lanes

LoRAs and other PEFT adapters are useful because many primitive steps are
repeated, narrow, and domain-shaped:

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
```

The goal is not to fine-tune everything. The goal is to let cheap adapters
compete against rules, retrieval, larger models, and human review on bounded
tasks.

Adapter records should include:

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

Use adapters only when they produce measurable downstream lift:

```text
better candidate recall
better route compile success
less source escalation
fewer false primitive matches
faster proof generation
better repair success
lower cost at same quality
```

### Mini-Agent And Micro-Policy Lanes

Small agentic models should be allowed, but only inside bounded jobs with
budgets and receipts.

Candidate micro-agent slots:

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
```

Each micro-agent run needs a strict envelope:

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

Micro-agents should be compared against deterministic alternatives. A
micro-agent only wins if it improves proofed outcomes, not if it writes a more
persuasive explanation.

### Simultaneous Trial Runs

The system should sometimes run multiple paths at the same time:

```text
exact_edge_search vs hybrid_search vs graph_route_search
rule_decomposer vs local_model_decomposer vs frontier_model_decomposer
template_slot_fill vs PlanDelta_compile vs source_fallback
brute_force_entity_resolution vs Splink_route vs BigQuery_managed_route
Three.js_scene_template vs Manim_scene_template vs WebGPU_shader_route
```

Trial manager primitive:

```text
TaskIntent+ExperimentPolicy+PathPortfolio
  -> ParallelTrialRunSet+ComparisonReceipt
```

Comparison receipt:

```text
path_id
random_seed
parameters
model_slot_assignments
primitive_bundle
route_candidate
compile_status
proof_status
latency
token_cost
source_read_depth
side_effects
artifact_quality_metrics
downstream_reuse_signal
winner_reason
loser_negative_memory
```

Parallelism should be selective. Use it when uncertainty is high, task value is
high, or the system is gathering evidence for a path family. For routine tasks,
use the current champion route and sample challengers at a low rate.

### Random Sprouting And Parameter Search

The system should deliberately sprout new variants from successful and failed
paths:

```text
mutate_blocking_rule
mutate_threshold
mutate_retriever_weights
mutate_context_depth_limit
mutate_candidate_bundle_size
mutate_model_slot_assignment
mutate_LoRA_adapter_choice
mutate_route_member_order
mutate_proof_gate_order
mutate_cache_policy
mutate_visual_render_settings
mutate_shader_precision
```

Exploration policies to test:

```text
random_search
grid_search_for_small_spaces
bayesian_optimization
successive_halving
population_based_training
evolutionary_mutation
multi_armed_bandit
contextual_bandit
MCTS_route_search
novelty_search
active_learning
human_review_sampling
```

Sprouted variants must be labeled as experiments:

```json
{
  "path_sprout": {
    "parent_path": "route:entity_resolution_splink_transparent",
    "mutation": "threshold_policy",
    "parameters": {
      "candidate_pair_cap": "medium",
      "clerical_review_band": "wider"
    },
    "selection_policy": "bayesian_optimization",
    "status": "candidate",
    "serves_truth": false
  }
}
```

Promote only if a sprout wins on held-out tasks, not only on the task that
created it.

### Ongoing Telemetry

Every path should emit telemetry that can improve future routing:

```text
request_decomposition_trace
candidate_retrieval_trace
reranking_trace
primitive_cooccurrence_trace
route_compile_trace
proof_execution_trace
model_slot_trace
cache_hit_miss_trace
source_escalation_trace
repair_loop_trace
human_review_trace
```

Core metrics:

```text
task_success
proof_success
compile_success
tokens_to_plan
tokens_to_pass
latency_p50
latency_p95
source_read_depth
source_files_read
model_calls_by_slot
adapter_calls_by_slot
cache_hit_rate
primitive_reuse_count
route_reuse_count
false_match_rate
false_block_rate
repair_attempts
negative_memory_created
human_review_rate
artifact_quality_score
downstream_regression_rate
cost_per_success
```

Use OpenTelemetry-like trace spans so a single request can be inspected as:

```text
decompose_request
retrieve_candidates
rerank_candidates
compile_route
run_trial_path
execute_proofs
emit_receipts
promote_or_record_negative_memory
```

### Primitive Co-Occurrence And Decomposition Learning

The registry should learn which primitives often appear together:

```text
csv_profile + schema_infer + schema_validate
blocking_key_generate + candidate_pair_generate + comparison_vector_emit
openapi_operation_extract + auth_scope_review + contract_test_generate
threejs_scene_create + camera_controls_bind + canvas_nonblank_receipt
shader_compile_validate + frame_budget_receipt + visual_regression_receipt
legal_source_search + effective_date_check + jurisdiction_filter
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

### Cache And Materialization Layer

Cache at multiple levels:

```text
source_surface_card_cache
schema_fingerprint_cache
edge_signature_cache
embedding_cache
candidate_bundle_cache
route_skeleton_cache
PlanLock_cache
proof_fixture_cache
execution_receipt_cache
negative_memory_cache
render_asset_cache
entity_resolution_block_cache
```

Cache policy should be path-specific:

```text
never_cache_sensitive_data
cache_source_refs_not_raw_private_payloads
cache_promoted_routes_longer
cache_candidate_routes_shorter
invalidate_on_schema_change
invalidate_on_api_version_change
invalidate_on_legal_effective_date_change
invalidate_on_benchmark_regression
invalidate_on_model_or_adapter_change
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

### Champion, Challenger, And Retirement Logic

Each task family should maintain a current champion path and challengers:

```text
champion_route
challenger_routes
exploration_rate
promotion_gate
retirement_gate
rollback_path
```

Ranking should be multi-objective:

```text
success_rate
proof_strength
cost
latency
source_escalation_depth
privacy_risk
side_effect_risk
maintenance_cost
reuse_count
freshness
human_review_burden
```

Best-to-worst ranking should be explicit for every comparable path family, but
the ranking should be contextual. The best entity-resolution path for a small,
labeled, transparent compliance workflow may not be the best path for a large
managed cloud match job.

## What To Borrow

Borrow the operating ideas:

```text
compile-time LLM use
zero or bounded runtime model calls
template-bounded generation
static graph validation
contract validation
security validation
sandboxed execution
fixture and benchmark gates
token amortization curves
break-even task accounting
deterministic receipts
regeneration only from validation errors
```

Rename and extend them for this system:

```text
Generated code artifact -> PlanLock or route artifact
Template -> primitive group / runtime wrapper
Validation pipeline -> proof obligations
Runtime logs -> execution receipts
Failed compilation -> negative memory
Cost curve -> route economics
```

## Do Not Narrow The Product

Do not make this repo's strategy:

```text
generate code once and run it
```

That is a good slice, but too small.

The strategy is:

```text
search first
reuse first
remix deterministically
generate only the missing edge
prove every route
promote only after receipts
remember failed matches
```

The strongest product phrase for internal architecture is:

```text
proof-aware primitive route market
```

For user-facing copy, keep PlanLock/CandidateBundle internals behind the
advanced view unless the audience is technical.

## Primitive Generation Paths

Keep these paths available and measurable:

| Path | What it does | When it should win |
| --- | --- | --- |
| `source_adapter_extract` | Mines OpenAPI, AsyncAPI, MCP, PyPI, npm, GitHub Actions, Terraform, Helm, docs, and benchmark sources into candidate cards | Source surface is machine-readable or well-structured |
| `marketplace_listing_extract` | Converts marketplace listings, workflow templates, app directories, data products, and cloud packages into capability cards | The market already exposes repeated buyer problems |
| `benchmark_task_demand_extract` | Converts BFCL, DocILE, SWE-bench, Terminal-Bench, AppWorld, MLE-bench, and similar tasks into primitive demands | Benchmark has executable or labeled evaluation |
| `trace_to_workflow_mine` | Converts successful agent/tool traces into structured route candidates | A task was solved once but should become reusable |
| `workflow_template_mine` | Mines n8n, Zapier, Make, Pipedream, Apple Shortcuts-like datasets, CI files, DAGs, and runbooks | Existing workflow ecosystem encodes domain practice |
| `repo_symbol_surface_extract` | Extracts public APIs, CLI commands, functions, schemas, config surfaces, and tests from repos | Codebase has reusable local capabilities |
| `schema_to_primitive_emit` | Converts schemas and standards into validators, mappers, wrappers, and proof obligations | JSON Schema, FHIR, XBRL, GS1, OpenAPI, protobuf, GraphQL, or dbt contracts exist |
| `human_curated_seed` | Lets a curator define a compact primitive or route demand manually | Domain is high-risk, underdocumented, or strategically important |
| `model_draft_candidate` | Uses a model to draft a candidate from a clear brief | Useful only as L1 draft; never promoted without source/proof |
| `negative_memory_to_gap` | Turns repeated failures and near misses into new primitive demands | Agents repeatedly choose wrong tools, stale sources, or unsafe adapters |

Ranking should not prefer one path globally. Rank by per-task evidence.

## Primitive Search Paths

Use multiple retrieval modes and compare them:

```text
exact edge search
type-compatible edge search
schema/contract search
lexical BM25 search
embedding similarity search
hybrid lexical+dense search
graph route search
known-chain / route-template search
source-ref search
benchmark-task search
marketplace-source search
negative-memory search
industry/country/schema overlay search
runtime-shape search
proof-requirement search
```

Search should return a `CandidateBundle`, not a single answer. The bundle should
include:

```text
best exact matches
near matches
route templates
mutator candidates
source refs
proof obligations
negative memory warnings
fallback escalation options
ranking explanation
```

Retrieval methods to test:

```text
BM25 only
dense embeddings only
hybrid BM25+dense
query expansion
HyDE-style hypothetical card search
RAG-Fusion / reciprocal rank fusion
graph-neighborhood expansion
schema-aware retrieval
source-authority reranking
freshness-aware reranking
negative-memory reranking
```

The system should record which search path found the winning route.

## Route Planning Paths

Treat route planning as a portfolio, not one planner:

| Planner | Shape | Use when |
| --- | --- | --- |
| `exact_route_lookup` | fetch promoted route by matching edge | High-confidence repeated demand |
| `template_slot_fill` | fill a primitive group template with selected overlays | Known family with variant dimensions |
| `deterministic_graph_search` | find compatible multi-step path through typed edges | Contracts are well-typed |
| `contract_diff_remix` | adapt near-match route using deterministic mutators | Similar route exists but fields/runtime differ |
| `llm_plan_delta` | model proposes compact PlanDelta over candidate cards | Ambiguity remains after deterministic search |
| `tree_or_graph_of_routes` | explore alternative route branches with scoring | Many plausible paths exist |
| `mcts_route_search` | sample and score route plans using proof/cost feedback | Search space is large and metrics are available |
| `evolutionary_route_search` | mutate and recombine successful route fragments | ML/data-science or optimization workflows |
| `trace_replay_compile` | reconstruct route from a successful trace | A prior ad hoc agent run worked |
| `human_review_route` | human chooses or edits route before compile | Regulated or high-side-effect workflow |

The route planner output is still candidate state until compiled, tested, and
receipted.

## Compilation Paths

Different routes should lower into different compiled artifacts:

```text
PlanLock canonical JSON
Python callable
TypeScript function
FastAPI endpoint
MCP tool wrapper
CLI command
queue consumer
cron job
Temporal activity
Airflow task
Dagster asset
dbt model
SQL query or view
browser automation script
OpenAPI client wrapper
Terraform plan/module wrapper
Kubernetes job or Helm values
guardrail policy bundle
human-review checklist
dashboard/report artifact
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

The executor should run the compiled artifact or PlanLock, not free-form model
text.

## Runtime And Execution Paths

Runtime should be selected by effects, latency, scale, security, and proof:

```text
local pure function
container job
serverless function
API middleware
MCP prehook
queue worker
browser worker
workflow engine
Kubernetes job
CI/CD action
database job
human-review queue
```

Support these execution patterns:

```text
strict deterministic execution
bounded LLM subcall under schema and policy
parallel tool execution
future/asynchronous tool execution
retry with idempotency key
compensation/rollback route
human approval before side effect
dry-run preview before mutation
shadow execution before promotion
```

Every runtime path must emit an execution receipt.

## Proof And Validation Paths

Use layered validation. Different primitives need different proof routes:

```text
schema validation
contract tests
unit tests
golden fixtures
roundtrip tests
idempotency tests
side-effect audit
privacy/PII boundary test
source-span verification
citation support check
license/terms gate
security/static-analysis scan
sandbox execution
benchmark scorecard
freshness/effective-date check
human review
regression replay
shadow production comparison
```

Promotion should require enough proof for the domain, not the same proof for
every primitive. A zero-side-effect formatting primitive needs lighter proof
than a healthcare, legal, finance, cloud-deploy, or data-export route.

## Repair And Improvement Paths

When compilation or execution fails, do not default to "ask the model again."
Try repair paths in order of evidence:

```text
read failure receipt
retrieve negative memory
classify failure layer: search, contract, adapter, runtime, source, proof
try deterministic mutator
try alternate route from same CandidateBundle
escalate one context ladder level
run focused source-ref resolver
allow bounded model micro-repair
recompile and rerun proof
write negative memory if still failing
create new primitive demand if gap is real
```

Model retries should be targeted by validation errors, not open-ended.

## Ranking And Decision Logic

Use a route portfolio and score every path with comparable fields:

```text
task_success_probability
compile_success_probability
proof_strength
source_authority
freshness_confidence
contract_fit
negative_memory_risk
effect_risk
privacy_risk
runtime_latency
runtime_cost
compile_cost
tokens_to_plan
runtime_llm_tokens
source_context_tokens
route_reuse_count
tokens_avoided_to_date
promotion_level
human_review_required
```

Start with a transparent weighted score. Move to contextual bandits or other
online ranking only after receipts accumulate.

Suggested initial score shape:

```text
route_score =
  proof_strength
  + source_authority
  + contract_fit
  + reuse_value
  - effect_risk
  - negative_memory_risk
  - freshness_risk
  - total_cost
  - source_escalation_depth
```

The score is a ranking aid, not truth.

## Metrics Decide The Path

Every experiment should compare paths on:

```text
success rate
first-pass compile rate
first-pass proof rate
token cost
wall-clock latency
source files/docs read
context depth reached
runtime model calls
side-effect safety
human review load
route reuse
new primitive/group creation
negative-memory creation
regression stability
```

Winning paths should be promoted by evidence:

```text
observed_success
proof_receipts
repeat reuse
low regression rate
low side-effect risk
clear source refs
freshness policy
```

Losing paths should produce negative memory, not disappear silently.

## Compile Lifecycle

Use this lifecycle for primitive route candidates:

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
L10 promoted, deprecated, or negative-memory only
```

Default remains:

```text
candidate=true
serves_truth=false
```

No model lane can promote truth by itself.

## Benchmark Harness To Build

Build a small first harness before scaling.

Start with 50 to 100 tasks across:

```text
BFCL-style function/tool routing
DocILE-style document extraction
SWE-bench-style repo repair/source escalation
Terminal-Bench-style CLI/runtime tasks
AppWorld-style API-state transition tasks
Kaggle or MLE-bench-style data-science workflows
OpenAPI/AsyncAPI/MCP registry primitive factories
Terraform/GitHub Actions/Kubernetes deployment wrappers
```

Compare these arms:

```text
A1 baseline runtime agent
A2 baseline agent with repo/search/RAG context
A3 compiled-code/template generation
A4 primitive-first CandidateBundle + deterministic remix
A5 primitive-first source fallback
```

Track:

```text
task_success
tokens_to_plan
tokens_to_pass
runtime_llm_tokens
source_files_or_docs_read
source_context_tokens
depth_to_solution
compile_success
proof_success
route_reuse
new_group_created
negative_memory_created
break_even_tasks
tokens_avoided_to_date
cost_per_success
```

The headline is not only pass/fail. The headline is:

```text
how shallow the system solved the task
how much context it avoided reading
how much runtime model use it eliminated
how much reusable route memory it created
```

## Depth-To-Solution Ladder

Record the deepest level needed:

```text
L1 edge card only
L2 contract card
L3 behavior card
L4 route card
L5 proof card
L6 source slice
L7 full source/docs/repo
```

This is the benchmark story:

```text
Primitive-first solved X% of tasks before full source escalation.
Primitive-first reduced tokens by Y%.
Primitive-first reused existing routes Z% of the time.
Primitive-first created N reusable route groups and M negative-memory records.
```

Keep these as placeholders until measured by scripts.

## Existing Local Assets To Reuse

Recent seed packs and handoffs already exist in the wider ecosystem. Reuse them
instead of inventing parallel schemas:

```text
docs/codex/primitive-family-expansion-handoff.md
docs/codex/primitive-variation-dimension-atlas-handoff.md
docs/codex/primitive-customization-overlays-handoff.md
docs/codex/primitive-agent-graph-path-mixtures-handoff.md
docs/codex/primitive-cloud-guardrail-runtime-handoff.md
docs/codex/high-priority-primitive-opportunity-rankings-handoff.md
docs/codex/primitive-problem-solution-details-handoff.md
docs/codex/marketplace-primitive-source-surfaces-handoff.md
docs/codex/aidevobserver-compiled-ai-evaluation-plan.md
```

Focused checkers:

```bash
python3 scripts/check_primitive_problem_solution_details.py --self-test
python3 scripts/check_high_priority_primitive_opportunity_rankings.py --self-test
python3 scripts/check_marketplace_primitive_source_surface_pack.py --self-test
python3 scripts/check_primitive_variation_dimension_atlas.py --self-test
python3 scripts/check_primitive_cloud_guardrail_runtime.py --self-test
python3 scripts/check_primitive_customization_overlays.py --self-test
python3 scripts/check_primitive_agent_graph_path_mixtures.py --self-test
python3 scripts/check_aidevobserver_compiled_ai_evaluation.py --self-test
python3 scripts/check_compiled_primitive_route_benchmark_seeds.py --self-test
python3 scripts/build_primitive_pipeline_catalog_intake.py --self-test
```

Repo-level sanity checks:

```bash
python3 scripts/check_handoff_docs_freshness.py --self-test
python3 scripts/check_ai_done_right_surface_family.py --self-test
python3 scripts/check_portfolio_dependency_law.py --self-test
```

## Next Build Slice (BUILT 2026-07-01)

The generated seed pack for compiled primitive benchmarks now exists in the
wider ecosystem:

```text
catalog/knowledge-packs/data/compiled-primitive-route-benchmark-seeds/
```

Builder (the single source — never hand-edit pack files) and checker:

```bash
python3 scripts/build_compiled_primitive_route_benchmark_seeds.py --write
python3 scripts/check_compiled_primitive_route_benchmark_seeds.py --self-test
```

Both are registered in `scripts/flywheel_proof_modules.py` and run under
`scripts/run_proofs.py`. Recompute counts from the pack `manifest.json`
(`row_counts` / `total_rows` / `content_sha256` are computed, never typed).

Files emitted (the originally suggested set, plus the adaptive-optimization
layer this handoff specifies — model/adapter/micro-agent lanes, trial runs,
sprouting, telemetry, co-occurrence, cache, champion/challenger, training
capture):

```text
manifest.json
benchmark_sources.jsonl
benchmark_task_demands.jsonl
primitive_generation_paths.jsonl
primitive_search_paths.jsonl
route_planning_paths.jsonl
compilation_paths.jsonl
proof_paths.jsonl
runtime_execution_paths.jsonl
repair_ladder.jsonl
comparison_arms.jsonl
scorecard_fields.jsonl
route_portfolio_examples.jsonl
compiled_route_lifecycle.jsonl
route_economics_model.json
model_slot_lanes.jsonl
adapter_lanes.jsonl
micro_agent_envelopes.jsonl
trial_run_policies.jsonl
exploration_policies.jsonl
path_sprout_rules.jsonl
telemetry_signals.jsonl
primitive_cooccurrence_examples.jsonl
cache_policies.jsonl
strategy_genome_examples.jsonl
champion_challenger_policy.json
route_attempt_training_capture_policy.json
```

Comparison arms cross-reference the Benchmark Lab adapter catalog's A0..A8
arms and L1..L7 depth ladder (imported from
`scripts/build_benchmark_lab_adapter_catalog.py`, never re-typed), and the
registry-factory source aligns with
`catalog/knowledge-packs/data/marketplace-primitive-source-surfaces`.

Validation rules (ENFORCED by the checker, plus referential integrity across
all path/slot/proof/cache references and a freshness gate that goes red on
hand-edited pack files):

```text
all rows candidate=true and serves_truth=false
every benchmark source has source_status and adapter_state
every task demand declares input_edge and output_edge
every comparison arm declares allowed model/runtime behavior
every scorecard includes token, proof, depth, and reuse metrics
every path record declares when it should win and how it can fail
every route portfolio includes at least three candidate paths
no benchmark claim is promoted without adapter receipts
no external paper number is treated as local measured evidence
model slots keep a >=2-lane portfolio and receipt every selection
adapters carry training-data lineage plus promotion/rollback receipts
micro-agent envelopes stay bounded (steps/tokens/wall-time/stop conditions)
sprouts stay candidate-isolated; promotion requires held-out wins
telemetry covers every declared feedback loop
caches declare invalidation triggers and the privacy rule
```

## Catalog Intake And Multi-Lane Generation Slice (BUILT 2026-07-01)

The owner-provided candidate catalog `primitive_pipeline_catalog_8000.md`
(repo root; 8,000 rows = 200 pipeline families x 20 industries x runtime
shapes) is consumed by ONE intake builder that feeds FOUR generation lanes —
recompute all counts from the intake manifest, never type them:

```bash
python3 scripts/build_primitive_pipeline_catalog_intake.py --self-test
python3 scripts/build_primitive_pipeline_catalog_intake.py --date-prefix <day> --write
```

Outputs (all candidate=true / serves_truth=false; registered in
`scripts/flywheel_proof_modules.py`):

```text
catalog_intake/<day>-c8k1/catalog_rows_staged.jsonl   lossless raw layer (every catalog row)
batch_runs/<day>-c8kdet/.../extracted_candidates.jsonl deterministic lane: deduped verifier-shape
                                                       family cards (zero model tokens; industry/
                                                       runtime preserved as variation_profile)
daily_shards_catalog8k/<day>-c8k1/shards.jsonl         Ollama lane shards (GLM/Kimi writers +
                                                       gemma-4-coding auxiliary role) that expand
                                                       families into MEMBER primitives, not restatements
catalog_intake/<day>-c8k1/fable_briefs.json            Fable ultracode workflow briefs: catalog
                                                       decompositions + the new place/open-data/
                                                       geospatial, entity-resolution, similarity/
                                                       indexing, visual/math, rendering, algorithm,
                                                       guardrail, and company-surface lanes
```

Lane run labels follow `<day>-c8kdet` (deterministic), `<day>-c8k1` (Ollama),
`<day>-uc02` (Fable workflow); each lane is verified by the standard
`scripts/run_primitive_verification_loop.py --max-ticks 1` one-shot into
`verified_candidates/<label>/manifest.json`, and lane quality is compared on
verified/duplicate/rejected counts plus
`scripts/track_primitive_saturation_and_savings.py`. Honor
`data/dev-intel/primitive_factory/GEMMA_PAUSE.json` before any Gemma calls.

## Minimum Candidate Row Shape

Use this for benchmark task demands:

```json
{
  "record_type": "compiled_primitive_benchmark_task_demand",
  "task_id": "task:source_family.capability.scope",
  "source_family": "bfcl|docile|swe_bench|terminal_bench|appworld|kaggle|openapi|mcp|terraform",
  "input_edge": "UserIntent+ToolSchemaSet",
  "output_edge": "ValidatedToolCallPlan+ExecutionReceipt",
  "primitive_demands": [
    "tool_schema_validate",
    "tool_select",
    "argument_bind",
    "abstain_when_no_safe_tool",
    "receipt_emit"
  ],
  "comparison_arms": [
    "baseline_runtime_agent",
    "baseline_search_agent",
    "compiled_code_template",
    "primitive_route_compile",
    "source_fallback"
  ],
  "scorecard_fields": [
    "task_success",
    "tokens_to_pass",
    "runtime_llm_tokens",
    "depth_to_solution",
    "proof_success",
    "route_reuse",
    "negative_memory_created"
  ],
  "candidate": true,
  "serves_truth": false
}
```

## Path Portfolio Row Shape

Use this shape when comparing alternative route methods:

```json
{
  "record_type": "compiled_primitive_route_portfolio",
  "portfolio_id": "portfolio:source_family.capability.scope",
  "task_ref": "task:source_family.capability.scope",
  "input_edge": "InputEnvelope+Policy",
  "output_edge": "OutputArtifact+Receipt",
  "candidate_paths": [
    {
      "path_id": "path:exact_route_lookup",
      "generation_path": "source_adapter_extract",
      "search_path": "exact_edge_search",
      "planner": "exact_route_lookup",
      "compiler": "deterministic_template_fill",
      "runtime": "local_pure_function",
      "proof": "contract_test",
      "expected_strength": "fastest_when_promoted_route_exists",
      "known_failure": "misses near matches and new variants"
    },
    {
      "path_id": "path:contract_diff_remix",
      "generation_path": "source_adapter_extract",
      "search_path": "type_compatible_edge_search",
      "planner": "contract_diff_remix",
      "compiler": "typed_graph_lowering",
      "runtime": "queue_worker",
      "proof": "fixture_and_side_effect_audit",
      "expected_strength": "adapts near matches without new model code",
      "known_failure": "bad adapter selection can hide semantic mismatch"
    },
    {
      "path_id": "path:llm_plan_delta_source_fallback",
      "generation_path": "model_draft_candidate",
      "search_path": "hybrid_search_with_source_fallback",
      "planner": "llm_plan_delta",
      "compiler": "bounded_function_generation",
      "runtime": "sandbox_then_container",
      "proof": "sandbox_execution_and_benchmark",
      "expected_strength": "handles novel gaps after search fails",
      "known_failure": "higher token cost and source-review burden"
    }
  ],
  "ranking_features": [
    "proof_strength",
    "contract_fit",
    "source_authority",
    "runtime_llm_tokens",
    "source_escalation_depth",
    "route_reuse_count",
    "effect_risk",
    "negative_memory_risk"
  ],
  "candidate": true,
  "serves_truth": false
}
```

## Experiment Design

Do paired comparisons. For each benchmark task, run multiple route paths against
the same input, fixtures, and proof gates:

```text
same task
same source refs
same acceptance criteria
same side-effect sandbox
same scorecard fields
different generation/search/planner/compiler/proof path
```

Minimum experiment cells:

```text
E1 exact route lookup
E2 hybrid search + template slot fill
E3 graph route search + deterministic mutators
E4 LLM PlanDelta over CandidateBundle
E5 trace-to-workflow replay compile
E6 source fallback + bounded model micro-repair
E7 human-reviewed route for high-risk domains
```

Do not declare one winner globally. Declare winners by task type:

```text
best_for_repeated_promoted_route
best_for_near_match_schema_variants
best_for_new_marketplace_surface
best_for_high_risk_regulated_domain
best_for_large_tool_graph
best_for_repo_repair
best_for_data_science_search
best_for_browser_or_terminal_workflow
```

## Improvement Backlog

High-value improvements to explore:

```text
multi-embedding primitive cards by edge, behavior, proof, runtime, industry, and source
source-authority reranker for official docs and standards
freshness-aware reranking for laws, APIs, packages, and market data
negative-memory-first search for repeated failure classes
route graph caching by input/output edge family
PlanLock canonicalization and hash stability tests
contract-diff explainability for near-match adapters
automatic proof-obligation generation from effect set
benchmark-task-to-primitive-demand compiler
trace-to-route distillation from successful agent sessions
marketplace-source adapters for MCP, OpenAPI, Terraform, GitHub Actions, n8n, Zapier, Make, Pipedream
shadow execution against existing agent workflows before replacing them
route amortization accounting: compile once, reuse many times
country and jurisdiction freshness policies
human-review queue for healthcare, finance, legal, cloud mutation, and data export
```

Questions to answer with data:

```text
When does exact edge search beat hybrid retrieval?
When does graph route search beat LLM PlanDelta?
When is bounded code generation cheaper than source fallback?
When does human review reduce downstream repair cost?
Which proof obligations predict real promotion success?
Which negative-memory classes prevent the most repeated waste?
Which source surfaces generate the most reusable route groups?
Which runtime wrappers create the most reuse: API, queue, CLI, MCP, workflow, or serverless?
```

## Product Positioning

Strong internal sentence:

```text
Compiled AI validates moving LLMs out of runtime; AI Done Right generalizes
that into compiled primitive routes with proof, receipts, and reusable registry
memory.
```

Avoid:

```text
We are a Compiled AI clone.
We generate deterministic code for every workflow.
The benchmark paper proves our product already works.
```

Use:

```text
Compiled AI is prior-art validation for compile-time intelligence.
Our system compiles capability routes, not only code.
Proof and receipts decide promotion.
The primitive registry compounds across tasks.
```

## Product Boundary Reminder

Keep naming clean:

```text
AI Done Right: portfolio and positioning
OpenHubForAI: open catalog and registry substrate
Teleon: capability compiler, deterministic runtime, proof, receipts
Baltor: verified context and truth-serving packs
AIDevObserver: observes AI-assisted development and recommends reuse routes
```

`aidevexplorer` is an internal or legacy namespace, not a branded surface.

## Immediate Claude Code Fable Instructions

1. Read this file and the read-first list.
2. Re-run focused checkers before reporting counts.
3. Build the compiled primitive benchmark seed pack with generated JSONL rows
   and a checker.
4. Update docs only after the checker passes.
5. Keep external research claims as prior-art notes until locally measured.
6. Do not start unbounded model loops without a stop file, ledger, and bounded
   dry run.
7. Do not promote generated candidate rows to truth.
