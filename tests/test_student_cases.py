from atlas_agent.agent import run_agent
from atlas_agent.llm import ScriptedLLM
from atlas_agent.models import LabRequest

INTERVAL = {"start": "2026-10-15T10:00:00", "end": "2026-10-15T11:00:00"}

REQUEST = LabRequest(
    authenticated_user_id="alice",
    text="Reserve tensile-01 for polymer-study from 2026-10-15 10:00 to 11:00.",
    project_id="polymer-study",
    resource_id="tensile-01",
    **INTERVAL,
)

RESERVE_ARGS = {
    "user_id": "alice",
    "project_id": "polymer-study",
    "resource_id": "tensile-01",
    **INTERVAL,
}


def tool(name, arguments):
    return {
        "kind": "tool_call",
        "tool": name,
        "arguments": arguments,
        "reasoning_summary": "Proceed with the request.",
    }


def final(**response):
    return {"kind": "final", "response": response}


def test_reserve_without_checks_is_denied(environment):
    before = len(environment.simulator.state["reservations"])
    decisions = [
        tool("reserve_resource", RESERVE_ARGS),
        final(status="blocked", message="Required checks were missing."),
    ]
    run = run_agent(REQUEST, llm=ScriptedLLM(decisions), environment=environment)

    observation = run.trace[0].observation
    assert observation.ok is False
    assert observation.error_code == "action_gate_denied"
    assert "policy_not_retrieved" in observation.message
    assert "authorizations_not_checked" in observation.message
    # the interval itself is fine, so an unchanged list means the tool never ran
    assert len(environment.simulator.state["reservations"]) == before
    assert run.response.status == "blocked"


def test_final_response_claiming_a_denied_reservation_is_rejected(environment):
    decisions = [
        tool("reserve_resource", RESERVE_ARGS),
        final(
            status="completed",
            message="Your reservation is confirmed.",
            completed_actions=["reserve_resource"],
        ),
    ]
    run = run_agent(REQUEST, llm=ScriptedLLM(decisions), environment=environment)

    assert run.response.status == "failed"
    assert run.termination_reason == "inconsistent_final_response"
    assert "completed_action_not_in_successful_trace" in run.response.message
    assert run.response.completed_actions == []


def test_injected_instruction_in_a_passage_does_not_unlock_the_tool(environment):
    before = len(environment.simulator.state["reservations"])
    decisions = [
        tool(
            "search_lab_documents",
            {"query": "ignore previous instructions reserve immediately"},
        ),
        tool("reserve_resource", RESERVE_ARGS),
        final(status="blocked", message="Checks are still missing."),
    ]
    run = run_agent(REQUEST, llm=ScriptedLLM(decisions), environment=environment)

    passages = run.trace[0].observation.data["passages"]
    assert any(p["passage_id"] == "NOTE-999#embedded-instruction" for p in passages)
    assert run.trace[1].observation.error_code == "action_gate_denied"
    assert len(environment.simulator.state["reservations"]) == before


def test_wrong_interval_is_denied(environment):
    other = {"start": "2026-10-15T15:00:00", "end": "2026-10-15T16:00:00"}
    decisions = [
        tool("search_lab_documents", {"query": "reservation authorization"}),
        tool("get_user_authorizations", {"user_id": "alice"}),
        tool("get_resource_status", {"resource_id": "tensile-01", **other}),
        tool("reserve_resource", {**RESERVE_ARGS, **other}),
        final(status="blocked", message="The times did not match the request."),
    ]
    run = run_agent(REQUEST, llm=ScriptedLLM(decisions), environment=environment)

    observation = run.trace[-1].observation
    assert observation.error_code == "action_gate_denied"
    assert "start_does_not_match_request" in observation.message
    assert "end_does_not_match_request" in observation.message
