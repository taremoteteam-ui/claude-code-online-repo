"""Seed data: MULTI-WAVE PIPELINE templates for the warehouse-analytics lane.

Pure data. No imports, no functions. One top-level constant: PIPELINES.

A pipeline is an ordered sequence of WAVES. Each wave is a SET of primitive
families that run together (parallelizable within a wave) before the next wave
starts. The waves form a valid topological layering over a shared warehouse
PORT vocabulary:

    RawSourceTable, StagingTable, IntermediateTable, DimensionTable, FactTable,
    MartTable, BronzeTable, SilverTable, GoldTable, WideTable, SCD2Dimension,
    SemanticMetricSet, MetricResultSet

WAVE-ORDERING CONTRACT (enforced by scripts/check_warehouse_analytics_pack.py):
    - wave_index starts at 1 and is contiguous.
    - Each wave consumes ONLY ports that are pipeline_inputs OR produced by an
      EARLIER wave. Wave 1 therefore consumes only pipeline_inputs.
    - Every declared pipeline_output must be produced by some wave.

Every member_family_ref is a REAL family_id defined in the wh_families_*_seed.py
modules (prim:dbt.*, prim:wh.*, prim:dewh.*, prim:analytics.*, prim:sem.*,
prim:mset.*). The builder stamps record_type/version/candidate/serves_truth;
seed rows must NOT set those fields.
"""

PIPELINES = [
    # ----------------------------------------------------------------------
    # 1. dbt layered core: staging -> intermediate -> marts
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:dbt_layered.staging_intermediate_marts",
        "title": "dbt Layered Marts (staging -> intermediate -> marts)",
        "pattern": "dbt_layered",
        "description": (
            "Canonical dbt layering. Raw sources are cleaned into staging "
            "views, reshaped in intermediate models, and published as "
            "business-facing marts, each layer referencing only the layer "
            "below via ref()."
        ),
        "pipeline_inputs": ["RawSourceTable"],
        "pipeline_outputs": ["MartTable"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "staging",
                "member_family_refs": [
                    "prim:dbt.source_define",
                    "prim:dbt.staging_model",
                    "prim:dbt.materialize_view",
                    "prim:dbt.generic_test_not_null",
                ],
                "parallelizable": True,
                "consumes": ["RawSourceTable"],
                "produces": ["StagingTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "intermediate",
                "member_family_refs": [
                    "prim:dbt.intermediate_model",
                    "prim:dbt.ref_resolve",
                    "prim:dbt.materialize_ephemeral",
                ],
                "parallelizable": True,
                "consumes": ["StagingTable"],
                "produces": ["IntermediateTable"],
            },
            {
                "wave_index": 3,
                "wave_name": "marts",
                "member_family_refs": [
                    "prim:dbt.mart_model",
                    "prim:dbt.materialize_table",
                    "prim:dbt.generic_test_unique",
                    "prim:dbt.lineage_emit",
                ],
                "parallelizable": False,
                "consumes": ["IntermediateTable"],
                "produces": ["MartTable"],
            },
        ],
        "invariants": [
            "each model references only the layer directly below via ref()",
            "grain is declared and unique for every mart model",
        ],
        "proof_requirements": [
            "dbt build passes every generic test in the DAG",
            "row_count_reconcile holds between staging and marts within the declared tolerance",
        ],
        "known_failure_modes": [
            "fan-out join in an intermediate model inflates mart grain",
            "staging view silently drifts when an upstream source column is renamed",
        ],
    },
    # ----------------------------------------------------------------------
    # 2. Medallion: bronze -> silver -> gold
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:medallion.bronze_silver_gold",
        "title": "Medallion (bronze -> silver -> gold)",
        "pattern": "medallion",
        "description": (
            "Lakehouse medallion architecture. Raw data lands in a bronze "
            "layer, is cleaned and conformed into silver, then aggregated and "
            "curated into gold consumption tables."
        ),
        "pipeline_inputs": ["RawSourceTable"],
        "pipeline_outputs": ["GoldTable"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "bronze_ingest",
                "member_family_refs": [
                    "prim:dewh.bronze_ingest_batch",
                    "prim:dewh.flatten_semi_structured",
                    "prim:dewh.schema_evolution_apply",
                ],
                "parallelizable": True,
                "consumes": ["RawSourceTable"],
                "produces": ["BronzeTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "silver_clean",
                "member_family_refs": [
                    "prim:dewh.silver_clean",
                    "prim:dewh.silver_conform_schema",
                    "prim:dewh.dedup_tie_break",
                    "prim:dewh.quarantine_bad_rows",
                ],
                "parallelizable": True,
                "consumes": ["BronzeTable"],
                "produces": ["SilverTable"],
            },
            {
                "wave_index": 3,
                "wave_name": "gold_curate",
                "member_family_refs": [
                    "prim:dewh.gold_curate",
                    "prim:dewh.gold_aggregate_rollup",
                    "prim:dewh.row_count_reconciliation",
                ],
                "parallelizable": False,
                "consumes": ["SilverTable"],
                "produces": ["GoldTable"],
            },
        ],
        "invariants": [
            "bronze retains the raw payload without lossy transforms",
            "silver enforces a conformed schema before any gold aggregate reads it",
        ],
        "proof_requirements": [
            "row_count_reconciliation between bronze and silver accounts for every quarantined row",
            "gold aggregates re-derive from silver deterministically on replay",
        ],
        "known_failure_modes": [
            "schema evolution in bronze breaks a downstream silver cast",
            "duplicate late-arriving records double-count a gold aggregate",
        ],
    },
    # ----------------------------------------------------------------------
    # 3. Star schema build: stage -> dims -> facts -> marts
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:star_build.stage_dims_facts_marts",
        "title": "Star Schema Build (stage -> dims -> facts -> marts)",
        "pattern": "star_build",
        "description": (
            "Kimball dimensional build. Staged sources feed dimension tables "
            "and fact tables (facts read both staged measures and dimension "
            "surrogate keys), which are then assembled into star marts."
        ),
        "pipeline_inputs": ["RawSourceTable"],
        "pipeline_outputs": ["MartTable"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "stage",
                "member_family_refs": [
                    "prim:dbt.staging_model",
                    "prim:dbt.source_freshness",
                    "prim:dewh.silver_clean",
                ],
                "parallelizable": True,
                "consumes": ["RawSourceTable"],
                "produces": ["StagingTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "dimensions",
                "member_family_refs": [
                    "prim:wh.dimension_build",
                    "prim:wh.surrogate_key_generate",
                    "prim:wh.date_dimension_generate",
                    "prim:wh.conformed_dimension_build",
                ],
                "parallelizable": True,
                "consumes": ["StagingTable"],
                "produces": ["DimensionTable"],
            },
            {
                "wave_index": 3,
                "wave_name": "facts",
                "member_family_refs": [
                    "prim:wh.transaction_fact_build",
                    "prim:wh.surrogate_key_lookup",
                    "prim:wh.fact_dimension_ri_check",
                    "prim:wh.grain_declare_enforce",
                ],
                "parallelizable": True,
                "consumes": ["StagingTable", "DimensionTable"],
                "produces": ["FactTable"],
            },
            {
                "wave_index": 4,
                "wave_name": "marts",
                "member_family_refs": [
                    "prim:wh.star_schema_assemble",
                    "prim:dbt.mart_model",
                ],
                "parallelizable": False,
                "consumes": ["FactTable", "DimensionTable"],
                "produces": ["MartTable"],
            },
        ],
        "invariants": [
            "every fact foreign key resolves to exactly one dimension surrogate key",
            "fact grain is declared before any measure is loaded",
        ],
        "proof_requirements": [
            "referential-integrity check passes for every fact-to-dimension edge",
            "grain uniqueness test passes on the fact table",
        ],
        "known_failure_modes": [
            "dimension load lags the fact load, orphaning fact rows to an inferred key",
            "duplicate surrogate keys collapse two distinct dimension members",
        ],
    },
    # ----------------------------------------------------------------------
    # 4. One Big Table refresh
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:one_big_table.obt_refresh",
        "title": "One Big Table Refresh (stage -> conform -> flatten)",
        "pattern": "one_big_table",
        "description": (
            "Denormalized one-big-table build. Staged sources are conformed "
            "and joined in an intermediate layer, then flattened into a single "
            "wide analytics table for BI tools that prefer no joins."
        ),
        "pipeline_inputs": ["RawSourceTable"],
        "pipeline_outputs": ["WideTable"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "stage",
                "member_family_refs": [
                    "prim:dbt.staging_model",
                    "prim:dewh.silver_clean",
                ],
                "parallelizable": True,
                "consumes": ["RawSourceTable"],
                "produces": ["StagingTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "conform",
                "member_family_refs": [
                    "prim:wh.dimension_conformance_check",
                    "prim:dbt.intermediate_model",
                    "prim:mset.left_join",
                ],
                "parallelizable": True,
                "consumes": ["StagingTable"],
                "produces": ["IntermediateTable"],
            },
            {
                "wave_index": 3,
                "wave_name": "flatten",
                "member_family_refs": [
                    "prim:wh.obt_flatten",
                    "prim:dbt.wide_model",
                    "prim:dbt.materialize_table",
                ],
                "parallelizable": False,
                "consumes": ["IntermediateTable"],
                "produces": ["WideTable"],
            },
        ],
        "invariants": [
            "the flatten step preserves the declared base grain (no row multiplication)",
            "conformed attribute names are stable across the wide table columns",
        ],
        "proof_requirements": [
            "row count of the wide table equals the base-grain row count",
            "column-level not-null contract holds for every conformed key",
        ],
        "known_failure_modes": [
            "a one-to-many join in the conform wave multiplies base-grain rows",
            "conflicting column names collide when two sources are flattened together",
        ],
    },
    # ----------------------------------------------------------------------
    # 5. CDC to SCD2 dimension history
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:cdc_to_scd2.dimension_history",
        "title": "CDC to SCD2 Dimension History",
        "pattern": "cdc_to_scd2",
        "description": (
            "Change-data-capture stream is captured into bronze, ordered and "
            "merged into a silver current-state table, then applied as a "
            "Type-2 slowly changing dimension that tracks full history."
        ),
        "pipeline_inputs": ["RawSourceTable"],
        "pipeline_outputs": ["SCD2Dimension"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "cdc_capture",
                "member_family_refs": [
                    "prim:dewh.cdc_capture",
                    "prim:dewh.cdc_bootstrap_snapshot",
                    "prim:dewh.watermark_incremental_extract",
                ],
                "parallelizable": True,
                "consumes": ["RawSourceTable"],
                "produces": ["BronzeTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "cdc_order",
                "member_family_refs": [
                    "prim:dewh.cdc_dedup_order",
                    "prim:dewh.cdc_apply_merge",
                    "prim:dewh.late_arriving_data_reconcile",
                ],
                "parallelizable": False,
                "consumes": ["BronzeTable"],
                "produces": ["SilverTable"],
            },
            {
                "wave_index": 3,
                "wave_name": "scd2_apply",
                "member_family_refs": [
                    "prim:wh.scd_type2_new_row",
                    "prim:dbt.snapshot_scd2",
                    "prim:wh.dimension_change_detect",
                    "prim:wh.surrogate_key_generate",
                ],
                "parallelizable": False,
                "consumes": ["SilverTable"],
                "produces": ["SCD2Dimension"],
            },
        ],
        "invariants": [
            "at most one open (current) version exists per natural key",
            "effective-from / effective-to ranges are contiguous and non-overlapping",
        ],
        "proof_requirements": [
            "no natural key has two rows flagged current",
            "validity ranges for a natural key tile the timeline with no gaps or overlaps",
        ],
        "known_failure_modes": [
            "out-of-order CDC events open a new version before closing the prior one",
            "a late-arriving change rewrites history that a downstream fact already keyed",
        ],
    },
    # ----------------------------------------------------------------------
    # 6. Snowflake normalize dimension outriggers
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:snowflake_normalize.dimension_outriggers",
        "title": "Snowflake Normalize (dimension outriggers)",
        "pattern": "snowflake_normalize",
        "description": (
            "Snowflaked dimensional model. A staged wide dimension is "
            "normalized by splitting repeating hierarchy levels into "
            "intermediate tables, then rebuilt with outrigger sub-dimensions."
        ),
        "pipeline_inputs": ["RawSourceTable"],
        "pipeline_outputs": ["DimensionTable"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "stage",
                "member_family_refs": [
                    "prim:dbt.staging_model",
                    "prim:dewh.silver_clean",
                ],
                "parallelizable": True,
                "consumes": ["RawSourceTable"],
                "produces": ["StagingTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "normalize",
                "member_family_refs": [
                    "prim:wh.snowflake_normalize_dimension",
                    "prim:wh.hierarchy_flatten",
                    "prim:dbt.intermediate_model",
                ],
                "parallelizable": True,
                "consumes": ["StagingTable"],
                "produces": ["IntermediateTable"],
            },
            {
                "wave_index": 3,
                "wave_name": "outriggers",
                "member_family_refs": [
                    "prim:wh.outrigger_dimension_build",
                    "prim:wh.dimension_build",
                    "prim:wh.surrogate_key_generate",
                ],
                "parallelizable": False,
                "consumes": ["IntermediateTable"],
                "produces": ["DimensionTable"],
            },
        ],
        "invariants": [
            "each normalized level keeps a stable surrogate key referenced by its parent",
            "no attribute is duplicated across a dimension and its outrigger",
        ],
        "proof_requirements": [
            "every outrigger foreign key resolves to exactly one parent-level row",
            "re-joining all outriggers reproduces the original denormalized attribute set",
        ],
        "known_failure_modes": [
            "a normalized level loses rows when a null hierarchy value is dropped on split",
            "outrigger reload reorders surrogate keys and breaks existing fact references",
        ],
    },
    # ----------------------------------------------------------------------
    # 7. Semantic layer build: marts -> metrics -> results
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:semantic_layer_build.marts_metrics_results",
        "title": "Semantic Layer Build (marts -> metrics -> results)",
        "pattern": "semantic_layer_build",
        "description": (
            "Governed metric layer. Curated marts are described as a semantic "
            "model of entities, dimensions, and measures, from which metric "
            "queries compile deterministically into result sets."
        ),
        "pipeline_inputs": ["MartTable"],
        "pipeline_outputs": ["MetricResultSet"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "semantic_model",
                "member_family_refs": [
                    "prim:sem.entity_define",
                    "prim:sem.dimension_define",
                    "prim:sem.measure_define",
                    "prim:sem.metric_define",
                    "prim:sem.model_validate",
                ],
                "parallelizable": True,
                "consumes": ["MartTable"],
                "produces": ["SemanticMetricSet"],
            },
            {
                "wave_index": 2,
                "wave_name": "compile_query",
                "member_family_refs": [
                    "prim:sem.metric_query_compile",
                    "prim:sem.saved_query_compile",
                    "prim:sem.time_grain_rollup",
                    "prim:sem.metric_lineage",
                ],
                "parallelizable": False,
                "consumes": ["SemanticMetricSet"],
                "produces": ["MetricResultSet"],
            },
        ],
        "invariants": [
            "every metric resolves to measures defined on a single declared grain",
            "a compiled query references only entities present in the semantic model",
        ],
        "proof_requirements": [
            "model_validate reports zero unresolved joins or measures",
            "the same metric query recompiles to an identical result on replay",
        ],
        "known_failure_modes": [
            "a fan-out join path inflates an additive measure",
            "an undeclared time grain silently double-counts a cumulative metric",
        ],
    },
    # ----------------------------------------------------------------------
    # 8. Analytics mart: marts -> sessionize -> cohort/funnel
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:analytics_mart.cohort_funnel_marts",
        "title": "Analytics Mart (cohort and funnel from marts)",
        "pattern": "analytics_mart",
        "description": (
            "Behavioral analytics mart. Event marts are sessionized into an "
            "intermediate table, then reduced into cohort, funnel, and "
            "retention metric result sets."
        ),
        "pipeline_inputs": ["MartTable"],
        "pipeline_outputs": ["MetricResultSet"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "sessionize",
                "member_family_refs": [
                    "prim:analytics.sessionize",
                    "prim:analytics.dedupe_latest_per_key",
                    "prim:analytics.new_vs_returning",
                ],
                "parallelizable": True,
                "consumes": ["MartTable"],
                "produces": ["IntermediateTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "cohort_funnel",
                "member_family_refs": [
                    "prim:analytics.cohort_build",
                    "prim:analytics.funnel_build",
                    "prim:analytics.funnel_dropoff",
                    "prim:analytics.retention_curve",
                ],
                "parallelizable": False,
                "consumes": ["IntermediateTable"],
                "produces": ["MetricResultSet"],
            },
        ],
        "invariants": [
            "session boundaries use a single declared inactivity timeout",
            "a user belongs to exactly one acquisition cohort",
        ],
        "proof_requirements": [
            "funnel step counts are monotonically non-increasing",
            "cohort sizes sum to the deduplicated user population",
        ],
        "known_failure_modes": [
            "duplicate events inflate a funnel step above the prior step",
            "timezone skew shifts users into the wrong cohort period",
        ],
    },
    # ----------------------------------------------------------------------
    # 9. Lakehouse ELT: iceberg incremental
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:lakehouse_elt.iceberg_incremental",
        "title": "Lakehouse ELT (iceberg incremental)",
        "pattern": "lakehouse_elt",
        "description": (
            "Incremental lakehouse ELT. Streaming and batch sources ingest to "
            "bronze, merge exactly-once into silver with file optimization, "
            "then curate into gold consumption tables."
        ),
        "pipeline_inputs": ["RawSourceTable"],
        "pipeline_outputs": ["GoldTable"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "ingest",
                "member_family_refs": [
                    "prim:dewh.bronze_ingest_streaming",
                    "prim:dewh.multi_source_union_ingest",
                    "prim:dewh.checkpoint_watermark_advance",
                ],
                "parallelizable": True,
                "consumes": ["RawSourceTable"],
                "produces": ["BronzeTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "merge_optimize",
                "member_family_refs": [
                    "prim:dewh.merge_into_upsert",
                    "prim:dewh.exactly_once_merge",
                    "prim:dewh.small_file_compaction",
                    "prim:dewh.zorder_cluster_optimize",
                ],
                "parallelizable": True,
                "consumes": ["BronzeTable"],
                "produces": ["SilverTable"],
            },
            {
                "wave_index": 3,
                "wave_name": "curate",
                "member_family_refs": [
                    "prim:dewh.gold_curate",
                    "prim:dewh.gold_aggregate_rollup",
                    "prim:dewh.optimize_vacuum_retention",
                ],
                "parallelizable": False,
                "consumes": ["SilverTable"],
                "produces": ["GoldTable"],
            },
        ],
        "invariants": [
            "the merge into silver is idempotent under stream replay",
            "checkpoint watermark advances only after a committed silver merge",
        ],
        "proof_requirements": [
            "replaying from the last checkpoint produces no duplicate silver rows",
            "gold rollups reconcile to silver row counts within the declared tolerance",
        ],
        "known_failure_modes": [
            "checkpoint advances before commit, dropping records on restart",
            "compaction runs concurrently with a merge and rewrites in-flight files",
        ],
    },
    # ----------------------------------------------------------------------
    # 10. Wide table refresh: denormalized daily
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:wide_table_refresh.denormalized_daily",
        "title": "Wide Table Refresh (denormalized daily)",
        "pattern": "wide_table_refresh",
        "description": (
            "Daily denormalized refresh. Staged incremental sources are "
            "widened directly into a reporting wide table, favoring read "
            "simplicity over normalization."
        ),
        "pipeline_inputs": ["RawSourceTable"],
        "pipeline_outputs": ["WideTable"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "stage",
                "member_family_refs": [
                    "prim:dbt.staging_model",
                    "prim:dewh.incremental_append_dedupe",
                ],
                "parallelizable": True,
                "consumes": ["RawSourceTable"],
                "produces": ["StagingTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "widen",
                "member_family_refs": [
                    "prim:dbt.wide_model",
                    "prim:wh.obt_flatten",
                    "prim:analytics.pivot_long_to_wide",
                ],
                "parallelizable": False,
                "consumes": ["StagingTable"],
                "produces": ["WideTable"],
            },
        ],
        "invariants": [
            "the daily refresh is deterministic for a fixed logical date",
            "pivoted columns form a stable, declared set across refreshes",
        ],
        "proof_requirements": [
            "re-running the refresh for a date yields an identical wide table",
            "no pivoted value column exceeds the declared cardinality bound",
        ],
        "known_failure_modes": [
            "a new pivot key appears and silently adds an unexpected column",
            "incremental dedupe keeps the wrong row when tie-break keys are equal",
        ],
    },
    # ----------------------------------------------------------------------
    # 11. Retail sales star (industry variant)
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:star_build.retail_sales_star",
        "title": "Retail Sales Star (POS transactions)",
        "pattern": "star_build",
        "description": (
            "Retail point-of-sale star schema. POS lines are staged and "
            "enriched, product/store/date/junk dimensions are built, sales "
            "transaction facts are loaded, then assembled into sales marts."
        ),
        "pipeline_inputs": ["RawSourceTable"],
        "pipeline_outputs": ["MartTable"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "stage_pos",
                "member_family_refs": [
                    "prim:dbt.staging_model",
                    "prim:dewh.silver_clean",
                    "prim:dewh.reference_data_enrich",
                ],
                "parallelizable": True,
                "consumes": ["RawSourceTable"],
                "produces": ["StagingTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "retail_dims",
                "member_family_refs": [
                    "prim:wh.dimension_build",
                    "prim:wh.date_dimension_generate",
                    "prim:wh.junk_dimension_build",
                    "prim:wh.conformed_dimension_build",
                    "prim:wh.surrogate_key_generate",
                ],
                "parallelizable": True,
                "consumes": ["StagingTable"],
                "produces": ["DimensionTable"],
            },
            {
                "wave_index": 3,
                "wave_name": "sales_facts",
                "member_family_refs": [
                    "prim:wh.transaction_fact_build",
                    "prim:wh.surrogate_key_lookup",
                    "prim:wh.degenerate_dimension_extract",
                    "prim:wh.fact_dimension_ri_check",
                ],
                "parallelizable": True,
                "consumes": ["StagingTable", "DimensionTable"],
                "produces": ["FactTable"],
            },
            {
                "wave_index": 4,
                "wave_name": "sales_marts",
                "member_family_refs": [
                    "prim:wh.star_schema_assemble",
                    "prim:wh.aggregate_fact_build",
                    "prim:dbt.mart_model",
                ],
                "parallelizable": False,
                "consumes": ["FactTable", "DimensionTable"],
                "produces": ["MartTable"],
            },
        ],
        "invariants": [
            "the order-line number stays a degenerate dimension on the fact, not a joined table",
            "product and store dimensions are conformed across every sales fact",
        ],
        "proof_requirements": [
            "sum of fact line amounts reconciles to the source order totals",
            "every sales fact FK resolves to a current product and store dimension row",
        ],
        "known_failure_modes": [
            "returns are counted as positive sales when sign handling is missed",
            "a new store loads facts before its dimension row exists",
        ],
    },
    # ----------------------------------------------------------------------
    # 12. Finance ledger star (industry variant)
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:star_build.finance_ledger",
        "title": "Finance General-Ledger Star",
        "pattern": "star_build",
        "description": (
            "Finance ledger warehouse. General-ledger entries are staged and "
            "masked, account/date/role-playing dimensions are built, periodic "
            "and accumulating balance facts are loaded, then published as "
            "finance marts."
        ),
        "pipeline_inputs": ["RawSourceTable"],
        "pipeline_outputs": ["MartTable"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "stage_gl",
                "member_family_refs": [
                    "prim:dbt.staging_model",
                    "prim:dewh.silver_clean",
                    "prim:dewh.pii_masking_apply",
                ],
                "parallelizable": True,
                "consumes": ["RawSourceTable"],
                "produces": ["StagingTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "ledger_dims",
                "member_family_refs": [
                    "prim:wh.dimension_build",
                    "prim:wh.role_playing_dimension",
                    "prim:wh.date_dimension_generate",
                    "prim:wh.surrogate_key_generate",
                ],
                "parallelizable": True,
                "consumes": ["StagingTable"],
                "produces": ["DimensionTable"],
            },
            {
                "wave_index": 3,
                "wave_name": "balance_facts",
                "member_family_refs": [
                    "prim:wh.periodic_snapshot_fact_build",
                    "prim:wh.accumulating_snapshot_fact_build",
                    "prim:wh.surrogate_key_lookup",
                    "prim:wh.measure_additivity_tag",
                ],
                "parallelizable": True,
                "consumes": ["StagingTable", "DimensionTable"],
                "produces": ["FactTable"],
            },
            {
                "wave_index": 4,
                "wave_name": "finance_marts",
                "member_family_refs": [
                    "prim:wh.star_schema_assemble",
                    "prim:dbt.mart_model",
                    "prim:dbt.metric_define",
                ],
                "parallelizable": False,
                "consumes": ["FactTable", "DimensionTable"],
                "produces": ["MartTable"],
            },
        ],
        "invariants": [
            "debits equal credits for every posted journal entry",
            "balance measures are tagged with their additivity across the date dimension",
        ],
        "proof_requirements": [
            "period-end snapshot balances reconcile to the source trial balance",
            "semi-additive balances are never summed across the time dimension in a mart",
        ],
        "known_failure_modes": [
            "a balance snapshot is summed over time and overstates period totals",
            "a reposted entry duplicates ledger lines without reversing the original",
        ],
    },
    # ----------------------------------------------------------------------
    # 13. Subscription SaaS semantic metrics (industry variant)
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:semantic_layer_build.saas_subscription_metrics",
        "title": "SaaS Subscription Metrics (MRR / ARR semantic layer)",
        "pattern": "semantic_layer_build",
        "description": (
            "Subscription revenue semantic layer. Billing marts are modeled as "
            "additive, ratio, and cumulative metrics, then compiled into MRR, "
            "ARR, and growth result sets over a monthly grain."
        ),
        "pipeline_inputs": ["MartTable"],
        "pipeline_outputs": ["MetricResultSet"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "semantic_entities",
                "member_family_refs": [
                    "prim:sem.entity_define",
                    "prim:sem.measure_define",
                    "prim:sem.additive_metric",
                    "prim:sem.ratio_metric",
                    "prim:sem.cumulative_metric",
                ],
                "parallelizable": True,
                "consumes": ["MartTable"],
                "produces": ["SemanticMetricSet"],
            },
            {
                "wave_index": 2,
                "wave_name": "mrr_arr_compile",
                "member_family_refs": [
                    "prim:sem.metric_query_compile",
                    "prim:sem.time_grain_rollup",
                    "prim:sem.derived_metric",
                    "prim:analytics.mom_growth",
                ],
                "parallelizable": False,
                "consumes": ["SemanticMetricSet"],
                "produces": ["MetricResultSet"],
            },
        ],
        "invariants": [
            "each subscription contributes to exactly one MRR bucket per month",
            "ARR is defined as a fixed derived multiple of MRR, never recomputed independently",
        ],
        "proof_requirements": [
            "net MRR movement equals new plus expansion minus contraction minus churn",
            "monthly MRR rolls up to the same ARR the derived metric reports",
        ],
        "known_failure_modes": [
            "mid-month plan changes are counted as both churn and new instead of expansion",
            "proration is dropped, overstating MRR for partial-month subscriptions",
        ],
    },
    # ----------------------------------------------------------------------
    # 14. Healthcare claims star (industry variant)
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:star_build.healthcare_claims",
        "title": "Healthcare Claims Star",
        "pattern": "star_build",
        "description": (
            "Healthcare claims warehouse. Claim records are staged, masked, "
            "and quarantined, member/provider/diagnosis dimensions are built "
            "with SCD2 history, accumulating claim-lifecycle facts are loaded, "
            "then assembled into claims marts."
        ),
        "pipeline_inputs": ["RawSourceTable"],
        "pipeline_outputs": ["MartTable"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "stage_claims",
                "member_family_refs": [
                    "prim:dbt.staging_model",
                    "prim:dewh.pii_masking_apply",
                    "prim:dewh.quarantine_bad_rows",
                    "prim:dewh.silver_clean",
                ],
                "parallelizable": True,
                "consumes": ["RawSourceTable"],
                "produces": ["StagingTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "claims_dims",
                "member_family_refs": [
                    "prim:wh.dimension_build",
                    "prim:wh.scd_type2_new_row",
                    "prim:wh.mini_dimension_split",
                    "prim:wh.surrogate_key_generate",
                ],
                "parallelizable": True,
                "consumes": ["StagingTable"],
                "produces": ["DimensionTable"],
            },
            {
                "wave_index": 3,
                "wave_name": "claims_facts",
                "member_family_refs": [
                    "prim:wh.accumulating_snapshot_fact_build",
                    "prim:wh.factless_fact_build",
                    "prim:wh.surrogate_key_lookup",
                    "prim:wh.fact_null_measure_handle",
                ],
                "parallelizable": True,
                "consumes": ["StagingTable", "DimensionTable"],
                "produces": ["FactTable"],
            },
            {
                "wave_index": 4,
                "wave_name": "claims_marts",
                "member_family_refs": [
                    "prim:wh.star_schema_assemble",
                    "prim:wh.drill_across_merge",
                    "prim:dbt.mart_model",
                ],
                "parallelizable": False,
                "consumes": ["FactTable", "DimensionTable"],
                "produces": ["MartTable"],
            },
        ],
        "invariants": [
            "every claim maps to exactly one member and one servicing provider version",
            "claim-lifecycle milestone dates only move forward across the accumulating fact",
        ],
        "proof_requirements": [
            "quarantined claims are accounted for in the row-count reconciliation",
            "every fact FK resolves to the dimension version effective on the service date",
        ],
        "known_failure_modes": [
            "a resubmitted claim double-counts against the original claim id",
            "a provider credential change opens an SCD2 version that mis-keys prior facts",
        ],
    },
    # ----------------------------------------------------------------------
    # 15. Marketing attribution mart (industry variant)
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:analytics_mart.marketing_attribution",
        "title": "Marketing Attribution Mart",
        "pattern": "analytics_mart",
        "description": (
            "Multi-touch attribution mart. Touch and conversion marts are "
            "unioned and sessionized into a journey table, then credited under "
            "first-touch, last-touch, and multi-touch models into result sets."
        ),
        "pipeline_inputs": ["MartTable"],
        "pipeline_outputs": ["MetricResultSet"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "sessionize_touches",
                "member_family_refs": [
                    "prim:analytics.sessionize",
                    "prim:analytics.dedupe_latest_per_key",
                    "prim:mset.union_all_align",
                ],
                "parallelizable": True,
                "consumes": ["MartTable"],
                "produces": ["IntermediateTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "attribution",
                "member_family_refs": [
                    "prim:analytics.attribution_first_touch",
                    "prim:analytics.attribution_last_touch",
                    "prim:analytics.attribution_multi_touch",
                    "prim:analytics.conversion_rate",
                ],
                "parallelizable": False,
                "consumes": ["IntermediateTable"],
                "produces": ["MetricResultSet"],
            },
        ],
        "invariants": [
            "credit assigned across all channels for a conversion sums to one",
            "a touch is attributed to at most one conversion within its lookback window",
        ],
        "proof_requirements": [
            "per-conversion attribution weights sum to exactly 1.0",
            "total attributed conversions equal the observed conversion count",
        ],
        "known_failure_modes": [
            "overlapping lookback windows credit one touch to two conversions",
            "unmatched touches inflate first-touch credit when joins miss a conversion",
        ],
    },
    # ----------------------------------------------------------------------
    # 16. dbt layered incremental merge
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:dbt_layered.incremental_merge_marts",
        "title": "dbt Layered Incremental Merge Marts",
        "pattern": "dbt_layered",
        "description": (
            "Incremental dbt layering. Staging models materialize "
            "incrementally with predicate pruning, intermediate models merge "
            "new keys, and marts enforce a model contract before publication."
        ),
        "pipeline_inputs": ["RawSourceTable"],
        "pipeline_outputs": ["MartTable"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "staging_incremental",
                "member_family_refs": [
                    "prim:dbt.staging_model",
                    "prim:dbt.materialize_incremental",
                    "prim:dbt.incremental_predicate_prune",
                    "prim:dbt.source_freshness",
                ],
                "parallelizable": True,
                "consumes": ["RawSourceTable"],
                "produces": ["StagingTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "intermediate_merge",
                "member_family_refs": [
                    "prim:dbt.intermediate_model",
                    "prim:dbt.incremental_merge",
                    "prim:dbt.ref_resolve",
                ],
                "parallelizable": True,
                "consumes": ["StagingTable"],
                "produces": ["IntermediateTable"],
            },
            {
                "wave_index": 3,
                "wave_name": "marts_contract",
                "member_family_refs": [
                    "prim:dbt.mart_model",
                    "prim:dbt.model_contract_enforce",
                    "prim:dbt.generic_test_relationships",
                    "prim:dbt.row_count_reconcile",
                ],
                "parallelizable": False,
                "consumes": ["IntermediateTable"],
                "produces": ["MartTable"],
            },
        ],
        "invariants": [
            "the incremental predicate covers every partition touched by new source rows",
            "the merge key is unique within each incremental batch",
        ],
        "proof_requirements": [
            "a full-refresh rebuild reproduces the incrementally built mart",
            "the enforced model contract rejects any column type or nullability drift",
        ],
        "known_failure_modes": [
            "a too-narrow incremental predicate skips late-arriving source rows",
            "a duplicate merge key overwrites the wrong existing row",
        ],
    },
    # ----------------------------------------------------------------------
    # 17. Medallion streaming CDC
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:medallion.streaming_cdc_medallion",
        "title": "Medallion Streaming CDC",
        "pattern": "medallion",
        "description": (
            "Streaming medallion with change capture. A CDC stream lands in "
            "bronze with dead-letter handling, is merged exactly-once and "
            "conformed into silver, then rolled up into gold."
        ),
        "pipeline_inputs": ["RawSourceTable"],
        "pipeline_outputs": ["GoldTable"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "bronze_stream",
                "member_family_refs": [
                    "prim:dewh.bronze_ingest_streaming",
                    "prim:dewh.checkpoint_watermark_advance",
                    "prim:dewh.dead_letter_reprocess",
                ],
                "parallelizable": True,
                "consumes": ["RawSourceTable"],
                "produces": ["BronzeTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "silver_cdc",
                "member_family_refs": [
                    "prim:dewh.cdc_apply_merge",
                    "prim:dewh.exactly_once_merge",
                    "prim:dewh.silver_conform_schema",
                    "prim:dewh.idempotent_upsert",
                ],
                "parallelizable": True,
                "consumes": ["BronzeTable"],
                "produces": ["SilverTable"],
            },
            {
                "wave_index": 3,
                "wave_name": "gold_rollup",
                "member_family_refs": [
                    "prim:dewh.gold_aggregate_rollup",
                    "prim:dewh.gold_curate",
                    "prim:dewh.optimize_vacuum_retention",
                ],
                "parallelizable": False,
                "consumes": ["SilverTable"],
                "produces": ["GoldTable"],
            },
        ],
        "invariants": [
            "each CDC event is applied to silver at most once",
            "gold rollups read only committed silver state",
        ],
        "proof_requirements": [
            "reprocessing the dead-letter queue does not create duplicate silver rows",
            "gold aggregates reconcile to silver counts after each micro-batch",
        ],
        "known_failure_modes": [
            "an at-least-once source delivers a duplicate that escapes the merge key",
            "a schema change in the stream routes valid rows to the dead-letter queue",
        ],
    },
    # ----------------------------------------------------------------------
    # 18. CDC to SCD2 Type-4 history split
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:cdc_to_scd2.type4_history_split",
        "title": "CDC to SCD2 Type-4 History Split",
        "pattern": "cdc_to_scd2",
        "description": (
            "Type-4 dimension with a separate history table. CDC is captured "
            "to bronze with soft deletes, ordered and reconciled into silver, "
            "then split into a current dimension plus a full history table."
        ),
        "pipeline_inputs": ["RawSourceTable"],
        "pipeline_outputs": ["SCD2Dimension"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "capture",
                "member_family_refs": [
                    "prim:dewh.cdc_capture",
                    "prim:dewh.watermark_incremental_extract",
                    "prim:dewh.soft_delete_apply",
                ],
                "parallelizable": True,
                "consumes": ["RawSourceTable"],
                "produces": ["BronzeTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "reconcile",
                "member_family_refs": [
                    "prim:dewh.cdc_dedup_order",
                    "prim:dewh.late_arriving_data_reconcile",
                    "prim:dewh.dedup_tie_break",
                ],
                "parallelizable": False,
                "consumes": ["BronzeTable"],
                "produces": ["SilverTable"],
            },
            {
                "wave_index": 3,
                "wave_name": "scd_split",
                "member_family_refs": [
                    "prim:wh.scd_type4_history_table",
                    "prim:wh.scd_type2_new_row",
                    "prim:wh.current_dimension_view",
                    "prim:wh.dimension_change_detect",
                ],
                "parallelizable": False,
                "consumes": ["SilverTable"],
                "produces": ["SCD2Dimension"],
            },
        ],
        "invariants": [
            "the current table holds exactly one row per natural key",
            "the history table records every prior version with closed validity ranges",
        ],
        "proof_requirements": [
            "the current view equals the latest history version for every natural key",
            "history validity ranges are contiguous with no gaps or overlaps",
        ],
        "known_failure_modes": [
            "a soft delete removes a key from current but leaves stale history open",
            "out-of-order events write a history version newer than the current row",
        ],
    },
    # ----------------------------------------------------------------------
    # 19. Lakehouse ELT schema/partition evolution
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:lakehouse_elt.schema_evolution_partitioned",
        "title": "Lakehouse ELT (schema and partition evolution)",
        "pattern": "lakehouse_elt",
        "description": (
            "Evolving-table lakehouse ELT. Bronze ingest applies schema and "
            "partition evolution, silver conforms schema and overwrites "
            "partitions with hidden partitioning, and gold curates with "
            "snapshot expiry."
        ),
        "pipeline_inputs": ["RawSourceTable"],
        "pipeline_outputs": ["GoldTable"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "ingest_evolve",
                "member_family_refs": [
                    "prim:dewh.bronze_ingest_batch",
                    "prim:dewh.schema_evolution_apply",
                    "prim:dewh.partition_evolution_apply",
                    "prim:dewh.flatten_semi_structured",
                ],
                "parallelizable": True,
                "consumes": ["RawSourceTable"],
                "produces": ["BronzeTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "conform_partition",
                "member_family_refs": [
                    "prim:dewh.silver_conform_schema",
                    "prim:dewh.insert_overwrite_partition",
                    "prim:dewh.hidden_partition_transform",
                    "prim:dewh.partition_prune_plan",
                ],
                "parallelizable": True,
                "consumes": ["BronzeTable"],
                "produces": ["SilverTable"],
            },
            {
                "wave_index": 3,
                "wave_name": "curate_expire",
                "member_family_refs": [
                    "prim:dewh.gold_curate",
                    "prim:dewh.iceberg_snapshot_expire",
                    "prim:dewh.manifest_rewrite",
                ],
                "parallelizable": False,
                "consumes": ["SilverTable"],
                "produces": ["GoldTable"],
            },
        ],
        "invariants": [
            "schema evolution is additive; existing columns keep their type",
            "partition overwrite is scoped to the pruned partition set only",
        ],
        "proof_requirements": [
            "a query written before evolution still returns on the evolved table",
            "partition-scoped overwrite leaves untouched partitions byte-identical",
        ],
        "known_failure_modes": [
            "a partition-spec change strands historical partitions from pruning",
            "snapshot expiry removes a snapshot a downstream reader still time-travels to",
        ],
    },
    # ----------------------------------------------------------------------
    # 20. Wide table refresh full rebuild
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:wide_table_refresh.full_rebuild_obt",
        "title": "Wide Table Full Rebuild (OBT)",
        "pattern": "wide_table_refresh",
        "description": (
            "Full-refresh wide table. Sources are fully rebuilt into staging, "
            "joined and conformed in an intermediate layer, then flattened "
            "into a single wide one-big-table for reporting."
        ),
        "pipeline_inputs": ["RawSourceTable"],
        "pipeline_outputs": ["WideTable"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "stage",
                "member_family_refs": [
                    "prim:dbt.staging_model",
                    "prim:dbt.full_refresh_rebuild",
                    "prim:dewh.silver_clean",
                ],
                "parallelizable": True,
                "consumes": ["RawSourceTable"],
                "produces": ["StagingTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "join_conform",
                "member_family_refs": [
                    "prim:mset.left_join",
                    "prim:mset.union_all_align",
                    "prim:wh.dimension_conformance_check",
                    "prim:dbt.intermediate_model",
                ],
                "parallelizable": True,
                "consumes": ["StagingTable"],
                "produces": ["IntermediateTable"],
            },
            {
                "wave_index": 3,
                "wave_name": "widen_flatten",
                "member_family_refs": [
                    "prim:wh.obt_flatten",
                    "prim:dbt.wide_model",
                    "prim:analytics.pivot_long_to_wide",
                    "prim:dbt.materialize_table",
                ],
                "parallelizable": False,
                "consumes": ["IntermediateTable"],
                "produces": ["WideTable"],
            },
        ],
        "invariants": [
            "the full rebuild is idempotent and depends only on current source state",
            "the flatten preserves the declared base grain",
        ],
        "proof_requirements": [
            "two consecutive rebuilds over identical sources produce identical output",
            "wide-table row count equals the base-grain row count after flatten",
        ],
        "known_failure_modes": [
            "a union of misaligned columns shifts values into the wrong field",
            "a many-side join multiplies base-grain rows in the wide table",
        ],
    },
    # ----------------------------------------------------------------------
    # 21. Snowflake normalize hierarchy bridge
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:snowflake_normalize.hierarchy_bridge",
        "title": "Snowflake Normalize with Hierarchy Bridge",
        "pattern": "snowflake_normalize",
        "description": (
            "Snowflaked ragged hierarchy. A staged dimension is normalized and "
            "split into mini-dimensions, then a hierarchy bridge with weighted "
            "paths is built to support drill-up and drill-down."
        ),
        "pipeline_inputs": ["RawSourceTable"],
        "pipeline_outputs": ["DimensionTable"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "stage",
                "member_family_refs": [
                    "prim:dbt.staging_model",
                    "prim:dewh.silver_clean",
                ],
                "parallelizable": True,
                "consumes": ["RawSourceTable"],
                "produces": ["StagingTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "normalize_split",
                "member_family_refs": [
                    "prim:wh.snowflake_normalize_dimension",
                    "prim:wh.mini_dimension_split",
                    "prim:wh.hierarchy_flatten",
                ],
                "parallelizable": True,
                "consumes": ["StagingTable"],
                "produces": ["IntermediateTable"],
            },
            {
                "wave_index": 3,
                "wave_name": "bridge_assemble",
                "member_family_refs": [
                    "prim:wh.hierarchy_bridge_build",
                    "prim:wh.bridge_table_build",
                    "prim:wh.multivalued_bridge_weighting",
                    "prim:wh.dimension_build",
                ],
                "parallelizable": False,
                "consumes": ["IntermediateTable"],
                "produces": ["DimensionTable"],
            },
        ],
        "invariants": [
            "bridge path weights for a parent sum to one across its children",
            "every hierarchy node reaches the root through exactly one bridge path",
        ],
        "proof_requirements": [
            "aggregating a measure through the bridge equals the direct total (no double count)",
            "every bridge edge references existing parent and child dimension rows",
        ],
        "known_failure_modes": [
            "a cyclic parent reference makes the bridge non-terminating",
            "unnormalized weights double-count a shared child across parents",
        ],
    },
    # ----------------------------------------------------------------------
    # 22. One big table for ML feature table
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:one_big_table.ml_feature_table",
        "title": "One Big Table ML Feature Build",
        "pattern": "one_big_table",
        "description": (
            "Feature-store one-big-table. Staged events are deduplicated, "
            "windowed aggregates and lag features are computed, then pivoted "
            "and flattened into a single wide feature table per entity."
        ),
        "pipeline_inputs": ["RawSourceTable"],
        "pipeline_outputs": ["WideTable"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "stage_events",
                "member_family_refs": [
                    "prim:dbt.staging_model",
                    "prim:dewh.silver_clean",
                    "prim:analytics.dedupe_latest_per_key",
                ],
                "parallelizable": True,
                "consumes": ["RawSourceTable"],
                "produces": ["StagingTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "aggregate_windows",
                "member_family_refs": [
                    "prim:analytics.rolling_average",
                    "prim:analytics.running_total",
                    "prim:analytics.lag_lead_delta",
                    "prim:analytics.window_row_number",
                ],
                "parallelizable": True,
                "consumes": ["StagingTable"],
                "produces": ["IntermediateTable"],
            },
            {
                "wave_index": 3,
                "wave_name": "flatten_features",
                "member_family_refs": [
                    "prim:wh.obt_flatten",
                    "prim:analytics.pivot_long_to_wide",
                    "prim:dbt.wide_model",
                ],
                "parallelizable": False,
                "consumes": ["IntermediateTable"],
                "produces": ["WideTable"],
            },
        ],
        "invariants": [
            "every feature is computed as-of the declared point in time with no future leakage",
            "the feature table has exactly one row per entity per as-of timestamp",
        ],
        "proof_requirements": [
            "no windowed feature reads a row with a timestamp after its as-of point",
            "feature-table grain uniqueness test passes per entity per as-of time",
        ],
        "known_failure_modes": [
            "an unbounded window leaks future events into a training feature",
            "a duplicate event skews a rolling average when dedupe misses a key",
        ],
    },
    # ----------------------------------------------------------------------
    # 23. Analytics mart customer RFM / LTV
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:analytics_mart.customer_rfm_ltv",
        "title": "Customer RFM and LTV Mart",
        "pattern": "analytics_mart",
        "description": (
            "Customer value mart. Transaction marts are aggregated to a "
            "customer grain, then scored into RFM segments, lifetime value, "
            "Pareto tiers, and churn flags as metric result sets."
        ),
        "pipeline_inputs": ["MartTable"],
        "pipeline_outputs": ["MetricResultSet"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "customer_agg",
                "member_family_refs": [
                    "prim:analytics.rollup_aggregate",
                    "prim:analytics.first_last_value_per_group",
                    "prim:analytics.period_to_date",
                ],
                "parallelizable": True,
                "consumes": ["MartTable"],
                "produces": ["IntermediateTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "segment_score",
                "member_family_refs": [
                    "prim:analytics.rfm_segmentation",
                    "prim:analytics.ltv_clv",
                    "prim:analytics.pareto_abc",
                    "prim:analytics.churn_flag",
                ],
                "parallelizable": False,
                "consumes": ["IntermediateTable"],
                "produces": ["MetricResultSet"],
            },
        ],
        "invariants": [
            "every active customer is assigned exactly one RFM segment",
            "Pareto tiers partition customers with no customer in two tiers",
        ],
        "proof_requirements": [
            "segment membership counts sum to the aggregated customer population",
            "lifetime value per customer reconciles to summed transaction revenue",
        ],
        "known_failure_modes": [
            "customers with no recent activity fall out of every RFM bucket",
            "refunds are ignored and overstate lifetime value",
        ],
    },
    # ----------------------------------------------------------------------
    # 24. Semantic layer cube materialize
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:semantic_layer_build.cube_materialized_metrics",
        "title": "Semantic Layer Cube Materialization",
        "pattern": "semantic_layer_build",
        "description": (
            "Pre-aggregated semantic cube. Marts are modeled with entities, "
            "dimensions, measures, and resolved join paths, then materialized "
            "as a cube and grouping-set result set for fast slice-and-dice."
        ),
        "pipeline_inputs": ["MartTable"],
        "pipeline_outputs": ["MetricResultSet"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "define_semantics",
                "member_family_refs": [
                    "prim:sem.entity_define",
                    "prim:sem.dimension_define",
                    "prim:sem.measure_define",
                    "prim:sem.metric_define",
                    "prim:sem.granularity_resolve",
                    "prim:sem.join_path_resolve",
                ],
                "parallelizable": True,
                "consumes": ["MartTable"],
                "produces": ["SemanticMetricSet"],
            },
            {
                "wave_index": 2,
                "wave_name": "materialize_cube",
                "member_family_refs": [
                    "prim:sem.cube_materialize",
                    "prim:sem.metric_query_compile",
                    "prim:sem.metric_filter_apply",
                    "prim:analytics.cube_aggregate",
                    "prim:analytics.grouping_sets",
                ],
                "parallelizable": False,
                "consumes": ["SemanticMetricSet"],
                "produces": ["MetricResultSet"],
            },
        ],
        "invariants": [
            "a materialized cube cell equals the on-the-fly metric for the same slice",
            "join paths resolve to a single declared path per entity pair",
        ],
        "proof_requirements": [
            "a sample of cube cells matches direct metric_query_compile results",
            "grouping-set subtotals reconcile to the grand total",
        ],
        "known_failure_modes": [
            "a stale cube serves results after the underlying mart changed",
            "an ambiguous join path fans out and inflates a measure in the cube",
        ],
    },
    # ----------------------------------------------------------------------
    # 25. Star build conformed bus matrix
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:star_build.conformed_bus_matrix",
        "title": "Conformed Bus-Matrix Star Build",
        "pattern": "star_build",
        "description": (
            "Enterprise bus-matrix build. Multiple sources are unioned into "
            "staging, conformed dimensions are built once, several fact tables "
            "are loaded against them, then drill-across marts merge the facts "
            "on shared dimensions."
        ),
        "pipeline_inputs": ["RawSourceTable"],
        "pipeline_outputs": ["MartTable"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "stage_sources",
                "member_family_refs": [
                    "prim:dbt.staging_model",
                    "prim:dewh.multi_source_union_ingest",
                    "prim:dewh.silver_clean",
                ],
                "parallelizable": True,
                "consumes": ["RawSourceTable"],
                "produces": ["StagingTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "conformed_dims",
                "member_family_refs": [
                    "prim:wh.conformed_dimension_build",
                    "prim:wh.dimension_conformance_check",
                    "prim:wh.date_dimension_generate",
                    "prim:wh.surrogate_key_generate",
                ],
                "parallelizable": True,
                "consumes": ["StagingTable"],
                "produces": ["DimensionTable"],
            },
            {
                "wave_index": 3,
                "wave_name": "multi_facts",
                "member_family_refs": [
                    "prim:wh.transaction_fact_build",
                    "prim:wh.periodic_snapshot_fact_build",
                    "prim:wh.consolidated_fact_build",
                    "prim:wh.surrogate_key_lookup",
                ],
                "parallelizable": True,
                "consumes": ["StagingTable", "DimensionTable"],
                "produces": ["FactTable"],
            },
            {
                "wave_index": 4,
                "wave_name": "drill_across_marts",
                "member_family_refs": [
                    "prim:wh.drill_across_merge",
                    "prim:wh.star_schema_assemble",
                    "prim:dbt.mart_model",
                ],
                "parallelizable": False,
                "consumes": ["FactTable", "DimensionTable"],
                "produces": ["MartTable"],
            },
        ],
        "invariants": [
            "shared dimensions are physically identical across every fact that uses them",
            "drill-across merges facts only on conformed dimension keys",
        ],
        "proof_requirements": [
            "conformance check passes for every dimension shared across facts",
            "a drill-across total equals the sum of the per-fact totals on the shared grain",
        ],
        "known_failure_modes": [
            "one fact loads a private copy of a dimension, breaking drill-across",
            "mismatched grains across facts produce a misleading merged total",
        ],
    },
    # ----------------------------------------------------------------------
    # 26. Medallion governed PII
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:medallion.governed_pii_medallion",
        "title": "Governed PII Medallion",
        "pattern": "medallion",
        "description": (
            "Compliance-governed medallion. Bronze ingest enforces a data "
            "contract and captures lineage, silver masks PII and quarantines "
            "and soft-deletes on request, and gold publishes a governed "
            "contract for consumers."
        ),
        "pipeline_inputs": ["RawSourceTable"],
        "pipeline_outputs": ["GoldTable"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "bronze_ingest",
                "member_family_refs": [
                    "prim:dewh.bronze_ingest_batch",
                    "prim:dewh.data_contract_enforce",
                    "prim:dewh.lineage_capture",
                ],
                "parallelizable": True,
                "consumes": ["RawSourceTable"],
                "produces": ["BronzeTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "silver_govern",
                "member_family_refs": [
                    "prim:dewh.silver_clean",
                    "prim:dewh.pii_masking_apply",
                    "prim:dewh.quarantine_bad_rows",
                    "prim:dewh.soft_delete_apply",
                ],
                "parallelizable": True,
                "consumes": ["BronzeTable"],
                "produces": ["SilverTable"],
            },
            {
                "wave_index": 3,
                "wave_name": "gold_publish",
                "member_family_refs": [
                    "prim:dewh.gold_curate",
                    "prim:dewh.data_contract_publish",
                    "prim:dewh.row_count_reconciliation",
                ],
                "parallelizable": False,
                "consumes": ["SilverTable"],
                "produces": ["GoldTable"],
            },
        ],
        "invariants": [
            "no unmasked PII column reaches the gold layer",
            "a soft-deleted subject is absent from every gold consumer view",
        ],
        "proof_requirements": [
            "a PII scan of gold finds no masked-designated column in the clear",
            "lineage links every gold column back to a contract-declared source field",
        ],
        "known_failure_modes": [
            "a new source column carrying PII bypasses the masking allowlist",
            "a soft delete lands after a gold snapshot already exported the subject",
        ],
    },
    # ----------------------------------------------------------------------
    # 27. dbt layered finance close
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:dbt_layered.finance_close_marts",
        "title": "dbt Finance Close Marts",
        "pattern": "dbt_layered",
        "description": (
            "Month-end finance close in dbt. Ledger sources and account seeds "
            "are staged and tested, running balances are built in the "
            "intermediate layer, and close marts expose metrics and a "
            "registered exposure."
        ),
        "pipeline_inputs": ["RawSourceTable"],
        "pipeline_outputs": ["MartTable"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "staging_gl",
                "member_family_refs": [
                    "prim:dbt.source_define",
                    "prim:dbt.staging_model",
                    "prim:dbt.seed_load",
                    "prim:dbt.generic_test_not_null",
                ],
                "parallelizable": True,
                "consumes": ["RawSourceTable"],
                "produces": ["StagingTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "intermediate_balances",
                "member_family_refs": [
                    "prim:dbt.intermediate_model",
                    "prim:dbt.surrogate_key_generate",
                    "prim:analytics.running_total",
                    "prim:dbt.ref_resolve",
                ],
                "parallelizable": True,
                "consumes": ["StagingTable"],
                "produces": ["IntermediateTable"],
            },
            {
                "wave_index": 3,
                "wave_name": "finance_marts",
                "member_family_refs": [
                    "prim:dbt.mart_model",
                    "prim:dbt.metric_define",
                    "prim:dbt.exposure_register",
                    "prim:dbt.generic_test_unique",
                ],
                "parallelizable": False,
                "consumes": ["IntermediateTable"],
                "produces": ["MartTable"],
            },
        ],
        "invariants": [
            "the account seed is the single source of the chart of accounts",
            "running balances are computed in a deterministic posting order",
        ],
        "proof_requirements": [
            "close-mart ending balances reconcile to the source trial balance",
            "every mart metric traces through a registered exposure to a consumer",
        ],
        "known_failure_modes": [
            "a stale account seed misclassifies new ledger accounts",
            "an out-of-order posting yields a non-reproducible running balance",
        ],
    },
    # ----------------------------------------------------------------------
    # 28. CDC to SCD2 subscription state (Type-6 hybrid)
    # ----------------------------------------------------------------------
    {
        "pipeline_id": "pipeline:cdc_to_scd2.subscription_state_scd2",
        "title": "Subscription State SCD2 (Type-6 hybrid)",
        "pattern": "cdc_to_scd2",
        "description": (
            "Subscription lifecycle dimension. Plan-change CDC is captured and "
            "appended to bronze, ordered exactly-once into silver, then "
            "applied as a Type-6 hybrid dimension carrying both current and "
            "historical plan attributes."
        ),
        "pipeline_inputs": ["RawSourceTable"],
        "pipeline_outputs": ["SCD2Dimension"],
        "waves": [
            {
                "wave_index": 1,
                "wave_name": "capture_state",
                "member_family_refs": [
                    "prim:dewh.cdc_capture",
                    "prim:dewh.cdc_bootstrap_snapshot",
                    "prim:dewh.append_only_load",
                ],
                "parallelizable": True,
                "consumes": ["RawSourceTable"],
                "produces": ["BronzeTable"],
            },
            {
                "wave_index": 2,
                "wave_name": "order_reconcile",
                "member_family_refs": [
                    "prim:dewh.cdc_dedup_order",
                    "prim:dewh.exactly_once_merge",
                    "prim:dewh.late_arriving_data_reconcile",
                ],
                "parallelizable": False,
                "consumes": ["BronzeTable"],
                "produces": ["SilverTable"],
            },
            {
                "wave_index": 3,
                "wave_name": "scd_hybrid",
                "member_family_refs": [
                    "prim:wh.scd_type6_hybrid",
                    "prim:wh.scd_type3_prior_column",
                    "prim:wh.dimension_change_detect",
                    "prim:wh.surrogate_key_generate",
                ],
                "parallelizable": False,
                "consumes": ["SilverTable"],
                "produces": ["SCD2Dimension"],
            },
        ],
        "invariants": [
            "the current-plan attribute matches the latest version row for each subscription",
            "each historical version carries the prior-plan value it superseded",
        ],
        "proof_requirements": [
            "the current attribute on every row equals the value on the open version",
            "version validity ranges per subscription are contiguous and non-overlapping",
        ],
        "known_failure_modes": [
            "a plan downgrade and re-upgrade in one batch collapses into a single version",
            "the current attribute is not backfilled on old rows and drifts from history",
        ],
    },
]
