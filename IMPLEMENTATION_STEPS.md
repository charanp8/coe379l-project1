# Getting Started

This guide gives you a testable path through the project. We highly recommend you complete the stages in the order 
described below. Note that you should not try to understand every implementation detail before beginning.

## Step 0: Initial setup 

### 1. Install the environment

```bash
uv sync --extra dev
```

### 2. Run the supplied infrastructure tests

```bash
uv run pytest \
  tests/test_retrieval.py \
  tests/test_tools.py \
  tests/test_llm.py \
  tests/test_policy_context.py
```

These tests should pass before you edit any files. If they do not, resolve the environment problem before continuing.

### 3. Invoke the tools without an LLM

```bash
uv run atlas-demo-tools
```

This code executes three tools: `get_user_authorizations`, `get_resource_status`, and `search_lab_documents`, and returns a 
typed `ToolObservation` object (serialized as a JSON object)for each call.

Inspect the returned `ToolObservation` objects. In particular, locate `ok`, `data`, `error_code`, and `message`.

### 4. Read the architecture map

Read `ARCHITECTURE.md`. Then inspect these supplied modules in order:

1. `models.py`
2. `tools.py`
3. `llm.py`
4. `policy_context.py`

Do not modify these modules for the assignment.

## Step  1: Typed decisions and prompts

Edit:

- `src/atlas_agent/agent_models.py`
- `src/atlas_agent/prompts.py`

Tasks:

1. Use the completed `ToolCallDecision` as your example.
2. Add the required fields to `ClarificationDecision`.
3. Add the required field to `FinalDecision`.
4. Convert `AgentDecision` into a discriminated union using `kind`.
5. Complete the system prompt sections concerning trust, preconditions, citations, and truthful action reporting.

Run:

```bash
uv run pytest tests/test_agent_models.py tests/test_prompts.py
```

Stop here until these tests pass.

## Step  2: Executable agent loop

Edit `src/atlas_agent/agent.py`. Complete TODOs 2.1 through 2.7 in order:

1. Obtain a typed decision from the StructuredLLM.
2. Return immediately when the decision requests clarification.
3. Validate and return a proposed final response.
4. Apply the action gate to a proposed tool call and dispatch the tool only when permitted.
5. Record the proposed tool call and resulting ToolObservation in a TraceEvent.
6. Append the serialized decision and observation to the message history so that the next model call can observe the result.
7. Return an explicit failure when the maximum step budget is exhausted.
8. Ensure that tests/test_agent_loop.py passes.

Note that each of step 1 through 7 corresponds to a TODO in the run_agent function (TODO 2.1, 2.2, 2.3, ..., 2.7).

Run:

```bash
uv run pytest tests/test_agent_loop.py
```

The tests use `ScriptedLLM`; no network service is involved.

## Step  3: Implement the three validators and conduct evaluation

Edit `src/atlas_agent/validation.py`. Implement only these three functions:

1. `validate_request_binding`
2. `validate_reservation_preconditions`
3. `validate_final_response`

For the last one, `validate_final_response`, here are some details instrucions 
with hints:

3a. Check that every citation in the response.citations was actually retrieved and appears in 
    the trace.
    hint: one can use retrieved_passage_ids(trace) to obtain the passage IDs returned
    by successful search_lab_documents calls.

3b. Collect all the names of tools that made a successful mutation into a list.
    Then check that every object in response.completed_actions that corresponds to a
    successful mutation.
    Hint: a tool call made a successful mutation if event.mutating is True AND event.observation.ok is True

3c. Check that if response.status is "completed" , then the response has at least one 
    successful mutation and at least one claimed completed action.
    Hint: with the checks above, response.completed_actions will contain successful mutations

3d. Check that if response.status is not "completed", then response.completed_actions must be 
    empty and the trace must not contain an unreported successful mutation.


Note also that the supplied `policy_context.py` performs trace lookup, qualification mapping, and time/approval calculations. Your validator should use the resulting Boolean facts; do not reimplement those mechanics.

Run:

```bash
uv run pytest tests/test_validation.py tests/test_agent.py
uv run atlas-evaluate-scripted
uv run pytest
```

## Step 4: Add your own tests 

Create `tests/test_student_cases.py` and add your tests. 
Do not add your tests to or modify the instructor-provided test files.

The file must contain at least three tests:

1. an unsafe action proposal that is denied before tool execution;
2. a contradictory final response that is rejected because it disagrees
   with the trace; and
3. one additional case of your choice.

Use `ScriptedLLM` so that all three tests are deterministic. Give each test a
descriptive name and assert the relevant response, trace, or termination
property. It is not enough to just check that the code executed without an exception. 

The tests must run as part of:

```bash
uv run pytest
```

## Step 5: Execute the public benchmark 

Once your implementation is completed and your tests are added and passing, execute the benchmark using the 
following command: 

`` 
uv run atlas-evaluate-scripted > public_benchmark.json
``

This will produce a file, `public_benchmark.json`, the contains 
information about the execution, including:

* aggregate metrics
* each scenario’s expected status
* the actual AgentRun
* the complete trace
* the final response
* the termination reason

Review the results and write a short, human-readable summary of 
the evaluation (say, a few sentences). Your summary should 
explain any failed or unexpected scenarios. If every public case passes, be sure to state that. You can include additional details such as a discussion of your student-authored tests, near-failures, etc. 

## Step 6: Create a small data flow diagram 

Include one small diagram showing how a single scenario moves through your
completed system. Your diagram must identify the initial request object (including the trusted metadata 
added to the request), model decisions, validation/action gate, tool observations, trace, and final response.

You may use Mermaid, a drawing tool (e.g., draw.io), presentation software (e.g., PowerPoint, Google Slides, 
etc.), or a legible hand-drawn diagram. No formal diagram notation is required. The diagram is
graded for conceptual accuracy and clarity, not visual design.

You may use the diagram in `ARCHITECTURE.md` as a reference, but your diagram
must specialize the flow to one concrete scenario.

## Step 7: Final report 

Write a short report (max 2 pages) providing an overview of the system and an analysis of its performance 
on the public benchmark. Include aggregate statistics and an analysis of success and failure cases. Describe 
the tests your wrote and an explanation of how they help ensure the quality of the system. 
Justify any other major implementation decisions you made. 

## When you are stuck

Use the smallest failing test as your starting point. Inspect the objects in the assertion and compare them with the corresponding Pydantic model. Reach out on the tacc-learn.slack.com slack team and ask questions. 
Remember: you should not change the simulator, retrieval code, or tool implementations. If you find yourself 
needing to make changes to these, you have done something wrong. Do not be afraid to ask for help. 

