import json

from atlas_agent.agent import run_agent
from atlas_agent.llm import ScriptedLLM
from atlas_agent.models import LabRequest


def tool(tool_name, arguments):
    return {
        "kind": "tool_call",
        "tool": tool_name,
        "arguments": arguments,
        "reasoning_summary": "Obtain information.",
    }


def test_loop_records_observation_and_returns_it_to_model(environment):
    decisions = [
        tool("get_user_authorizations", {"user_id": "alice"}),
        {
            "kind": "final",
            "response": {
                "status": "blocked",
                "message": "No action was requested.",
            },
        },
    ]
    llm = ScriptedLLM(decisions)
    request = LabRequest(authenticated_user_id="alice", text="Show my permissions.")
    run = run_agent(request, llm=llm, environment=environment)

    assert len(run.trace) == 1
    assert run.trace[0].observation.ok
    second_context = llm.calls[1]
    tool_messages = [message for message in second_context if message["role"] == "tool"]
    assert tool_messages
    assert json.loads(tool_messages[-1]["content"])["ok"] is True


def test_loop_returns_clarification_without_tool_call(environment):
    llm = ScriptedLLM(
        [
            {
                "kind": "clarification",
                "question": "What exact start and end times should I use?",
                "missing_fields": ["start", "end"],
            }
        ]
    )
    request = LabRequest(authenticated_user_id="alice", text="Reserve it tomorrow.")
    run = run_agent(request, llm=llm, environment=environment)
    assert run.response.status == "clarification_required"
    assert not run.trace


def test_loop_enforces_maximum_steps(environment):
    llm = ScriptedLLM(
        [
            tool("search_lab_documents", {"query": "reservation"}),
            tool("search_lab_documents", {"query": "reservation"}),
        ]
    )
    request = LabRequest(authenticated_user_id="alice", text="Find policy.")
    run = run_agent(request, llm=llm, environment=environment, max_steps=2)
    assert run.response.status == "failed"
    assert run.termination_reason == "maximum_steps_exceeded"
