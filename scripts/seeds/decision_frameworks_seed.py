"""Seed data for decision frameworks: reusable typed DAGs of decision forks.

Each framework declares initial_state_keys, goal_state_keys, and the ordered
forks whose state contracts (consumes/produces) chain to reach the goal. The
builder injects record_type, version, candidate=True, serves_truth=False. The
checker validates that the fork order composes by the wave rule (every consumed
key produced by the initial state or an earlier fork) and reaches the goal, so a
decision framework is a proven control-flow scaffold, not a wish.
"""

DECISION_FRAMEWORKS = [
    {
        "framework_id": "dframework:solve",
        "problem": "Solve a stated problem end to end by retrieving primitives, wiring a validated order, and executing it.",
        "initial_state_keys": ["problem_intent", "want_type", "have", "want", "effect_profile"],
        "goal_state_keys": ["execution_result"],
        "forks": [
            "decision:retrieval.plane_selection",
            "decision:orchestration.ordering_strategy",
            "decision:solve.execution_target",
        ],
    },
]
