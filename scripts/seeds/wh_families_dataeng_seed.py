"""Seed rows for reusable-primitive families in the data_engineering_wh domain.

Pure data module: one top-level constant FAMILIES (list of dicts). Each row
is candidate seed material describing one recurring lakehouse / data-
engineering building block; the builder (scripts/build_universal_primitive_
pack.py) injects record_type, version, candidate=True, and serves_truth=
False, and crosses each family with the runtime wrappers it declares
applicable.

Scope (all domain="data_engineering_wh", ids "prim:dewh.*"): the medallion
lakehouse lane - bronze batch and streaming ingest, append-only and multi-
source union loads, stream replay, semi-structured flatten; silver clean /
conform / dedupe / reference enrich / PII mask; gold curate and aggregate;
change-data-capture capture, ordering, apply-merge, soft delete, and
bootstrap snapshot; idempotent / merge-into / exactly-once / incremental
append upserts; delete-insert and insert-overwrite partition refreshes;
watermark incremental extract and advance, bounded backfill, late-arriving
reconcile; small-file compaction, clustering, vacuum, snapshot expire,
manifest rewrite, partition evolution, time-travel restore, zero-copy clone;
partition prune and hidden-partition planning; schema evolution, data-
contract enforce / quarantine / dead-letter reprocess / publish; row-count
reconciliation, source freshness, and lineage capture.

Ports use the canonical warehouse vocabulary so families compose on the
typed edge graph (config ports carry request-supplied policy/spec; receipt
ports are evidence outputs). Effects are declared honestly: SQL transforms
that read a source and write a target declare database_read+database_write,
lake-file maintenance adds file_read/file_write, read-only checks declare
database_read, and artifact producers declare artifact_write. No unmeasured
performance, savings, or benchmark claims appear anywhere. Idempotent merge
and upsert families carry idempotency_test; lossless flatten / clone /
layout rewrites carry roundtrip_test; keyed and dimensional builds carry
unique_key_test and, where a table references another, referential_
integrity_check. Destructive merges, overwrites, deletes, vacuum, snapshot
expiry, and restores set human_review_required=True.

Grounded in Delta Lake and Apache Iceberg table maintenance, the medallion
lakehouse architecture, dbt incremental materializations, and log-based
change-data-capture patterns.
"""

FAMILIES = [   {   'family_id': 'prim:dewh.bronze_ingest_batch',
        'domain': 'data_engineering_wh',
        'title': 'Bronze Batch Ingest',
        'input_edge': 'RawSourceExtract+SchemaSpec',
        'output_edge': 'BronzeTable+ModelRunReceipt',
        'blackbox': {   'does': 'Lands a raw source extract into an append-only bronze table '
                                'verbatim, adding ingest audit columns and emitting a run '
                                'receipt with the loaded row count.'},
        'effects': ['database_read', 'database_write', 'file_read', 'file_write'],
        'base_runtime_targets': ['lakehouse.table', 'spark.job', 'local.python'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:queue_worker',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['parquet', 'json_object', 'csv', 'rows'],
        'proof_requirements': [   'schema_validation',
                                  'row_count_reconciliation',
                                  'idempotency_test'],
        'problem_solution': {   'problem': 'Raw source data must be captured into the lake '
                                           'exactly as received, with provenance columns, '
                                           'before any cleaning happens, so that reprocessing '
                                           'can always start from an untouched copy.',
                                'naive_agent_failure': 'An agent transforms or filters rows '
                                                       'during ingest, so the bronze layer no '
                                                       'longer reflects the source and a later '
                                                       'logic change cannot be replayed from '
                                                       'raw.',
                                'solution': 'An append-only landing capability that copies the '
                                            'extract without semantic change, stamps load '
                                            'timestamp and batch id, and reconciles the '
                                            'written count against the source count.',
                                'core_components': [   'extract reader',
                                                       'audit-column stamper',
                                                       'append writer',
                                                       'load-count reconciler'],
                                'common_inputs': [   'raw source extract',
                                                     'target schema spec',
                                                     'batch id'],
                                'common_outputs': [   'bronze table',
                                                      'loaded row count',
                                                      'model run receipt'],
                                'known_pitfalls': [   'cleaning during ingest',
                                                      'dropping malformed rows silently',
                                                      'losing source ingest timestamp'],
                                'success_signals': [   'bronze row count equals source extract '
                                                       'count',
                                                       'each row carries a batch id and load '
                                                       'timestamp']},
        'source_ref_families': [   'medallion lakehouse architecture patterns',
                                   'Delta Lake documentation',
                                   'data-engineering pipeline patterns'],
        'risk_class': 'low',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.bronze_ingest_streaming',
        'domain': 'data_engineering_wh',
        'title': 'Bronze Streaming Micro-Batch Ingest',
        'input_edge': 'RawSourceExtract+IncrementalPolicy',
        'output_edge': 'BronzeTable+ModelRunReceipt',
        'blackbox': {   'does': 'Consumes a streaming source in bounded micro-batches, appends '
                                'each batch to the bronze table, and advances the stream '
                                'position recorded in the run receipt.'},
        'effects': ['database_read', 'database_write', 'file_read', 'file_write'],
        'base_runtime_targets': ['lakehouse.table', 'spark.job', 'stream.consumer'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:queue_worker',
                                           'wrap:cloud_function',
                                           'wrap:kubernetes_job'],
        'applicable_data_formats': ['json_object', 'arrow', 'parquet', 'rows'],
        'proof_requirements': [   'schema_validation',
                                  'idempotency_test',
                                  'row_count_reconciliation'],
        'problem_solution': {   'problem': 'A continuous event stream must be persisted to the '
                                           'lake in bounded batches so that offsets advance '
                                           'monotonically and a restart resumes without gaps '
                                           'or double-counting.',
                                'naive_agent_failure': 'An agent commits offsets before the '
                                                       'write completes, so a crash between '
                                                       'commit and write loses events that '
                                                       'will never be re-read.',
                                'solution': 'A micro-batch loop that writes the batch first, '
                                            'records the max processed offset in the receipt, '
                                            'and only advances the committed position after a '
                                            'durable write.',
                                'core_components': [   'batch boundary reader',
                                                       'append writer',
                                                       'offset tracker',
                                                       'commit-after-write barrier'],
                                'common_inputs': [   'stream source',
                                                     'incremental policy',
                                                     'last committed offset'],
                                'common_outputs': [   'bronze table',
                                                      'advanced offset',
                                                      'model run receipt'],
                                'known_pitfalls': [   'committing offset before write',
                                                      'unbounded batch sizes',
                                                      'reprocessing without idempotency key'],
                                'success_signals': [   'restart resumes at the last durable '
                                                       'offset',
                                                       'no gap between committed offset and '
                                                       'written rows']},
        'source_ref_families': [   'medallion lakehouse architecture patterns',
                                   'Delta Lake documentation',
                                   'data-engineering pipeline patterns'],
        'risk_class': 'medium',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.append_only_load',
        'domain': 'data_engineering_wh',
        'title': 'Append-Only Load',
        'input_edge': 'StagingTable+MaterializationPolicy',
        'output_edge': 'BronzeTable+ModelRunReceipt',
        'blackbox': {   'does': 'Appends new staging rows to a target table without touching '
                                'existing rows, using an insert-only strategy and reconciling '
                                'appended versus staged counts.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['warehouse.table', 'lakehouse.table', 'local.python'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:mcp_tool',
                                           'wrap:queue_worker',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job'],
        'applicable_data_formats': ['rows', 'parquet'],
        'proof_requirements': [   'row_count_reconciliation',
                                  'idempotency_test',
                                  'schema_validation'],
        'problem_solution': {   'problem': 'Some tables grow purely by insertion and must '
                                           'never update or delete prior rows, yet loads still '
                                           'need protection against re-inserting the same '
                                           'staged batch.',
                                'naive_agent_failure': 'An agent re-runs the load after a '
                                                       'partial failure and appends the same '
                                                       'rows twice because there is no '
                                                       'batch-level insert guard.',
                                'solution': 'An insert-only writer that checks a batch marker '
                                            'before appending and reconciles the appended '
                                            'count so a re-run of an already-loaded batch adds '
                                            'nothing.',
                                'core_components': [   'batch marker check',
                                                       'insert writer',
                                                       'append-count reconciler'],
                                'common_inputs': [   'staging rows',
                                                     'materialization policy',
                                                     'batch marker'],
                                'common_outputs': [   'appended table',
                                                      'appended row count',
                                                      'model run receipt'],
                                'known_pitfalls': [   'double append on re-run',
                                                      'accidental update of prior rows',
                                                      'unmarked batches'],
                                'success_signals': [   're-loading a completed batch appends '
                                                       'zero rows',
                                                       'existing rows are unchanged']},
        'source_ref_families': [   'medallion lakehouse architecture patterns',
                                   'data-engineering pipeline patterns',
                                   'Delta Lake documentation'],
        'risk_class': 'low',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.multi_source_union_ingest',
        'domain': 'data_engineering_wh',
        'title': 'Multi-Source Union Ingest',
        'input_edge': 'RecordSetA+RecordSetB',
        'output_edge': 'UnionedRecordSet+ModelRunReceipt',
        'blackbox': {   'does': 'Aligns two source record sets onto a common schema and unions '
                                'them into a single record set, tagging each row with its '
                                'origin and reconciling the combined count.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['lakehouse.table', 'spark.job', 'local.python'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:mcp_tool',
                                           'wrap:queue_worker',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job'],
        'applicable_data_formats': ['rows', 'parquet', 'arrow'],
        'proof_requirements': [   'schema_validation',
                                  'row_count_reconciliation',
                                  'contract_test'],
        'problem_solution': {   'problem': 'Two feeds that describe the same entity in '
                                           'different shapes must be combined into one table '
                                           'with a shared schema and a preserved record of '
                                           'which feed each row came from.',
                                'naive_agent_failure': 'An agent unions mismatched columns '
                                                       'positionally, so values land in the '
                                                       'wrong fields and the origin of each '
                                                       'row is lost.',
                                'solution': 'A schema-aligning union that maps each source to '
                                            'the shared columns by name, tags origin, and '
                                            'reconciles the output count against the sum of '
                                            'inputs.',
                                'core_components': [   'schema aligner',
                                                       'origin tagger',
                                                       'union writer',
                                                       'count reconciler'],
                                'common_inputs': [   'record set A',
                                                     'record set B',
                                                     'shared schema'],
                                'common_outputs': [   'unioned record set',
                                                      'per-origin counts',
                                                      'model run receipt'],
                                'known_pitfalls': [   'positional union across mismatched '
                                                      'schemas',
                                                      'losing source origin',
                                                      'type coercion silently nulling values'],
                                'success_signals': [   'output count equals sum of input '
                                                       'counts',
                                                       'every row carries a valid origin tag']},
        'source_ref_families': [   'data-engineering pipeline patterns',
                                   'medallion lakehouse architecture patterns',
                                   'dbt incremental materialization documentation'],
        'risk_class': 'low',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.replay_from_offset',
        'domain': 'data_engineering_wh',
        'title': 'Stream Replay From Offset',
        'input_edge': 'RawSourceExtract+IncrementalPolicy',
        'output_edge': 'BronzeTable+ModelRunReceipt',
        'blackbox': {   'does': 'Re-reads a stream from a supplied starting offset and '
                                're-lands the events, using an event idempotency key so '
                                'already-present events are not duplicated on replay.'},
        'effects': ['database_read', 'database_write', 'file_read', 'file_write'],
        'base_runtime_targets': ['stream.consumer', 'lakehouse.table', 'spark.job'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:queue_worker',
                                           'wrap:cloud_function',
                                           'wrap:kubernetes_job'],
        'applicable_data_formats': ['json_object', 'arrow', 'parquet'],
        'proof_requirements': [   'idempotency_test',
                                  'row_count_reconciliation',
                                  'schema_validation'],
        'problem_solution': {   'problem': 'After a logic fix or data loss, a stream must be '
                                           'reprocessed from a known offset without creating '
                                           'duplicate rows for events that were already '
                                           'landed.',
                                'naive_agent_failure': 'An agent replays from an offset and '
                                                       'blindly appends, doubling every event '
                                                       'that had already been ingested past '
                                                       'that point.',
                                'solution': 'A replay reader that seeks to the offset and '
                                            'lands events through an idempotency-key guard so '
                                            're-seen events are skipped rather than '
                                            'duplicated.',
                                'core_components': [   'offset seeker',
                                                       'event-key deduper',
                                                       'idempotent writer',
                                                       'replay-range reconciler'],
                                'common_inputs': [   'stream source',
                                                     'start offset',
                                                     'incremental policy'],
                                'common_outputs': [   'bronze table',
                                                      'replayed range',
                                                      'model run receipt'],
                                'known_pitfalls': [   'duplicating already-landed events',
                                                      'seeking to the wrong offset',
                                                      'unbounded replay window'],
                                'success_signals': [   'replaying a covered range adds no new '
                                                       'rows',
                                                       'the replayed offset range is recorded '
                                                       'in the receipt']},
        'source_ref_families': [   'change-data-capture and log-based replication patterns',
                                   'Delta Lake documentation',
                                   'data-engineering pipeline patterns'],
        'risk_class': 'medium',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.flatten_semi_structured',
        'domain': 'data_engineering_wh',
        'title': 'Semi-Structured Flatten',
        'input_edge': 'BronzeTable+SchemaSpec',
        'output_edge': 'SilverTable+ModelRunReceipt',
        'blackbox': {   'does': 'Explodes nested JSON objects and arrays from a bronze column '
                                'into typed relational rows and columns according to a schema '
                                'spec, preserving a path back to the source row.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['lakehouse.table', 'spark.job', 'local.python'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:mcp_tool',
                                           'wrap:queue_worker',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job'],
        'applicable_data_formats': ['json_object', 'rows', 'parquet'],
        'proof_requirements': [   'schema_validation',
                                  'roundtrip_test',
                                  'row_count_reconciliation'],
        'problem_solution': {   'problem': 'Nested payloads landed in bronze must be flattened '
                                           'into typed columns and exploded array rows so '
                                           'downstream models can query them relationally '
                                           'without parsing JSON.',
                                'naive_agent_failure': 'An agent flattens only the top level '
                                                       'and drops nested arrays, silently '
                                                       'losing repeated child records.',
                                'solution': 'A structured flattener that walks the declared '
                                            'paths, explodes arrays into child rows keyed to '
                                            'the parent, and keeps a source path so the '
                                            'collapse is reversible.',
                                'core_components': [   'path walker',
                                                       'array exploder',
                                                       'type caster',
                                                       'parent-link keeper'],
                                'common_inputs': [   'bronze rows',
                                                     'schema spec',
                                                     'explode paths'],
                                'common_outputs': [   'flattened silver table',
                                                      'exploded child rows',
                                                      'model run receipt'],
                                'known_pitfalls': [   'dropping nested arrays',
                                                      'type loss on cast',
                                                      'orphaned child rows without a parent '
                                                      'link'],
                                'success_signals': [   're-nesting the flattened output '
                                                       'reproduces the source structure',
                                                       'child rows all resolve to a parent']},
        'source_ref_families': [   'medallion lakehouse architecture patterns',
                                   'data-engineering pipeline patterns',
                                   'Delta Lake documentation'],
        'risk_class': 'low',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.silver_clean',
        'domain': 'data_engineering_wh',
        'title': 'Silver Clean And Conform',
        'input_edge': 'BronzeTable+SchemaSpec',
        'output_edge': 'SilverTable+ModelRunReceipt',
        'blackbox': {   'does': 'Transforms raw bronze rows into a cleaned, typed, conformed '
                                'silver table by casting types, trimming and standardizing '
                                'values, and applying the declared naming and null rules.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['warehouse.table', 'lakehouse.table', 'dbt.model'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:queue_worker',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['rows', 'parquet'],
        'proof_requirements': [   'schema_validation',
                                  'row_count_reconciliation',
                                  'contract_test'],
        'problem_solution': {   'problem': 'Bronze data carries source quirks, inconsistent '
                                           'types, and raw naming that must be normalized once '
                                           'into a trustworthy silver layer that every '
                                           'downstream model can rely on.',
                                'naive_agent_failure': 'An agent hard-codes cleaning inline in '
                                                       'many downstream models, so the same '
                                                       'field is cleaned differently in each '
                                                       'place and the results disagree.',
                                'solution': 'A single conform step that casts types, '
                                            'standardizes values, applies naming and null '
                                            'policy, and reconciles the row count so cleaning '
                                            'is defined exactly once.',
                                'core_components': [   'type caster',
                                                       'value standardizer',
                                                       'naming mapper',
                                                       'null-policy applier'],
                                'common_inputs': [   'bronze rows',
                                                     'schema spec',
                                                     'naming and null policy'],
                                'common_outputs': [   'silver table',
                                                      'cleaned row count',
                                                      'model run receipt'],
                                'known_pitfalls': [   'cleaning logic duplicated downstream',
                                                      'silent type coercion',
                                                      'losing rows to overly strict filters'],
                                'success_signals': [   'all downstream models read one '
                                                       'conformed field definition',
                                                       'row count reconciles with bronze minus '
                                                       'documented drops']},
        'source_ref_families': [   'medallion lakehouse architecture patterns',
                                   'dbt incremental materialization documentation',
                                   'data-engineering pipeline patterns'],
        'risk_class': 'low',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.silver_conform_schema',
        'domain': 'data_engineering_wh',
        'title': 'Schema Conform To Contract',
        'input_edge': 'BronzeTable+SchemaSpec',
        'output_edge': 'SilverTable+ContractReport',
        'blackbox': {   'does': 'Projects and coerces a bronze table onto an exact target '
                                'column set, order, and types defined by a schema spec, '
                                'reporting any columns added, dropped, or coerced.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['warehouse.table', 'lakehouse.table', 'local.python'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:mcp_tool',
                                           'wrap:queue_worker',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job'],
        'applicable_data_formats': ['rows', 'parquet', 'arrow'],
        'proof_requirements': ['schema_validation', 'contract_test', 'roundtrip_test'],
        'problem_solution': {   'problem': 'Downstream consumers require a stable column set '
                                           'and types, so an upstream table must be conformed '
                                           'to an agreed schema and any deviation must be '
                                           'surfaced rather than passed through.',
                                'naive_agent_failure': 'An agent select-stars the source, so a '
                                                       'new upstream column silently flows '
                                                       'downstream and breaks a consumer '
                                                       'expecting a fixed shape.',
                                'solution': 'A conform step that projects to the declared '
                                            'columns in order, coerces types, and emits a '
                                            'report of every add, drop, and coercion it '
                                            'applied.',
                                'core_components': [   'column projector',
                                                       'type coercer',
                                                       'deviation reporter'],
                                'common_inputs': ['bronze rows', 'schema spec'],
                                'common_outputs': ['conformed silver table', 'contract report'],
                                'known_pitfalls': [   'select-star leaking new columns',
                                                      'silent lossy coercion',
                                                      'column reordering breaking positional '
                                                      'consumers'],
                                'success_signals': [   'output shape matches the schema spec '
                                                       'exactly',
                                                       'every deviation appears in the '
                                                       'contract report']},
        'source_ref_families': [   'data-engineering pipeline patterns',
                                   'dbt incremental materialization documentation',
                                   'data contract specification patterns'],
        'risk_class': 'low',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.dedup_tie_break',
        'domain': 'data_engineering_wh',
        'title': 'Deduplicate With Tie-Break',
        'input_edge': 'StagingTable+DedupePolicy',
        'output_edge': 'DedupedTable+ModelRunReceipt',
        'blackbox': {   'does': 'Collapses duplicate rows sharing a business key down to one '
                                'survivor per key chosen by a deterministic tie-break order, '
                                'and reports how many duplicates were removed.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['warehouse.table', 'lakehouse.table', 'local.python'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:mcp_tool',
                                           'wrap:queue_worker',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job'],
        'applicable_data_formats': ['rows', 'parquet'],
        'proof_requirements': [   'unique_key_test',
                                  'row_count_reconciliation',
                                  'idempotency_test'],
        'problem_solution': {   'problem': 'A staging feed contains multiple rows per business '
                                           'key and exactly one deterministic survivor must be '
                                           'kept so downstream joins do not fan out.',
                                'naive_agent_failure': 'An agent uses distinct or an arbitrary '
                                                       'group-by that keeps a nondeterministic '
                                                       'row, so the survivor changes run to '
                                                       'run and results are unstable.',
                                'solution': 'A dedupe that ranks rows within each key by an '
                                            'explicit tie-break order and keeps rank one, '
                                            'reporting removed counts so the choice is stable '
                                            'and auditable.',
                                'core_components': [   'key partitioner',
                                                       'tie-break ranker',
                                                       'survivor selector',
                                                       'removed-count reporter'],
                                'common_inputs': [   'staging rows',
                                                     'dedupe policy',
                                                     'tie-break columns'],
                                'common_outputs': [   'deduped table',
                                                      'removed duplicate count',
                                                      'model run receipt'],
                                'known_pitfalls': [   'nondeterministic survivor',
                                                      'tie-break omitting a total order',
                                                      'removing rows that differ on unkeyed '
                                                      'columns'],
                                'success_signals': [   'exactly one row remains per business '
                                                       'key',
                                                       'the same survivor is chosen on every '
                                                       're-run']},
        'source_ref_families': [   'data-engineering pipeline patterns',
                                   'dbt incremental materialization documentation',
                                   'Delta Lake documentation'],
        'risk_class': 'low',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.reference_data_enrich',
        'domain': 'data_engineering_wh',
        'title': 'Reference Data Enrich',
        'input_edge': 'StagingTable+JoinPolicy',
        'output_edge': 'JoinedTable+ModelRunReceipt',
        'blackbox': {   'does': 'Left-joins staging rows to a governed reference lookup to add '
                                'descriptive attributes, routing unmatched keys to an unknown '
                                'member rather than dropping the rows.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['warehouse.table', 'lakehouse.table', 'dbt.model'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:mcp_tool',
                                           'wrap:queue_worker',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job'],
        'applicable_data_formats': ['rows', 'parquet'],
        'proof_requirements': [   'referential_integrity_check',
                                  'row_count_reconciliation',
                                  'unique_key_test'],
        'problem_solution': {   'problem': 'Fact-shaped rows must be enriched with attributes '
                                           'from a reference table without inflating or losing '
                                           'rows when a lookup key is missing or non-unique.',
                                'naive_agent_failure': 'An agent inner-joins to the reference '
                                                       'and drops every row whose key is '
                                                       'absent, and a duplicate reference key '
                                                       'fans the rows out.',
                                'solution': 'A left join against a uniqueness-checked '
                                            'reference that substitutes an unknown member for '
                                            'missing keys and reconciles input and output '
                                            'counts.',
                                'core_components': [   'reference uniqueness guard',
                                                       'left-join enricher',
                                                       'unknown-member substituter',
                                                       'count reconciler'],
                                'common_inputs': [   'staging rows',
                                                     'reference lookup',
                                                     'join policy'],
                                'common_outputs': [   'enriched joined table',
                                                      'unmatched count',
                                                      'model run receipt'],
                                'known_pitfalls': [   'inner join dropping unmatched rows',
                                                      'duplicate reference key fanning out '
                                                      'rows',
                                                      'null attributes not mapped to unknown '
                                                      'member'],
                                'success_signals': [   'input and output row counts reconcile',
                                                       'unmatched keys resolve to the unknown '
                                                       'member']},
        'source_ref_families': [   'data-engineering pipeline patterns',
                                   'dbt incremental materialization documentation',
                                   'The Data Warehouse Toolkit (Kimball)'],
        'risk_class': 'medium',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.pii_masking_apply',
        'domain': 'data_engineering_wh',
        'title': 'PII Masking Apply',
        'input_edge': 'SilverTable+DataContract',
        'output_edge': 'SilverTable+ContractReport',
        'blackbox': {   'does': 'Applies deterministic masking, hashing, or tokenization to '
                                'the sensitive columns named in a data contract, producing a '
                                'protected table and a report of masked fields.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['warehouse.table', 'lakehouse.table', 'local.python'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:mcp_tool',
                                           'wrap:queue_worker',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job'],
        'applicable_data_formats': ['rows', 'parquet'],
        'proof_requirements': ['contract_test', 'schema_validation', 'idempotency_test'],
        'problem_solution': {   'problem': 'Sensitive columns must be masked before data '
                                           'reaches broad-access layers, and the masking must '
                                           'be deterministic so joins on the masked key still '
                                           'work.',
                                'naive_agent_failure': 'An agent applies a random or '
                                                       'salted-per-run hash, so the same '
                                                       'identity masks to different values '
                                                       'across tables and can no longer be '
                                                       'joined.',
                                'solution': 'A contract-driven masker that applies a stable '
                                            'transform to each declared sensitive column and '
                                            'reports which fields were masked and by which '
                                            'method.',
                                'core_components': [   'sensitive-column selector',
                                                       'deterministic mask function',
                                                       'masked-field reporter'],
                                'common_inputs': [   'silver rows',
                                                     'data contract',
                                                     'masking method'],
                                'common_outputs': ['masked silver table', 'contract report'],
                                'known_pitfalls': [   'nondeterministic hashing breaking joins',
                                                      'missing a sensitive column',
                                                      'reversible masking leaking values'],
                                'success_signals': [   'the same input value masks to the same '
                                                       'output every run',
                                                       'every contract-listed field is '
                                                       'masked']},
        'source_ref_families': [   'data governance and privacy patterns',
                                   'data-engineering pipeline patterns',
                                   'data contract specification patterns'],
        'risk_class': 'medium',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.gold_curate',
        'domain': 'data_engineering_wh',
        'title': 'Gold Curate',
        'input_edge': 'SilverTable+GrainSpec',
        'output_edge': 'GoldTable+ModelRunReceipt',
        'blackbox': {   'does': 'Assembles business-ready gold tables from conformed silver '
                                'inputs at a declared grain, applying business rules and '
                                'derived measures for direct consumption by reporting.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['warehouse.table', 'lakehouse.table', 'dbt.model'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:queue_worker',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['rows', 'parquet', 'wide_table'],
        'proof_requirements': [   'schema_validation',
                                  'unique_key_test',
                                  'row_count_reconciliation'],
        'problem_solution': {   'problem': 'Reporting needs curated, business-rule-applied '
                                           'tables at a stated grain, built from trustworthy '
                                           'silver inputs rather than each dashboard '
                                           're-deriving logic from raw.',
                                'naive_agent_failure': 'An agent builds the gold table '
                                                       'straight from bronze, re-implementing '
                                                       'cleaning and business rules that then '
                                                       'drift from the shared definitions.',
                                'solution': 'A curate step that consumes conformed silver at '
                                            'the declared grain, applies business rules once, '
                                            'and enforces one row per grain key.',
                                'core_components': [   'silver consumer',
                                                       'business-rule applier',
                                                       'grain enforcer',
                                                       'measure deriver'],
                                'common_inputs': [   'silver rows',
                                                     'grain spec',
                                                     'business rules'],
                                'common_outputs': [   'gold table',
                                                      'derived measures',
                                                      'model run receipt'],
                                'known_pitfalls': [   'building gold from raw bronze',
                                                      'grain drift producing duplicate keys',
                                                      'business logic diverging from shared '
                                                      'definitions'],
                                'success_signals': [   'exactly one row per grain key',
                                                       'reporting reads gold without further '
                                                       'transformation']},
        'source_ref_families': [   'medallion lakehouse architecture patterns',
                                   'dbt incremental materialization documentation',
                                   'The Data Warehouse Toolkit (Kimball)'],
        'risk_class': 'low',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.gold_aggregate_rollup',
        'domain': 'data_engineering_wh',
        'title': 'Gold Aggregate Rollup',
        'input_edge': 'SilverTable+GrainSpec',
        'output_edge': 'GoldTable+ModelRunReceipt',
        'blackbox': {   'does': 'Pre-aggregates additive measures from a detailed silver table '
                                'up to a coarser reporting grain, producing one summarized row '
                                'per group with reconciled measure totals.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['warehouse.table', 'lakehouse.table', 'dbt.model'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:mcp_tool',
                                           'wrap:queue_worker',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job'],
        'applicable_data_formats': ['rows', 'parquet', 'wide_table'],
        'proof_requirements': [   'unique_key_test',
                                  'row_count_reconciliation',
                                  'schema_validation'],
        'problem_solution': {   'problem': 'Dashboards over billions of detail rows are slow, '
                                           'so an aggregate at a coarser grain must be '
                                           'maintained whose totals still tie out to the '
                                           'detail.',
                                'naive_agent_failure': 'An agent sums a semi-additive or '
                                                       'non-additive measure across a '
                                                       'dimension where that is invalid, '
                                                       'producing inflated totals.',
                                'solution': 'A rollup that groups to the declared grain, '
                                            'aggregates only measures valid for that grain, '
                                            'and reconciles the aggregate totals against the '
                                            'detail.',
                                'core_components': [   'grain grouper',
                                                       'additivity-aware aggregator',
                                                       'total reconciler'],
                                'common_inputs': [   'silver detail rows',
                                                     'grain spec',
                                                     'measure additivity rules'],
                                'common_outputs': [   'aggregate gold table',
                                                      'one row per group',
                                                      'model run receipt'],
                                'known_pitfalls': [   'summing non-additive measures',
                                                      'double counting from a fan-out join',
                                                      'grain not covering the group-by keys'],
                                'success_signals': [   'aggregate totals tie to the detail '
                                                       'totals',
                                                       'exactly one row per group key']},
        'source_ref_families': [   'The Data Warehouse Toolkit (Kimball)',
                                   'dbt incremental materialization documentation',
                                   'data-engineering pipeline patterns'],
        'risk_class': 'low',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.snapshot_isolation_read',
        'domain': 'data_engineering_wh',
        'title': 'Snapshot Isolation Read',
        'input_edge': 'SilverTable+MaterializationPolicy',
        'output_edge': 'AnalyticsResultSet+ModelRunReceipt',
        'blackbox': {   'does': 'Reads a table as of a single consistent table version so a '
                                'multi-statement job sees a stable snapshot even while '
                                'concurrent writers commit new versions.'},
        'effects': ['database_read'],
        'base_runtime_targets': ['lakehouse.table', 'warehouse.table', 'local.python'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:mcp_tool',
                                           'wrap:cron_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['rows', 'parquet', 'arrow'],
        'proof_requirements': ['schema_validation', 'roundtrip_test'],
        'problem_solution': {   'problem': 'A job that issues several reads must see one '
                                           'consistent version of a table, otherwise a writer '
                                           'committing mid-job yields a result mixing two '
                                           'states.',
                                'naive_agent_failure': 'An agent issues repeated reads without '
                                                       'pinning a version, so a concurrent '
                                                       'commit changes the data between reads '
                                                       'and the outputs disagree.',
                                'solution': 'A read that pins the current table version or a '
                                            'requested snapshot id up front and serves every '
                                            'read of the job from that fixed version.',
                                'core_components': [   'version pinner',
                                                       'snapshot reader',
                                                       'version-stamped receipt'],
                                'common_inputs': [   'silver table',
                                                     'materialization policy',
                                                     'snapshot id'],
                                'common_outputs': [   'analytics result set',
                                                      'pinned version id',
                                                      'model run receipt'],
                                'known_pitfalls': [   'reading without pinning a version',
                                                      'pinning an expired snapshot',
                                                      'mixing versions across statements'],
                                'success_signals': [   'all reads in the job resolve to one '
                                                       'version id',
                                                       'the served version is recorded in the '
                                                       'receipt']},
        'source_ref_families': [   'Apache Iceberg documentation',
                                   'Delta Lake documentation',
                                   'data-engineering pipeline patterns'],
        'risk_class': 'low',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.cdc_capture',
        'domain': 'data_engineering_wh',
        'title': 'CDC Change Capture',
        'input_edge': 'RawSourceTable+IncrementalPolicy',
        'output_edge': 'CDCChangeSet+ModelRunReceipt',
        'blackbox': {   'does': 'Reads inserts, updates, and deletes from a source change log '
                                'or high-water comparison and emits an ordered change set of '
                                'typed operations with before and after images.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['stream.consumer', 'warehouse.table', 'spark.job'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:queue_worker',
                                           'wrap:cloud_function',
                                           'wrap:kubernetes_job'],
        'applicable_data_formats': ['json_object', 'rows', 'parquet'],
        'proof_requirements': [   'schema_validation',
                                  'row_count_reconciliation',
                                  'contract_test'],
        'problem_solution': {   'problem': 'Downstream tables must track source inserts, '
                                           'updates, and deletes, so the source changes have '
                                           'to be captured as an ordered, typed change set '
                                           'rather than re-read in full.',
                                'naive_agent_failure': 'An agent captures only inserts and '
                                                       'updates and misses deletes, so removed '
                                                       'source rows live on forever '
                                                       'downstream.',
                                'solution': 'A capture that reads the change log or diffs '
                                            'against a high-water mark, emits typed operations '
                                            'with ordering metadata, and records the captured '
                                            'range.',
                                'core_components': [   'change-log reader',
                                                       'operation typer',
                                                       'ordering-metadata attacher',
                                                       'captured-range recorder'],
                                'common_inputs': [   'source table or log',
                                                     'incremental policy',
                                                     'last captured position'],
                                'common_outputs': [   'cdc change set',
                                                      'captured range',
                                                      'model run receipt'],
                                'known_pitfalls': [   'missing delete events',
                                                      'losing operation ordering',
                                                      'gaps when the log is truncated'],
                                'success_signals': [   'deletes appear as typed operations in '
                                                       'the change set',
                                                       'the captured position advances without '
                                                       'gaps']},
        'source_ref_families': [   'change-data-capture and log-based replication patterns',
                                   'Delta Lake documentation',
                                   'data-engineering pipeline patterns'],
        'risk_class': 'medium',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.cdc_dedup_order',
        'domain': 'data_engineering_wh',
        'title': 'CDC Order And Collapse',
        'input_edge': 'CDCChangeSet+DedupePolicy',
        'output_edge': 'DedupedTable+ModelRunReceipt',
        'blackbox': {   'does': 'Orders a change set by its commit sequence and collapses '
                                'multiple operations per key down to the single net latest '
                                'operation, ready for a one-pass apply.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['warehouse.table', 'spark.job', 'local.python'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:mcp_tool',
                                           'wrap:queue_worker',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job'],
        'applicable_data_formats': ['rows', 'parquet'],
        'proof_requirements': [   'unique_key_test',
                                  'idempotency_test',
                                  'row_count_reconciliation'],
        'problem_solution': {   'problem': 'A change set can contain several operations for '
                                           'the same key within one batch, and applying them '
                                           'out of order would leave the target in a wrong '
                                           'final state.',
                                'naive_agent_failure': 'An agent applies changes in arrival '
                                                       'order, so an update landing after a '
                                                       'later delete resurrects a row that '
                                                       'should be gone.',
                                'solution': 'An ordering and collapse step that sorts by '
                                            'commit sequence per key and keeps only the net '
                                            'latest operation so the apply is a single '
                                            'deterministic pass.',
                                'core_components': [   'sequence sorter',
                                                       'per-key collapser',
                                                       'net-operation selector'],
                                'common_inputs': [   'cdc change set',
                                                     'dedupe policy',
                                                     'sequence column'],
                                'common_outputs': [   'collapsed change set',
                                                      'one operation per key',
                                                      'model run receipt'],
                                'known_pitfalls': [   'applying operations out of order',
                                                      'keeping stale operations',
                                                      'ties without a total sequence order'],
                                'success_signals': [   'one net operation remains per key',
                                                       'collapse is stable on re-run']},
        'source_ref_families': [   'change-data-capture and log-based replication patterns',
                                   'Delta Lake documentation',
                                   'data-engineering pipeline patterns'],
        'risk_class': 'low',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.cdc_apply_merge',
        'domain': 'data_engineering_wh',
        'title': 'CDC Apply Merge',
        'input_edge': 'CDCChangeSet+MergePolicy',
        'output_edge': 'SilverTable+MergeReceipt',
        'blackbox': {   'does': 'Applies a collapsed change set to a target table as an atomic '
                                'merge, inserting new keys, updating changed keys, and '
                                'deleting tombstoned keys, and emits a merge receipt.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['warehouse.table', 'lakehouse.table', 'dbt.model'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:mcp_tool',
                                           'wrap:queue_worker',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job'],
        'applicable_data_formats': ['rows', 'parquet'],
        'proof_requirements': [   'idempotency_test',
                                  'unique_key_test',
                                  'referential_integrity_check',
                                  'row_count_reconciliation'],
        'problem_solution': {   'problem': 'A captured change set must be reflected in the '
                                           'target so that the target converges to the source, '
                                           'including physically removing rows for delete '
                                           'operations.',
                                'naive_agent_failure': 'An agent applies inserts and updates '
                                                       'but ignores deletes, so the target '
                                                       'keeps rows that were removed at the '
                                                       'source.',
                                'solution': 'An atomic merge keyed on the business key that '
                                            'inserts, updates, and deletes per operation type '
                                            'and reports counts by operation, idempotent on '
                                            'the same change set.',
                                'core_components': [   'merge planner',
                                                       'operation dispatcher',
                                                       'delete applier',
                                                       'per-operation counter'],
                                'common_inputs': [   'collapsed change set',
                                                     'merge policy',
                                                     'target table'],
                                'common_outputs': [   'converged silver table',
                                                      'per-operation counts',
                                                      'merge receipt'],
                                'known_pitfalls': [   'ignoring deletes',
                                                      'non-atomic apply leaving a partial '
                                                      'state',
                                                      'merging an unordered change set'],
                                'success_signals': [   're-applying the same change set '
                                                       'changes no rows',
                                                       'the target matches the source after '
                                                       'apply']},
        'source_ref_families': [   'change-data-capture and log-based replication patterns',
                                   'Delta Lake documentation',
                                   'dbt incremental materialization documentation'],
        'risk_class': 'high',
        'human_review_required': True},
    {   'family_id': 'prim:dewh.soft_delete_apply',
        'domain': 'data_engineering_wh',
        'title': 'Soft Delete Apply',
        'input_edge': 'CDCChangeSet+MergePolicy',
        'output_edge': 'SilverTable+MergeReceipt',
        'blackbox': {   'does': 'Applies delete operations from a change set as a soft delete, '
                                'setting a deleted flag and delete timestamp on matched rows '
                                'rather than physically removing them.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['warehouse.table', 'lakehouse.table', 'dbt.model'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:mcp_tool',
                                           'wrap:queue_worker',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job'],
        'applicable_data_formats': ['rows', 'parquet'],
        'proof_requirements': [   'idempotency_test',
                                  'unique_key_test',
                                  'row_count_reconciliation'],
        'problem_solution': {   'problem': 'Deletes must be reflected while keeping history '
                                           'queryable, so removed keys should be flagged '
                                           'deleted rather than dropped, without hiding '
                                           'still-active rows.',
                                'naive_agent_failure': 'An agent overwrites the whole row on a '
                                                       'soft delete and loses the prior '
                                                       'attribute values that history queries '
                                                       'still need.',
                                'solution': 'A soft-delete merge that sets a deleted flag and '
                                            'timestamp on matched keys, preserves the last '
                                            'attribute values, and is idempotent on the same '
                                            'deletes.',
                                'core_components': [   'delete-operation selector',
                                                       'flag-and-timestamp setter',
                                                       'active-row preserver'],
                                'common_inputs': [   'cdc change set',
                                                     'merge policy',
                                                     'target table'],
                                'common_outputs': [   'flagged silver table',
                                                      'soft-deleted count',
                                                      'merge receipt'],
                                'known_pitfalls': [   'physically dropping rows',
                                                      'overwriting attributes on delete',
                                                      'not filtering deleted rows in active '
                                                      'views'],
                                'success_signals': [   'deleted rows carry a flag and '
                                                       'timestamp',
                                                       're-applying the same deletes flips no '
                                                       'additional rows']},
        'source_ref_families': [   'change-data-capture and log-based replication patterns',
                                   'dbt incremental materialization documentation',
                                   'data-engineering pipeline patterns'],
        'risk_class': 'medium',
        'human_review_required': True},
    {   'family_id': 'prim:dewh.cdc_bootstrap_snapshot',
        'domain': 'data_engineering_wh',
        'title': 'CDC Bootstrap Snapshot',
        'input_edge': 'RawSourceTable+MaterializationPolicy',
        'output_edge': 'BronzeTable+ModelRunReceipt',
        'blackbox': {   'does': 'Takes a one-time consistent full snapshot of a source table '
                                'to seed a target before the ongoing change stream is applied, '
                                'recording the snapshot boundary position.'},
        'effects': ['database_read', 'database_write', 'file_read', 'file_write'],
        'base_runtime_targets': ['warehouse.table', 'lakehouse.table', 'spark.job'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['rows', 'parquet'],
        'proof_requirements': [   'schema_validation',
                                  'row_count_reconciliation',
                                  'idempotency_test'],
        'problem_solution': {   'problem': 'Before applying an incremental change stream, the '
                                           'target must be seeded with a full consistent copy '
                                           'of the source and the exact log position of that '
                                           'copy must be known.',
                                'naive_agent_failure': 'An agent snapshots the source and '
                                                       'starts the stream from now, leaving a '
                                                       'gap of changes that happened during '
                                                       'the snapshot.',
                                'solution': 'A bootstrap that reads a consistent full snapshot '
                                            'at a pinned source position and records that '
                                            'boundary so the stream resumes exactly where the '
                                            'snapshot ended.',
                                'core_components': [   'consistent snapshot reader',
                                                       'boundary-position recorder',
                                                       'full-load writer'],
                                'common_inputs': [   'source table',
                                                     'materialization policy',
                                                     'snapshot position'],
                                'common_outputs': [   'seeded bronze table',
                                                      'snapshot boundary position',
                                                      'model run receipt'],
                                'known_pitfalls': [   'gap between snapshot and stream start',
                                                      'inconsistent snapshot under concurrent '
                                                      'writes',
                                                      'unknown boundary position'],
                                'success_signals': [   'the stream resumes at the recorded '
                                                       'snapshot boundary',
                                                       'no change is lost or double-applied '
                                                       'across the handoff']},
        'source_ref_families': [   'change-data-capture and log-based replication patterns',
                                   'Delta Lake documentation',
                                   'data-engineering pipeline patterns'],
        'risk_class': 'medium',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.idempotent_upsert',
        'domain': 'data_engineering_wh',
        'title': 'Idempotent Upsert',
        'input_edge': 'StagingTable+MergePolicy',
        'output_edge': 'SilverTable+MergeReceipt',
        'blackbox': {   'does': 'Upserts staging rows into a target keyed on a unique business '
                                'key, inserting new keys and updating existing ones so that '
                                're-running the same batch leaves the target unchanged.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['warehouse.table', 'lakehouse.table', 'dbt.model'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:mcp_tool',
                                           'wrap:queue_worker',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job'],
        'applicable_data_formats': ['rows', 'parquet'],
        'proof_requirements': [   'idempotency_test',
                                  'unique_key_test',
                                  'row_count_reconciliation'],
        'problem_solution': {   'problem': 'A load must be safe to retry after a partial '
                                           'failure, so applying the same staging batch twice '
                                           'must produce exactly the same target as applying '
                                           'it once.',
                                'naive_agent_failure': 'An agent inserts unconditionally, so a '
                                                       'retry duplicates every row because '
                                                       'there is no key-based match on the '
                                                       'target.',
                                'solution': 'An upsert keyed on the unique business key that '
                                            'updates matched rows and inserts unmatched rows, '
                                            'making a repeat of the same batch a no-op.',
                                'core_components': [   'unique-key matcher',
                                                       'update-on-match',
                                                       'insert-on-miss',
                                                       'change counter'],
                                'common_inputs': ['staging rows', 'merge policy', 'unique key'],
                                'common_outputs': [   'upserted silver table',
                                                      'inserted and updated counts',
                                                      'merge receipt'],
                                'known_pitfalls': [   'unconditional insert on retry',
                                                      'non-unique merge key updating many rows',
                                                      'partial upsert leaving a mixed state'],
                                'success_signals': [   're-running the same batch changes zero '
                                                       'rows',
                                                       'each business key appears once in the '
                                                       'target']},
        'source_ref_families': [   'dbt incremental materialization documentation',
                                   'Delta Lake documentation',
                                   'Apache Iceberg documentation'],
        'risk_class': 'medium',
        'human_review_required': True},
    {   'family_id': 'prim:dewh.merge_into_upsert',
        'domain': 'data_engineering_wh',
        'title': 'Merge-Into Upsert',
        'input_edge': 'StagingTable+MergePolicy',
        'output_edge': 'SilverTable+MergeReceipt',
        'blackbox': {   'does': 'Executes a single atomic merge-into statement matching source '
                                'to target on a key, applying matched updates and unmatched '
                                'inserts in one transaction with a merge receipt.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['lakehouse.table', 'warehouse.table', 'spark.job'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:mcp_tool',
                                           'wrap:queue_worker',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job'],
        'applicable_data_formats': ['rows', 'parquet'],
        'proof_requirements': [   'idempotency_test',
                                  'unique_key_test',
                                  'row_count_reconciliation'],
        'problem_solution': {   'problem': 'Update and insert must be applied atomically '
                                           'against a large target so a reader never sees a '
                                           'half-applied batch and the merge key does not '
                                           'match multiple targets.',
                                'naive_agent_failure': 'An agent runs a delete then an insert '
                                                       'in two statements, so a concurrent '
                                                       'reader between them sees the target '
                                                       'missing rows.',
                                'solution': 'A single merge-into that matches on the key and '
                                            'applies updates and inserts atomically, guarded '
                                            'against a source key matching more than one '
                                            'target row.',
                                'core_components': [   'merge condition builder',
                                                       'matched-update clause',
                                                       'unmatched-insert clause',
                                                       'multi-match guard'],
                                'common_inputs': [   'staging source rows',
                                                     'merge policy',
                                                     'match key'],
                                'common_outputs': [   'merged silver table',
                                                      'matched and inserted counts',
                                                      'merge receipt'],
                                'known_pitfalls': [   'source key matching multiple target '
                                                      'rows',
                                                      'non-atomic delete-then-insert window',
                                                      'unguarded merge cardinality error'],
                                'success_signals': [   'the merge applies in one atomic commit',
                                                       're-running the merge changes no rows']},
        'source_ref_families': [   'Delta Lake documentation',
                                   'Apache Iceberg documentation',
                                   'dbt incremental materialization documentation'],
        'risk_class': 'medium',
        'human_review_required': True},
    {   'family_id': 'prim:dewh.exactly_once_merge',
        'domain': 'data_engineering_wh',
        'title': 'Exactly-Once Merge',
        'input_edge': 'CDCChangeSet+MergePolicy',
        'output_edge': 'SilverTable+MergeReceipt',
        'blackbox': {   'does': 'Merges a change set while deduplicating on an idempotency key '
                                'recorded in the target so that redelivered or replayed '
                                'operations are applied at most once.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['warehouse.table', 'lakehouse.table', 'stream.consumer'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:queue_worker',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job'],
        'applicable_data_formats': ['rows', 'parquet'],
        'proof_requirements': [   'idempotency_test',
                                  'unique_key_test',
                                  'row_count_reconciliation'],
        'problem_solution': {   'problem': 'At-least-once delivery means the same operation '
                                           'can arrive more than once, and the merge must '
                                           'apply each unique operation exactly one time.',
                                'naive_agent_failure': 'An agent merges every delivered '
                                                       'operation, so a redelivered event is '
                                                       'applied twice and a counter or balance '
                                                       'drifts.',
                                'solution': "A merge that records each applied operation's "
                                            'idempotency key in the target and skips any '
                                            'operation whose key is already present.',
                                'core_components': [   'idempotency-key store',
                                                       'already-applied filter',
                                                       'keyed merge applier'],
                                'common_inputs': [   'change set',
                                                     'merge policy',
                                                     'idempotency key'],
                                'common_outputs': [   'merged silver table',
                                                      'skipped-duplicate count',
                                                      'merge receipt'],
                                'known_pitfalls': [   'reapplying redelivered operations',
                                                      'idempotency key not persisted',
                                                      'key collision across unrelated '
                                                      'operations'],
                                'success_signals': [   'redelivering an operation applies it '
                                                       'zero additional times',
                                                       'each idempotency key appears once in '
                                                       'the target']},
        'source_ref_families': [   'change-data-capture and log-based replication patterns',
                                   'Delta Lake documentation',
                                   'data-engineering pipeline patterns'],
        'risk_class': 'medium',
        'human_review_required': True},
    {   'family_id': 'prim:dewh.incremental_append_dedupe',
        'domain': 'data_engineering_wh',
        'title': 'Incremental Append And Dedupe',
        'input_edge': 'StagingTable+DedupePolicy',
        'output_edge': 'SilverTable+MergeReceipt',
        'blackbox': {   'does': 'Runs a dbt-style incremental build that filters to new source '
                                'rows since the last run, deduplicates on the unique key, and '
                                'merges only the new keys into the target.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['warehouse.table', 'dbt.model', 'lakehouse.table'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:queue_worker',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['rows', 'parquet'],
        'proof_requirements': [   'idempotency_test',
                                  'unique_key_test',
                                  'row_count_reconciliation'],
        'problem_solution': {   'problem': 'An incremental model must process only rows '
                                           'arrived since the last run and still keep exactly '
                                           'one row per unique key when a source resends a '
                                           'record.',
                                'naive_agent_failure': 'An agent filters incrementally but '
                                                       'skips dedupe, so a resent record '
                                                       'produces two rows for the same key in '
                                                       'the incremental target.',
                                'solution': 'An incremental strategy that selects new rows by '
                                            'the incremental predicate, deduplicates within '
                                            'the batch, and merges on the unique key.',
                                'core_components': [   'incremental predicate',
                                                       'batch deduper',
                                                       'unique-key merge'],
                                'common_inputs': [   'staging rows',
                                                     'dedupe policy',
                                                     'incremental column and unique key'],
                                'common_outputs': [   'incremental silver table',
                                                      'merged key count',
                                                      'merge receipt'],
                                'known_pitfalls': [   'missing dedupe on resent rows',
                                                      'incremental predicate missing late rows',
                                                      'full refresh silently overwriting '
                                                      'history'],
                                'success_signals': [   'one row per unique key after each '
                                                       'incremental run',
                                                       're-running the same window changes no '
                                                       'rows']},
        'source_ref_families': [   'dbt incremental materialization documentation',
                                   'Delta Lake documentation',
                                   'data-engineering pipeline patterns'],
        'risk_class': 'medium',
        'human_review_required': True},
    {   'family_id': 'prim:dewh.delete_insert_refresh',
        'domain': 'data_engineering_wh',
        'title': 'Delete-Insert Partition Refresh',
        'input_edge': 'StagingTable+IncrementalPolicy',
        'output_edge': 'SilverTable+ModelRunReceipt',
        'blackbox': {   'does': 'Refreshes a bounded set of partitions by deleting their '
                                'existing rows and inserting the freshly computed rows in one '
                                'transaction, replacing only the targeted partitions.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['warehouse.table', 'lakehouse.table', 'dbt.model'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['rows', 'parquet'],
        'proof_requirements': [   'row_count_reconciliation',
                                  'idempotency_test',
                                  'schema_validation'],
        'problem_solution': {   'problem': 'When a recomputation can change many rows within '
                                           'known partitions, those partitions must be fully '
                                           'replaced without disturbing partitions outside the '
                                           'refresh window.',
                                'naive_agent_failure': 'An agent deletes the whole table '
                                                       'before inserting, wiping partitions '
                                                       'that were not part of the refresh '
                                                       'window.',
                                'solution': 'A scoped delete-then-insert bounded to the target '
                                            'partitions inside one transaction, so only those '
                                            'partitions are replaced and the rest are '
                                            'untouched.',
                                'core_components': [   'partition-scope resolver',
                                                       'scoped delete',
                                                       'insert of recomputed rows',
                                                       'transaction wrapper'],
                                'common_inputs': [   'recomputed staging rows',
                                                     'incremental policy',
                                                     'target partitions'],
                                'common_outputs': [   'refreshed silver table',
                                                      'replaced-partition list',
                                                      'model run receipt'],
                                'known_pitfalls': [   'deleting beyond the refresh window',
                                                      'non-transactional gap exposing empty '
                                                      'partitions',
                                                      'partition predicate mismatch'],
                                'success_signals': [   'only the targeted partitions change',
                                                       're-running the refresh yields the same '
                                                       'partition contents']},
        'source_ref_families': [   'dbt incremental materialization documentation',
                                   'Delta Lake documentation',
                                   'Apache Iceberg documentation'],
        'risk_class': 'high',
        'human_review_required': True},
    {   'family_id': 'prim:dewh.insert_overwrite_partition',
        'domain': 'data_engineering_wh',
        'title': 'Insert-Overwrite Partition',
        'input_edge': 'StagingTable+PartitionPolicy',
        'output_edge': 'SilverTable+ModelRunReceipt',
        'blackbox': {   'does': 'Atomically overwrites the specific partitions present in the '
                                'staging batch with the staged rows, leaving all other '
                                'partitions of the target untouched.'},
        'effects': ['database_read', 'database_write', 'file_read', 'file_write'],
        'base_runtime_targets': ['lakehouse.table', 'spark.job', 'warehouse.table'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['parquet', 'rows'],
        'proof_requirements': [   'row_count_reconciliation',
                                  'idempotency_test',
                                  'schema_validation'],
        'problem_solution': {   'problem': 'A recompute produces the full contents of certain '
                                           'partitions and must swap them in atomically, '
                                           'without a dynamic overwrite accidentally clearing '
                                           'unrelated partitions.',
                                'naive_agent_failure': 'An agent runs a static overwrite that '
                                                       'replaces the entire table when only a '
                                                       'few partitions were recomputed.',
                                'solution': 'A dynamic partition overwrite scoped to the '
                                            'partition values present in the batch, swapping '
                                            'just those partitions in one atomic operation.',
                                'core_components': [   'partition-value detector',
                                                       'dynamic overwrite mode',
                                                       'atomic partition swap'],
                                'common_inputs': [   'staging rows',
                                                     'partition policy',
                                                     'partition columns'],
                                'common_outputs': [   'overwritten silver table',
                                                      'overwritten-partition list',
                                                      'model run receipt'],
                                'known_pitfalls': [   'static overwrite clearing the whole '
                                                      'table',
                                                      'partitions in the batch not matching '
                                                      'the target scheme',
                                                      'non-atomic swap exposing empty '
                                                      'partitions'],
                                'success_signals': [   'only partitions present in the batch '
                                                       'are replaced',
                                                       're-running the same batch yields '
                                                       'identical partitions']},
        'source_ref_families': [   'Delta Lake documentation',
                                   'Apache Iceberg documentation',
                                   'Apache Spark documentation'],
        'risk_class': 'high',
        'human_review_required': True},
    {   'family_id': 'prim:dewh.watermark_incremental_extract',
        'domain': 'data_engineering_wh',
        'title': 'Watermark Incremental Extract',
        'input_edge': 'RawSourceTable+IncrementalPolicy',
        'output_edge': 'StagingTable+ModelRunReceipt',
        'blackbox': {   'does': 'Extracts only source rows whose change column exceeds the '
                                'stored watermark, using an inclusive lower bound with overlap '
                                'so boundary rows are never missed.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['warehouse.table', 'stream.consumer', 'local.python'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:mcp_tool',
                                           'wrap:queue_worker',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job'],
        'applicable_data_formats': ['rows', 'parquet'],
        'proof_requirements': [   'row_count_reconciliation',
                                  'idempotency_test',
                                  'schema_validation'],
        'problem_solution': {   'problem': 'Only rows changed since the last extract should be '
                                           'pulled, but a strict boundary can skip rows '
                                           'sharing the watermark timestamp under clock or '
                                           'commit skew.',
                                'naive_agent_failure': 'An agent filters strictly greater than '
                                                       'the watermark, so rows with the exact '
                                                       'boundary timestamp are silently '
                                                       'skipped forever.',
                                'solution': 'An extract with an inclusive lower bound and a '
                                            'small overlap window that re-pulls boundary rows, '
                                            'relying on a downstream dedupe to absorb the '
                                            'overlap.',
                                'core_components': [   'watermark reader',
                                                       'overlap-window predicate',
                                                       'boundary-inclusive filter'],
                                'common_inputs': [   'source table',
                                                     'incremental policy',
                                                     'stored watermark'],
                                'common_outputs': [   'incremental staging table',
                                                      'extracted range',
                                                      'model run receipt'],
                                'known_pitfalls': [   'strict boundary skipping tied '
                                                      'timestamps',
                                                      'watermark advanced before load '
                                                      'succeeded',
                                                      'clock skew across sources'],
                                'success_signals': [   'no changed row is skipped at the '
                                                       'boundary',
                                                       'the extracted range is recorded in the '
                                                       'receipt']},
        'source_ref_families': [   'dbt incremental materialization documentation',
                                   'change-data-capture and log-based replication patterns',
                                   'data-engineering pipeline patterns'],
        'risk_class': 'medium',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.checkpoint_watermark_advance',
        'domain': 'data_engineering_wh',
        'title': 'Checkpoint Watermark Advance',
        'input_edge': 'StagingTable+IncrementalPolicy',
        'output_edge': 'ModelRunReceipt',
        'blackbox': {   'does': 'Advances the stored watermark to the maximum successfully '
                                'processed change value only after a load commits, so a failed '
                                'load never moves the watermark forward.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['warehouse.table', 'local.python', 'stream.consumer'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:mcp_tool',
                                           'wrap:queue_worker',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job'],
        'applicable_data_formats': ['rows', 'json_object'],
        'proof_requirements': ['idempotency_test', 'contract_test'],
        'problem_solution': {   'problem': 'The watermark must move forward exactly to the '
                                           'last committed change so the next extract neither '
                                           'reprocesses old rows nor skips uncommitted ones.',
                                'naive_agent_failure': 'An agent advances the watermark before '
                                                       'the load commits, so a subsequent '
                                                       'failure loses every row between the '
                                                       'old and new watermark.',
                                'solution': 'A commit-ordered advance that computes the max '
                                            'processed value from the committed batch and only '
                                            'then persists the new watermark, recording old '
                                            'and new values.',
                                'core_components': [   'max-processed computer',
                                                       'commit-after-load ordering',
                                                       'watermark persister'],
                                'common_inputs': [   'committed staging batch',
                                                     'incremental policy',
                                                     'current watermark'],
                                'common_outputs': [   'advanced watermark',
                                                      'old and new values',
                                                      'model run receipt'],
                                'known_pitfalls': [   'advancing before commit',
                                                      'advancing past uncommitted rows',
                                                      'non-monotonic watermark going '
                                                      'backwards'],
                                'success_signals': [   'watermark only advances after a '
                                                       'durable load',
                                                       'a failed load leaves the watermark '
                                                       'unchanged']},
        'source_ref_families': [   'dbt incremental materialization documentation',
                                   'change-data-capture and log-based replication patterns',
                                   'data-engineering pipeline patterns'],
        'risk_class': 'medium',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.backfill_window',
        'domain': 'data_engineering_wh',
        'title': 'Bounded Backfill Window',
        'input_edge': 'RawSourceTable+IncrementalPolicy',
        'output_edge': 'StagingTable+ModelRunReceipt',
        'blackbox': {   'does': 'Reprocesses a bounded historical time window from the source '
                                'into staging on demand, without disturbing the live watermark '
                                'used by the ongoing incremental load.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['warehouse.table', 'spark.job', 'local.python'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['rows', 'parquet'],
        'proof_requirements': [   'row_count_reconciliation',
                                  'idempotency_test',
                                  'schema_validation'],
        'problem_solution': {   'problem': 'A historical correction requires reprocessing a '
                                           'specific past window, and it must not move or '
                                           'reset the live watermark that the normal '
                                           'incremental depends on.',
                                'naive_agent_failure': 'An agent resets the shared watermark '
                                                       'to run a backfill, so the ongoing '
                                                       'incremental reprocesses everything '
                                                       'after that point.',
                                'solution': 'A backfill that reads a bounded start-to-end '
                                            'window into staging as a separate run, leaving '
                                            'the live watermark untouched for the normal '
                                            'pipeline.',
                                'core_components': [   'window-bound resolver',
                                                       'range reader',
                                                       'watermark isolation'],
                                'common_inputs': [   'source table',
                                                     'incremental policy',
                                                     'backfill window bounds'],
                                'common_outputs': [   'backfilled staging table',
                                                      'processed window',
                                                      'model run receipt'],
                                'known_pitfalls': [   'resetting the shared watermark',
                                                      'unbounded backfill window',
                                                      'overlapping a running incremental load'],
                                'success_signals': [   'the live watermark is unchanged by the '
                                                       'backfill',
                                                       'only rows within the requested window '
                                                       'are reprocessed']},
        'source_ref_families': [   'dbt incremental materialization documentation',
                                   'data-engineering pipeline patterns',
                                   'Delta Lake documentation'],
        'risk_class': 'medium',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.late_arriving_data_reconcile',
        'domain': 'data_engineering_wh',
        'title': 'Late-Arriving Data Reconcile',
        'input_edge': 'StagingTable+MergePolicy',
        'output_edge': 'SilverTable+MergeReceipt',
        'blackbox': {   'does': 'Merges records that arrived after their event-time partition '
                                'was built into the correct historical partitions, updating '
                                'affected aggregates and reporting touched partitions.'},
        'effects': ['database_read', 'database_write', 'file_read', 'file_write'],
        'base_runtime_targets': ['warehouse.table', 'lakehouse.table', 'spark.job'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['rows', 'parquet'],
        'proof_requirements': [   'idempotency_test',
                                  'row_count_reconciliation',
                                  'unique_key_test'],
        'problem_solution': {   'problem': 'Events sometimes arrive after their event-time '
                                           'partition has already been processed, so they must '
                                           'be routed to the correct past partition rather '
                                           'than the arrival day.',
                                'naive_agent_failure': 'An agent writes late events into the '
                                                       'current partition by processing time, '
                                                       'so historical partitions and their '
                                                       'aggregates stay wrong.',
                                'solution': 'A reconcile that keys late rows by event time, '
                                            'merges them into the correct historical '
                                            'partitions, and recomputes the affected partition '
                                            'aggregates.',
                                'core_components': [   'event-time router',
                                                       'historical-partition merger',
                                                       'affected-aggregate recomputer',
                                                       'touched-partition reporter'],
                                'common_inputs': [   'late staging rows',
                                                     'merge policy',
                                                     'event-time column'],
                                'common_outputs': [   'reconciled silver table',
                                                      'touched partitions',
                                                      'merge receipt'],
                                'known_pitfalls': [   'placing late rows by arrival time',
                                                      'not recomputing dependent aggregates',
                                                      'double-counting a late row on re-run'],
                                'success_signals': [   'late rows land in their event-time '
                                                       'partition',
                                                       're-running the reconcile changes no '
                                                       'counts']},
        'source_ref_families': [   'data-engineering pipeline patterns',
                                   'Delta Lake documentation',
                                   'dbt incremental materialization documentation'],
        'risk_class': 'high',
        'human_review_required': True},
    {   'family_id': 'prim:dewh.small_file_compaction',
        'domain': 'data_engineering_wh',
        'title': 'Small-File Compaction',
        'input_edge': 'BronzeTable+PartitionPolicy',
        'output_edge': 'BronzeTable+MaterializationReceipt',
        'blackbox': {   'does': 'Rewrites many small data files within targeted partitions '
                                'into fewer right-sized files, preserving the exact row set '
                                'and reporting the file count before and after.'},
        'effects': ['database_read', 'database_write', 'file_read', 'file_write'],
        'base_runtime_targets': ['lakehouse.table', 'spark.job', 'warehouse.table'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['parquet', 'arrow'],
        'proof_requirements': [   'row_count_reconciliation',
                                  'golden_output_test',
                                  'idempotency_test'],
        'problem_solution': {   'problem': 'Streaming and frequent loads produce many tiny '
                                           'files that slow reads, so files must be compacted '
                                           'into larger ones without changing any row.',
                                'naive_agent_failure': 'An agent rewrites files but reorders '
                                                       'or drops rows, so the compacted table '
                                                       'no longer matches the original '
                                                       'contents.',
                                'solution': 'A bin-packing compaction that rewrites small '
                                            'files into target-sized files within a partition '
                                            'scope, verifying the row set is byte-for-value '
                                            'identical.',
                                'core_components': [   'small-file selector',
                                                       'bin-packing rewriter',
                                                       'row-set verifier',
                                                       'file-count reporter'],
                                'common_inputs': [   'bronze table files',
                                                     'partition policy',
                                                     'target file size'],
                                'common_outputs': [   'compacted bronze table',
                                                      'file counts before and after',
                                                      'materialization receipt'],
                                'known_pitfalls': [   'dropping or reordering rows',
                                                      'compacting an actively written '
                                                      'partition',
                                                      'target file size mismatched to reads'],
                                'success_signals': [   'row set is unchanged after compaction',
                                                       're-running compaction rewrites '
                                                       'nothing']},
        'source_ref_families': [   'Delta Lake documentation',
                                   'Apache Iceberg documentation',
                                   'Apache Spark documentation'],
        'risk_class': 'medium',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.zorder_cluster_optimize',
        'domain': 'data_engineering_wh',
        'title': 'Cluster Optimize',
        'input_edge': 'SilverTable+PartitionPolicy',
        'output_edge': 'SilverTable+MaterializationReceipt',
        'blackbox': {   'does': "Reorganizes a table's data files to co-locate rows by "
                                'high-cardinality filter columns using a clustering or z-order '
                                'layout, preserving the row set exactly.'},
        'effects': ['database_read', 'database_write', 'file_read', 'file_write'],
        'base_runtime_targets': ['lakehouse.table', 'spark.job', 'warehouse.table'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['parquet', 'arrow'],
        'proof_requirements': [   'row_count_reconciliation',
                                  'golden_output_test',
                                  'idempotency_test'],
        'problem_solution': {   'problem': 'Selective queries scan too many files because '
                                           'related rows are scattered, so files should be '
                                           'reorganized to cluster rows by the columns queries '
                                           'filter on.',
                                'naive_agent_failure': 'An agent clusters on columns that are '
                                                       'rarely filtered, adding rewrite cost '
                                                       'while queries still scan everything.',
                                'solution': 'A layout optimize that clusters files by the '
                                            'declared high-cardinality filter columns, leaving '
                                            'the row set unchanged and recording the layout '
                                            'applied.',
                                'core_components': [   'cluster-column selector',
                                                       'layout rewriter',
                                                       'row-set verifier'],
                                'common_inputs': [   'silver table files',
                                                     'partition policy',
                                                     'cluster columns'],
                                'common_outputs': [   'reclustered silver table',
                                                      'layout description',
                                                      'materialization receipt'],
                                'known_pitfalls': [   'clustering on unfiltered columns',
                                                      'over-frequent reclustering churn',
                                                      'reordering that changes the row set'],
                                'success_signals': [   'row set is unchanged after optimize',
                                                       'files cluster on the declared '
                                                       'columns']},
        'source_ref_families': [   'Delta Lake documentation',
                                   'Apache Iceberg documentation',
                                   'data-engineering pipeline patterns'],
        'risk_class': 'medium',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.optimize_vacuum_retention',
        'domain': 'data_engineering_wh',
        'title': 'Vacuum Retention Cleanup',
        'input_edge': 'SilverTable+PartitionPolicy',
        'output_edge': 'SilverTable+MaterializationReceipt',
        'blackbox': {   'does': 'Permanently removes data files no longer referenced by any '
                                'snapshot within the retention window, reclaiming storage and '
                                'reporting the files deleted.'},
        'effects': ['database_read', 'database_write', 'file_read', 'file_write'],
        'base_runtime_targets': ['lakehouse.table', 'spark.job', 'warehouse.table'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['parquet'],
        'proof_requirements': ['row_count_reconciliation', 'contract_test'],
        'problem_solution': {   'problem': 'Old unreferenced files accumulate and must be '
                                           'removed to reclaim storage, but deleting files '
                                           'still inside the retention window breaks time '
                                           'travel and readers.',
                                'naive_agent_failure': 'An agent vacuums with a zero retention '
                                                       'window and deletes files a concurrent '
                                                       'long-running reader still needs, '
                                                       'causing read failures.',
                                'solution': 'A vacuum that only removes files unreferenced by '
                                            'any live snapshot and older than the retention '
                                            'window, reporting deleted files and honoring the '
                                            'minimum retention.',
                                'core_components': [   'reference tracer',
                                                       'retention-window gate',
                                                       'safe file deleter',
                                                       'deleted-file reporter'],
                                'common_inputs': [   'silver table metadata',
                                                     'partition policy',
                                                     'retention window'],
                                'common_outputs': [   'cleaned silver table',
                                                      'deleted-file list',
                                                      'materialization receipt'],
                                'known_pitfalls': [   'vacuuming inside the retention window',
                                                      'breaking in-flight readers',
                                                      'deleting files still referenced by a '
                                                      'snapshot'],
                                'success_signals': [   'current table contents are unchanged',
                                                       'only unreferenced, out-of-retention '
                                                       'files are removed']},
        'source_ref_families': [   'Delta Lake documentation',
                                   'Apache Iceberg documentation',
                                   'data-engineering pipeline patterns'],
        'risk_class': 'high',
        'human_review_required': True},
    {   'family_id': 'prim:dewh.iceberg_snapshot_expire',
        'domain': 'data_engineering_wh',
        'title': 'Snapshot Expire',
        'input_edge': 'SilverTable+PartitionPolicy',
        'output_edge': 'SilverTable+MaterializationReceipt',
        'blackbox': {   'does': 'Expires table snapshots older than a retention threshold and '
                                'removes the metadata and data files they alone referenced, '
                                'keeping the newest snapshots reachable.'},
        'effects': ['database_read', 'database_write', 'file_read', 'file_write'],
        'base_runtime_targets': ['lakehouse.table', 'spark.job'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['parquet'],
        'proof_requirements': ['row_count_reconciliation', 'contract_test'],
        'problem_solution': {   'problem': 'Snapshot history grows without bound, so old '
                                           'snapshots must be expired to control metadata size '
                                           'while keeping recent versions available for time '
                                           'travel.',
                                'naive_agent_failure': 'An agent expires snapshots more recent '
                                                       'than the retention threshold, '
                                                       'destroying versions that rollback or '
                                                       'audits still need.',
                                'solution': 'A snapshot expiry that keeps snapshots newer than '
                                            'the threshold, removes only files uniquely '
                                            'referenced by expired snapshots, and reports what '
                                            'was expired.',
                                'core_components': [   'snapshot-age evaluator',
                                                       'unique-reference remover',
                                                       'retained-version keeper',
                                                       'expiry reporter'],
                                'common_inputs': [   'table snapshot log',
                                                     'partition policy',
                                                     'retention threshold'],
                                'common_outputs': [   'pruned table history',
                                                      'expired-snapshot list',
                                                      'materialization receipt'],
                                'known_pitfalls': [   'expiring within the retention threshold',
                                                      'removing files shared with a retained '
                                                      'snapshot',
                                                      'leaving orphaned metadata'],
                                'success_signals': [   'snapshots newer than the threshold '
                                                       'remain reachable',
                                                       'current table contents are unchanged']},
        'source_ref_families': [   'Apache Iceberg documentation',
                                   'Delta Lake documentation',
                                   'data-engineering pipeline patterns'],
        'risk_class': 'high',
        'human_review_required': True},
    {   'family_id': 'prim:dewh.manifest_rewrite',
        'domain': 'data_engineering_wh',
        'title': 'Manifest Rewrite',
        'input_edge': 'SilverTable+PartitionPolicy',
        'output_edge': 'SilverTable+MaterializationReceipt',
        'blackbox': {   'does': "Rewrites and compacts a table's metadata manifests so "
                                'planning reads fewer manifest files, without moving or '
                                'changing any underlying data file.'},
        'effects': ['database_read', 'database_write', 'file_read', 'file_write'],
        'base_runtime_targets': ['lakehouse.table', 'spark.job'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['parquet'],
        'proof_requirements': ['row_count_reconciliation', 'idempotency_test'],
        'problem_solution': {   'problem': 'Frequent commits fragment table metadata into many '
                                           'manifest files, slowing query planning even when '
                                           'the data files themselves are fine.',
                                'naive_agent_failure': 'An agent rewrites data files to fix '
                                                       'planning cost when only the metadata '
                                                       'manifests were fragmented, doing far '
                                                       'more work than needed.',
                                'solution': 'A metadata-only manifest rewrite that compacts '
                                            'manifest files and leaves every data file and row '
                                            'untouched, recording manifest counts before and '
                                            'after.',
                                'core_components': [   'manifest fragmentation detector',
                                                       'manifest compactor',
                                                       'data-file untouched verifier'],
                                'common_inputs': ['table metadata', 'partition policy'],
                                'common_outputs': [   'compacted metadata',
                                                      'manifest counts before and after',
                                                      'materialization receipt'],
                                'known_pitfalls': [   'rewriting data files unnecessarily',
                                                      'invalidating snapshot references',
                                                      'changing table contents'],
                                'success_signals': [   'no data file is moved or changed',
                                                       'planning reads fewer manifests after '
                                                       'the rewrite']},
        'source_ref_families': [   'Apache Iceberg documentation',
                                   'Delta Lake documentation',
                                   'data-engineering pipeline patterns'],
        'risk_class': 'low',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.partition_evolution_apply',
        'domain': 'data_engineering_wh',
        'title': 'Partition Spec Evolution',
        'input_edge': 'SilverTable+PartitionPolicy',
        'output_edge': 'SilverTable+MaterializationReceipt',
        'blackbox': {   'does': 'Applies a new partition specification to an existing table so '
                                'future writes use the new layout while existing data remains '
                                'readable under its original partitioning.'},
        'effects': ['database_read', 'database_write', 'file_read', 'file_write'],
        'base_runtime_targets': ['lakehouse.table', 'spark.job'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['parquet'],
        'proof_requirements': ['contract_test', 'row_count_reconciliation', 'roundtrip_test'],
        'problem_solution': {   'problem': 'As data volume grows the partition layout must '
                                           'change, but existing partitions cannot be '
                                           'rewritten cheaply and queries must still read '
                                           'across both layouts.',
                                'naive_agent_failure': 'An agent rewrites the whole table to '
                                                       'change partitioning, incurring a full '
                                                       'rewrite and a long outage instead of '
                                                       'evolving the spec.',
                                'solution': 'A partition-spec evolution that registers the new '
                                            'spec for future writes while old files keep their '
                                            'original spec, so reads span both transparently.',
                                'core_components': [   'new-spec registrar',
                                                       'mixed-spec read planner',
                                                       'backward-read verifier'],
                                'common_inputs': [   'table metadata',
                                                     'partition policy',
                                                     'new partition spec'],
                                'common_outputs': [   'evolved table spec',
                                                      'spec change record',
                                                      'materialization receipt'],
                                'known_pitfalls': [   'forcing a full table rewrite',
                                                      'queries that cannot span two specs',
                                                      'losing readability of old partitions'],
                                'success_signals': [   'existing data stays readable under its '
                                                       'original spec',
                                                       'new writes use the new spec']},
        'source_ref_families': [   'Apache Iceberg documentation',
                                   'data-engineering pipeline patterns',
                                   'Delta Lake documentation'],
        'risk_class': 'high',
        'human_review_required': True},
    {   'family_id': 'prim:dewh.time_travel_restore',
        'domain': 'data_engineering_wh',
        'title': 'Time-Travel Restore',
        'input_edge': 'SilverTable+MaterializationPolicy',
        'output_edge': 'SilverTable+MaterializationReceipt',
        'blackbox': {   'does': 'Restores a table to a prior snapshot or version as a new '
                                'current version, reverting a bad write while retaining the '
                                'intervening history for audit.'},
        'effects': ['database_read', 'database_write', 'file_read', 'file_write'],
        'base_runtime_targets': ['lakehouse.table', 'spark.job'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['parquet', 'rows'],
        'proof_requirements': ['row_count_reconciliation', 'roundtrip_test', 'contract_test'],
        'problem_solution': {   'problem': 'A bad load can corrupt a table, and it must be '
                                           'reverted to a known-good prior version quickly '
                                           'without destroying the record of what happened in '
                                           'between.',
                                'naive_agent_failure': 'An agent deletes rows manually to undo '
                                                       'a bad load, guessing at what changed '
                                                       'and leaving the table in a third, '
                                                       'still-wrong state.',
                                'solution': "A restore that sets the table's current version "
                                            'to a chosen prior snapshot as a new commit, so '
                                            'the revert is exact and the intervening history '
                                            'is preserved.',
                                'core_components': [   'target-version selector',
                                                       'restore-as-new-commit applier',
                                                       'history preserver'],
                                'common_inputs': [   'table snapshot log',
                                                     'materialization policy',
                                                     'target version id'],
                                'common_outputs': [   'restored table',
                                                      'restore commit record',
                                                      'materialization receipt'],
                                'known_pitfalls': [   'manual row surgery instead of restore',
                                                      'restoring to an expired snapshot',
                                                      'discarding intervening history'],
                                'success_signals': [   'current contents match the target '
                                                       'version',
                                                       'the intervening history remains '
                                                       'queryable']},
        'source_ref_families': [   'Delta Lake documentation',
                                   'Apache Iceberg documentation',
                                   'data-engineering pipeline patterns'],
        'risk_class': 'high',
        'human_review_required': True},
    {   'family_id': 'prim:dewh.table_clone_zero_copy',
        'domain': 'data_engineering_wh',
        'title': 'Zero-Copy Table Clone',
        'input_edge': 'SilverTable+MaterializationPolicy',
        'output_edge': 'SilverTable+MaterializationReceipt',
        'blackbox': {   'does': 'Creates a shallow metadata-only clone of a table that shares '
                                'the source data files, giving an isolated writable copy for '
                                'testing without duplicating storage.'},
        'effects': ['database_read', 'database_write', 'file_read'],
        'base_runtime_targets': ['lakehouse.table', 'spark.job'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['parquet'],
        'proof_requirements': [   'roundtrip_test',
                                  'row_count_reconciliation',
                                  'schema_validation'],
        'problem_solution': {   'problem': 'A safe isolated copy of a large table is needed '
                                           'for testing or a what-if, but physically '
                                           'duplicating the data is slow and wastes storage.',
                                'naive_agent_failure': 'An agent deep-copies every file to '
                                                       'make a test copy, taking a long time '
                                                       'and doubling storage for a throwaway.',
                                'solution': 'A shallow clone that copies only metadata and '
                                            'references the existing data files, giving an '
                                            'isolated version whose later writes do not affect '
                                            'the source.',
                                'core_components': [   'metadata cloner',
                                                       'shared-file referencer',
                                                       'clone-isolation verifier'],
                                'common_inputs': [   'source table metadata',
                                                     'materialization policy',
                                                     'clone name'],
                                'common_outputs': [   'cloned table',
                                                      'shared-file reference count',
                                                      'materialization receipt'],
                                'known_pitfalls': [   'deep-copying unnecessarily',
                                                      'clone writes leaking back to the source',
                                                      'source vacuum removing files the clone '
                                                      'shares'],
                                'success_signals': [   'the clone reads identical contents to '
                                                       'the source at clone time',
                                                       'writes to the clone do not change the '
                                                       'source']},
        'source_ref_families': [   'Delta Lake documentation',
                                   'Apache Iceberg documentation',
                                   'data-engineering pipeline patterns'],
        'risk_class': 'low',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.partition_prune_plan',
        'domain': 'data_engineering_wh',
        'title': 'Partition Prune Plan',
        'input_edge': 'SilverTable+PartitionPolicy',
        'output_edge': 'PartitionPlan',
        'blackbox': {   'does': 'Computes which table partitions a query predicate can safely '
                                'skip from catalog statistics and partition metadata, '
                                'producing a prune plan without reading data files.'},
        'effects': ['database_read'],
        'base_runtime_targets': ['lakehouse.table', 'warehouse.table', 'local.python'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:mcp_tool',
                                           'wrap:cron_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['json_object', 'rows'],
        'proof_requirements': ['schema_validation', 'contract_test'],
        'problem_solution': {   'problem': 'A query should read only the partitions its '
                                           'predicate can match, so a prune plan must identify '
                                           'skippable partitions from metadata before any data '
                                           'is scanned.',
                                'naive_agent_failure': 'An agent reads all partitions because '
                                                       'the predicate is not mapped to '
                                                       'partition columns, scanning far more '
                                                       'than necessary.',
                                'solution': 'A pruning planner that maps predicates to '
                                            'partition columns, uses partition statistics to '
                                            'mark non-matching partitions skippable, and emits '
                                            'the plan.',
                                'core_components': [   'predicate-to-partition mapper',
                                                       'statistics evaluator',
                                                       'prune-plan emitter'],
                                'common_inputs': [   'table partition metadata',
                                                     'partition policy',
                                                     'query predicate'],
                                'common_outputs': [   'partition prune plan',
                                                      'skippable-partition list'],
                                'known_pitfalls': [   'predicate not aligned to partition '
                                                      'columns',
                                                      'stale partition statistics',
                                                      'over-pruning a matching partition'],
                                'success_signals': [   'only partitions that can match remain '
                                                       'in the plan',
                                                       'no matching partition is pruned']},
        'source_ref_families': [   'Apache Iceberg documentation',
                                   'Delta Lake documentation',
                                   'data-engineering pipeline patterns'],
        'risk_class': 'low',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.hidden_partition_transform',
        'domain': 'data_engineering_wh',
        'title': 'Hidden Partition Transform',
        'input_edge': 'StagingTable+PartitionPolicy',
        'output_edge': 'PartitionPlan',
        'blackbox': {   'does': 'Derives hidden partition values from source columns using '
                                'declared transforms such as day-of-timestamp or '
                                'bucket-of-key, so writers partition without exposing extra '
                                'columns.'},
        'effects': ['database_read'],
        'base_runtime_targets': ['lakehouse.table', 'local.python', 'spark.job'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:mcp_tool',
                                           'wrap:cron_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['rows', 'json_object'],
        'proof_requirements': ['schema_validation', 'contract_test', 'roundtrip_test'],
        'problem_solution': {   'problem': 'Partitioning should follow a transform of a source '
                                           'column, but forcing queries to filter on a '
                                           'separate derived column is error-prone and easy to '
                                           'forget.',
                                'naive_agent_failure': 'An agent materializes a redundant '
                                                       'partition column and queries that '
                                                       'filter only the base column then fail '
                                                       'to prune.',
                                'solution': 'A hidden partition transform that derives the '
                                            'partition value from the base column via a '
                                            'declared function so queries filtering the base '
                                            'column still prune.',
                                'core_components': [   'transform-function resolver',
                                                       'derived-value computer',
                                                       'prune-mapping emitter'],
                                'common_inputs': [   'staging rows',
                                                     'partition policy',
                                                     'partition transform'],
                                'common_outputs': [   'partition plan',
                                                      'derived partition mapping'],
                                'known_pitfalls': [   'redundant derived column breaking '
                                                      'pruning',
                                                      'transform mismatch between write and '
                                                      'read',
                                                      'non-deterministic transform'],
                                'success_signals': [   'queries filtering the base column '
                                                       'prune correctly',
                                                       'the same input maps to the same '
                                                       'partition value']},
        'source_ref_families': [   'Apache Iceberg documentation',
                                   'data-engineering pipeline patterns',
                                   'Delta Lake documentation'],
        'risk_class': 'low',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.schema_evolution_apply',
        'domain': 'data_engineering_wh',
        'title': 'Schema Evolution Apply',
        'input_edge': 'BronzeTable+SchemaSpec',
        'output_edge': 'BronzeTable+ContractReport',
        'blackbox': {   'does': 'Applies an additive, backward-compatible schema change such '
                                'as a new nullable column or a widened type, and reports the '
                                'change while rejecting breaking alterations.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['lakehouse.table', 'warehouse.table', 'dbt.model'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:mcp_tool',
                                           'wrap:queue_worker',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job'],
        'applicable_data_formats': ['parquet', 'rows'],
        'proof_requirements': ['schema_validation', 'contract_test', 'roundtrip_test'],
        'problem_solution': {   'problem': 'Source schemas change over time and the table must '
                                           'absorb additive changes automatically while '
                                           'blocking changes that would break existing '
                                           'readers.',
                                'naive_agent_failure': 'An agent applies any incoming schema '
                                                       'change, including a narrowing type or '
                                                       'dropped column, and silently breaks '
                                                       'downstream consumers.',
                                'solution': 'An evolution applier that permits additive and '
                                            'widening changes, refuses narrowing or drops '
                                            'without review, and reports every change it '
                                            'applied.',
                                'core_components': [   'change classifier',
                                                       'additive-change applier',
                                                       'breaking-change blocker',
                                                       'change reporter'],
                                'common_inputs': [   'current table schema',
                                                     'schema spec',
                                                     'incoming schema'],
                                'common_outputs': [   'evolved table',
                                                      'applied-change list',
                                                      'contract report'],
                                'known_pitfalls': [   'applying a narrowing change',
                                                      'reordering columns',
                                                      'dropping a column readers depend on'],
                                'success_signals': [   'existing readers keep working after '
                                                       'the change',
                                                       'breaking changes are rejected with a '
                                                       'reason']},
        'source_ref_families': [   'Delta Lake documentation',
                                   'Apache Iceberg documentation',
                                   'data contract specification patterns'],
        'risk_class': 'medium',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.data_contract_enforce',
        'domain': 'data_engineering_wh',
        'title': 'Data Contract Enforce',
        'input_edge': 'StagingTable+DataContract',
        'output_edge': 'SilverTable+ContractReport',
        'blackbox': {   'does': 'Validates a staging table against a data contract covering '
                                'schema, nullability, ranges, and allowed values, passing '
                                'conforming rows and reporting every violation.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['warehouse.table', 'lakehouse.table', 'dbt.model'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:queue_worker',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['rows', 'parquet'],
        'proof_requirements': [   'contract_test',
                                  'schema_validation',
                                  'row_count_reconciliation'],
        'problem_solution': {   'problem': 'A producer and consumer agree on a contract, and '
                                           'every load must be checked against it so '
                                           'violations are caught at the boundary rather than '
                                           'downstream.',
                                'naive_agent_failure': 'An agent checks only column names and '
                                                       'lets out-of-range or null-in-required '
                                                       'values pass, so bad data corrupts '
                                                       'downstream models.',
                                'solution': 'A contract enforcer that checks schema, '
                                            'nullability, ranges, and enumerations, admits '
                                            'conforming rows, and emits a violation report by '
                                            'rule.',
                                'core_components': [   'contract loader',
                                                       'multi-rule validator',
                                                       'conforming-row gate',
                                                       'violation reporter'],
                                'common_inputs': ['staging rows', 'data contract'],
                                'common_outputs': [   'conforming silver table',
                                                      'violation report'],
                                'known_pitfalls': [   'checking only names not values',
                                                      'passing nulls in required fields',
                                                      'silent range violations'],
                                'success_signals': [   'only conforming rows reach silver',
                                                       'every violation is reported with its '
                                                       'rule']},
        'source_ref_families': [   'data contract specification patterns',
                                   'dbt incremental materialization documentation',
                                   'data-engineering pipeline patterns'],
        'risk_class': 'medium',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.quarantine_bad_rows',
        'domain': 'data_engineering_wh',
        'title': 'Quarantine Bad Rows',
        'input_edge': 'StagingTable+DataContract',
        'output_edge': 'QuarantineTable+ContractReport',
        'blackbox': {   'does': 'Splits a staging table against a contract into a passing set '
                                'and a quarantine set, tagging each quarantined row with its '
                                'failed rule so the good data keeps flowing.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['warehouse.table', 'lakehouse.table', 'dbt.model'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:mcp_tool',
                                           'wrap:queue_worker',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job'],
        'applicable_data_formats': ['rows', 'parquet'],
        'proof_requirements': [   'contract_test',
                                  'row_count_reconciliation',
                                  'schema_validation'],
        'problem_solution': {   'problem': 'A few bad rows should not fail an entire load, so '
                                           'violating rows must be diverted to a quarantine '
                                           'with their reason while valid rows proceed.',
                                'naive_agent_failure': 'An agent fails the whole batch on the '
                                                       'first bad row, blocking good data, or '
                                                       'drops bad rows with no record of why.',
                                'solution': 'A split that routes conforming rows onward and '
                                            'diverts violating rows to a quarantine table '
                                            'tagged with the failed rule and count by rule.',
                                'core_components': [   'row validator',
                                                       'pass-fail splitter',
                                                       'reason tagger',
                                                       'quarantine writer'],
                                'common_inputs': ['staging rows', 'data contract'],
                                'common_outputs': [   'quarantine table',
                                                      'passing row count',
                                                      'contract report'],
                                'known_pitfalls': [   'failing the whole batch on one bad row',
                                                      'dropping bad rows without a reason',
                                                      'quarantine growing unmonitored'],
                                'success_signals': [   'passing plus quarantined equals the '
                                                       'input count',
                                                       'each quarantined row carries its '
                                                       'failed rule']},
        'source_ref_families': [   'data contract specification patterns',
                                   'data-engineering pipeline patterns',
                                   'dbt incremental materialization documentation'],
        'risk_class': 'medium',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.dead_letter_reprocess',
        'domain': 'data_engineering_wh',
        'title': 'Dead-Letter Reprocess',
        'input_edge': 'QuarantineTable+MergePolicy',
        'output_edge': 'SilverTable+MergeReceipt',
        'blackbox': {   'does': 'Re-validates quarantined rows after a fix and merges the '
                                'now-conforming rows into the target, leaving still-failing '
                                'rows in quarantine with an incremented attempt count.'},
        'effects': ['database_read', 'database_write'],
        'base_runtime_targets': ['warehouse.table', 'lakehouse.table', 'queue.worker'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:queue_worker',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job'],
        'applicable_data_formats': ['rows', 'parquet'],
        'proof_requirements': ['idempotency_test', 'row_count_reconciliation', 'contract_test'],
        'problem_solution': {   'problem': 'Rows quarantined for a fixable reason must be '
                                           'retried after the fix and merged in, without '
                                           'reprocessing rows that still fail or '
                                           'double-applying ones that pass.',
                                'naive_agent_failure': 'An agent re-runs the whole quarantine '
                                                       'and re-merges rows that were already '
                                                       'recovered on a prior pass, duplicating '
                                                       'them.',
                                'solution': 'A reprocess that re-validates quarantined rows, '
                                            'merges the passing ones idempotently, and '
                                            'increments an attempt counter on those that still '
                                            'fail.',
                                'core_components': [   're-validator',
                                                       'idempotent merge of recovered rows',
                                                       'attempt-count incrementer',
                                                       'still-failing retainer'],
                                'common_inputs': [   'quarantine table',
                                                     'merge policy',
                                                     'updated contract'],
                                'common_outputs': [   'merged silver table',
                                                      'recovered and remaining counts',
                                                      'merge receipt'],
                                'known_pitfalls': [   're-merging already-recovered rows',
                                                      'losing the failure reason on retry',
                                                      'unbounded retries without a cap'],
                                'success_signals': [   'recovered rows merge exactly once',
                                                       'still-failing rows remain quarantined '
                                                       'with a higher attempt count']},
        'source_ref_families': [   'data-engineering pipeline patterns',
                                   'dbt incremental materialization documentation',
                                   'data contract specification patterns'],
        'risk_class': 'medium',
        'human_review_required': True},
    {   'family_id': 'prim:dewh.data_contract_publish',
        'domain': 'data_engineering_wh',
        'title': 'Data Contract Publish',
        'input_edge': 'SilverTable+SchemaSpec',
        'output_edge': 'DataContract+ContractReport',
        'blackbox': {   'does': 'Derives a versioned data contract from a table and a schema '
                                'spec, capturing columns, types, nullability, and key '
                                'constraints so consumers can validate against it.'},
        'effects': ['database_read', 'artifact_write'],
        'base_runtime_targets': ['warehouse.table', 'lakehouse.table', 'local.python'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['json_object', 'rows'],
        'proof_requirements': ['schema_validation', 'contract_test'],
        'problem_solution': {   'problem': 'Consumers need an explicit, versioned contract for '
                                           'a producer table, yet contracts are often stale '
                                           'documents that drift from the table they describe.',
                                'naive_agent_failure': 'An agent hand-writes a contract that '
                                                       'omits nullability and keys, so '
                                                       'consumers validate against an '
                                                       'incomplete shape and still break.',
                                'solution': 'A publisher that reads the table plus schema spec '
                                            'and emits a versioned contract with columns, '
                                            'types, nullability, and keys as an artifact.',
                                'core_components': [   'schema introspector',
                                                       'constraint extractor',
                                                       'contract-version stamper',
                                                       'artifact writer'],
                                'common_inputs': ['silver table', 'schema spec'],
                                'common_outputs': [   'published data contract',
                                                      'contract report'],
                                'known_pitfalls': [   'contract drifting from the table',
                                                      'omitting nullability or keys',
                                                      'unversioned contract overwrites'],
                                'success_signals': [   'the published contract matches the '
                                                       'current table shape',
                                                       'each publish carries a distinct '
                                                       'version']},
        'source_ref_families': [   'data contract specification patterns',
                                   'data-engineering pipeline patterns',
                                   'dbt incremental materialization documentation'],
        'risk_class': 'low',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.row_count_reconciliation',
        'domain': 'data_engineering_wh',
        'title': 'Row-Count Reconciliation',
        'input_edge': 'RecordSetA+RecordSetB',
        'output_edge': 'RowCountReconcileReport',
        'blackbox': {   'does': 'Compares row counts between a source and a target set at the '
                                'whole-table and per-partition level and reports any '
                                'discrepancy beyond the configured tolerance.'},
        'effects': ['database_read'],
        'base_runtime_targets': ['warehouse.table', 'lakehouse.table', 'local.python'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:mcp_tool',
                                           'wrap:cron_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['rows', 'json_object'],
        'proof_requirements': ['row_count_reconciliation', 'contract_test'],
        'problem_solution': {   'problem': 'A load can silently lose or duplicate rows, so '
                                           'source and target counts must be reconciled '
                                           'overall and per partition to detect drift early.',
                                'naive_agent_failure': 'An agent compares only total counts, '
                                                       'so a partition that gained rows and '
                                                       'another that lost the same number net '
                                                       'to zero and hide the error.',
                                'solution': 'A reconciliation that compares counts at the '
                                            'table and partition grain, flags any '
                                            'per-partition gap past tolerance, and reports the '
                                            'differences.',
                                'core_components': [   'count aggregator',
                                                       'partition-grain comparator',
                                                       'tolerance evaluator',
                                                       'discrepancy reporter'],
                                'common_inputs': [   'source record set',
                                                     'target record set',
                                                     'partition grain and tolerance'],
                                'common_outputs': [   'reconciliation report',
                                                      'per-partition differences'],
                                'known_pitfalls': [   'comparing only totals',
                                                      'ignoring partition-level offsets that '
                                                      'net out',
                                                      'tolerance masking real drift'],
                                'success_signals': [   'per-partition counts reconcile within '
                                                       'tolerance',
                                                       'any discrepancy is reported with its '
                                                       'partition']},
        'source_ref_families': [   'data-engineering pipeline patterns',
                                   'dbt incremental materialization documentation',
                                   'data reconciliation patterns'],
        'risk_class': 'low',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.source_freshness_check',
        'domain': 'data_engineering_wh',
        'title': 'Source Freshness Check',
        'input_edge': 'RawSourceTable+SourceFreshnessPolicy',
        'output_edge': 'FreshnessReport',
        'blackbox': {   'does': 'Measures the age of the newest loaded record against warn and '
                                'error thresholds and reports whether a source is fresh, '
                                'stale, or breached before dependent models run.'},
        'effects': ['database_read'],
        'base_runtime_targets': ['warehouse.table', 'lakehouse.table', 'local.python'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:mcp_tool',
                                           'wrap:cron_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['rows', 'json_object'],
        'proof_requirements': ['contract_test', 'schema_validation'],
        'problem_solution': {   'problem': 'Downstream models should not run on stale inputs, '
                                           'so the age of the newest source record must be '
                                           'checked against thresholds before builds proceed.',
                                'naive_agent_failure': 'An agent trusts that a source loaded '
                                                       'and builds on data that is hours stale '
                                                       'because a broken upstream job left it '
                                                       'frozen.',
                                'solution': 'A freshness check that reads the newest load '
                                            'timestamp, compares it to warn and error '
                                            'thresholds, and reports a fresh, warn, or error '
                                            'status.',
                                'core_components': [   'max-timestamp reader',
                                                       'threshold comparator',
                                                       'status reporter'],
                                'common_inputs': [   'source table',
                                                     'source freshness policy',
                                                     'warn and error thresholds'],
                                'common_outputs': ['freshness report', 'source status'],
                                'known_pitfalls': [   'using load time instead of event time '
                                                      'when required',
                                                      'no threshold configured',
                                                      'timezone skew inflating age'],
                                'success_signals': [   'stale sources are flagged before '
                                                       'dependents build',
                                                       'the reported age matches the newest '
                                                       'record']},
        'source_ref_families': [   'dbt incremental materialization documentation',
                                   'data-engineering pipeline patterns',
                                   'data observability patterns'],
        'risk_class': 'low',
        'human_review_required': False},
    {   'family_id': 'prim:dewh.lineage_capture',
        'domain': 'data_engineering_wh',
        'title': 'Lineage Capture',
        'input_edge': 'SilverTable+MaterializationPolicy',
        'output_edge': 'LineageReceipt',
        'blackbox': {   'does': 'Records the upstream inputs, transform identity, and produced '
                                'outputs of a model run as a lineage receipt so downstream '
                                'impact and provenance can be traced.'},
        'effects': ['database_read', 'artifact_write'],
        'base_runtime_targets': ['warehouse.table', 'lakehouse.table', 'local.python'],
        'applicable_runtime_wrappers': [   'wrap:python_function',
                                           'wrap:cron_job',
                                           'wrap:kubernetes_job',
                                           'wrap:github_action'],
        'applicable_data_formats': ['json_object', 'rows'],
        'proof_requirements': ['schema_validation', 'contract_test'],
        'problem_solution': {   'problem': 'When a column is wrong, teams need to know which '
                                           'inputs and transform produced it and what depends '
                                           'on it, which requires captured lineage per run.',
                                'naive_agent_failure': 'An agent leaves lineage implicit in '
                                                       'code, so tracing a bad value means '
                                                       'manually reading every model to guess '
                                                       'its inputs.',
                                'solution': "A lineage capture that records the run's declared "
                                            'inputs, transform id, and outputs into a receipt, '
                                            'building a traceable input-to-output graph.',
                                'core_components': [   'input recorder',
                                                       'transform identifier',
                                                       'output recorder',
                                                       'lineage-receipt writer'],
                                'common_inputs': [   'model run inputs',
                                                     'materialization policy',
                                                     'transform id'],
                                'common_outputs': ['lineage receipt', 'input-to-output edges'],
                                'known_pitfalls': [   'implicit undeclared inputs',
                                                      'missing column-level detail',
                                                      'lineage diverging from actual reads'],
                                'success_signals': [   'every output traces to its declared '
                                                       'inputs',
                                                       'the receipt matches the inputs the run '
                                                       'actually read']},
        'source_ref_families': [   'data observability patterns',
                                   'data-engineering pipeline patterns',
                                   'dbt incremental materialization documentation'],
        'risk_class': 'low',
        'human_review_required': False}]
