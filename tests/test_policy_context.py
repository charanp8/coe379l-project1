from atlas_agent.agent_models import ToolCallDecision
from atlas_agent.models import ToolObservation, TraceEvent
from atlas_agent.policy_context import build_reservation_context


def event(step, tool, arguments, data):
    return TraceEvent(
        step=step,
        decision={"kind": "tool_call", "tool": tool, "arguments": arguments},
        observation=ToolObservation(ok=True, tool=tool, data=data),
        mutating=False,
    )


def test_supplied_context_builder_collects_trace_facts():
    interval = {"start": "2026-10-15T10:00:00", "end": "2026-10-15T11:00:00"}
    trace = [
        event(1, "search_lab_documents", {"query": "policy"}, {"passages": []}),
        event(
            2,
            "get_user_authorizations",
            {"user_id": "alice"},
            {
                "projects": ["polymer-study"],
                "qualifications": ["lab_safety"],
                "approvals": [],
            },
        ),
        event(
            3,
            "get_resource_status",
            {"resource_id": "tensile-01", **interval},
            {
                "kind": "tensile_tester",
                "available": True,
                "calibration_current": True,
                "maintenance": False,
            },
        ),
    ]
    decision = ToolCallDecision(
        kind="tool_call",
        tool="reserve_resource",
        arguments={
            "user_id": "alice",
            "project_id": "polymer-study",
            "resource_id": "tensile-01",
            **interval,
        },
        reasoning_summary="All checks have completed.",
    )
    context = build_reservation_context(decision, trace)
    assert all(context.model_dump().values())
