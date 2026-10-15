from atlas_agent.agent_models import (
    ClarificationDecision,
    DecisionAdapter,
    FinalDecision,
    ToolCallDecision,
)


def test_discriminated_decision_union():
    tool = DecisionAdapter.validate_python(
        {
            "kind": "tool_call",
            "tool": "get_user_authorizations",
            "arguments": {"user_id": "alice"},
            "reasoning_summary": "Check the authenticated user's permissions.",
        }
    )
    assert isinstance(tool, ToolCallDecision)

    clarification = DecisionAdapter.validate_python(
        {
            "kind": "clarification",
            "question": "What exact end time should I use?",
            "missing_fields": ["end"],
        }
    )
    assert isinstance(clarification, ClarificationDecision)

    final = DecisionAdapter.validate_python(
        {
            "kind": "final",
            "response": {
                "status": "blocked",
                "message": "The request cannot be completed.",
            },
        }
    )
    assert isinstance(final, FinalDecision)

    schema = DecisionAdapter.json_schema()
    assert schema["discriminator"]["propertyName"] == "kind"
