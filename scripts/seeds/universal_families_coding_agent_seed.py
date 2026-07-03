"""Seed rows for reusable-primitive families: coding_agent (SWE-bench /
Terminal-Bench style repository-repair primitives), competitive_programming
(LeetCode / contest problem-solving primitives), and algorithms (classic
algorithm and data-structure kernels the solver assembles).

Pure data module: one top-level constant FAMILIES (list of dicts). Each row is
candidate seed material describing one recurring coding-task capability; the
builder (scripts/build_universal_primitive_pack.py) injects record_type,
version, candidate=True, serves_truth=False, and crosses each family with the
runtime wrappers it declares applicable.

Why this lane: the north-star thesis is that a small code model can grab
primitives, order them by their typed edges, and drive a structured, monitored
solve loop instead of emitting one monolithic completion. That only works if the
loop's steps are edge-typed so they compose without reading each other's
internals. The two loops below are authored so they compile end-to-end on the
capability graph with zero model calls (see scripts/run_route_compiler_demo.py),
and the reasoning-heavy steps (localize, generate_patch, classify_pattern,
fill_solution) declare a model_call effect honestly - those are the only steps a
model touches; everything else is deterministic scaffolding.

Port vocabulary (all CamelCase alphanumeric so they parse as typed ports; names
avoid the config suffixes Policy/Spec/Context/Weights so the DATA products in
each loop chain as required inputs, and use *Report/*Verdict only where an
evidence receipt is intended):

  SWE loop (coding_agent, ids "prim:swe.*"):
    IssueText -> parse_issue -> ParsedIssue
    RepoSnapshot -> build_repo_index -> RepoIndex
    ParsedIssue + RepoIndex -> localize_fault -> FaultLocation
    FaultLocation + RepoSnapshot -> read_code_slice -> CodeSlice
    ParsedIssue + RepoSnapshot -> reproduce_bug -> FailingTestArtifact
    ParsedIssue + CodeSlice + FailingTestArtifact -> generate_patch -> PatchDraft
    PatchDraft + RepoSnapshot -> apply_patch -> PatchedWorkspace
    PatchedWorkspace -> run_tests -> TestReport
    TestReport + PatchDraft -> validate_patch -> ValidatedPatch

  CP loop (competitive_programming, ids "prim:cp.*"):
    ProblemStatement -> parse_problem -> ParsedProblem
    ParsedProblem -> extract_constraints -> ConstraintSet
    ConstraintSet -> estimate_complexity_budget -> ComplexityBudget
    ParsedProblem + ConstraintSet -> classify_algorithm_pattern -> AlgorithmPattern
    AlgorithmPattern + ComplexityBudget -> select_solution_template -> SolutionTemplate
    SolutionTemplate + ParsedProblem -> fill_solution -> SolutionCode
    ParsedProblem -> generate_tests -> TestCaseSet
    SolutionCode + TestCaseSet -> run_solution -> JudgeResult

  algorithms (ids "prim:algo.*"): classic kernels keyed by AlgorithmPattern that
    a filled solution is assembled from - binary search, two pointers, sliding
    window, prefix sum, BFS/DFS, Dijkstra, union-find, topological sort, DP
    table, monotonic stack, heap top-k, KMP, interval merge, backtracking.

Honesty: no unmeasured performance/speed/savings claims appear anywhere - the
SLM-uplift comparison is a benchmark SPEC in
docs/codex/coding-agent-lane-handoff.md, not a measured result. Families that
execute untrusted code (reproduce_bug, apply_patch, run_tests, run_solution,
differential_test, stress_test) are risk_class high with human_review_required
True; reasoning families that emit code are risk_class medium. Every row stays
candidate=true / serves_truth=false.

Grounded in the SWE-bench task structure (issue text + repo + fail-to-pass
tests), the unified-diff / git patch format, competitive-programming problem
structure (statement + constraints + judge), algorithmic complexity analysis,
and standard algorithms and data structures.
"""

FAMILIES = [
    # ==================================================================
    # coding_agent (SWE-bench / Terminal-Bench style repository repair)
    # ==================================================================
    {
        "family_id": "prim:swe.parse_issue",
        "domain": "coding_agent",
        "title": "Parse Issue To Structured Brief",
        "input_edge": "IssueText",
        "output_edge": "ParsedIssue",
        "blackbox": {
            "does": "Extracts referenced file paths, symbol names, error strings, and expected-vs-actual behavior from a freeform issue report into a structured brief the localizer can act on."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "agent.tool"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json", "text"],
        "proof_requirements": ["schema_validation", "determinism_test"],
        "problem_solution": {
            "problem": "An issue report is freeform prose mixing symptoms, stack traces, and file references, and the solver needs a structured brief before it can localize anything.",
            "naive_agent_failure": "An agent reads the raw issue and jumps straight to editing a plausible-sounding file, ignoring the concrete symbols and error strings the issue actually names.",
            "solution": "A parse step that pulls referenced paths, symbols, error strings, and the expected-vs-actual behavior into a typed brief keyed to the issue.",
            "core_components": ["reference extractor", "error-string collector", "expected-vs-actual splitter"],
            "common_inputs": ["issue title and body", "attached traceback or logs"],
            "common_outputs": ["structured issue brief", "referenced files and symbols", "reproduction hints"],
            "known_pitfalls": ["hallucinating files the issue never names", "dropping the concrete error string", "confusing expected with actual behavior"],
            "success_signals": ["every extracted path or symbol appears verbatim in the issue", "the brief names a concrete failure to reproduce"],
        },
        "source_ref_families": ["SWE-bench task structure", "issue-triage practice"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:swe.build_repo_index",
        "domain": "coding_agent",
        "title": "Build Repository Symbol Index",
        "input_edge": "RepoSnapshot+IndexPolicy",
        "output_edge": "RepoIndex",
        "blackbox": {
            "does": "Parses a repository snapshot with a language AST into a symbol index mapping every definition and reference to a file and line span, so later steps navigate by symbol rather than by grep."
        },
        "effects": ["file_read", "artifact_write"],
        "base_runtime_targets": ["local.python", "agent.tool"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
            "wrap:kubernetes_job",
        ],
        "applicable_data_formats": ["json", "parquet"],
        "proof_requirements": ["schema_validation", "referential_integrity_test"],
        "problem_solution": {
            "problem": "Navigating a large repo by text search is noisy and misses definitions, so the agent needs a symbol index that resolves names to exact locations.",
            "naive_agent_failure": "An agent greps for a function name, gets dozens of unrelated hits, and edits the wrong definition because it cannot tell a definition from a call site.",
            "solution": "An index build that AST-parses the snapshot into a definition/reference map keyed by symbol, each entry pointing at a real file and line span.",
            "core_components": ["language AST parser", "definition/reference classifier", "symbol-to-span map builder"],
            "common_inputs": ["repository snapshot", "language and include/exclude policy"],
            "common_outputs": ["symbol index", "definition and reference spans", "import graph"],
            "known_pitfalls": ["indexing generated or vendored code as source", "missing dynamically defined symbols", "stale index after edits"],
            "success_signals": ["every index entry resolves to a real span in the snapshot", "definitions and references are distinguished"],
        },
        "source_ref_families": ["code intelligence / LSP symbol indexing", "AST parsing"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:swe.symbol_search",
        "domain": "coding_agent",
        "title": "Symbol Search Over Index",
        "input_edge": "SymbolQuery+RepoIndex",
        "output_edge": "SymbolHitSet",
        "blackbox": {
            "does": "Resolves a symbol or signature query against the repository index into a ranked hit set of definition and usage spans, returning locations rather than raw text matches."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "agent.tool"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json"],
        "proof_requirements": ["schema_validation", "determinism_test"],
        "problem_solution": {
            "problem": "The agent knows a symbol name from the issue but needs its definition and all call sites, ranked by relevance, not a flat text-match dump.",
            "naive_agent_failure": "An agent substring-matches the name and treats a comment mention or a similarly named variable as the definition.",
            "solution": "A search step that resolves the query against the index and returns typed hits (definition, references) ranked by proximity to the query intent.",
            "core_components": ["query resolver", "hit classifier", "relevance ranker"],
            "common_inputs": ["symbol or signature query", "repository index"],
            "common_outputs": ["ranked symbol hit set", "definition and reference spans"],
            "known_pitfalls": ["substring collisions across unrelated names", "ranking comments above code", "ignoring scope and shadowing"],
            "success_signals": ["the definition ranks above incidental mentions", "each hit points at a real span"],
        },
        "source_ref_families": ["code intelligence / LSP symbol search", "information retrieval ranking"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:swe.localize_fault",
        "domain": "coding_agent",
        "title": "Localize Fault To Code Span",
        "input_edge": "ParsedIssue+RepoIndex+LocalizePolicy",
        "output_edge": "FaultLocation",
        "blackbox": {
            "does": "Ranks the repository's symbols and spans by how likely they are the fault for a parsed issue, using index structure and issue references, and returns the top candidate locations to edit."
        },
        "effects": ["model_call"],
        "base_runtime_targets": ["local.python", "agent.tool"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:queue_worker",
        ],
        "applicable_data_formats": ["json"],
        "proof_requirements": ["schema_validation", "ranking_stability_test"],
        "problem_solution": {
            "problem": "A repo has thousands of spans and only a few are the fault, so the solver must narrow to the right location before spending effort on a patch.",
            "naive_agent_failure": "An agent picks the first file whose name resembles the issue and edits there, missing the true fault in a helper it never inspected.",
            "solution": "A localization step that scores candidate spans by issue references, index proximity, and change-coupling, returning a ranked, bounded candidate list.",
            "core_components": ["candidate collector", "relevance scorer", "top-k selector"],
            "common_inputs": ["parsed issue brief", "repository index", "candidate-count policy"],
            "common_outputs": ["ranked fault locations", "per-candidate rationale", "bounded candidate list"],
            "known_pitfalls": ["fixating on filename similarity", "ignoring the call chain into the fault", "returning too many candidates to act on"],
            "success_signals": ["the true fault appears in the top candidates on known tasks", "candidates are bounded and ranked"],
        },
        "source_ref_families": ["SWE-bench task structure", "fault-localization research"],
        "risk_class": "medium",
        "human_review_required": False,
    },
    {
        "family_id": "prim:swe.read_code_slice",
        "domain": "coding_agent",
        "title": "Read Grounded Code Slice",
        "input_edge": "FaultLocation+RepoSnapshot",
        "output_edge": "CodeSlice",
        "blackbox": {
            "does": "Reads the exact source spans around a fault location plus their imports and callers into a compact, byte-grounded code slice, so the patch generator sees real code and not a paraphrase."
        },
        "effects": ["file_read"],
        "base_runtime_targets": ["local.python", "agent.tool"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json", "text"],
        "proof_requirements": ["schema_validation", "source_span_grounding"],
        "problem_solution": {
            "problem": "A patch must be written against the actual current code, but dumping whole files wastes context while a paraphrase invites edits that do not apply.",
            "naive_agent_failure": "An agent recalls what it thinks the function looks like and patches against that from memory, so the diff fails to apply to the real file.",
            "solution": "A slice reader that returns the exact byte spans at the fault plus the minimal surrounding context (imports, signature, callers), each tagged with its file and line range.",
            "core_components": ["span reader", "context expander", "byte-offset tagger"],
            "common_inputs": ["fault location", "repository snapshot"],
            "common_outputs": ["grounded code slice", "file and line ranges", "surrounding context"],
            "known_pitfalls": ["patching against a remembered rather than actual body", "slicing too little context to edit safely", "losing exact byte offsets"],
            "success_signals": ["slice text matches the snapshot byte-for-byte", "the slice includes enough context to edit"],
        },
        "source_ref_families": ["source-span grounding (document-extraction lane)", "code intelligence"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:swe.reproduce_bug",
        "domain": "coding_agent",
        "title": "Reproduce Bug As Failing Test",
        "input_edge": "ParsedIssue+RepoSnapshot+TestPolicy",
        "output_edge": "FailingTestArtifact",
        "blackbox": {
            "does": "Derives or selects a test that exercises the reported bug and runs it against the unpatched snapshot to capture a concrete failing artifact, establishing the fail-to-pass target the patch must flip."
        },
        "effects": ["file_read", "artifact_write"],
        "base_runtime_targets": ["local.python", "sandbox.runner"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:cli_command", "wrap:queue_worker",
            "wrap:kubernetes_job",
        ],
        "applicable_data_formats": ["json", "text"],
        "proof_requirements": ["schema_validation", "failing_test_reproduction"],
        "problem_solution": {
            "problem": "Without a test that actually fails on the current code, there is no objective target and a patch might change behavior without fixing anything.",
            "naive_agent_failure": "An agent assumes the bug reproduces and writes a fix, never confirming the pre-patch code fails, so it cannot tell whether the patch did anything.",
            "solution": "A reproduce step that constructs or selects a test from the issue and runs it against the unpatched snapshot in a sandbox, capturing the failing output as an artifact.",
            "core_components": ["test constructor/selector", "sandboxed runner", "failure capturer"],
            "common_inputs": ["parsed issue brief", "repository snapshot", "runner and timeout policy"],
            "common_outputs": ["failing test artifact", "captured failure output", "fail-to-pass target"],
            "known_pitfalls": ["a test that passes even before the fix", "flaky reproduction", "reproducing a different bug than reported"],
            "success_signals": ["the test fails on the unpatched snapshot", "the failure matches the reported symptom"],
        },
        "source_ref_families": ["SWE-bench fail-to-pass structure", "regression-test authoring"],
        "risk_class": "high",
        "human_review_required": True,
    },
    {
        "family_id": "prim:swe.generate_patch",
        "domain": "coding_agent",
        "title": "Generate Unified-Diff Patch",
        "input_edge": "ParsedIssue+CodeSlice+FailingTestArtifact+PatchPolicy",
        "output_edge": "PatchDraft",
        "blackbox": {
            "does": "Produces a minimal unified-diff patch against the grounded code slice aimed at flipping the failing test, editing only the sliced spans and preserving surrounding code exactly."
        },
        "effects": ["model_call"],
        "base_runtime_targets": ["local.python", "agent.tool"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:queue_worker",
        ],
        "applicable_data_formats": ["diff", "text"],
        "proof_requirements": ["schema_validation", "patch_applies_cleanly"],
        "problem_solution": {
            "problem": "A fix must be expressed as a diff that applies cleanly to the real file and targets the failing test, not a rewrite of whole files.",
            "naive_agent_failure": "An agent rewrites an entire file from memory, drifting from the real contents so the patch does not apply or clobbers unrelated code.",
            "solution": "A generate step that emits a minimal unified diff against the grounded slice, editing only the necessary hunks and leaving surrounding lines byte-identical.",
            "core_components": ["hunk planner", "diff emitter", "minimality trimmer"],
            "common_inputs": ["parsed issue brief", "grounded code slice", "failing test artifact", "patch-size policy"],
            "common_outputs": ["unified-diff patch draft", "touched files and hunks"],
            "known_pitfalls": ["rewriting whole files instead of hunks", "diff context lines not matching the source", "edits outside the sliced spans"],
            "success_signals": ["the diff applies to the snapshot without fuzz", "only sliced spans are touched"],
        },
        "source_ref_families": ["unified-diff / git patch format", "SWE-bench task structure"],
        "risk_class": "medium",
        "human_review_required": True,
    },
    {
        "family_id": "prim:swe.apply_patch",
        "domain": "coding_agent",
        "title": "Apply Patch To Workspace",
        "input_edge": "PatchDraft+RepoSnapshot",
        "output_edge": "PatchedWorkspace",
        "blackbox": {
            "does": "Applies a unified-diff patch to a copy of the repository snapshot, verifying every hunk lands at its declared location and failing loudly on any reject rather than partially applying."
        },
        "effects": ["file_read", "file_write"],
        "base_runtime_targets": ["local.python", "sandbox.runner"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:cli_command", "wrap:kubernetes_job",
        ],
        "applicable_data_formats": ["diff", "text"],
        "proof_requirements": ["schema_validation", "patch_applies_cleanly",
                               "idempotency_test"],
        "problem_solution": {
            "problem": "A patch that applies only partially leaves the workspace in a broken hybrid state that misleads every downstream test.",
            "naive_agent_failure": "An agent force-applies a patch with fuzz, silently relocating a hunk to the wrong place and corrupting the file.",
            "solution": "An apply step that patches a fresh copy of the snapshot, checks each hunk lands exactly, and aborts atomically on any reject.",
            "core_components": ["hunk locator", "atomic applier", "reject detector"],
            "common_inputs": ["patch draft", "repository snapshot"],
            "common_outputs": ["patched workspace", "applied-hunk manifest", "clean-or-aborted status"],
            "known_pitfalls": ["fuzzy application relocating a hunk", "partial apply leaving a half-patched file", "patching the original instead of a copy"],
            "success_signals": ["every hunk applies at its declared location", "reapplying the same patch is a no-op"],
        },
        "source_ref_families": ["unified-diff / git patch format", "atomic file operations"],
        "risk_class": "high",
        "human_review_required": True,
    },
    {
        "family_id": "prim:swe.run_tests",
        "domain": "coding_agent",
        "title": "Run Test Suite In Sandbox",
        "input_edge": "PatchedWorkspace+TestPolicy",
        "output_edge": "TestReport",
        "blackbox": {
            "does": "Runs the selected test suite against a patched workspace inside a resource-bounded sandbox and returns a structured report of per-test pass/fail, durations, and captured output."
        },
        "effects": ["file_read", "artifact_write"],
        "base_runtime_targets": ["sandbox.runner", "ci.action"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:cli_command", "wrap:github_action",
            "wrap:kubernetes_job",
        ],
        "applicable_data_formats": ["json", "text"],
        "proof_requirements": ["schema_validation", "deterministic_test_selection"],
        "problem_solution": {
            "problem": "Test results are only trustworthy if the suite runs in an isolated, bounded environment with a stable, declared selection of tests.",
            "naive_agent_failure": "An agent runs tests in the host environment with an ad-hoc selection, so results depend on local state and are not reproducible.",
            "solution": "A run step that executes a declared test selection in a resource-bounded sandbox and returns a structured per-test report.",
            "core_components": ["test selector", "sandboxed executor", "result parser"],
            "common_inputs": ["patched workspace", "test selection and resource policy"],
            "common_outputs": ["structured test report", "per-test pass/fail and durations", "captured output"],
            "known_pitfalls": ["leaking host state into the run", "non-deterministic test ordering", "timeouts reported as failures without distinction"],
            "success_signals": ["the same workspace and selection yield the same report", "each test's status is captured individually"],
        },
        "source_ref_families": ["test-runner isolation", "SWE-bench evaluation harness"],
        "risk_class": "high",
        "human_review_required": True,
    },
    {
        "family_id": "prim:swe.validate_patch",
        "domain": "coding_agent",
        "title": "Validate Patch Fail-To-Pass",
        "input_edge": "TestReport+PatchDraft",
        "output_edge": "ValidatedPatch",
        "blackbox": {
            "does": "Confirms the previously failing test now passes and no formerly passing test regressed, promoting a patch draft to a validated patch only when the fail-to-pass transition holds with no new failures."
        },
        "effects": ["file_read"],
        "base_runtime_targets": ["local.python", "agent.tool"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json"],
        "proof_requirements": ["schema_validation", "regression_guard",
                               "fail_to_pass_transition"],
        "problem_solution": {
            "problem": "A patch is only correct if it flips the target test to passing without breaking anything that previously passed.",
            "naive_agent_failure": "An agent declares victory because the target test passes, never checking that its edit broke ten other tests.",
            "solution": "A validate step that compares the post-patch report against the pre-patch baseline and promotes the patch only on a clean fail-to-pass transition with no regressions.",
            "core_components": ["baseline comparator", "fail-to-pass checker", "regression detector"],
            "common_inputs": ["post-patch test report", "patch draft", "pre-patch baseline"],
            "common_outputs": ["validated patch or rejection", "fail-to-pass confirmation", "regression list if any"],
            "known_pitfalls": ["ignoring newly broken tests", "counting an already-passing test as fixed", "comparing against the wrong baseline"],
            "success_signals": ["the target test transitions fail to pass", "no previously passing test now fails"],
        },
        "source_ref_families": ["SWE-bench fail-to-pass / pass-to-pass evaluation", "regression testing"],
        "risk_class": "medium",
        "human_review_required": False,
    },
    {
        "family_id": "prim:swe.parse_traceback",
        "domain": "coding_agent",
        "title": "Parse Traceback To Frames",
        "input_edge": "TracebackText",
        "output_edge": "TracebackAnalysis",
        "blackbox": {
            "does": "Parses a stack trace into ordered frames with file, line, and function, identifies the deepest in-repo frame, and extracts the exception type and message for use as a localization signal."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "agent.tool"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json", "text"],
        "proof_requirements": ["schema_validation", "source_span_grounding"],
        "problem_solution": {
            "problem": "A raw traceback is a dense wall of frames, and the useful signal is the deepest in-repo frame and the exception, not the library internals.",
            "naive_agent_failure": "An agent fixates on the top library frame where the exception surfaced rather than the in-repo frame that actually caused it.",
            "solution": "A parse step that splits the trace into ordered frames, marks in-repo versus third-party, and surfaces the deepest in-repo frame plus the exception type and message.",
            "core_components": ["frame splitter", "in-repo/library classifier", "exception extractor"],
            "common_inputs": ["raw traceback text", "repository root paths"],
            "common_outputs": ["ordered frame list", "deepest in-repo frame", "exception type and message"],
            "known_pitfalls": ["blaming the top library frame", "mis-parsing multi-language or chained traces", "losing the exception message"],
            "success_signals": ["each frame's file and line resolve in the repo", "the deepest in-repo frame is identified"],
        },
        "source_ref_families": ["stack-trace formats", "fault-localization signals"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:swe.minimize_patch",
        "domain": "coding_agent",
        "title": "Minimize Patch To Essential Hunks",
        "input_edge": "ValidatedPatch+TestPolicy",
        "output_edge": "MinimalPatch",
        "blackbox": {
            "does": "Shrinks a validated patch by removing hunks and re-running the fail-to-pass check, keeping only the minimal set of edits that still flips the target test without regressions."
        },
        "effects": ["file_read", "artifact_write"],
        "base_runtime_targets": ["local.python", "sandbox.runner"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:cli_command", "wrap:kubernetes_job",
        ],
        "applicable_data_formats": ["diff", "json"],
        "proof_requirements": ["schema_validation", "behavior_preservation_test"],
        "problem_solution": {
            "problem": "A working patch often carries incidental edits, and a smaller diff is easier to review and less likely to hide a regression.",
            "naive_agent_failure": "An agent keeps every speculative edit it tried, shipping a bloated diff whose extra hunks are unexplained.",
            "solution": "A minimize step that removes hunks one at a time, re-checking fail-to-pass, and retains only the edits required to keep the fix.",
            "core_components": ["hunk ablator", "fail-to-pass re-checker", "minimal-set selector"],
            "common_inputs": ["validated patch", "test policy"],
            "common_outputs": ["minimal patch", "removed-hunk record", "preserved fail-to-pass status"],
            "known_pitfalls": ["removing a hunk that silently reintroduces the bug", "over-minimizing past a needed edit", "not re-running the guard after each removal"],
            "success_signals": ["every retained hunk is necessary for the fix", "the minimized patch still passes validation"],
        },
        "source_ref_families": ["delta-debugging / patch minimization", "code review practice"],
        "risk_class": "medium",
        "human_review_required": False,
    },
    {
        "family_id": "prim:swe.regression_guard",
        "domain": "coding_agent",
        "title": "Regression Guard Over Suite",
        "input_edge": "TestReport+TestReport",
        "output_edge": "RegressionReport",
        "blackbox": {
            "does": "Diffs a post-change test report against a baseline report to enumerate exactly which tests newly fail, newly pass, or changed status, producing an auditable regression verdict."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "agent.tool", "ci.action"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:github_action",
        ],
        "applicable_data_formats": ["json"],
        "proof_requirements": ["schema_validation", "no_new_failures_test"],
        "problem_solution": {
            "problem": "Deciding whether a change is safe requires an exact set difference between two test reports, not a gut sense that things still work.",
            "naive_agent_failure": "An agent eyeballs a summary count and misses that two tests flipped to failing while three new ones started passing.",
            "solution": "A guard that computes the status delta between baseline and current reports and lists every newly failing, newly passing, and status-changed test.",
            "core_components": ["report aligner", "status-delta computer", "verdict emitter"],
            "common_inputs": ["current test report", "baseline test report"],
            "common_outputs": ["regression report", "newly failing and newly passing lists", "safe-or-blocked verdict"],
            "known_pitfalls": ["comparing reports from different selections", "ignoring newly added tests", "treating flaky flips as regressions"],
            "success_signals": ["the delta lists tests by name and transition", "a clean change reports zero new failures"],
        },
        "source_ref_families": ["regression testing", "CI status-diff practice"],
        "risk_class": "low",
        "human_review_required": False,
    },
    # ==================================================================
    # competitive_programming (LeetCode / contest problem solving)
    # ==================================================================
    {
        "family_id": "prim:cp.parse_problem",
        "domain": "competitive_programming",
        "title": "Parse Problem Statement",
        "input_edge": "ProblemStatement",
        "output_edge": "ParsedProblem",
        "blackbox": {
            "does": "Structures a contest problem statement into signature, input/output format, sample cases, and stated limits, separating the task specification from prose so downstream steps operate on a typed problem."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "agent.tool"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json", "text"],
        "proof_requirements": ["schema_validation", "determinism_test"],
        "problem_solution": {
            "problem": "A contest statement mixes narrative, formal I/O format, samples, and limits, and solving requires a clean separation of those parts.",
            "naive_agent_failure": "An agent skims the prose and misreads the I/O format or the sample cases, so its solution answers a slightly different question.",
            "solution": "A parse step that extracts the function signature, input/output format, sample cases, and stated limits into a typed problem object.",
            "core_components": ["signature extractor", "io-format parser", "sample-case collector"],
            "common_inputs": ["problem statement text", "sample cases"],
            "common_outputs": ["parsed problem object", "io format and signature", "sample cases and limits"],
            "known_pitfalls": ["misreading the output format", "dropping a sample case", "confusing 1-indexed and 0-indexed inputs"],
            "success_signals": ["parsed samples round-trip against the statement", "the signature matches the required function"],
        },
        "source_ref_families": ["competitive-programming problem structure", "problem-statement parsing"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:cp.extract_constraints",
        "domain": "competitive_programming",
        "title": "Extract Numeric Constraints",
        "input_edge": "ParsedProblem",
        "output_edge": "ConstraintSet",
        "blackbox": {
            "does": "Pulls the numeric bounds on input sizes and value ranges from a parsed problem into a typed constraint set, the raw material for choosing a complexity budget and algorithm class."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "agent.tool"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json"],
        "proof_requirements": ["schema_validation", "bounds_sanity_test"],
        "problem_solution": {
            "problem": "The input bounds decide which algorithms are viable, but they are scattered through the statement and easy to overlook.",
            "naive_agent_failure": "An agent ignores that n can reach ten million and writes a quadratic solution that will time out.",
            "solution": "An extract step that collects every size and value bound into a typed constraint set with units and ranges made explicit.",
            "core_components": ["bound scanner", "range normalizer", "unit tagger"],
            "common_inputs": ["parsed problem object"],
            "common_outputs": ["numeric constraint set", "input-size and value bounds", "special-case limits"],
            "known_pitfalls": ["missing an upper bound", "confusing per-test and total limits", "ignoring value ranges that force big integers"],
            "success_signals": ["every stated bound appears in the set", "bounds carry explicit ranges and units"],
        },
        "source_ref_families": ["competitive-programming problem structure", "constraint analysis"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:cp.estimate_complexity_budget",
        "domain": "competitive_programming",
        "title": "Estimate Complexity Budget",
        "input_edge": "ConstraintSet",
        "output_edge": "ComplexityBudget",
        "blackbox": {
            "does": "Translates input-size constraints and the time/memory limits into an allowed asymptotic budget, ruling out complexity classes that cannot finish within the limits before any algorithm is chosen."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "agent.tool"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json"],
        "proof_requirements": ["schema_validation", "budget_feasibility_test"],
        "problem_solution": {
            "problem": "Choosing an algorithm blind wastes attempts, when the input bounds already imply which asymptotic classes can finish in time.",
            "naive_agent_failure": "An agent picks an approach it likes and only discovers at submission that the complexity was infeasible for the bounds.",
            "solution": "An estimate step that maps the largest input bound and the time limit to a target asymptotic class and marks classes that cannot finish as out of budget.",
            "core_components": ["operation-budget estimator", "asymptotic-class mapper", "feasibility filter"],
            "common_inputs": ["numeric constraint set", "time and memory limits"],
            "common_outputs": ["complexity budget", "target asymptotic class", "excluded classes"],
            "known_pitfalls": ["ignoring the constant factor of the language", "treating memory as unbounded", "over-budgeting so nothing qualifies"],
            "success_signals": ["the budget admits at least one feasible class", "classes that would time out are excluded"],
        },
        "source_ref_families": ["algorithmic complexity analysis", "competitive-programming budgeting heuristics"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:cp.classify_algorithm_pattern",
        "domain": "competitive_programming",
        "title": "Classify Algorithm Pattern",
        "input_edge": "ParsedProblem+ConstraintSet",
        "output_edge": "AlgorithmPattern",
        "blackbox": {
            "does": "Maps a parsed problem and its constraints to one or more candidate algorithmic patterns (two pointers, binary search, DP, graph, greedy, and so on), ranked, so template selection has a typed target."
        },
        "effects": ["model_call"],
        "base_runtime_targets": ["local.python", "agent.tool"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:queue_worker",
        ],
        "applicable_data_formats": ["json"],
        "proof_requirements": ["schema_validation", "determinism_test"],
        "problem_solution": {
            "problem": "Most problems fall into a small set of recurring patterns, and naming the pattern early narrows the entire solution space.",
            "naive_agent_failure": "An agent recognizes no pattern and writes a bespoke brute force, missing that the problem is a standard sliding-window task.",
            "solution": "A classify step that maps the problem shape and bounds to ranked candidate patterns, each with a short rationale.",
            "core_components": ["shape featurizer", "pattern matcher", "candidate ranker"],
            "common_inputs": ["parsed problem object", "numeric constraint set"],
            "common_outputs": ["ranked algorithm patterns", "per-pattern rationale"],
            "known_pitfalls": ["forcing a familiar pattern onto a different problem", "returning one guess with no alternative", "ignoring bounds that rule a pattern out"],
            "success_signals": ["the correct pattern appears among the top candidates on known problems", "each candidate carries a rationale"],
        },
        "source_ref_families": ["competitive-programming pattern taxonomy", "algorithm classification"],
        "risk_class": "medium",
        "human_review_required": False,
    },
    {
        "family_id": "prim:cp.select_solution_template",
        "domain": "competitive_programming",
        "title": "Select Solution Template",
        "input_edge": "AlgorithmPattern+ComplexityBudget",
        "output_edge": "SolutionTemplate",
        "blackbox": {
            "does": "Chooses a concrete, budget-fitting solution template (the skeleton and the algorithm kernels it calls) for a ranked algorithm pattern, so filling in the solution is a bounded specialization rather than a blank page."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "agent.tool"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json", "text"],
        "proof_requirements": ["schema_validation", "template_type_match_test"],
        "problem_solution": {
            "problem": "Given a pattern and a budget, the solver needs a proven skeleton to specialize, not a blank editor where boilerplate bugs creep in.",
            "naive_agent_failure": "An agent rewrites a binary search or a DFS from scratch each time and reintroduces the same off-by-one and recursion-depth bugs.",
            "solution": "A select step that picks a template whose asymptotic class fits the budget and names the algorithm kernels it composes.",
            "core_components": ["template catalog matcher", "budget-fit checker", "kernel binder"],
            "common_inputs": ["ranked algorithm pattern", "complexity budget"],
            "common_outputs": ["chosen solution template", "referenced algorithm kernels", "budget-fit confirmation"],
            "known_pitfalls": ["choosing a template above the budget", "a template whose I/O type does not match the problem", "ignoring available kernels and reimplementing them"],
            "success_signals": ["the template's class fits the budget", "its signature matches the problem's required interface"],
        },
        "source_ref_families": ["solution-template libraries", "competitive-programming pattern taxonomy"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:cp.fill_solution",
        "domain": "competitive_programming",
        "title": "Fill Solution From Template",
        "input_edge": "SolutionTemplate+ParsedProblem+SolvePolicy",
        "output_edge": "SolutionCode",
        "blackbox": {
            "does": "Specializes a chosen solution template to the parsed problem - binding the signature, state transitions, and I/O parsing - into compilable solution code that targets the required interface."
        },
        "effects": ["model_call"],
        "base_runtime_targets": ["local.python", "agent.tool"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:queue_worker",
        ],
        "applicable_data_formats": ["text", "json"],
        "proof_requirements": ["schema_validation", "compile_test"],
        "problem_solution": {
            "problem": "The template gives structure, but the problem-specific transitions, parsing, and edge handling still have to be filled in correctly and made to compile.",
            "naive_agent_failure": "An agent writes free-form code that ignores the template's proven skeleton and reintroduces boilerplate mistakes, or produces code that does not compile.",
            "solution": "A fill step that binds the template's holes to the problem's signature and logic, emitting solution code that compiles against the required interface.",
            "core_components": ["signature binder", "transition/logic filler", "io-parsing generator"],
            "common_inputs": ["chosen solution template", "parsed problem object", "language and style policy"],
            "common_outputs": ["compilable solution code", "bound signature", "io handling"],
            "known_pitfalls": ["mismatching the required function signature", "off-by-one in the filled transition", "forgetting to parse a multi-line input"],
            "success_signals": ["the code compiles against the required interface", "the sample cases run without error"],
        },
        "source_ref_families": ["solution-template libraries", "code generation from skeletons"],
        "risk_class": "medium",
        "human_review_required": False,
    },
    {
        "family_id": "prim:cp.generate_tests",
        "domain": "competitive_programming",
        "title": "Generate Tests From Samples",
        "input_edge": "ParsedProblem",
        "output_edge": "TestCaseSet",
        "blackbox": {
            "does": "Builds a test-case set from the stated sample cases plus derived cases (min/max bounds, empty, single element), each a concrete input paired with its expected output where the sample provides one."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "agent.tool"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json"],
        "proof_requirements": ["schema_validation", "oracle_agreement_test"],
        "problem_solution": {
            "problem": "The sample cases alone rarely exercise the boundaries, and a solution can pass samples while failing on an empty or maximal input.",
            "naive_agent_failure": "An agent runs only the two given samples, ships, and fails a hidden test at the size limit.",
            "solution": "A generate step that keeps the sample cases as oracles and derives boundary cases (min/max, empty, single) as additional inputs.",
            "core_components": ["sample-case importer", "boundary-case deriver", "oracle attacher"],
            "common_inputs": ["parsed problem object"],
            "common_outputs": ["test-case set", "sample cases with expected outputs", "derived boundary inputs"],
            "known_pitfalls": ["derived cases that violate the constraints", "no expected output for a derived case", "duplicating the samples without adding coverage"],
            "success_signals": ["sample cases carry their expected outputs", "boundary inputs respect the constraints"],
        },
        "source_ref_families": ["competitive-programming problem structure", "boundary-value test design"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:cp.enumerate_edge_cases",
        "domain": "competitive_programming",
        "title": "Enumerate Edge Cases",
        "input_edge": "ParsedProblem+ConstraintSet",
        "output_edge": "EdgeCaseSet",
        "blackbox": {
            "does": "Systematically enumerates the boundary and degenerate cases a problem's constraints imply - empty input, extreme values, ties, overflow thresholds, disconnected structure - as concrete inputs for stress testing."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "agent.tool"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json"],
        "proof_requirements": ["schema_validation", "boundary_coverage_test"],
        "problem_solution": {
            "problem": "Most wrong answers hide in a handful of degenerate cases that the samples never show, and enumerating them by hand is easy to do incompletely.",
            "naive_agent_failure": "An agent tests only typical inputs and never checks the empty case, the single element, or the value that overflows a 32-bit integer.",
            "solution": "An enumerate step that derives the degenerate and boundary inputs the constraints imply and emits each as a concrete case.",
            "core_components": ["boundary deriver", "degenerate-case generator", "overflow-threshold finder"],
            "common_inputs": ["parsed problem object", "numeric constraint set"],
            "common_outputs": ["edge-case set", "boundary and degenerate inputs", "overflow-threshold cases"],
            "known_pitfalls": ["skipping the empty or single-element case", "ignoring integer-overflow thresholds", "generating cases outside the constraints"],
            "success_signals": ["the empty, single, and maximal cases are present", "each case satisfies the constraints"],
        },
        "source_ref_families": ["boundary-value analysis", "competitive-programming edge-case checklists"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:cp.run_solution",
        "domain": "competitive_programming",
        "title": "Run Solution Against Judge",
        "input_edge": "SolutionCode+TestCaseSet+JudgePolicy",
        "output_edge": "JudgeResult",
        "blackbox": {
            "does": "Executes solution code against a test-case set in a resource-bounded sandbox and returns a per-case judge result of accepted, wrong-answer, time-limit, or runtime-error with the failing input on the first mismatch."
        },
        "effects": ["file_read", "artifact_write"],
        "base_runtime_targets": ["sandbox.runner", "local.python"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:cli_command", "wrap:queue_worker",
            "wrap:kubernetes_job",
        ],
        "applicable_data_formats": ["json", "text"],
        "proof_requirements": ["schema_validation", "sandbox_isolation_test"],
        "problem_solution": {
            "problem": "A solution is only as good as its judged behavior on real inputs under the real time and memory limits, isolated from the host.",
            "naive_agent_failure": "An agent reasons that the code looks right and submits, without ever executing it against the samples or the limits.",
            "solution": "A run step that executes the code per case in a bounded sandbox and classifies each outcome, surfacing the first failing input.",
            "core_components": ["sandboxed executor", "per-case verdict classifier", "first-failure capturer"],
            "common_inputs": ["solution code", "test-case set", "time and memory limits"],
            "common_outputs": ["per-case judge result", "verdict classification", "first failing input"],
            "known_pitfalls": ["running without enforcing limits", "swallowing a runtime error as wrong-answer", "leaking host state into execution"],
            "success_signals": ["every case gets a verdict", "the first mismatch reports its input"],
        },
        "source_ref_families": ["online-judge evaluation model", "sandboxed execution"],
        "risk_class": "high",
        "human_review_required": True,
    },
    {
        "family_id": "prim:cp.complexity_gate",
        "domain": "competitive_programming",
        "title": "Complexity Gate On Solution",
        "input_edge": "SolutionCode+ComplexityBudget",
        "output_edge": "ComplexityReport",
        "blackbox": {
            "does": "Statically and empirically checks whether a solution's growth stays within the complexity budget - inspecting nesting and measuring runtime across increasing input sizes - and flags a solution whose observed growth exceeds the budget."
        },
        "effects": ["file_read"],
        "base_runtime_targets": ["local.python", "sandbox.runner"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:cli_command", "wrap:kubernetes_job",
        ],
        "applicable_data_formats": ["json"],
        "proof_requirements": ["schema_validation", "complexity_bound_test"],
        "problem_solution": {
            "problem": "A solution can be correct yet exceed the time budget, and that only shows up as a limit exceeded verdict unless it is checked ahead of submission.",
            "naive_agent_failure": "An agent trusts a correct-looking solution and never checks that its growth curve stays within the budget at the largest input.",
            "solution": "A gate that inspects loop nesting for a static estimate and times the solution across growing inputs, flagging growth that exceeds the budget.",
            "core_components": ["static nesting estimator", "growth-curve profiler", "budget comparator"],
            "common_inputs": ["solution code", "complexity budget"],
            "common_outputs": ["complexity report", "observed growth curve", "within-budget or over-budget verdict"],
            "known_pitfalls": ["static estimate fooled by hidden library complexity", "profiling only small inputs", "ignoring memory growth"],
            "success_signals": ["the observed growth matches the intended class", "over-budget solutions are flagged before submission"],
        },
        "source_ref_families": ["algorithmic complexity analysis", "empirical growth profiling"],
        "risk_class": "medium",
        "human_review_required": False,
    },
    {
        "family_id": "prim:cp.differential_test",
        "domain": "competitive_programming",
        "title": "Differential Test Against Reference",
        "input_edge": "SolutionCode+ReferenceSolution+TestCaseSet+StressPolicy",
        "output_edge": "DiffReport",
        "blackbox": {
            "does": "Runs a candidate solution and a trusted (usually brute-force) reference on the same generated inputs and reports the first input where their outputs disagree, isolating a minimal counterexample."
        },
        "effects": ["file_read", "artifact_write"],
        "base_runtime_targets": ["sandbox.runner", "local.python"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:cli_command", "wrap:queue_worker",
            "wrap:kubernetes_job",
        ],
        "applicable_data_formats": ["json", "text"],
        "proof_requirements": ["schema_validation", "reference_agreement_test"],
        "problem_solution": {
            "problem": "A fast solution can be subtly wrong in ways no hand-written case catches, and the surest check is agreement with a trusted reference on random inputs.",
            "naive_agent_failure": "An agent ships an optimized solution that disagrees with a brute force on a case it never generated, and only the judge finds out.",
            "solution": "A differential step that generates inputs, runs both solutions, and reports the first disagreement as a minimized counterexample.",
            "core_components": ["input generator", "dual executor", "counterexample minimizer"],
            "common_inputs": ["candidate solution", "trusted reference solution", "generated test cases"],
            "common_outputs": ["differential report", "first disagreeing input", "minimized counterexample"],
            "known_pitfalls": ["a reference that shares the candidate's bug", "generated inputs violating constraints", "non-determinism making disagreement irreproducible"],
            "success_signals": ["agreement across many random inputs raises confidence", "any disagreement yields a concrete counterexample"],
        },
        "source_ref_families": ["differential / property-based testing", "competitive-programming stress-testing"],
        "risk_class": "high",
        "human_review_required": True,
    },
    {
        "family_id": "prim:cp.stress_test",
        "domain": "competitive_programming",
        "title": "Stress Test Under Constraints",
        "input_edge": "SolutionCode+ConstraintSet+StressPolicy",
        "output_edge": "StressReport",
        "blackbox": {
            "does": "Repeatedly runs a solution on randomized inputs at and near the constraint limits, checking declared invariants and time/memory bounds, and reports the first input that breaks an invariant or a limit."
        },
        "effects": ["file_read", "artifact_write"],
        "base_runtime_targets": ["sandbox.runner", "local.python"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:cli_command", "wrap:queue_worker",
            "wrap:kubernetes_job",
        ],
        "applicable_data_formats": ["json", "text"],
        "proof_requirements": ["schema_validation", "invariant_preservation_test"],
        "problem_solution": {
            "problem": "Behavior at the constraint limits differs from behavior on small inputs, and time or memory blowups only appear under maximal randomized load.",
            "naive_agent_failure": "An agent validates on tiny inputs and never stresses the solution at the size limit where it actually breaks.",
            "solution": "A stress step that generates randomized inputs at and near the limits, checks invariants and bounds each run, and reports the first breakage.",
            "core_components": ["limit-scaled input generator", "invariant checker", "first-breakage reporter"],
            "common_inputs": ["solution code", "numeric constraint set", "iteration and seed policy"],
            "common_outputs": ["stress report", "first invariant or limit breakage", "coverage summary"],
            "known_pitfalls": ["generating below the real limits", "no invariant to check against", "an unbounded generator that never reaches the limit"],
            "success_signals": ["the solution holds invariants across randomized limit-scale runs", "any breakage reports its input"],
        },
        "source_ref_families": ["competitive-programming stress-testing", "property-based testing"],
        "risk_class": "high",
        "human_review_required": True,
    },
    # ==================================================================
    # algorithms (classic kernels a filled solution is assembled from)
    # ==================================================================
    {
        "family_id": "prim:algo.binary_search",
        "domain": "algorithms",
        "title": "Binary Search On Monotone Predicate",
        "input_edge": "SortedArray+TargetValue",
        "output_edge": "SearchResult",
        "blackbox": {
            "does": "Finds the boundary index in a sorted array or monotone predicate where the condition flips, in logarithmic steps, returning the insertion point when the target is absent."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "library.call"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json"],
        "proof_requirements": ["schema_validation", "correctness_property_test"],
        "problem_solution": {
            "problem": "Locating a value or a predicate boundary in a sorted range by scanning is wasteful when the order lets you halve the search each step.",
            "naive_agent_failure": "An agent hand-rolls the loop bounds and produces the classic off-by-one that skips the boundary or loops forever.",
            "solution": "A binary-search kernel with tested half-open bounds that returns the boundary or the insertion point without off-by-one drift.",
            "core_components": ["half-open bound manager", "midpoint evaluator", "boundary/insertion resolver"],
            "common_inputs": ["sorted array or monotone predicate", "target value"],
            "common_outputs": ["boundary index", "found flag", "insertion point when absent"],
            "known_pitfalls": ["off-by-one in the loop bounds", "infinite loop on equal bounds", "integer midpoint overflow in fixed-width languages"],
            "success_signals": ["the returned index satisfies the boundary property", "absent targets return the correct insertion point"],
        },
        "source_ref_families": ["classic algorithms (binary search)"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:algo.two_pointers",
        "domain": "algorithms",
        "title": "Two-Pointer Scan",
        "input_edge": "SortedArray+TargetValue",
        "output_edge": "PairResultSet",
        "blackbox": {
            "does": "Sweeps a pair of indices inward or in tandem over a sorted sequence to find pairs or subarrays meeting a target relation in a single linear pass."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "library.call"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json"],
        "proof_requirements": ["schema_validation", "correctness_property_test"],
        "problem_solution": {
            "problem": "Finding pairs or ranges meeting a relation over a sorted sequence should not cost a quadratic double loop when a coordinated pointer sweep suffices.",
            "naive_agent_failure": "An agent writes nested loops and misses that the sorted order lets a single inward sweep find every qualifying pair.",
            "solution": "A two-pointer kernel that advances the pointers by the relation, covering all qualifying pairs in one linear pass.",
            "core_components": ["pointer initializer", "relation-driven advancer", "result collector"],
            "common_inputs": ["sorted sequence", "target relation or value"],
            "common_outputs": ["qualifying pair or range set", "pointer trace"],
            "known_pitfalls": ["advancing the wrong pointer and skipping a pair", "double-counting symmetric pairs", "assuming sorted input that is not"],
            "success_signals": ["every qualifying pair is found once", "the scan stays linear"],
        },
        "source_ref_families": ["classic algorithms (two pointers)"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:algo.sliding_window",
        "domain": "algorithms",
        "title": "Sliding Window Aggregate",
        "input_edge": "NumericArray+WindowPolicy",
        "output_edge": "WindowResult",
        "blackbox": {
            "does": "Maintains a running aggregate over a moving contiguous window, expanding and contracting the bounds to satisfy a window condition while updating the aggregate in constant amortized work per step."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "library.call"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json"],
        "proof_requirements": ["schema_validation", "correctness_property_test"],
        "problem_solution": {
            "problem": "Recomputing an aggregate over every contiguous window from scratch is quadratic when the window can be updated incrementally as it slides.",
            "naive_agent_failure": "An agent recomputes the sum or count for each window position, turning a linear scan into a quadratic one.",
            "solution": "A sliding-window kernel that expands and contracts the bounds against a condition and updates the aggregate incrementally.",
            "core_components": ["window-bound controller", "incremental aggregator", "condition evaluator"],
            "common_inputs": ["numeric array", "window condition or size policy"],
            "common_outputs": ["best or qualifying window result", "window bounds", "aggregate value"],
            "known_pitfalls": ["failing to contract the window when the condition breaks", "stale aggregate after a move", "off-by-one at the window edges"],
            "success_signals": ["the aggregate matches a recomputed window", "the scan stays linear"],
        },
        "source_ref_families": ["classic algorithms (sliding window)"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:algo.prefix_sum",
        "domain": "algorithms",
        "title": "Prefix Sum And Range Query",
        "input_edge": "NumericArray",
        "output_edge": "PrefixSumArray",
        "blackbox": {
            "does": "Precomputes cumulative sums so any contiguous range total is answered in constant time by a single difference, converting repeated range queries from linear to constant per query."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "library.call"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json"],
        "proof_requirements": ["schema_validation", "correctness_property_test"],
        "problem_solution": {
            "problem": "Answering many range-sum queries by re-adding the range each time is wasteful when one precomputation makes each query a constant-time difference.",
            "naive_agent_failure": "An agent loops over each queried range every time, so a batch of range queries becomes quadratic.",
            "solution": "A prefix-sum kernel that precomputes cumulative totals once and answers each range as a difference of two prefixes.",
            "core_components": ["cumulative accumulator", "range-difference resolver", "index-bound guard"],
            "common_inputs": ["numeric array"],
            "common_outputs": ["prefix-sum array", "constant-time range totals"],
            "known_pitfalls": ["off-by-one between inclusive and exclusive bounds", "ignoring integer overflow on large sums", "forgetting the empty-prefix zero"],
            "success_signals": ["a range total matches a direct summation", "each query is constant time"],
        },
        "source_ref_families": ["classic algorithms (prefix sums)"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:algo.bfs_traverse",
        "domain": "algorithms",
        "title": "Breadth-First Traversal",
        "input_edge": "Graph+SourceNode",
        "output_edge": "TraversalOrder",
        "blackbox": {
            "does": "Explores a graph in breadth-first layers from a source, producing the visit order and shortest unweighted-hop distances, visiting each node and edge once."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "library.call"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json"],
        "proof_requirements": ["schema_validation", "correctness_property_test"],
        "problem_solution": {
            "problem": "Shortest paths in an unweighted graph and layer-by-layer exploration need a queue-ordered traversal, not a depth-first dive.",
            "naive_agent_failure": "An agent uses recursion or a stack and gets depth-first order, so its hop distances are wrong.",
            "solution": "A BFS kernel that expands a FIFO frontier layer by layer, recording visit order and unweighted-hop distances.",
            "core_components": ["FIFO frontier", "visited set", "distance recorder"],
            "common_inputs": ["graph adjacency", "source node"],
            "common_outputs": ["breadth-first visit order", "unweighted-hop distances", "predecessor map"],
            "known_pitfalls": ["revisiting nodes without a visited set", "using a stack and getting DFS order", "not handling disconnected components"],
            "success_signals": ["distances equal the true minimum hop count", "each node is dequeued once"],
        },
        "source_ref_families": ["classic algorithms (breadth-first search)"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:algo.dfs_traverse",
        "domain": "algorithms",
        "title": "Depth-First Traversal",
        "input_edge": "Graph+SourceNode",
        "output_edge": "TraversalOrder",
        "blackbox": {
            "does": "Explores a graph depth-first from a source with an explicit stack, producing pre/post visit order and detecting back edges, without risking native recursion-depth limits."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "library.call"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json"],
        "proof_requirements": ["schema_validation", "correctness_property_test"],
        "problem_solution": {
            "problem": "Depth-first order, cycle detection, and post-order processing need a controlled traversal that does not blow the native recursion stack on deep graphs.",
            "naive_agent_failure": "An agent recurses naively and hits a recursion-depth error on a long path, or misses back-edge detection.",
            "solution": "A DFS kernel with an explicit stack that records pre/post order and flags back edges, immune to recursion-depth limits.",
            "core_components": ["explicit stack", "pre/post-order recorder", "back-edge detector"],
            "common_inputs": ["graph adjacency", "source node"],
            "common_outputs": ["depth-first visit order", "pre/post numbers", "back-edge flags"],
            "known_pitfalls": ["native recursion overflow on deep graphs", "missing post-order for a dependent computation", "not marking nodes on the current path"],
            "success_signals": ["every reachable node is visited", "back edges are detected on cyclic graphs"],
        },
        "source_ref_families": ["classic algorithms (depth-first search)"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:algo.dijkstra_shortest_path",
        "domain": "algorithms",
        "title": "Dijkstra Shortest Paths",
        "input_edge": "WeightedGraph+SourceNode",
        "output_edge": "DistanceMap",
        "blackbox": {
            "does": "Computes single-source shortest paths over non-negative edge weights with a priority-queue frontier, settling each node at its final distance and recording predecessors for path reconstruction."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "library.call"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json"],
        "proof_requirements": ["schema_validation", "correctness_property_test"],
        "problem_solution": {
            "problem": "Shortest paths with weighted edges need a priority-ordered frontier; a plain BFS gives wrong distances once weights differ.",
            "naive_agent_failure": "An agent applies BFS to a weighted graph and reports hop counts instead of weighted distances, or applies Dijkstra to negative weights.",
            "solution": "A Dijkstra kernel with a min-priority frontier over non-negative weights that settles each node once and records predecessors.",
            "core_components": ["min-priority frontier", "distance relaxer", "predecessor recorder"],
            "common_inputs": ["weighted graph with non-negative edges", "source node"],
            "common_outputs": ["distance map", "predecessor map", "settled-node order"],
            "known_pitfalls": ["applying it to negative edge weights", "not skipping stale queue entries", "re-relaxing a settled node"],
            "success_signals": ["distances satisfy the triangle inequality", "reconstructed paths match the distances"],
        },
        "source_ref_families": ["classic algorithms (Dijkstra shortest path)"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:algo.union_find",
        "domain": "algorithms",
        "title": "Union-Find Connectivity",
        "input_edge": "EdgeList",
        "output_edge": "ComponentMap",
        "blackbox": {
            "does": "Maintains disjoint-set connectivity with path compression and union by rank, answering same-component queries and assigning each node a component id in near-constant amortized time per operation."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "library.call"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json"],
        "proof_requirements": ["schema_validation", "correctness_property_test"],
        "problem_solution": {
            "problem": "Tracking which elements are connected as edges arrive, and answering same-group queries, is slow without a disjoint-set structure.",
            "naive_agent_failure": "An agent recomputes connectivity with a fresh traversal per query, turning an incremental problem quadratic.",
            "solution": "A union-find kernel with path compression and union by rank that answers connectivity in near-constant amortized time.",
            "core_components": ["parent forest", "path compressor", "union-by-rank merger"],
            "common_inputs": ["edge list or union operations"],
            "common_outputs": ["component id per node", "same-component query results", "component count"],
            "known_pitfalls": ["skipping path compression and degrading to linear finds", "union without rank creating tall trees", "off-by-one node indexing"],
            "success_signals": ["same-component queries agree with a reference traversal", "operations stay near-constant amortized"],
        },
        "source_ref_families": ["classic data structures (disjoint set / union-find)"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:algo.topological_sort",
        "domain": "algorithms",
        "title": "Topological Sort",
        "input_edge": "DirectedGraph",
        "output_edge": "TopologicalOrder",
        "blackbox": {
            "does": "Orders the nodes of a directed acyclic graph so every edge points forward, using indegree peeling, and reports a cycle when no valid ordering exists."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "library.call"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json"],
        "proof_requirements": ["schema_validation", "correctness_property_test"],
        "problem_solution": {
            "problem": "Scheduling tasks with dependencies requires an order where prerequisites come first, and detecting when the dependencies form a cycle.",
            "naive_agent_failure": "An agent orders tasks by a heuristic and violates a dependency, or loops forever on a cyclic graph without detecting it.",
            "solution": "A topological-sort kernel that peels zero-indegree nodes and reports a cycle if any node remains unpeeled.",
            "core_components": ["indegree counter", "zero-indegree queue", "cycle detector"],
            "common_inputs": ["directed graph adjacency"],
            "common_outputs": ["topological order", "cycle report when present"],
            "known_pitfalls": ["not detecting a cycle and returning a partial order", "unstable ordering when a deterministic one is required", "miscounting indegrees"],
            "success_signals": ["every edge points forward in the order", "a cyclic graph is reported, not ordered"],
        },
        "source_ref_families": ["classic algorithms (topological sort)"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:algo.dp_table",
        "domain": "algorithms",
        "title": "Dynamic Programming Table Fill",
        "input_edge": "DPRecurrence+DPBounds",
        "output_edge": "OptimalValue",
        "blackbox": {
            "does": "Fills a memoized state table in dependency order from a declared recurrence and base cases, computing each state once and reconstructing the optimal value and choice path from the table."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "library.call"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json"],
        "proof_requirements": ["schema_validation", "correctness_property_test"],
        "problem_solution": {
            "problem": "Overlapping subproblems recomputed naively cause exponential blowup, when each state need only be solved once and reused.",
            "naive_agent_failure": "An agent writes a plain recursion that recomputes the same subproblem exponentially and times out.",
            "solution": "A DP kernel that evaluates states in dependency order from a declared recurrence and base cases, memoizing each once and reconstructing the answer.",
            "core_components": ["state-order resolver", "recurrence evaluator", "choice-path reconstructor"],
            "common_inputs": ["state recurrence and transition", "base cases and state bounds"],
            "common_outputs": ["optimal value", "filled state table", "reconstructed choice path"],
            "known_pitfalls": ["evaluating a state before its dependencies", "wrong base cases", "exceeding memory on a large table"],
            "success_signals": ["each state is computed once", "the reconstructed path realizes the optimal value"],
        },
        "source_ref_families": ["classic algorithms (dynamic programming)"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:algo.monotonic_stack",
        "domain": "algorithms",
        "title": "Monotonic Stack Next-Greater",
        "input_edge": "NumericArray",
        "output_edge": "SpanArray",
        "blackbox": {
            "does": "Maintains a monotonic stack to answer next-greater / previous-smaller and span queries for every element in a single linear pass, each element pushed and popped at most once."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "library.call"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json"],
        "proof_requirements": ["schema_validation", "correctness_property_test"],
        "problem_solution": {
            "problem": "Next-greater-element and span problems look quadratic but resolve in one linear pass with a stack that stays monotonic.",
            "naive_agent_failure": "An agent scans forward from each element to find its next greater, producing a quadratic solution.",
            "solution": "A monotonic-stack kernel that pushes indices and pops on the boundary condition, resolving each element's answer once.",
            "core_components": ["monotonic stack", "pop-on-condition resolver", "index-to-answer writer"],
            "common_inputs": ["numeric array"],
            "common_outputs": ["next-greater or span array", "per-element answer"],
            "known_pitfalls": ["maintaining the wrong monotonic direction", "storing values instead of indices when the index is needed", "not draining the stack at the end"],
            "success_signals": ["each element is pushed and popped at most once", "answers match a brute-force reference"],
        },
        "source_ref_families": ["classic algorithms (monotonic stack)"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:algo.heap_top_k",
        "domain": "algorithms",
        "title": "Heap Top-K Selection",
        "input_edge": "NumericArray+KValue",
        "output_edge": "TopKSet",
        "blackbox": {
            "does": "Selects the k largest or smallest elements of a stream using a bounded heap of size k, processing each element once and keeping only k in memory."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "library.call"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json"],
        "proof_requirements": ["schema_validation", "correctness_property_test"],
        "problem_solution": {
            "problem": "Finding the top k of a large or streaming set by fully sorting is wasteful when a bounded heap keeps only k candidates.",
            "naive_agent_failure": "An agent sorts the entire input to take the last k, paying a full sort and holding everything in memory.",
            "solution": "A heap kernel that maintains a size-k heap, replacing its extreme as better elements arrive, in a single pass.",
            "core_components": ["bounded k-heap", "replace-extreme rule", "final-order extractor"],
            "common_inputs": ["numeric array or stream", "k"],
            "common_outputs": ["top-k set", "optionally ordered"],
            "known_pitfalls": ["using a max-heap where a min-heap is needed for top-k largest", "k larger than the input", "unstable ties when order matters"],
            "success_signals": ["the result equals the k extremes from a full sort", "memory stays bounded by k"],
        },
        "source_ref_families": ["classic data structures (binary heap / priority queue)"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:algo.kmp_search",
        "domain": "algorithms",
        "title": "KMP Substring Search",
        "input_edge": "TextString+PatternString",
        "output_edge": "MatchPositionSet",
        "blackbox": {
            "does": "Finds all occurrences of a pattern in text in linear time using a precomputed prefix-function to skip redundant comparisons, never re-scanning already-matched text."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "library.call"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json", "text"],
        "proof_requirements": ["schema_validation", "correctness_property_test"],
        "problem_solution": {
            "problem": "Substring search by restarting the comparison after every mismatch is quadratic in the worst case, when a prefix-function lets it skip ahead.",
            "naive_agent_failure": "An agent uses a naive character-by-character rescan and degrades to quadratic on adversarial repetitive text.",
            "solution": "A KMP kernel that precomputes the prefix-function and advances without re-scanning matched text, staying linear.",
            "core_components": ["prefix-function builder", "mismatch-skip driver", "match collector"],
            "common_inputs": ["text string", "pattern string"],
            "common_outputs": ["all match positions", "match count"],
            "known_pitfalls": ["an incorrect prefix-function table", "off-by-one at the pattern boundary", "missing overlapping matches"],
            "success_signals": ["all matches agree with a brute-force scan", "runtime stays linear on repetitive text"],
        },
        "source_ref_families": ["classic algorithms (Knuth-Morris-Pratt string matching)"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:algo.interval_merge",
        "domain": "algorithms",
        "title": "Interval Merge And Sweep",
        "input_edge": "IntervalSet",
        "output_edge": "MergedIntervalSet",
        "blackbox": {
            "does": "Sorts intervals by start and sweeps once to merge overlaps, producing a disjoint set of maximal intervals and the peak overlap count along the sweep."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "library.call"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json"],
        "proof_requirements": ["schema_validation", "correctness_property_test"],
        "problem_solution": {
            "problem": "Overlapping intervals must be consolidated into disjoint maximal ranges, and comparing every pair to find overlaps is quadratic.",
            "naive_agent_failure": "An agent compares all interval pairs and mishandles touching-but-not-overlapping endpoints.",
            "solution": "An interval kernel that sorts by start and sweeps once, merging while the current end covers the next start.",
            "core_components": ["start-order sorter", "overlap merger", "peak-overlap counter"],
            "common_inputs": ["set of intervals"],
            "common_outputs": ["merged disjoint intervals", "peak concurrent overlap"],
            "known_pitfalls": ["treating touching endpoints inconsistently", "forgetting to sort first", "losing an interval at the boundary"],
            "success_signals": ["output intervals are disjoint and maximal", "their union covers the same points as the input"],
        },
        "source_ref_families": ["classic algorithms (interval scheduling / sweep line)"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:algo.backtracking_enumerate",
        "domain": "algorithms",
        "title": "Backtracking Enumeration",
        "input_edge": "ChoiceSpace+PruneRule",
        "output_edge": "SolutionSet",
        "blackbox": {
            "does": "Explores a decision tree depth-first, extending partial solutions and pruning branches that violate constraints, enumerating all complete solutions without materializing the full space."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "library.call"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json"],
        "proof_requirements": ["schema_validation", "correctness_property_test"],
        "problem_solution": {
            "problem": "Enumerating combinations, permutations, or placements by generating the entire space and filtering is infeasible when pruning invalid branches early is possible.",
            "naive_agent_failure": "An agent generates all candidates then filters, exhausting memory on a space that pruning would have kept small.",
            "solution": "A backtracking kernel that extends partial solutions depth-first and prunes as soon as a constraint is violated, yielding only complete valid solutions.",
            "core_components": ["partial-solution extender", "constraint pruner", "solution emitter"],
            "common_inputs": ["choice space and construction step", "pruning constraint"],
            "common_outputs": ["enumerated valid solutions", "explored-branch count"],
            "known_pitfalls": ["not undoing a choice on backtrack", "pruning too aggressively and dropping valid solutions", "pruning too late and exploring dead branches"],
            "success_signals": ["every emitted solution satisfies the constraints", "pruned branches contain no valid solution"],
        },
        "source_ref_families": ["classic algorithms (backtracking / branch and bound)"],
        "risk_class": "low",
        "human_review_required": False,
    },
]
