"""Safety and consistency checks applied to model-proposed decisions."""

from __future__ import annotations

from .agent_models import ToolCallDecision
from .models import AgentResponse, LabRequest, TraceEvent
from .policy_context import ReservationContext, build_reservation_context
from .tools import MUTATING_TOOLS

BOUND_FIELDS = ("project_id", "resource_id", "start", "end")

REQUIRED_FACTS = (
    ("arguments_complete", "reservation_arguments_incomplete"),
    ("policy_retrieved", "policy_not_retrieved"),
    ("authorizations_checked", "authorizations_not_checked"),
    ("resource_status_checked", "resource_status_not_checked"),
    ("project_authorized", "project_not_authorized"),
    ("qualification_current", "required_qualification_missing"),
    ("resource_available", "resource_not_available"),
    ("calibration_current", "calibration_not_current"),
    ("maintenance_clear", "resource_in_maintenance"),
    ("after_hours_approval_satisfied", "after_hours_approval_missing"),
)


def validate_request_binding(
    decision: ToolCallDecision,
    *,
    request: LabRequest,
) -> list[str]:
    """Reject substitution of the authenticated user or any resolved field."""
    errors: list[str] = []
    arguments = decision.arguments

    proposed_user = arguments.get("user_id")
    if proposed_user is not None and proposed_user != request.authenticated_user_id:
        errors.append("user_id_must_match_authenticated_user")

    for field in BOUND_FIELDS:
        proposed = arguments.get(field)
        if proposed is None:
            continue
        resolved = getattr(request, field)
        if resolved is None:
            # only block a guessed value when the call would change lab state
            if decision.tool in MUTATING_TOOLS:
                errors.append(f"{field}_unresolved_in_request")
        elif proposed != resolved:
            errors.append(f"{field}_does_not_match_request")

    return errors


def validate_reservation_preconditions(context: ReservationContext) -> list[str]:
    """Return an error for every required context fact that is false."""
    return [
        error for fact, error in REQUIRED_FACTS if not getattr(context, fact)
    ]


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
    if invented:
        errors.append("citations_not_retrieved: " + ", ".join(invented))

    succeeded = [
        event.observation.tool
        for event in trace
        if event.mutating and event.observation.ok
    ]
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
