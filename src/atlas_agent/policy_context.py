"""Supplied helpers that turn tool observations into policy-relevant facts."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from .agent_models import ToolCallDecision
from .models import TraceEvent

REQUIRED_QUALIFICATION = {
    "laser_cutter": "laser_safety",
    "tensile_tester": "lab_safety",
    "robotic_cell": "robotics_level_2",
}


class ReservationContext(BaseModel):
    """Facts computed from a proposed reservation and the preceding trace."""

    arguments_complete: bool
    policy_retrieved: bool
    authorizations_checked: bool
    resource_status_checked: bool
    project_authorized: bool
    qualification_current: bool
    resource_available: bool
    calibration_current: bool
    maintenance_clear: bool
    after_hours_approval_satisfied: bool


def matching_event(
    trace: list[TraceEvent],
    tool: str,
    **arguments: str,
) -> TraceEvent | None:
    """Return the latest successful call to tool with the specified arguments."""
    for event in reversed(trace):
        if event.observation.tool != tool or not event.observation.ok:
            continue
        proposed = event.decision.get("arguments", {})
        if all(proposed.get(key) == value for key, value in arguments.items()):
            return event
    return None


def has_after_hours_approval(authorizations: dict, start: str, end: str) -> bool:
    """Check whether the interval is daytime or covered by an approval."""
    requested_start = datetime.fromisoformat(start)
    requested_end = datetime.fromisoformat(end)
    requires_approval = requested_start.hour < 8 or requested_end.hour > 18
    if not requires_approval:
        return True
    for approval in authorizations.get("approvals", []):
        if approval.get("kind") != "after_hours":
            continue
        if datetime.fromisoformat(
            approval["start"]
        ) <= requested_start and requested_end <= datetime.fromisoformat(
            approval["end"]
        ):
            return True
    return False


def build_reservation_context(
    decision: ToolCallDecision,
    trace: list[TraceEvent],
) -> ReservationContext:
    """Collect policy facts; students decide how the action gate uses them."""
    args = decision.arguments
    required = {"user_id", "project_id", "resource_id", "start", "end"}
    complete = required.issubset(args)
    policy_retrieved = any(
        event.observation.tool == "search_lab_documents" and event.observation.ok
        for event in trace
    )
    if not complete:
        return ReservationContext(
            arguments_complete=False,
            policy_retrieved=policy_retrieved,
            authorizations_checked=False,
            resource_status_checked=False,
            project_authorized=False,
            qualification_current=False,
            resource_available=False,
            calibration_current=False,
            maintenance_clear=False,
            after_hours_approval_satisfied=False,
        )

    auth_event = matching_event(
        trace,
        "get_user_authorizations",
        user_id=args["user_id"],
    )
    status_event = matching_event(
        trace,
        "get_resource_status",
        resource_id=args["resource_id"],
        start=args["start"],
        end=args["end"],
    )
    authorizations = auth_event.observation.data if auth_event else {}
    status = status_event.observation.data if status_event else {}
    required_qualification = REQUIRED_QUALIFICATION.get(status.get("kind"))

    return ReservationContext(
        arguments_complete=True,
        policy_retrieved=policy_retrieved,
        authorizations_checked=auth_event is not None,
        resource_status_checked=status_event is not None,
        project_authorized=args["project_id"] in authorizations.get("projects", []),
        qualification_current=(
            required_qualification is not None
            and required_qualification in authorizations.get("qualifications", [])
        ),
        resource_available=status.get("available", False),
        calibration_current=status.get("calibration_current", False),
        maintenance_clear=status.get("maintenance") is False,
        after_hours_approval_satisfied=(
            has_after_hours_approval(authorizations, args["start"], args["end"])
            if auth_event
            else False
        ),
    )
