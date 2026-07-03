"""Seed data for the decision-portfolio substrate: three structurally DISSIMILAR
decision points, each owning a portfolio of contract-substitutable execution
paths. The point of picking unlike decisions is to prove ONE engine drives all
of them from data alone - runtime retrieval, a runtime remix ladder, and a
development (CI) decision.

Pure data: two top-level constants DECISION_POINTS and EXECUTION_PATHS. The
builder (scripts/build_decision_portfolio_pack.py) injects record_type, version,
candidate=True, serves_truth=False. Every path's decision_id references a real
decision; every decision's default_path references one of its paths (the pack
checker enforces both). candidate=true / serves_truth=false throughout.
"""

DECISION_POINTS = [
    {
        "decision_id": "decision:retrieval.plane_selection",
        "title": "Retrieval plane selection",
        "question": "Which retrieval plane(s) best answer this intent - lexical, typed-edge, or fused?",
        "regime": "runtime",
        "context_signature": ["want_type_known"],
        "contract": {
            "input": "natural-language intent (+ optional wanted output type)",
            "output": "ranked node_ids",
            "win_definition": "target primitive appears in top-k (hit@k)",
        },
        "selection_policy": "argmax_receipts",
        "default_path": "path:retrieval.lexical_only",
        "execute_all_when_cheap": True,
    },
    {
        "decision_id": "decision:remix.escalation",
        "title": "Remix escalation ladder",
        "question": "How to bridge a near-match to the needed contract - deterministic mutator, adapter, or bounded model?",
        "regime": "runtime",
        "context_signature": ["diff_kind"],
        "contract": {
            "input": "a candidate primitive + the contract diff to the target",
            "output": "a bridged primitive/route that satisfies the target contract",
            "win_definition": "bridge applies and its proofs pass with least cost / risk",
        },
        "selection_policy": "deterministic_tier",
        "default_path": "path:remix.bounded_model",
        "execute_all_when_cheap": False,
    },
    {
        "decision_id": "decision:dev.proof_stage_order",
        "title": "Proof-stage ordering (development)",
        "question": "In what order should run_proofs execute its stages to surface a failure soonest at least cost?",
        "regime": "development",
        "context_signature": ["changed_lane"],
        "contract": {
            "input": "the set of proof stages + what changed",
            "output": "an ordering (and early-exit policy) for the stages",
            "win_definition": "a real failure is surfaced at the least wall-clock / compute",
        },
        "selection_policy": "cheapest_that_proves",
        "default_path": "path:dev.fail_fast_cheap",
        "execute_all_when_cheap": False,
    },
]

EXECUTION_PATHS = [
    # ---- decision:retrieval.plane_selection ----
    {
        "path_id": "path:retrieval.lexical_only",
        "decision_id": "decision:retrieval.plane_selection",
        "title": "Lexical only",
        "method": "IDF token overlap over title/edges/lane; always applicable, no type needed",
        "applicability": {"requires_keys": [], "conditions": []},
        "cost_model": {"tokens": 0, "latency_ms": 5, "side_effect_risk": "none", "build_effort": "low"},
        "reversibility": "reversible", "preference_rank": 0, "deterministic": True,
        "handler_ref": "primitives.decision_handlers:retrieval_lexical",
        "expected_receipts": ["hit_at_k", "reciprocal_rank"],
    },
    {
        "path_id": "path:retrieval.typed_edge",
        "decision_id": "decision:retrieval.plane_selection",
        "title": "Typed-edge only",
        "method": "producers of the wanted canonical type (edge-truth), deterministic order, no lexical",
        "applicability": {"requires_keys": ["want_type_known"],
                          "conditions": [{"key": "want_type_known", "op": "truthy"}]},
        "cost_model": {"tokens": 0, "latency_ms": 6, "side_effect_risk": "none", "build_effort": "low"},
        "reversibility": "reversible", "preference_rank": 1, "deterministic": True,
        "handler_ref": "primitives.decision_handlers:retrieval_typed_edge",
        "expected_receipts": ["hit_at_k", "reciprocal_rank"],
    },
    {
        "path_id": "path:retrieval.lexical_plus_typed",
        "decision_id": "decision:retrieval.plane_selection",
        "title": "Fused (lexical + typed-edge)",
        "method": "IDF lexical fused with typed-edge blocking-key bonus for producers of the wanted type",
        "applicability": {"requires_keys": ["want_type_known"],
                          "conditions": [{"key": "want_type_known", "op": "truthy"}]},
        "cost_model": {"tokens": 0, "latency_ms": 8, "side_effect_risk": "none", "build_effort": "medium"},
        "reversibility": "reversible", "preference_rank": 2, "deterministic": True,
        "handler_ref": "primitives.decision_handlers:retrieval_fused",
        "expected_receipts": ["hit_at_k", "reciprocal_rank"],
    },
    # ---- decision:remix.escalation ----
    {
        "path_id": "path:remix.deterministic_mutator",
        "decision_id": "decision:remix.escalation",
        "title": "Deterministic mutator",
        "method": "a pure format/route mutator (field_rename, wide_to_long, ...) with a roundtrip proof; zero tokens",
        "applicability": {"requires_keys": ["diff_kind"],
                          "conditions": [{"key": "diff_kind", "op": "in", "value": ["format", "rename", "reshape", "project"]}]},
        "cost_model": {"tokens": 0, "latency_ms": 3, "side_effect_risk": "none", "build_effort": "low"},
        "reversibility": "reversible", "preference_rank": 0, "deterministic": True,
        "handler_ref": "primitives.mutators:field_rename",
        "expected_receipts": ["proof_pass", "lossless"],
    },
    {
        "path_id": "path:remix.type_adapter",
        "decision_id": "decision:remix.escalation",
        "title": "Type adapter",
        "method": "a reviewed deterministic FromPort->ToPort adapter node with a fixture proof",
        "applicability": {"requires_keys": ["diff_kind"],
                          "conditions": [{"key": "diff_kind", "op": "in", "value": ["envelope", "project", "wrap", "reshape"]}]},
        "cost_model": {"tokens": 0, "latency_ms": 4, "side_effect_risk": "low", "build_effort": "medium"},
        "reversibility": "reversible", "preference_rank": 1, "deterministic": True,
        "handler_ref": "primitives.type_adapters:webhook_request_to_provider_webhook",
        "expected_receipts": ["proof_pass", "disclosed_lossiness"],
    },
    {
        "path_id": "path:remix.bounded_model",
        "decision_id": "decision:remix.escalation",
        "title": "Bounded model glue",
        "method": "a bounded model call proposes the missing edge; deterministic compiler disposes; candidate until proven",
        "applicability": {"requires_keys": [], "conditions": []},
        "cost_model": {"tokens": 600, "latency_ms": 900, "side_effect_risk": "medium", "build_effort": "low"},
        "reversibility": "reversible", "preference_rank": 2, "deterministic": False,
        "expected_receipts": ["proof_pass", "human_review"],
        "revival_trigger": "no deterministic mutator or adapter covers the contract diff",
    },
    # ---- decision:dev.proof_stage_order ----
    {
        "path_id": "path:dev.fail_fast_cheap",
        "decision_id": "decision:dev.proof_stage_order",
        "title": "Fail-fast cheapest-first",
        "method": "order stages by ascending cost, stop on first failure - surfaces a break soonest",
        "applicability": {"requires_keys": [], "conditions": []},
        "cost_model": {"tokens": 0, "latency_ms": 200, "side_effect_risk": "none", "build_effort": "low"},
        "reversibility": "reversible", "preference_rank": 0, "deterministic": True,
        "expected_receipts": ["time_to_first_failure"],
    },
    {
        "path_id": "path:dev.full_parallel",
        "decision_id": "decision:dev.proof_stage_order",
        "title": "Full parallel",
        "method": "run every stage regardless - complete signal, higher compute",
        "applicability": {"requires_keys": [], "conditions": []},
        "cost_model": {"tokens": 0, "latency_ms": 1200, "side_effect_risk": "none", "build_effort": "low"},
        "reversibility": "reversible", "preference_rank": 1, "deterministic": True,
        "expected_receipts": ["total_wall_clock", "complete_signal"],
    },
    {
        "path_id": "path:dev.dependency_topo",
        "decision_id": "decision:dev.proof_stage_order",
        "title": "Dependency-topological, changed-lane first",
        "method": "run stages touching the changed lane first, then their dependents",
        "applicability": {"requires_keys": ["changed_lane"],
                          "conditions": [{"key": "changed_lane", "op": "exists"}]},
        "cost_model": {"tokens": 0, "latency_ms": 400, "side_effect_risk": "none", "build_effort": "medium"},
        "reversibility": "reversible", "preference_rank": 2, "deterministic": True,
        "expected_receipts": ["time_to_first_failure", "changed_lane_covered"],
    },
]
