"""Seed rows for reusable-primitive families that fill genuine producer gaps
surfaced by the route-compiler gap queue: string similarity, entity-resolution
blocking and link-graph assembly, and CRM batch import.

Pure data module: one top-level constant FAMILIES (list of dicts). The builder
(scripts/build_universal_primitive_pack.py) injects record_type, version,
candidate=True, serves_truth=False and crosses each family with its applicable
wrappers. Ports reuse the existing vocabulary so these families both PRODUCE the
types earlier targets wanted (SimilarityScore, CandidatePair, LinkGraph,
CrmImportReceipt) and compose with the entity-resolution chain already in the
bank (candidate_block -> comparison_vector_emit -> probabilistic_match_score
-> [adapter match_score_to_set] -> link_graph_assemble). Config ports end in
Policy so they never block composition. No unmeasured claims. Every row stays
candidate=true / serves_truth=false.
"""

FAMILIES = [
    {
        "family_id": "prim:sim.string_similarity",
        "domain": "similarity_indexing",
        "title": "String Similarity Score",
        "input_edge": "ShortText+ShortText+SimilarityPolicy",
        "output_edge": "SimilarityScore+SimilarityReceipt",
        "blackbox": {
            "does": "Scores how similar two short strings are on a chosen measure (token Jaccard, edit distance, or Jaro-Winkler) into a normalized similarity in the unit interval."
        },
        "effects": ["none"],
        "base_runtime_targets": ["local.python", "library.call"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:cli_command",
        ],
        "applicable_data_formats": ["json", "text"],
        "proof_requirements": ["schema_validation", "unit_range_test"],
        "problem_solution": {
            "problem": "Comparing two short strings for a match needs a normalized, symmetric similarity score, not an ad-hoc equality check that misses near-duplicates.",
            "naive_agent_failure": "An agent compares strings with exact equality and treats 'Acme Inc' and 'ACME, Inc.' as unrelated, missing an obvious match.",
            "solution": "A similarity step that applies a declared measure, normalizes to the unit interval, and is symmetric in its two inputs.",
            "core_components": ["measure selector", "normalizer", "symmetry guarantee"],
            "common_inputs": ["two short strings", "similarity measure policy"],
            "common_outputs": ["similarity score in [0,1]", "chosen measure"],
            "known_pitfalls": ["an unnormalized raw distance", "asymmetric scoring", "case or punctuation defeating the measure"],
            "success_signals": ["identical strings score 1", "the score is symmetric in the inputs"],
        },
        "source_ref_families": ["string similarity measures (Jaccard, edit distance, Jaro-Winkler)"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:er.candidate_block",
        "domain": "entity_resolution",
        "title": "Entity Resolution Candidate Blocking",
        "input_edge": "RawEntityRecordSet+BlockingPolicy",
        "output_edge": "CandidatePair+BlockingReceipt",
        "blackbox": {
            "does": "Groups an entity record set into blocks by a blocking key and emits only the within-block candidate pairs, so comparison runs on a tractable subset instead of the full quadratic cross product."
        },
        "effects": ["database_read", "database_write"],
        "base_runtime_targets": ["local.python", "warehouse.table"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:queue_worker",
            "wrap:kubernetes_job",
        ],
        "applicable_data_formats": ["rows", "parquet"],
        "proof_requirements": ["schema_validation", "block_coverage_test"],
        "problem_solution": {
            "problem": "Entity resolution cannot compare every pair of records at scale, so it must first block records into groups where a match is plausible and only compare within blocks.",
            "naive_agent_failure": "An agent compares all record pairs and the run explodes quadratically, or blocks so aggressively that true matches land in different blocks and are never compared.",
            "solution": "A blocking step that derives a blocking key, groups records, and emits within-block candidate pairs with a coverage report.",
            "core_components": ["blocking-key deriver", "block grouper", "within-block pair emitter"],
            "common_inputs": ["entity record set", "blocking key policy"],
            "common_outputs": ["candidate pairs", "block assignment", "coverage report"],
            "known_pitfalls": ["over-blocking that separates true matches", "under-blocking that keeps the pair count quadratic", "a blocking key with poor selectivity"],
            "success_signals": ["candidate pairs are a small fraction of the full cross product", "known matches share a block"],
        },
        "source_ref_families": ["entity resolution blocking / indexing techniques"],
        "risk_class": "low",
        "human_review_required": False,
    },
    {
        "family_id": "prim:er.link_graph_assemble",
        "domain": "entity_resolution",
        "title": "Link Graph Assemble From Match Scores",
        "input_edge": "MatchScoreSet+LinkPolicy",
        "output_edge": "LinkGraph+LinkReceipt",
        "blackbox": {
            "does": "Thresholds a set of pairwise match scores into accepted links and assembles the transitive clusters into a link graph of resolved entities, guarding against contradictory transitive merges."
        },
        "effects": ["database_read", "database_write"],
        "base_runtime_targets": ["local.python", "warehouse.table"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:mcp_tool", "wrap:queue_worker",
            "wrap:kubernetes_job",
        ],
        "applicable_data_formats": ["rows", "parquet", "json"],
        "proof_requirements": ["schema_validation", "transitive_consistency_test"],
        "problem_solution": {
            "problem": "Pairwise match scores must be resolved into entity clusters, but naive transitive closure can chain weak links into one giant wrong cluster.",
            "naive_agent_failure": "An agent takes the transitive closure of every above-threshold pair and merges distinct entities through a chain of weak links.",
            "solution": "An assemble step that thresholds scores into accepted links and forms clusters with a consistency guard against contradictory merges.",
            "core_components": ["score thresholder", "cluster former", "transitive-consistency guard"],
            "common_inputs": ["match score set", "link threshold and clustering policy"],
            "common_outputs": ["link graph of clusters", "accepted and rejected links", "cluster sizes"],
            "known_pitfalls": ["runaway transitive chaining", "threshold too low merging distinct entities", "ignoring must-not-link constraints"],
            "success_signals": ["clusters respect must-not-link constraints", "no cluster forms only through sub-threshold links"],
        },
        "source_ref_families": ["entity resolution clustering / correlation clustering"],
        "risk_class": "medium",
        "human_review_required": False,
    },
    {
        "family_id": "prim:crud.crm_batch_import",
        "domain": "crud_data_app",
        "title": "CRM Batch Import",
        "input_edge": "RawCustomerRecordBatch+ImportPolicy",
        "output_edge": "CrmImportReceipt",
        "blackbox": {
            "does": "Validates, dedupes, and upserts a batch of raw customer records into a CRM, returning an import receipt of created, updated, skipped, and rejected counts with per-record status."
        },
        "effects": ["database_read", "database_write"],
        "base_runtime_targets": ["local.python", "api.endpoint"],
        "applicable_runtime_wrappers": [
            "wrap:python_function", "wrap:fastapi_endpoint", "wrap:queue_worker",
            "wrap:cron_job",
        ],
        "applicable_data_formats": ["rows", "json"],
        "proof_requirements": ["schema_validation", "idempotency_test"],
        "problem_solution": {
            "problem": "Importing a batch of customer records into a CRM must validate, dedupe, and upsert idempotently, or a retried import creates duplicate contacts.",
            "naive_agent_failure": "An agent inserts every row blindly, so a retried batch doubles the contacts and corrupts the CRM.",
            "solution": "An import step that validates and dedupes on a natural key, upserts idempotently, and returns a receipt of created/updated/skipped/rejected counts.",
            "core_components": ["record validator", "dedupe-on-key", "idempotent upsert", "status reporter"],
            "common_inputs": ["raw customer record batch", "import and matching policy"],
            "common_outputs": ["import receipt", "per-record status", "created/updated/skipped/rejected counts"],
            "known_pitfalls": ["duplicate contacts on retry", "overwriting a richer record with a sparse one", "silently dropping rejected rows"],
            "success_signals": ["re-running the same batch changes nothing", "every input row has a disclosed status"],
        },
        "source_ref_families": ["CRM upsert / idempotent batch import patterns"],
        "risk_class": "medium",
        "human_review_required": False,
    },
]
