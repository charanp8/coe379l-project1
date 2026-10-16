# Data Flow Diagram

Scenario `success_tensile` from `data/public_scenarios.json`, traced through the
completed system. Alice asks to reserve the tensile tester for an hour; every
required check passes and the reservation is created.

```mermaid
flowchart TD
    REQ["<b>LabRequest</b> (trusted envelope)<br/>authenticated_user_id = alice<br/>project_id = polymer-study<br/>resource_id = tensile-01<br/>start = 2026-10-15T10:00:00<br/>end = 2026-10-15T11:00:00<br/><i>text = 'Reserve tensile-01 for polymer-study...'</i>"]

    MSG["<b>initialize_messages</b><br/>system = SYSTEM_PROMPT (trusted rules)<br/>user = envelope + raw request text"]

    LLM{{"<b>ScriptedLLM.generate</b><br/>validated by DecisionAdapter<br/>(discriminated on 'kind')"}}

    D1["<b>Decision 1 - ToolCallDecision</b><br/>search_lab_documents<br/>query = 'tensile tester lab_safety<br/>authorization calibration', top_k = 8"]
    D2["<b>Decision 2 - ToolCallDecision</b><br/>get_user_authorizations<br/>user_id = alice"]
    D3["<b>Decision 3 - ToolCallDecision</b><br/>get_resource_status<br/>tensile-01, 10:00-11:00"]
    D4["<b>Decision 4 - ToolCallDecision</b><br/>reserve_resource<br/>alice, polymer-study,<br/>tensile-01, 10:00-11:00"]
    D5["<b>Decision 5 - FinalDecision</b><br/>status = completed<br/>citations = [TRN-210#tensile-tester]<br/>completed_actions = [reserve_resource]"]

    GATE{"<b>ACTION GATE</b><br/>validate_proposed_tool_call<br/>binding + preconditions"}

    O1["ToolObservation ok=true<br/>passages: TRN-210#tensile-tester,<br/>CAL-310#calibration, AFT-130#after-hours"]
    O2["ToolObservation ok=true<br/>qualifications = [lab_safety, laser_safety]<br/>projects = [polymer-study]"]
    O3["ToolObservation ok=true<br/>kind = tensile_tester, available = true<br/>calibration_current = true, maintenance = false"]
    O4["ToolObservation ok=true<br/>reservation_id = r-xxxxxxxxxx<br/>status = confirmed"]

    SIM[("LabSimulator<br/>reservations[] mutated<br/><b>only reached via the gate</b>")]

    TRACE["<b>trace: list[TraceEvent]</b><br/>1 search_lab_documents ok=true mutating=false<br/>2 get_user_authorizations ok=true mutating=false<br/>3 get_resource_status ok=true mutating=false<br/>4 reserve_resource ok=true <b>mutating=true</b>"]

    FVAL{"<b>validate_final_response</b><br/>citation in retrieved_passage_ids? yes<br/>claimed action a successful mutation? yes<br/>completed backed by ok=true mutation? yes"}

    RESP["<b>AgentRun</b><br/>response.status = completed<br/>message = 'The reservation was created.'<br/>citations = [TRN-210#tensile-tester]<br/>completed_actions = [reserve_resource]<br/>termination_reason = model_finished"]

    REQ --> MSG --> LLM
    LLM --> D1 --> GATE
    LLM --> D2 --> GATE
    LLM --> D3 --> GATE
    LLM --> D4 --> GATE
    LLM --> D5 --> FVAL

    GATE -->|"permitted"| O1
    GATE -->|"permitted"| O2
    GATE -->|"permitted (steps 1-3 in trace,<br/>all facts true, fields bound)"| O4
    GATE -->|"permitted"| O3
    GATE -.->|"denied -> ok=false,<br/>error_code=action_gate_denied<br/>(tool never dispatched)"| TRACE

    O4 --> SIM

    O1 --> TRACE
    O2 --> TRACE
    O3 --> TRACE
    O4 --> TRACE

    TRACE -.->|"observation appended as a<br/>'tool' message for the next step"| LLM
    TRACE --> FVAL
    FVAL -->|"consistent"| RESP
    FVAL -.->|"inconsistent -> status=failed,<br/>termination_reason=<br/>inconsistent_final_response"| RESP

    linkStyle default stroke:#475569,color:#1e293b

    classDef trusted fill:#dbeafe,stroke:#1e40af,color:#1e293b
    classDef model fill:#fef3c7,stroke:#b45309,color:#1e293b
    classDef gate fill:#fee2e2,stroke:#b91c1c,color:#1e293b
    classDef obs fill:#dcfce7,stroke:#15803d,color:#1e293b
    classDef record fill:#ede9fe,stroke:#6d28d9,color:#1e293b

    class REQ,MSG trusted
    class LLM,D1,D2,D3,D4,D5 model
    class GATE,FVAL gate
    class O1,O2,O3,O4,SIM obs
    class TRACE,RESP record
```

**Reading the diagram.** Blue is trusted input, yellow is model-proposed and
therefore untrusted, red is application-owned validation, green is observed
fact, purple is the authoritative record. The model never reaches the simulator
directly: every proposal passes through the action gate, and the gate is what
decides whether `reserve_resource` is dispatched. Dashed edges are the paths
taken when a check fails. Note that steps 1-3 are not merely informative — the
gate reads them back out of the trace, so the reservation in step 4 is only
permitted because those three observations are already recorded.
