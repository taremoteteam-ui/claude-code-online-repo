"""Seed rows for reusable-primitive families: semantic_layer (metric/dimension
definition and metric-query resolution) and multiset_ops (set-algebra families
over record sets - the multi-input / multi-output primitives the north-star
brief calls "multi-set").

Pure data module: one top-level constant FAMILIES (list of dicts). Each row is
candidate seed material describing one recurring semantic-layer or set-algebra
pattern; the builder (scripts/build_universal_primitive_pack.py, reused by
scripts/build_warehouse_analytics_pack.py) injects record_type, version,
candidate=True, serves_truth=False, and crosses each family with the runtime
wrappers it declares applicable.

Two domains:

  semantic_layer  (ids "prim:semantic.*"): the metric/dimension abstraction that
    sits between physical marts and consumers - metric definition, dimension
    definition, semantic model assembly, metric-query planning and resolution,
    metric-to-SQL compilation, governed metric catalogs, metric consistency
    checks, and cross-metric joins on shared grain. Ports: SemanticModelSpec,
    MetricSpec, DimensionSpec (config, request-supplied), MartTable/StagingTable
    (physical source), MetricQuery (a request), MetricResultSet /
    AnalyticsResultSet (result), SemanticModel (assembled model), MetricCatalog.

  multiset_ops  (ids "prim:multiset.*"): set algebra over record sets so agents
    can compose union / intersect / except / symmetric-difference / semi-join /
    anti-join / cross-join / distinct-union / n-ary union / partition / set
    membership and Jaccard overlap on the typed edge graph. Ports reuse the
    dataeng set vocabulary: RecordSetA, RecordSetB, RecordSetFamily (a set of
    sets), UnionedRecordSet, IntersectedRecordSet, DifferenceRecordSet,
    SymmetricDifferenceSet, MatchKeySpec/SetOpPolicy (config), OverlapReport.

Ports use the canonical warehouse vocabulary already emitted by the dbt /
modeling / dataeng / analytics seeds so these families compose with them on the
typed edge graph (e.g. a dedupe/union multiset op feeds a StagingTable that an
analytics window family then consumes). Effects are declared honestly: set
algebra and metric resolution read source tables and write a result table, so
they declare database_read+database_write. Union/intersect/except carry
set-law proofs (idempotency for union-distinct, commutativity where it holds,
row_count_reconciliation bounding the output cardinality). Metric definitions
are pure specs (no source read) and declare only schema_validation +
determinism. No unmeasured performance, savings, or benchmark claims appear
anywhere. None of these patterns overwrite or destroy their source, so
human_review_required is False throughout.

Grounded in ANSI SQL set operators (UNION / INTERSECT / EXCEPT), relational
set-algebra semantics, and the semantic-layer / metrics-layer pattern (a
governed metric definition compiled to SQL at query time).
"""

FAMILIES = [
    # ==================================================================
    # semantic_layer: metric and dimension definitions
    # ==================================================================
    {
        "family_id": "prim:semantic.metric_define",
        "domain": "semantic_layer",
        "title": "Metric Definition",
        "input_edge": "MetricSpec",
        "output_edge": "SemanticModel",
        "blackbox": {
            "does": "Validates a metric definition (name, aggregation, base measure, allowed grains, filters) into a governed semantic-model entry with a stable metric key, without touching any physical table."
        },
        "effects": ["none"],
        "base_runtime_targets": ["semantic.metric", "dbt.metric"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:fastapi_endpoint",
        ],
        "applicable_data_formats": ["rows", "json"],
        "proof_requirements": ["schema_validation", "determinism_test"],
        "problem_solution": {
            "problem": "Business metrics like active users or net revenue are re-derived inconsistently in every dashboard, so two reports disagree on the same number because the aggregation, filters, or grain differ silently.",
            "naive_agent_failure": "An agent writes ad-hoc SUM/COUNT SQL per dashboard, embedding filter logic inline, so no single governed definition exists and the same metric name means different math in different places.",
            "solution": "A definition step that captures the aggregation, base measure, allowed grains, and canonical filters once as a validated semantic-model entry keyed by a stable metric id.",
            "core_components": ["metric spec validator", "aggregation and grain resolver", "stable metric-key assigner"],
            "common_inputs": ["metric name and description", "aggregation function", "base measure column", "allowed grains and canonical filters"],
            "common_outputs": ["validated metric entry", "stable metric key", "semantic model fragment"],
            "known_pitfalls": ["embedding filters that should be query-time dimensions", "allowing a grain the base measure cannot support", "duplicate metric keys for the same concept"],
            "success_signals": ["metric key is stable across rebuilds", "the same definition drives every consumer"],
        },
        "source_ref_families": ["semantic layer / metrics layer pattern", "governed metric definition practice"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:semantic.dimension_define",
        "domain": "semantic_layer",
        "title": "Dimension Definition",
        "input_edge": "DimensionSpec",
        "output_edge": "SemanticModel",
        "blackbox": {
            "does": "Validates a dimension definition (name, key, attribute columns, and the join path back to fact grain) into a governed semantic-model entry so metrics can be sliced by it consistently."
        },
        "effects": ["none"],
        "base_runtime_targets": ["semantic.dimension", "dbt.model"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:fastapi_endpoint",
        ],
        "applicable_data_formats": ["rows", "json"],
        "proof_requirements": ["schema_validation", "determinism_test"],
        "problem_solution": {
            "problem": "Slicing a metric by a dimension requires a known join path and attribute set, but those are re-invented per query so the same slice yields different joins and double-counts fanned-out rows.",
            "naive_agent_failure": "An agent joins a dimension table without declaring its key grain, fanning out the fact rows and inflating additive measures.",
            "solution": "A definition step that records the dimension key, attributes, and the validated join path to fact grain so every metric slices it the same way.",
            "core_components": ["dimension spec validator", "join-path resolver", "grain-fanout guard"],
            "common_inputs": ["dimension name and key", "attribute columns", "join path to fact grain"],
            "common_outputs": ["validated dimension entry", "declared join path", "semantic model fragment"],
            "known_pitfalls": ["joining at a finer grain than the dimension key", "missing surrogate key on the dimension", "attributes that belong to a different grain"],
            "success_signals": ["dimension key uniquely identifies its rows", "slicing does not inflate additive measures"],
        },
        "source_ref_families": ["semantic layer / metrics layer pattern", "dimensional modeling conformed dimensions"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:semantic.model_assemble",
        "domain": "semantic_layer",
        "title": "Semantic Model Assemble",
        "input_edge": "SemanticModelSpec",
        "output_edge": "SemanticModel+MetricCatalog",
        "blackbox": {
            "does": "Assembles validated metric and dimension entries plus their physical bindings into one semantic model and emits a queryable metric catalog with resolvable metric/dimension keys."
        },
        "effects": ["none"],
        "base_runtime_targets": ["semantic.model", "dbt.semantic_model"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:fastapi_endpoint",
            "wrap:cron_job",
        ],
        "applicable_data_formats": ["rows", "json"],
        "proof_requirements": ["schema_validation", "referential_integrity_test"],
        "problem_solution": {
            "problem": "Metrics, dimensions, and their physical table bindings live in scattered files, so a consumer cannot discover what is queryable or how a metric maps to real columns.",
            "naive_agent_failure": "An agent hardcodes table and column names in each query, so when a mart is renamed every consumer breaks and nothing lists the available metrics.",
            "solution": "An assembly step that binds validated metrics and dimensions to physical marts and emits a single catalog whose keys are the only interface consumers touch.",
            "core_components": ["metric/dimension collector", "physical-binding resolver", "catalog emitter"],
            "common_inputs": ["validated metric entries", "validated dimension entries", "physical mart bindings"],
            "common_outputs": ["assembled semantic model", "queryable metric catalog", "resolvable metric and dimension keys"],
            "known_pitfalls": ["dangling binding to a nonexistent column", "two metrics bound to conflicting grains", "catalog omitting a defined metric"],
            "success_signals": ["every catalog metric resolves to a real column", "consumers reference keys, never raw tables"],
        },
        "source_ref_families": ["semantic layer / metrics layer pattern", "metric catalog governance"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:semantic.metric_query_plan",
        "domain": "semantic_layer",
        "title": "Metric Query Plan",
        "input_edge": "MetricQuery+SemanticModel",
        "output_edge": "MetricQueryPlan",
        "blackbox": {
            "does": "Resolves a metric query (metrics, group-by dimensions, filters, grain) against the semantic model into a validated query plan, rejecting requests for unsupported grains or undefined metrics before any SQL runs."
        },
        "effects": ["none"],
        "base_runtime_targets": ["semantic.query_planner", "local.python"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:fastapi_endpoint",
        ],
        "applicable_data_formats": ["json", "rows"],
        "proof_requirements": ["schema_validation", "determinism_test"],
        "problem_solution": {
            "problem": "A consumer asks for metrics grouped by dimensions at a grain, but not every metric supports every grain, and unsupported combinations must fail early rather than return silently-wrong numbers.",
            "naive_agent_failure": "An agent generates SQL for any requested grain, so a non-additive metric gets summed across an unsupported dimension and returns a plausible but wrong total.",
            "solution": "A planning step that validates each requested metric and dimension against the semantic model, checks grain compatibility, and emits a resolved plan or an explicit rejection.",
            "core_components": ["metric/dimension resolver", "grain-compatibility checker", "query-plan emitter"],
            "common_inputs": ["requested metrics", "group-by dimensions and filters", "target grain", "semantic model"],
            "common_outputs": ["validated metric query plan", "resolved join and grain", "explicit rejection on unsupported combos"],
            "known_pitfalls": ["allowing a non-additive metric at an unsupported grain", "silently dropping an unknown dimension", "ignoring metric-specific filters"],
            "success_signals": ["unsupported grain requests are rejected, not answered wrongly", "the plan names every table and join it will use"],
        },
        "source_ref_families": ["semantic layer / metrics layer pattern", "query planning against a metric model"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:semantic.metric_compile_sql",
        "domain": "semantic_layer",
        "title": "Metric Query Compile To SQL",
        "input_edge": "MetricQueryPlan",
        "output_edge": "CompiledQuery",
        "blackbox": {
            "does": "Compiles a validated metric query plan into dialect-specific SQL with the correct aggregations, joins, group-by, and filters, deterministically for a given plan and dialect."
        },
        "effects": ["none"],
        "base_runtime_targets": ["semantic.compiler", "local.python"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json", "sql"],
        "proof_requirements": ["schema_validation", "determinism_test"],
        "problem_solution": {
            "problem": "The same metric query must become correct SQL for whatever warehouse dialect is in play, and the compilation must be reproducible so a plan always yields the same query.",
            "naive_agent_failure": "An agent writes dialect-specific SQL by hand each time, so aggregations and quoting drift between engines and the output is not reproducible.",
            "solution": "A compile step that turns the resolved plan into dialect SQL from a single template set, keyed by plan and dialect, with a byte-stable result.",
            "core_components": ["plan-to-SQL templater", "dialect adapter", "deterministic rendering"],
            "common_inputs": ["validated metric query plan", "target SQL dialect"],
            "common_outputs": ["compiled SQL text", "bound parameters", "referenced tables list"],
            "known_pitfalls": ["dialect-specific quoting or date functions", "non-deterministic column ordering", "losing a plan filter during compilation"],
            "success_signals": ["same plan and dialect compile to identical SQL", "compiled SQL references only planned tables"],
        },
        "source_ref_families": ["semantic layer / metrics layer pattern", "SQL dialect compilation"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:semantic.metric_resolve",
        "domain": "semantic_layer",
        "title": "Metric Query Resolve",
        "input_edge": "MetricQuery+SemanticModel+MartTable",
        "output_edge": "MetricResultSet+AnalyticsResultSet",
        "blackbox": {
            "does": "End-to-end resolves a metric query against the semantic model and physical marts into a metric result set, planning, compiling, and executing under the governed definitions so the numbers match every other consumer."
        },
        "effects": ["database_read", "database_write"],
        "base_runtime_targets": ["semantic.query", "warehouse.query"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:fastapi_endpoint",
            "wrap:queue_worker",
        ],
        "applicable_data_formats": ["rows", "json", "parquet"],
        "proof_requirements": ["schema_validation", "row_count_reconciliation",
                               "determinism_test"],
        "problem_solution": {
            "problem": "Consumers want a metric result set for a query, and it must equal what every other consumer would get for the same query so dashboards agree.",
            "naive_agent_failure": "An agent runs bespoke SQL that bypasses the governed definitions, so its totals differ from the canonical metric and reconciliation fails.",
            "solution": "A resolve step that plans and compiles against the semantic model, executes, and returns a result set carrying the metric keys and grain it was computed at.",
            "core_components": ["governed planner", "SQL compiler", "executor and result shaper"],
            "common_inputs": ["metric query", "semantic model", "physical marts"],
            "common_outputs": ["metric result set", "grain and metric keys on each row", "analytics result set"],
            "known_pitfalls": ["bypassing governed definitions with raw SQL", "returning a grain different from the request", "double counting via a fan-out join"],
            "success_signals": ["result reconciles with the governed metric definition", "same query returns the same totals across consumers"],
        },
        "source_ref_families": ["semantic layer / metrics layer pattern", "governed metric resolution"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:semantic.metric_consistency_check",
        "domain": "semantic_layer",
        "title": "Metric Consistency Check",
        "input_edge": "SemanticModel+MartTable",
        "output_edge": "MetricConsistencyReport",
        "blackbox": {
            "does": "Recomputes each governed metric two independent ways (definition-driven and a reference reconciliation query) and reports any metric whose totals disagree beyond a tolerance."
        },
        "effects": ["database_read"],
        "base_runtime_targets": ["semantic.audit", "warehouse.query"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cron_job",
            "wrap:kubernetes_job",
        ],
        "applicable_data_formats": ["rows", "json"],
        "proof_requirements": ["schema_validation", "row_count_reconciliation"],
        "problem_solution": {
            "problem": "A governed metric can drift from reality when its underlying marts change, and nothing detects that the definition and the physical data no longer agree.",
            "naive_agent_failure": "An agent trusts the definition without ever reconciling it against an independent recomputation, so silent drift ships to dashboards.",
            "solution": "A check that recomputes each metric via its definition and via an independent reference query and flags disagreements beyond tolerance.",
            "core_components": ["definition recomputation", "reference reconciliation query", "tolerance comparator"],
            "common_inputs": ["semantic model", "physical marts", "tolerance threshold"],
            "common_outputs": ["consistency report", "per-metric agreement status", "flagged drift list"],
            "known_pitfalls": ["comparing at mismatched grains", "tolerance too loose to catch drift", "reference query sharing the same bug as the definition"],
            "success_signals": ["disagreements are surfaced with the offending metric", "clean metrics report exact agreement"],
        },
        "source_ref_families": ["semantic layer / metrics layer pattern", "metric reconciliation audit"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:semantic.metric_join_conformed",
        "domain": "semantic_layer",
        "title": "Cross-Metric Conformed Join",
        "input_edge": "MetricResultSetA+MetricResultSetB+GrainSpec",
        "output_edge": "MetricResultSet+AnalyticsResultSet",
        "blackbox": {
            "does": "Joins two metric result sets on their shared conformed grain into one aligned result set, guarding against fan-out and preserving each metric at the requested grain."
        },
        "effects": ["database_read", "database_write"],
        "base_runtime_targets": ["semantic.query", "warehouse.query"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:queue_worker",
        ],
        "applicable_data_formats": ["rows", "parquet"],
        "proof_requirements": ["schema_validation", "unique_key_test",
                               "row_count_reconciliation"],
        "problem_solution": {
            "problem": "Two metrics computed separately must be compared side by side, but they only align if joined on a truly conformed grain, or the join fans out and corrupts both.",
            "naive_agent_failure": "An agent joins two metric outputs on an approximately-matching key, fanning rows out and inflating both metrics.",
            "solution": "A conformed-join step that aligns two metric result sets on a declared shared grain and verifies the joined grain stays unique.",
            "core_components": ["conformed-grain aligner", "fan-out guard", "aligned-result emitter"],
            "common_inputs": ["metric result set A", "metric result set B", "shared conformed grain"],
            "common_outputs": ["aligned metric result set", "one row per shared grain key", "analytics result set"],
            "known_pitfalls": ["joining on a non-conformed key", "grain of one metric finer than the other", "nulls in the join key dropping rows"],
            "success_signals": ["joined grain key is unique", "neither metric total changes after the join"],
        },
        "source_ref_families": ["semantic layer / metrics layer pattern", "conformed-dimension join"],
        "risk_class": "low",
        "human_review_required": False,
    },
    # ==================================================================
    # multiset_ops: set algebra over record sets
    # ==================================================================
    {
        "family_id": "prim:multiset.union_all",
        "domain": "multiset_ops",
        "title": "Multiset Union All",
        "input_edge": "RecordSetA+RecordSetB",
        "output_edge": "UnionedRecordSet",
        "blackbox": {
            "does": "Concatenates two schema-compatible record sets into one multiset preserving duplicates (SQL UNION ALL), after checking column compatibility, so cardinality equals the sum of inputs."
        },
        "effects": ["database_read", "database_write"],
        "base_runtime_targets": ["warehouse.table", "local.python"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cron_job",
            "wrap:kubernetes_job",
        ],
        "applicable_data_formats": ["rows", "parquet", "arrow"],
        "proof_requirements": ["schema_validation", "row_count_reconciliation"],
        "problem_solution": {
            "problem": "Two record sets with the same shape must be combined keeping every row, but only if their columns truly line up by name, type, and order.",
            "naive_agent_failure": "An agent unions sets with mismatched column order so values land in the wrong columns, or silently drops duplicates it was meant to keep.",
            "solution": "A union-all step that validates schema compatibility, then concatenates preserving duplicates so output cardinality equals the input sum.",
            "core_components": ["schema-compatibility check", "column aligner", "duplicate-preserving concatenator"],
            "common_inputs": ["record set A", "record set B"],
            "common_outputs": ["combined multiset", "row count equal to the input sum"],
            "known_pitfalls": ["mismatched column order or types", "accidentally deduplicating", "incompatible nullability"],
            "success_signals": ["output row count equals sum of inputs", "columns align by name and type"],
        },
        "source_ref_families": ["ANSI SQL set operators (UNION ALL)", "relational set algebra"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:multiset.union_distinct",
        "domain": "multiset_ops",
        "title": "Set Union Distinct",
        "input_edge": "RecordSetA+RecordSetB",
        "output_edge": "UnionedRecordSet+DedupedTable",
        "blackbox": {
            "does": "Unions two schema-compatible record sets and removes exact duplicate rows (SQL UNION), producing a set whose rows are distinct and idempotent under re-union with either input."
        },
        "effects": ["database_read", "database_write"],
        "base_runtime_targets": ["warehouse.table", "local.python"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cron_job",
            "wrap:kubernetes_job",
        ],
        "applicable_data_formats": ["rows", "parquet", "arrow"],
        "proof_requirements": ["schema_validation", "idempotency_test",
                               "row_count_reconciliation"],
        "problem_solution": {
            "problem": "Two overlapping record sets must be merged into a distinct set, and re-merging an already-merged set with either input must not change it.",
            "naive_agent_failure": "An agent uses UNION ALL and forgets to deduplicate, so overlapping rows appear twice and downstream counts inflate.",
            "solution": "A union-distinct step that combines both sets and removes exact-duplicate rows, yielding an idempotent distinct set.",
            "core_components": ["schema-compatibility check", "concatenator", "exact-duplicate remover"],
            "common_inputs": ["record set A", "record set B"],
            "common_outputs": ["distinct unioned set", "no duplicate rows"],
            "known_pitfalls": ["treating near-duplicates as distinct", "case or whitespace differences defeating dedup", "cost of distinct on huge sets ignored"],
            "success_signals": ["re-union with either input leaves the set unchanged", "no exact-duplicate rows remain"],
        },
        "source_ref_families": ["ANSI SQL set operators (UNION)", "relational set algebra"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:multiset.intersect",
        "domain": "multiset_ops",
        "title": "Set Intersect",
        "input_edge": "RecordSetA+RecordSetB",
        "output_edge": "IntersectedRecordSet",
        "blackbox": {
            "does": "Returns the distinct rows present in BOTH schema-compatible record sets (SQL INTERSECT), a commutative operation whose output cardinality never exceeds the smaller input."
        },
        "effects": ["database_read", "database_write"],
        "base_runtime_targets": ["warehouse.table", "local.python"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cron_job",
            "wrap:kubernetes_job",
        ],
        "applicable_data_formats": ["rows", "parquet", "arrow"],
        "proof_requirements": ["schema_validation", "row_count_reconciliation"],
        "problem_solution": {
            "problem": "You need only the rows two sets have in common, and the result must not exceed the smaller set or depend on operand order.",
            "naive_agent_failure": "An agent emulates intersect with a join but mishandles duplicates or nulls, returning rows that are not truly in both sets.",
            "solution": "An intersect step that returns the distinct rows present in both sets, bounded by the smaller input and independent of operand order.",
            "core_components": ["schema-compatibility check", "common-row matcher", "distinct emitter"],
            "common_inputs": ["record set A", "record set B"],
            "common_outputs": ["intersection set", "rows present in both inputs"],
            "known_pitfalls": ["null-vs-null equality surprises", "duplicate handling differing from INTERSECT semantics", "column subset mismatch"],
            "success_signals": ["output cardinality does not exceed the smaller input", "swapping operands yields the same set"],
        },
        "source_ref_families": ["ANSI SQL set operators (INTERSECT)", "relational set algebra"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:multiset.except_minus",
        "domain": "multiset_ops",
        "title": "Set Except (Minus)",
        "input_edge": "RecordSetA+RecordSetB",
        "output_edge": "DifferenceRecordSet",
        "blackbox": {
            "does": "Returns the distinct rows in the first record set that are NOT in the second (SQL EXCEPT/MINUS), an order-sensitive operation bounded by the first input's cardinality."
        },
        "effects": ["database_read", "database_write"],
        "base_runtime_targets": ["warehouse.table", "local.python"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cron_job",
            "wrap:kubernetes_job",
        ],
        "applicable_data_formats": ["rows", "parquet", "arrow"],
        "proof_requirements": ["schema_validation", "row_count_reconciliation"],
        "problem_solution": {
            "problem": "You need the rows in one set that are absent from another - for anti-membership, reconciliation, or 'what's new' - and direction matters.",
            "naive_agent_failure": "An agent swaps the operands or uses an inner join instead of an anti-semantics, returning the wrong difference direction.",
            "solution": "An except step that returns distinct rows of the first set not found in the second, order-sensitive and bounded by the first input.",
            "core_components": ["schema-compatibility check", "anti-membership matcher", "distinct emitter"],
            "common_inputs": ["minuend record set", "subtrahend record set"],
            "common_outputs": ["difference set", "rows only in the first input"],
            "known_pitfalls": ["reversing minuend and subtrahend", "null handling changing membership", "expecting commutativity"],
            "success_signals": ["output is a subset of the first input", "rows in the second input never appear"],
        },
        "source_ref_families": ["ANSI SQL set operators (EXCEPT/MINUS)", "relational set algebra"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:multiset.symmetric_difference",
        "domain": "multiset_ops",
        "title": "Set Symmetric Difference",
        "input_edge": "RecordSetA+RecordSetB",
        "output_edge": "SymmetricDifferenceSet",
        "blackbox": {
            "does": "Returns rows in exactly one of two record sets - the union minus the intersection - a commutative operation useful for diffing two snapshots into added-plus-removed."
        },
        "effects": ["database_read", "database_write"],
        "base_runtime_targets": ["warehouse.table", "local.python"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cron_job",
            "wrap:kubernetes_job",
        ],
        "applicable_data_formats": ["rows", "parquet", "arrow"],
        "proof_requirements": ["schema_validation", "row_count_reconciliation"],
        "problem_solution": {
            "problem": "Diffing two snapshots requires the rows present in exactly one side (added or removed), not those common to both.",
            "naive_agent_failure": "An agent returns only additions or only removals, missing half the diff, or includes unchanged rows.",
            "solution": "A symmetric-difference step that emits union-minus-intersection, so both added and removed rows appear and unchanged rows do not.",
            "core_components": ["union computation", "intersection computation", "difference combiner"],
            "common_inputs": ["record set A", "record set B"],
            "common_outputs": ["symmetric difference set", "rows in exactly one input"],
            "known_pitfalls": ["including common rows", "losing which side a row came from", "asymmetric handling of duplicates"],
            "success_signals": ["no row common to both inputs appears", "swapping operands yields the same set"],
        },
        "source_ref_families": ["relational set algebra (symmetric difference)", "snapshot diffing"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:multiset.nary_union",
        "domain": "multiset_ops",
        "title": "N-ary Multiset Union",
        "input_edge": "RecordSetFamily",
        "output_edge": "UnionedRecordSet",
        "blackbox": {
            "does": "Unions an arbitrary family of schema-compatible record sets into one set in a single pass, validating that every member shares the common schema before concatenating."
        },
        "effects": ["database_read", "database_write"],
        "base_runtime_targets": ["warehouse.table", "local.python"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cron_job",
            "wrap:kubernetes_job", "wrap:queue_worker",
        ],
        "applicable_data_formats": ["rows", "parquet", "arrow"],
        "proof_requirements": ["schema_validation", "row_count_reconciliation"],
        "problem_solution": {
            "problem": "Many partitioned or per-source record sets must be combined into one, and folding pairwise is error-prone when a single member has a divergent schema.",
            "naive_agent_failure": "An agent folds unions pairwise and lets one odd member's schema silently coerce the whole result, corrupting columns.",
            "solution": "An n-ary union that first validates every member against the common schema, then concatenates them in one pass.",
            "core_components": ["common-schema validator", "member iterator", "single-pass concatenator"],
            "common_inputs": ["a family of record sets", "the expected common schema"],
            "common_outputs": ["single unioned set", "row count equal to the member sum"],
            "known_pitfalls": ["one member with a divergent schema", "empty family handling", "quadratic pairwise folding"],
            "success_signals": ["every member validated before concatenation", "output count equals the sum of member counts"],
        },
        "source_ref_families": ["relational set algebra (n-ary union)", "partition consolidation pattern"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:multiset.semi_join",
        "domain": "multiset_ops",
        "title": "Semi Join (Filter By Membership)",
        "input_edge": "RecordSetA+RecordSetB+MatchKeySpec",
        "output_edge": "RecordSetA",
        "blackbox": {
            "does": "Returns rows of the first set whose match key appears in the second set (SQL WHERE EXISTS), never duplicating first-set rows regardless of how many second-set matches exist."
        },
        "effects": ["database_read", "database_write"],
        "base_runtime_targets": ["warehouse.table", "local.python"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cron_job",
            "wrap:kubernetes_job",
        ],
        "applicable_data_formats": ["rows", "parquet", "arrow"],
        "proof_requirements": ["schema_validation", "row_count_reconciliation"],
        "problem_solution": {
            "problem": "You want to keep first-set rows that have a match in the second set without pulling second-set columns or fanning out on multiple matches.",
            "naive_agent_failure": "An agent uses an inner join, so a first-set row with three matches appears three times and second-set columns leak in.",
            "solution": "A semi-join that filters the first set by existence of a matching key in the second, preserving first-set cardinality exactly.",
            "core_components": ["match-key extractor", "existence probe", "first-set filter"],
            "common_inputs": ["driving record set A", "probe record set B", "match key spec"],
            "common_outputs": ["filtered subset of A", "no duplication and no B columns"],
            "known_pitfalls": ["using an inner join and fanning out", "leaking B columns", "null keys matching unexpectedly"],
            "success_signals": ["output is a subset of A with A's exact columns", "row count never exceeds A"],
        },
        "source_ref_families": ["relational algebra (semi-join)", "SQL WHERE EXISTS pattern"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:multiset.anti_join",
        "domain": "multiset_ops",
        "title": "Anti Join (Filter By Non-Membership)",
        "input_edge": "RecordSetA+RecordSetB+MatchKeySpec",
        "output_edge": "RecordSetA",
        "blackbox": {
            "does": "Returns rows of the first set whose match key is absent from the second set (SQL WHERE NOT EXISTS), the anti-membership complement of a semi-join, with first-set cardinality preserved."
        },
        "effects": ["database_read", "database_write"],
        "base_runtime_targets": ["warehouse.table", "local.python"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cron_job",
            "wrap:kubernetes_job",
        ],
        "applicable_data_formats": ["rows", "parquet", "arrow"],
        "proof_requirements": ["schema_validation", "row_count_reconciliation"],
        "problem_solution": {
            "problem": "You want first-set rows with NO match in the second set - unmatched, orphaned, or new records - without fan-out and without null-key false negatives.",
            "naive_agent_failure": "An agent uses a left join with an IS NULL filter but mishandles null keys, so rows with null match keys wrongly appear or disappear.",
            "solution": "An anti-join that keeps first-set rows whose key is absent from the second set, handling null keys explicitly and preserving first-set columns.",
            "core_components": ["match-key extractor", "non-existence probe", "null-safe filter"],
            "common_inputs": ["driving record set A", "probe record set B", "match key spec"],
            "common_outputs": ["unmatched subset of A", "no B columns, no fan-out"],
            "known_pitfalls": ["null keys producing false negatives", "using an inner join by mistake", "duplicate keys in B changing results"],
            "success_signals": ["semi-join and anti-join partition A exactly", "output is a subset of A"],
        },
        "source_ref_families": ["relational algebra (anti-join)", "SQL WHERE NOT EXISTS pattern"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:multiset.cross_join",
        "domain": "multiset_ops",
        "title": "Cross Join (Cartesian Product)",
        "input_edge": "RecordSetA+RecordSetB+SetOpPolicy",
        "output_edge": "JoinedTable",
        "blackbox": {
            "does": "Forms the Cartesian product of two record sets under an explicit size-guard policy that caps or rejects the output when the product would exceed a declared row budget."
        },
        "effects": ["database_read", "database_write"],
        "base_runtime_targets": ["warehouse.table", "local.python"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:kubernetes_job",
        ],
        "applicable_data_formats": ["rows", "parquet"],
        "proof_requirements": ["schema_validation", "row_count_reconciliation"],
        "problem_solution": {
            "problem": "Some tasks genuinely need every pairing of two sets (grids, scenario matrices), but an unguarded Cartesian product can explode to an unusable size.",
            "naive_agent_failure": "An agent issues a cross join with no size guard and materializes billions of rows, exhausting the warehouse.",
            "solution": "A guarded cross join that computes the expected product size against a declared budget and caps or rejects before materializing.",
            "core_components": ["product-size estimator", "row-budget guard", "cartesian generator"],
            "common_inputs": ["record set A", "record set B", "row-budget policy"],
            "common_outputs": ["cartesian product set", "size within budget or explicit rejection"],
            "known_pitfalls": ["unbounded product explosion", "forgetting the product is |A|*|B|", "cross join hidden behind a missing join predicate"],
            "success_signals": ["output size equals the product of inputs", "over-budget requests are rejected before materializing"],
        },
        "source_ref_families": ["relational algebra (Cartesian product)", "SQL CROSS JOIN pattern"],
        "risk_class": "medium",
        "human_review_required": False,
    },
    {
        "family_id": "prim:multiset.overlap_report",
        "domain": "multiset_ops",
        "title": "Set Overlap Report",
        "input_edge": "RecordSetA+RecordSetB+MatchKeySpec",
        "output_edge": "OverlapReport",
        "blackbox": {
            "does": "Computes membership overlap statistics between two record sets on a match key - intersection size, each side's exclusive count, union size, and Jaccard overlap - without materializing the joined rows."
        },
        "effects": ["database_read"],
        "base_runtime_targets": ["warehouse.query", "local.python"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cron_job",
            "wrap:kubernetes_job",
        ],
        "applicable_data_formats": ["rows", "json"],
        "proof_requirements": ["schema_validation", "row_count_reconciliation"],
        "problem_solution": {
            "problem": "Before joining or reconciling two sets you need to know how much they overlap on a key, but running the full join just to count is wasteful and can mislead on duplicates.",
            "naive_agent_failure": "An agent estimates overlap from a fanned-out join count, over-counting when keys are non-unique.",
            "solution": "An overlap report that counts distinct keys per side and their intersection to report exclusive counts, union size, and Jaccard.",
            "core_components": ["distinct-key counter per side", "intersection counter", "Jaccard computation"],
            "common_inputs": ["record set A", "record set B", "match key spec"],
            "common_outputs": ["overlap report", "intersection and exclusive counts", "Jaccard overlap"],
            "known_pitfalls": ["counting fanned-out join rows instead of distinct keys", "null keys inflating a side", "Jaccard divide-by-zero on empty union"],
            "success_signals": ["exclusive plus intersection equals each side's distinct count", "Jaccard lies in zero to one"],
        },
        "source_ref_families": ["relational set algebra", "Jaccard set-overlap statistic"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:multiset.partition_split",
        "domain": "multiset_ops",
        "title": "Record Set Partition Split",
        "input_edge": "RecordSetA+SetOpPolicy",
        "output_edge": "RecordSetFamily",
        "blackbox": {
            "does": "Splits one record set into a family of disjoint subsets by a partition predicate or key so that the subsets are mutually exclusive and their union reconstructs the input exactly."
        },
        "effects": ["database_read", "database_write"],
        "base_runtime_targets": ["warehouse.table", "local.python"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cron_job",
            "wrap:kubernetes_job",
        ],
        "applicable_data_formats": ["rows", "parquet", "arrow"],
        "proof_requirements": ["schema_validation", "row_count_reconciliation"],
        "problem_solution": {
            "problem": "A single set must be divided into subsets for parallel handling or routing, and the split must lose no rows and duplicate none - a true partition.",
            "naive_agent_failure": "An agent writes overlapping filter predicates so some rows land in two subsets and others in none, and the parts no longer sum to the whole.",
            "solution": "A partition step whose predicate assigns each row to exactly one subset, verified so the subsets are disjoint and their union equals the input.",
            "core_components": ["partition-key evaluator", "disjoint-subset router", "coverage reconciler"],
            "common_inputs": ["record set", "partition predicate or key policy"],
            "common_outputs": ["family of disjoint subsets", "subsets that reconstruct the input"],
            "known_pitfalls": ["overlapping predicates assigning a row twice", "a row matching no subset", "subset row counts not summing to the input"],
            "success_signals": ["subset counts sum to the input count", "unioning the subsets reproduces the input"],
        },
        "source_ref_families": ["relational set algebra (partition)", "disjoint routing pattern"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:multiset.dedupe_across_sets",
        "domain": "multiset_ops",
        "title": "Cross-Set Deduplicate",
        "input_edge": "RecordSetFamily+DedupePolicy",
        "output_edge": "DedupedTable+UnionedRecordSet",
        "blackbox": {
            "does": "Unions a family of record sets and keeps one winning row per dedup key using a declared precedence (source priority or recency), idempotent under re-running on its own output."
        },
        "effects": ["database_read", "database_write"],
        "base_runtime_targets": ["warehouse.table", "local.python"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cron_job",
            "wrap:kubernetes_job", "wrap:queue_worker",
        ],
        "applicable_data_formats": ["rows", "parquet", "arrow"],
        "proof_requirements": ["schema_validation", "idempotency_test",
                               "unique_key_test"],
        "problem_solution": {
            "problem": "The same entity arrives in several source sets and must collapse to one winning row by a declared precedence, and re-running must not change the survivors.",
            "naive_agent_failure": "An agent unions the sets and deduplicates arbitrarily, so which duplicate survives depends on scan order and changes run to run.",
            "solution": "A cross-set dedupe that unions the family and picks one row per key by an explicit precedence, yielding a unique-key idempotent result.",
            "core_components": ["family unioner", "precedence ranker", "one-per-key selector"],
            "common_inputs": ["a family of record sets", "dedup key", "precedence policy"],
            "common_outputs": ["deduplicated set", "one row per key", "stable winner selection"],
            "known_pitfalls": ["nondeterministic winner without an explicit precedence", "precedence ties unresolved", "key normalization missing"],
            "success_signals": ["exactly one row per dedup key", "re-running on the output changes nothing"],
        },
        "source_ref_families": ["relational set algebra", "deduplicate-latest / winner-per-key pattern"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:multiset.membership_flag",
        "domain": "multiset_ops",
        "title": "Set Membership Flag",
        "input_edge": "RecordSetA+RecordSetB+MatchKeySpec",
        "output_edge": "RecordSetA",
        "blackbox": {
            "does": "Annotates each row of the first set with a boolean flag indicating whether its key is present in the second set, preserving cardinality and adding one column."
        },
        "effects": ["database_read", "database_write"],
        "base_runtime_targets": ["warehouse.table", "local.python"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cron_job",
            "wrap:kubernetes_job",
        ],
        "applicable_data_formats": ["rows", "parquet", "arrow"],
        "proof_requirements": ["schema_validation", "row_count_reconciliation"],
        "problem_solution": {
            "problem": "You want to keep every first-set row but mark which ones exist in a reference set, for downstream branching, without dropping or duplicating any rows.",
            "naive_agent_failure": "An agent joins to the reference set to get the flag and fans out on duplicate reference keys, changing the row count.",
            "solution": "A membership-flag step that probes existence in the reference set and adds a boolean column while holding cardinality constant.",
            "core_components": ["match-key extractor", "existence probe", "boolean annotator"],
            "common_inputs": ["record set A", "reference record set B", "match key spec"],
            "common_outputs": ["A with an added membership boolean", "unchanged row count"],
            "known_pitfalls": ["fan-out from duplicate reference keys", "null keys flagged inconsistently", "overwriting an existing column"],
            "success_signals": ["output row count equals A's", "the flag matches a semi-join membership exactly"],
        },
        "source_ref_families": ["relational algebra (semi-join membership)", "SQL EXISTS flag pattern"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:multiset.schema_align",
        "domain": "multiset_ops",
        "title": "Set Schema Align For Union",
        "input_edge": "RecordSetA+RecordSetB+SchemaSpec",
        "output_edge": "RecordSetA+RecordSetB",
        "blackbox": {
            "does": "Reconciles two record sets to a common target schema - aligning column names, order, and types and filling missing columns with nulls - so a subsequent set operation is well-defined."
        },
        "effects": ["database_read", "database_write"],
        "base_runtime_targets": ["warehouse.table", "local.python"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cron_job",
            "wrap:kubernetes_job",
        ],
        "applicable_data_formats": ["rows", "parquet", "arrow"],
        "proof_requirements": ["schema_validation", "row_count_reconciliation"],
        "problem_solution": {
            "problem": "Set operations require identical schemas, but real sources differ in column order, names, and types, so a pre-alignment step is needed before any union or intersect.",
            "naive_agent_failure": "An agent unions mismatched sets directly and lets positional coercion put values in the wrong columns.",
            "solution": "A schema-align step that maps both sets onto a declared target schema, filling absent columns with nulls and coercing types safely, preserving row counts.",
            "core_components": ["target-schema mapper", "type coercer", "missing-column filler"],
            "common_inputs": ["record set A", "record set B", "target schema spec"],
            "common_outputs": ["two sets sharing the target schema", "row counts unchanged"],
            "known_pitfalls": ["lossy type coercion", "silently dropping unmapped columns", "filling a required column with nulls"],
            "success_signals": ["both outputs match the target schema exactly", "row counts equal their inputs"],
        },
        "source_ref_families": ["relational set algebra (union compatibility)", "schema reconciliation pattern"],
        "risk_class": "low",
        "human_review_required": False,
    },
]
