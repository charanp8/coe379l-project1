# Data Flow Diagram

Scenario: `success_tensile` from `data/public_scenarios.json`. Alice reserves the
tensile tester from 10:00 to 11:00 and all the checks pass.

```mermaid
flowchart TD
    REQ["LabRequest (trusted envelope)<br/>authenticated_user_id=alice, project_id=polymer-study,<br/>resource_id=tensile-01, start=10:00, end=11:00<br/>text='Reserve tensile-01 for polymer-study...'"]
    MSG["initialize_messages<br/>system prompt (trusted) + envelope + request text"]
    LLM["model returns one typed decision<br/>(validated by DecisionAdapter)"]
    GATE{"action gate<br/>validate_proposed_tool_call"}
    TOOL["dispatch tool to ToolEnvironment"]
    DENY["ToolObservation ok=false<br/>error_code=action_gate_denied"]
    OBS["ToolObservation ok=true"]
    TRACE["append TraceEvent to trace<br/>(decision + observation + mutating)"]
    FINAL{"validate_final_response<br/>citations and claimed actions vs trace"}
    RESP["AgentResponse status=completed<br/>termination_reason=model_finished"]
    FAIL["status=failed<br/>termination_reason=inconsistent_final_response"]

    REQ --> MSG --> LLM
    LLM -->|tool call| GATE
    GATE -->|permitted| TOOL --> OBS --> TRACE
    GATE -->|denied| DENY --> TRACE
    TRACE -->|observation sent back as a tool message| LLM
    LLM -->|final| FINAL
    FINAL -->|consistent| RESP
    FINAL -->|inconsistent| FAIL
```

The model decisions for this scenario, in order:

1. `search_lab_documents` -> returns `TRN-210#tensile-tester` and other passages
2. `get_user_authorizations` -> alice has `lab_safety` and project `polymer-study`
3. `get_resource_status` -> tensile-01 available, calibration current, no maintenance
4. `reserve_resource` -> gate allows it because steps 1-3 are already in the trace,
   so the simulator creates the reservation (`ok=true`, `mutating=true`)
5. final decision -> `validate_final_response` passes, status stays `completed`

A clarification decision would return straight from the loop without any tool call,
and the loop stops with `maximum_steps_exceeded` if the model never finishes.
