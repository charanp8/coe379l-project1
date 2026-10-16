"""Bounded decision-action-observation loop."""

from __future__ import annotations

import json

from pydantic import ValidationError

from .agent_models import ClarificationDecision, DecisionAdapter, FinalDecision
from .llm import StructuredLLM
from .models import AgentResponse, AgentRun, LabRequest, ToolObservation, TraceEvent
from .prompts import initialize_messages
from .tools import MUTATING_TOOLS, ToolEnvironment
from .validation import validate_final_response, validate_proposed_tool_call


def _failed(message: str, trace: list[TraceEvent], reason: str) -> AgentRun:
    return AgentRun(
        response=AgentResponse(status="failed", message=message),
        trace=trace,
        termination_reason=reason,
    )


def run_agent(
    request: LabRequest,
    *,
    llm: StructuredLLM,
    environment: ToolEnvironment,
    max_steps: int = 10,
) -> AgentRun:
    messages = initialize_messages(request)
    trace: list[TraceEvent] = []

    for step in range(1, max_steps + 1):
        try:
            decision = llm.generate(messages=messages, response_model=DecisionAdapter)
        except (ValidationError, ValueError, TypeError, RuntimeError) as exc:
            return _failed(
                f"The model did not produce a valid decision: {exc}",
                trace,
                "invalid_model_decision",
            )

        if isinstance(decision, ClarificationDecision):
            message = decision.question
            if decision.missing_fields:
                message += " Missing: " + ", ".join(decision.missing_fields)
            return AgentRun(
                response=AgentResponse(
                    status="clarification_required",
                    message=message,
                ),
                trace=trace,
                termination_reason="clarification_requested",
            )

        if isinstance(decision, FinalDecision):
            errors = validate_final_response(decision.response, trace)
            if errors:
                return _failed(
                    "The proposed final response disagreed with the trace: "
                    + "; ".join(errors),
                    trace,
                    "inconsistent_final_response",
                )
            return AgentRun(
                response=decision.response,
                trace=trace,
                termination_reason="model_finished",
            )

        # DecisionAdapter leaves a tool call as the only remaining variant
        errors = validate_proposed_tool_call(decision, request=request, trace=trace)
        if errors:
            observation = ToolObservation(
                ok=False,
                tool=decision.tool,
                error_code="action_gate_denied",
                message="; ".join(errors),
            )
        else:
            observation = environment.dispatch(decision.tool, decision.arguments)

        trace.append(
            TraceEvent(
                step=step,
                decision=decision.model_dump(),
                observation=observation,
                mutating=decision.tool in MUTATING_TOOLS,
            )
        )

        messages.append(
            {"role": "assistant", "content": json.dumps(decision.model_dump())}
        )
        messages.append(
            {"role": "tool", "content": json.dumps(observation.model_dump())}
        )

    return _failed(
        "The step budget ran out before the model returned a final response.",
        trace,
        "maximum_steps_exceeded",
    )
