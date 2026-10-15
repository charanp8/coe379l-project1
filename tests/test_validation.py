from atlas_agent.agent_models import ToolCallDecision
from atlas_agent.models import AgentResponse, LabRequest, ToolObservation, TraceEvent
from atlas_agent.policy_context import ReservationContext
from atlas_agent.validation import (
    validate_final_response,
    validate_request_binding,
    validate_reservation_preconditions,
)


def test_request_binding_rejects_identity_and_project_substitution():
    request = LabRequest(
        authenticated_user_id="alice",
        text="Reserve tensile-01 for polymer-study.",
        project_id="polymer-study",
        resource_id="tensile-01",
    )
    decision = ToolCallDecision(
        kind="tool_call",
        tool="reserve_resource",
        arguments={
            "user_id": "bob",
            "project_id": "different-project",
            "resource_id": "tensile-01",
        },
        reasoning_summary="Propose a reservation.",
    )
    errors = validate_request_binding(decision, request=request)
    assert "user_id_must_match_authenticated_user" in errors
    assert "project_id_does_not_match_request" in errors


def test_request_binding_rejects_reservation_when_request_is_unresolved():
    request = LabRequest(authenticated_user_id="alice", text="Reserve it tomorrow.")
    decision = ToolCallDecision(
        kind="tool_call",
        tool="reserve_resource",
        arguments={
            "user_id": "alice",
            "project_id": "polymer-study",
            "resource_id": "tensile-01",
            "start": "2026-10-15T10:00:00",
            "end": "2026-10-15T11:00:00",
        },
        reasoning_summary="Guess the missing fields.",
    )
    errors = validate_request_binding(decision, request=request)
    assert "project_id_unresolved_in_request" in errors
    assert "start_unresolved_in_request" in errors


def test_reservation_preconditions_report_false_facts():
    context = ReservationContext(
        arguments_complete=True,
        policy_retrieved=True,
        authorizations_checked=True,
        resource_status_checked=True,
        project_authorized=True,
        qualification_current=False,
        resource_available=True,
        calibration_current=False,
        maintenance_clear=True,
        after_hours_approval_satisfied=True,
    )
    errors = validate_reservation_preconditions(context)
    assert errors == ["required_qualification_missing", "calibration_not_current"]


def test_unretrieved_citation_is_rejected():
    response = AgentResponse(
        status="blocked",
        message="Policy prevents the action.",
        citations=["MADE-UP#passage"],
    )
    errors = validate_final_response(response, [])
    assert errors
    assert errors[0].startswith("citations_not_retrieved")


def test_failed_mutation_cannot_be_claimed_as_completed():
    trace = [
        TraceEvent(
            step=1,
            decision={"kind": "tool_call", "tool": "reserve_resource", "arguments": {}},
            observation=ToolObservation(
                ok=False,
                tool="reserve_resource",
                error_code="reservation_conflict",
            ),
            mutating=True,
        )
    ]
    response = AgentResponse(
        status="completed",
        message="Reserved.",
        completed_actions=["reserve_resource"],
    )
    errors = validate_final_response(response, trace)
    assert "completed_action_not_in_successful_trace" in errors
    assert "completed_without_successful_mutation" in errors
