"""Seed rows for the type-adapter connector layer.

Pure data module: one top-level constant ADAPTERS (list of dicts). Each row is a
reviewed, deterministic bridge FromPort -> ToPort, backed by a real
implementation in primitives/type_adapters.py whose proofs the checker runs. The
builder (scripts/build_type_adapters_pack.py) injects record_type, version,
candidate=True, and serves_truth=False. Rows carry reviewed=True because an
adapter is a curated equivalence, not a heuristic.

input_edge is the single from_port; output_edge is to_port + AdapterReceipt so
the capability-graph node produces the target data port plus an evidence
receipt. transform_kind and lossiness disclose the reshape; lossy adapters name
what they drop in blackbox.does and their implementation emits fields_dropped.

Why adapters instead of widening the canonical-type buckets: each adapter is one
auditable node, so an adapter-mediated route shows the bridge as an explicit
step (the route compiler labels the step kind). Distinct artifacts never merge
silently - a reviewer added each of these on purpose, backed by a proof.
"""

ADAPTERS = [
    {
        "adapter_id": "adapt:webhook_request_to_provider_webhook",
        "title": "Webhook HTTP Request to Provider Webhook",
        "from_port": "WebhookHttpRequest",
        "to_port": "ProviderWebhook",
        "input_edge": "WebhookHttpRequest",
        "output_edge": "ProviderWebhook+AdapterReceipt",
        "transform_kind": "rename_envelope",
        "lossiness": "lossless",
        "blackbox": {
            "does": "Reads the provider identity from the X-Webhook-Provider header and carries method, headers, and body verbatim into a typed provider-webhook envelope."
        },
        "effects": ["none"],
        "proof_requirements": ["schema_validation", "provider_identified", "roundtrip_test"],
        "implementation_ref": "primitives.type_adapters:webhook_request_to_provider_webhook",
        "reviewed": True,
    },
    {
        "adapter_id": "adapt:auth_decision_to_authenticated_subject",
        "title": "Auth Decision to Authenticated Subject",
        "from_port": "AuthDecision",
        "to_port": "AuthenticatedSubject",
        "input_edge": "AuthDecision",
        "output_edge": "AuthenticatedSubject+AdapterReceipt",
        "transform_kind": "project_subset",
        "lossiness": "lossy",
        "blackbox": {
            "does": "Exposes the authenticated subject carried by a positive (allow) auth decision; a deny decision has no subject and fails the gate. Drops and discloses decision metadata."
        },
        "effects": ["none"],
        "proof_requirements": ["schema_validation", "allow_decision_gate", "subject_preserved"],
        "implementation_ref": "primitives.type_adapters:auth_decision_to_authenticated_subject",
        "reviewed": True,
    },
    {
        "adapter_id": "adapt:session_grant_to_token",
        "title": "Session Grant to Session Token",
        "from_port": "SessionGrant",
        "to_port": "SessionToken",
        "input_edge": "SessionGrant",
        "output_edge": "SessionToken+AdapterReceipt",
        "transform_kind": "project_subset",
        "lossiness": "lossy",
        "blackbox": {
            "does": "Extracts the bearer token string from a session grant record, dropping and disclosing grant metadata (expiry, scope) that the token itself does not carry."
        },
        "effects": ["none"],
        "proof_requirements": ["schema_validation", "token_present", "token_preserved"],
        "implementation_ref": "primitives.type_adapters:session_grant_to_token",
        "reviewed": True,
    },
    {
        "adapter_id": "adapt:match_score_to_set",
        "title": "Match Score to Match Score Set",
        "from_port": "MatchScore",
        "to_port": "MatchScoreSet",
        "input_edge": "MatchScore",
        "output_edge": "MatchScoreSet+AdapterReceipt",
        "transform_kind": "wrap_singleton",
        "lossiness": "lossless",
        "blackbox": {
            "does": "Wraps a single pair match score into a singleton match-score set so a set-consuming primitive (clustering, linkage) can accept a one-pair result; the inverse takes the sole element."
        },
        "effects": ["none"],
        "proof_requirements": ["schema_validation", "score_in_unit_range", "roundtrip_test"],
        "implementation_ref": "primitives.type_adapters:match_score_to_set",
        "reviewed": True,
    },
    {
        "adapter_id": "adapt:entity_records_to_rows",
        "title": "Entity Record Set to Row Set",
        "from_port": "EntityRecordSet",
        "to_port": "RowSet",
        "input_edge": "EntityRecordSet",
        "output_edge": "RowSet+AdapterReceipt",
        "transform_kind": "reshape_structural",
        "lossiness": "lossless",
        "blackbox": {
            "does": "Pivots a set of entity records into a columns+rows table, backed by the tested json_records_to_rows mutator; lossless modulo the disclosed missing-key to null normalization."
        },
        "effects": ["none"],
        "proof_requirements": ["schema_validation", "column_coverage", "roundtrip_test"],
        "implementation_ref": "primitives.type_adapters:entity_records_to_rows",
        "reviewed": True,
    },
    {
        "adapter_id": "adapt:entity_records_to_geojson_points",
        "title": "Entity Record Set to Point Feature Collection",
        "from_port": "EntityRecordSet",
        "to_port": "PointFeatureCollection",
        "input_edge": "EntityRecordSet",
        "output_edge": "PointFeatureCollection+AdapterReceipt",
        "transform_kind": "coordinate_reproject",
        "lossiness": "lossless",
        "blackbox": {
            "does": "Lifts lat/lon-bearing entity records into a GeoJSON FeatureCollection of Points in [lon,lat] order, backed by the tested records_to_geojson_points mutator; the inverse rebuilds the records."
        },
        "effects": ["none"],
        "proof_requirements": ["schema_validation", "coordinate_range_check", "roundtrip_test"],
        "implementation_ref": "primitives.type_adapters:entity_records_to_geojson_points",
        "reviewed": True,
    },
]
