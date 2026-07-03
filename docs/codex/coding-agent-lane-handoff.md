# Coding-agent & competitive-programming lane handoff

Last updated: 2026-07-03

Audience: Claude Code, Codex, and agents extending the coding-task primitive
lane and its SLM-uplift benchmark.

Status: seeded and edge-composable today. The two solve loops below compile
end-to-end on the capability graph with ZERO model calls (see
`scripts/run_route_compiler_demo.py`); the primitives themselves are candidate
families, not source-backed implementations, and stay
`candidate=true / serves_truth=false` until a real implementation earns
execution receipts.

## Why this lane

The north-star thesis for this lane: a small code model (e.g. a Gemma-class
coder tuned with a LoRA) does not have to emit one monolithic solution. If the
solve steps are edge-typed primitives, the model's job shrinks to (1) retrieve
the right primitives and (2) let the deterministic route compiler ORDER them,
then (3) fill only the few reasoning holes. The rest of the loop -- indexing,
slicing, applying a diff, running tests, judging, gating complexity -- is
deterministic scaffolding that runs the same way every time and is individually
monitorable.

This is the same compile-by-edges idea as every other lane, aimed at the
agentic-coding and contest-solving benchmarks (SWE-bench, Terminal-Bench,
LeetCode / competitive programming). The payoff we want to MEASURE (not claim)
is that a structured small-model loop can be more monitored and more debuggable
than an unstructured frontier one-shot -- see the benchmark spec below. No
speed, cost, or accuracy advantage is asserted anywhere in the pack; those are
open measurements.

## The two loops (compile from edges, zero model calls)

Seed module: `scripts/seeds/universal_families_coding_agent_seed.py`. Built into
the universal catalog by `scripts/build_universal_primitive_pack.py`.

### SWE loop (coding_agent, `prim:swe.*`) -- repository repair

```text
IssueText                              -> parse_issue          -> ParsedIssue
RepoSnapshot + IndexPolicy             -> build_repo_index      -> RepoIndex
ParsedIssue + RepoIndex + LocalizePol. -> localize_fault        -> FaultLocation   [model_call]
FaultLocation + RepoSnapshot           -> read_code_slice       -> CodeSlice
ParsedIssue + RepoSnapshot + TestPol.  -> reproduce_bug         -> FailingTestArtifact
ParsedIssue + CodeSlice + FailingTest  -> generate_patch        -> PatchDraft       [model_call]
PatchDraft + RepoSnapshot              -> apply_patch           -> PatchedWorkspace
PatchedWorkspace + TestPolicy          -> run_tests             -> TestReport
TestReport + PatchDraft                -> validate_patch        -> ValidatedPatch
```

Compiled target `{have: [IssueText, RepoSnapshot]} -> ValidatedPatch` = **9
steps, all exact-tier**. `generate_patch` is a genuine multi-input join
(ParsedIssue + CodeSlice + FailingTestArtifact). Supporting families in the same
domain: `symbol_search`, `parse_traceback`, `minimize_patch`, `regression_guard`.

Only `localize_fault` and `generate_patch` carry a `model_call` effect -- the
two reasoning holes. Everything else is deterministic. The families that execute
untrusted repo code (`reproduce_bug`, `apply_patch`, `run_tests`) are
`risk_class: high, human_review_required: true`.

### CP loop (competitive_programming, `prim:cp.*`) -- contest solving

```text
ProblemStatement                       -> parse_problem                -> ParsedProblem
ParsedProblem                          -> extract_constraints          -> ConstraintSet
ConstraintSet                          -> estimate_complexity_budget   -> ComplexityBudget
ParsedProblem + ConstraintSet          -> classify_algorithm_pattern   -> AlgorithmPattern   [model_call]
AlgorithmPattern + ComplexityBudget    -> select_solution_template     -> SolutionTemplate
SolutionTemplate + ParsedProblem       -> fill_solution                -> SolutionCode        [model_call]
ParsedProblem                          -> generate_tests               -> TestCaseSet
SolutionCode + TestCaseSet + JudgePol. -> run_solution                 -> JudgeResult
```

Compiled target `{have: [ProblemStatement]} -> JudgeResult` = **8 steps**. The
budget prefix `-> ComplexityBudget` compiles in 3 steps. Verification families
in the same domain: `enumerate_edge_cases`, `complexity_gate`,
`differential_test` (candidate vs trusted reference), `stress_test`.

Only `classify_algorithm_pattern` and `fill_solution` carry `model_call`. The
key discipline this encodes: choose the complexity budget from the constraints
BEFORE choosing an algorithm, so an infeasible approach is ruled out by edges,
not discovered at submission.

### algorithms (`prim:algo.*`) -- the kernels a solution is assembled from

Fourteen classic kernels with honest algorithm-data edges: `binary_search`,
`two_pointers`, `sliding_window`, `prefix_sum`, `bfs_traverse`, `dfs_traverse`,
`dijkstra_shortest_path`, `union_find`, `topological_sort`, `dp_table`,
`monotonic_stack`, `heap_top_k`, `kmp_search`, `interval_merge`,
`backtracking_enumerate`. These are the library `select_solution_template` binds
and `fill_solution` specializes; each carries a `correctness_property_test`
obligation (agreement with a brute-force reference).

## Shared coding-task port vocabulary

Data ports (chain as required inputs / produced outputs):

```text
swe:  IssueText, ParsedIssue, RepoSnapshot, RepoIndex, SymbolQuery, SymbolHitSet,
      FaultLocation, CodeSlice, FailingTestArtifact, PatchDraft, PatchedWorkspace,
      ValidatedPatch, MinimalPatch, TracebackText, TracebackAnalysis
cp:   ProblemStatement, ParsedProblem, ConstraintSet, ComplexityBudget,
      AlgorithmPattern, SolutionTemplate, SolutionCode, TestCaseSet, EdgeCaseSet,
      JudgeResult, ReferenceSolution
algo: SortedArray, NumericArray, TargetValue, KValue, Graph, WeightedGraph,
      DirectedGraph, SourceNode, EdgeList, IntervalSet, TextString, PatternString,
      DPRecurrence, DPBounds, ChoiceSpace, and their result ports
config (request-supplied, never block composition): IndexPolicy, LocalizePolicy,
      PatchPolicy, TestPolicy, SolvePolicy, JudgePolicy, StressPolicy, WindowPolicy,
      PruneRule
receipt (evidence outputs): TestReport, RegressionReport, ComplexityReport,
      DiffReport, StressReport
```

Port roles follow `primitives/edges.py`: names ending in
`Policy/Spec/Context/Weights/Preference/Config/Settings` are config (supplied by
the request); names ending in `Report/Verdict/Digest/...` are receipts; the rest
are data. This is why the loop products are named `ParsedIssue` and
`ParsedProblem` (data) rather than `IssueSpec` / `ProblemSpec` (which would be
misread as request-supplied config and break the chain).

## SLM-uplift benchmark spec (a SPEC, not a result)

Goal: measure whether a small code model driving this primitive loop is more
correct / more monitored / more debuggable than an unstructured baseline -- on
the SAME tasks, with the SAME judge. Nothing here is measured yet; this is the
harness design. Follow the existing benchmark honesty rules
(`docs/codex/place-discovery-...` and the run checker): only arms that actually
run get scorecards, baselines are never simulated, and per-step evidence is
disclosed.

Arms (each runs the identical task set through the same sandboxed judge):

```text
B0  frontier one-shot      : one large-model completion, no loop, no tools
B1  frontier multi-shot    : large model with free-form tool use, no typed loop
A1  SLM one-shot           : small model, single completion (floor for the SLM)
A2  SLM + primitive loop   : small model retrieves + orders these primitives;
                             deterministic steps run as scaffolding; model fills
                             only the model_call holes (localize/generate_patch
                             or classify/fill_solution)
A3  SLM + loop + verifiers  : A2 plus complexity_gate / differential_test /
                             regression_guard gating before a solution is accepted
```

Task sets:
- SWE: SWE-bench-style (issue + repo + fail-to-pass tests). Primary metric =
  resolved rate (fail-to-pass flips with no pass-to-pass regressions), scored by
  `validate_patch`'s objective transition, not model judgment.
- CP: LeetCode / contest-style (statement + hidden tests). Primary metric =
  accepted rate under the real time/memory limits via `run_solution`.

Per-arm honesty artifacts (this is the actual point -- structure is
observable):
- a PlanLock (the compiled route) for every A2/A3 attempt, so the ordering is
  auditable before execution;
- an ExecutionReceipt per primitive step (which step ran, effects observed,
  proof results) -- the monitored-loop evidence a one-shot cannot produce;
- `runtime_llm_tokens` recorded per arm, and NO token-savings or speedup claim
  until B-arms actually run. A2/A3 have model calls only at the `model_call`
  steps; that count is measured, never assumed zero.

Open measurements (do NOT pre-claim any direction):
- resolved/accepted rate: A2/A3 vs B0/B1 and vs A1;
- model-token count per solved task per arm;
- localization precision (does `localize_fault` surface the gold file);
- how often a verifier (A3) catches a wrong solution the raw loop (A2) accepted.

## Honesty & scope

- Every seeded family is `candidate=true / serves_truth=false`. These describe
  capabilities and contracts; none is a source-backed implementation yet. A
  family becomes source-backed only when a real implementation runs through
  `primitives/core.py`, emits an ExecutionReceipt, and clears its proof
  obligations.
- No measured performance/speed/cost/accuracy claim appears in the pack. The
  claim-language gate in `scripts/check_universal_primitive_pack.py` enforces
  this; the SLM-uplift narrative lives here as a spec.
- Families that execute untrusted code (repo tests, candidate solutions,
  differential/stress runs) are high-risk and human-review-flagged; a real
  harness must run them in a resource-bounded sandbox (the `sandbox.runner` /
  `kubernetes.job` runtime targets on those families).

## Commands

```bash
# Rebuild the universal catalog (now includes the coding-agent lane) and check
python3 scripts/build_universal_primitive_pack.py --write
python3 scripts/check_universal_primitive_pack.py --self-test

# Rebuild the capability graph and confirm both loops compile from edges
python3 scripts/build_capability_graph.py --write
python3 scripts/run_route_compiler_demo.py --self-test   # SWE 9-step, CP 8-step

# Full proof suite (CI)
python3 scripts/run_proofs.py
```

## Next build slices

1. Implement one loop end-to-end against a real fixture repo / problem: the
   deterministic families first (`build_repo_index`, `apply_patch`, `run_tests`)
   with FixtureTransport-style sandboxing, so they earn execution receipts and
   move from candidate to source-backed.
2. Stand up the benchmark harness (arms above) with the run-checker honesty
   gates -- PlanLock per attempt, ExecutionReceipt per step, no simulated
   baselines.
3. Add `primitive_template` skeletons for the CP `SolutionTemplate` catalog and
   wire `select_solution_template` to the `prim:algo.*` kernels by
   `AlgorithmPattern`.
4. Mine real coding-agent and CP-template repos through the repo-mining factory
   (`docs/codex/repo-mining-factory-spec.md`) to attach source refs to these
   candidate families.
