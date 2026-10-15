from atlas_agent.agent import run_agent
from atlas_agent.llm import ScriptedLLM
from atlas_agent.models import LabRequest

REQUEST = LabRequest(
    authenticated_user_id="alice",
    text="Reserve tensile-01 for polymer-study from 2026-10-15 10:00 to 11:00.",
    project_id="polymer-study",
    resource_id="tensile-01",
    start="2026-10-15T10:00:00",
    end="2026-10-15T11:00:00",
)


def tool(tool, arguments):
    return {
        "kind": "tool_call",
        "tool": tool,
        "arguments": arguments,
        "reasoning_summary": "Obtain required evidence before acting.",
    }


def test_successful_bounded_agent_run(environment):
    interval = {"start": "2026-10-15T10:00:00", "end": "2026-10-15T11:00:00"}
    decisions = [
        tool(
            "search_lab_documents",
            {
                "query": "tensile tester lab_safety authorization calibration",
                "top_k": 8,
            },
        ),
        tool("get_user_authorizations", {"user_id": "alice"}),
        tool("get_resource_status", {"resource_id": "tensile-01", **interval}),
        tool(
            "reserve_resource",
            {
                "user_id": "alice",
                "project_id": "polymer-study",
                "resource_id": "tensile-01",
                **interval,
            },
        ),
        {
            "kind": "final",
            "response": {
                "status": "completed",
                "message": "The reservation was created.",
                "citations": ["TRN-210#tensile-tester"],
                "completed_actions": ["reserve_resource"],
            },
        },
    ]
    run = run_agent(REQUEST, llm=ScriptedLLM(decisions), environment=environment)
    assert run.response.status == "completed"
    assert run.termination_reason == "model_finished"
    assert len(run.trace) == 4
    assert run.trace[-1].observation.ok


def test_action_gate_records_and_blocks_unsafe_attempt(environment):
    interval = {"start": "2026-10-15T10:00:00", "end": "2026-10-15T11:00:00"}
    decisions = [
        tool(
            "reserve_resource",
            {
                "user_id": "alice",
                "project_id": "polymer-study",
                "resource_id": "tensile-01",
                **interval,
            },
        ),
        {
            "kind": "final",
            "response": {
                "status": "blocked",
                "message": "Required checks were not completed.",
                "citations": [],
                "completed_actions": [],
            },
        },
    ]
    run = run_agent(REQUEST, llm=ScriptedLLM(decisions), environment=environment)
    assert run.response.status == "blocked"
    assert run.trace[0].observation.error_code == "action_gate_denied"
    assert len(environment.simulator.state["reservations"]) == 1


def test_action_gate_rejects_project_substitution(environment):
    interval = {"start": "2026-10-15T10:00:00", "end": "2026-10-15T11:00:00"}
    decisions = [
        tool("search_lab_documents", {"query": "reservation authorization"}),
        tool("get_user_authorizations", {"user_id": "alice"}),
        tool("get_resource_status", {"resource_id": "tensile-01", **interval}),
        tool(
            "reserve_resource",
            {
                "user_id": "alice",
                "project_id": "different-project",
                "resource_id": "tensile-01",
                **interval,
            },
        ),
        {
            "kind": "final",
            "response": {
                "status": "blocked",
                "message": "The proposed project does not match the request.",
            },
        },
    ]
    run = run_agent(REQUEST, llm=ScriptedLLM(decisions), environment=environment)
    assert run.trace[-1].observation.error_code == "action_gate_denied"
    assert "project_id_does_not_match_request" in run.trace[-1].observation.message


def test_maximum_step_termination(environment):
    repeated = [
        tool("search_lab_documents", {"query": "reservation policy"}),
        tool("search_lab_documents", {"query": "reservation policy"}),
    ]
    run = run_agent(
        REQUEST,
        llm=ScriptedLLM(repeated),
        environment=environment,
        max_steps=2,
    )
    assert run.response.status == "failed"
    assert run.termination_reason == "maximum_steps_exceeded"


def test_ambiguous_request_can_request_clarification(environment):
    request = LabRequest(
        authenticated_user_id="alice",
        text="Reserve the tensile tester tomorrow afternoon.",
    )
    model = ScriptedLLM(
        [
            {
                "kind": "clarification",
                "question": "What project and exact start and end times should I use?",
                "missing_fields": ["project_id", "start", "end"],
            }
        ]
    )
    run = run_agent(request, llm=model, environment=environment)
    assert run.response.status == "clarification_required"
    assert not run.trace
