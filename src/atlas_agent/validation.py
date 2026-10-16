"""Safety and consistency checks applied to model-proposed decisions."""

from __future__ import annotations

from .agent_models import ToolCallDecision
from .models import AgentResponse, LabRequest, TraceEvent
from .policy_context import ReservationContext, build_reservation_context
from .tools import MUTATING_TOOLS


def validate_request_binding(
    decision: ToolCallDecision,
    *,
    request: LabRequest,
) -> list[str]:
    """Reject substitution of the authenticated user or any resolved field."""
    errors: list[str] = []
    arguments = decision.arguments
    # only block a guessed value when the call would change lab state
    mutating = decision.tool in MUTATING_TOOLS

    proposed_user = arguments.get("user_id")
    if proposed_user is not None and proposed_user != request.authenticated_user_id:
        errors.append("user_id_must_match_authenticated_user")

    proposed_project = arguments.get("project_id")
    if proposed_project is not None:
        if request.project_id is None:
            if mutating:
                errors.append("project_id_unresolved_in_request")
        elif proposed_project != request.project_id:
            errors.append("project_id_does_not_match_request")

    proposed_resource = arguments.get("resource_id")
    if proposed_resource is not None:
        if request.resource_id is None:
            if mutating:
                errors.append("resource_id_unresolved_in_request")
        elif proposed_resource != request.resource_id:
            errors.append("resource_id_does_not_match_request")

    proposed_start = arguments.get("start")
    if proposed_start is not None:
        if request.start is None:
            if mutating:
                errors.append("start_unresolved_in_request")
        elif proposed_start != request.start:
            errors.append("start_does_not_match_request")

    proposed_end = arguments.get("end")
    if proposed_end is not None:
        if request.end is None:
            if mutating:
                errors.append("end_unresolved_in_request")
        elif proposed_end != request.end:
            errors.append("end_does_not_match_request")

    return errors


def validate_reservation_preconditions(context: ReservationContext) -> list[str]:
    """Return an error for every required context fact that is false."""
    errors: list[str] = []

    if not context.arguments_complete:
        errors.append("reservation_arguments_incomplete")
    if not context.policy_retrieved:
        errors.append("policy_not_retrieved")
    if not context.authorizations_checked:
        errors.append("authorizations_not_checked")
    if not context.resource_status_checked:
        errors.append("resource_status_not_checked")
    if not context.project_authorized:
        errors.append("project_not_authorized")
    if not context.qualification_current:
        errors.append("required_qualification_missing")
    if not context.resource_available:
        errors.append("resource_not_available")
    if not context.calibration_current:
        errors.append("calibration_not_current")
    if not context.maintenance_clear:
        errors.append("resource_in_maintenance")
    if not context.after_hours_approval_satisfied:
        errors.append("after_hours_approval_missing")

    return errors


def validate_proposed_tool_call(
    decision: ToolCallDecision,
    *,
    request: LabRequest,
    trace: list[TraceEvent],
) -> list[str]:
    """Supplied wrapper. Do not modify this function."""
    errors = validate_request_binding(decision, request=request)
    if decision.tool == "reserve_resource":
        context = build_reservation_context(decision, trace)
        errors.extend(validate_reservation_preconditions(context))
    return errors


def retrieved_passage_ids(trace: list[TraceEvent]) -> set[str]:
    """Supplied helper. Do not modify this function."""
    identifiers: set[str] = set()
    for event in trace:
        if event.observation.tool != "search_lab_documents" or not event.observation.ok:
            continue
        identifiers.update(
            passage["passage_id"]
            for passage in event.observation.data.get("passages", [])
        )
    return identifiers


def validate_final_response(
    response: AgentResponse, trace: list[TraceEvent]
) -> list[str]:
    """Check citations, claimed actions, and status against the trace."""
    errors: list[str] = []

    invented = sorted(set(response.citations) - retrieved_passage_ids(trace))
    for passage_id in invented:
        errors.append(f"citations_not_retrieved: {passage_id}")

    succeeded = {
        event.observation.tool
        for event in trace
        if event.mutating and event.observation.ok
    }
    if any(action not in succeeded for action in response.completed_actions):
        errors.append("completed_action_not_in_successful_trace")

    if response.status == "completed":
        if not succeeded:
            errors.append("completed_without_successful_mutation")
        if not response.completed_actions:
            errors.append("completed_without_claimed_action")
    else:
        if response.completed_actions:
            errors.append("non_completed_status_claims_actions")
        if succeeded:
            errors.append("unreported_successful_mutation")

    return errors
