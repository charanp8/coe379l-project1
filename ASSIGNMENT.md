# Midterm Project: Atlas Laboratory Agent

## Overview

In this project, you will implement and evaluate a typed, tool-using agent ic application for a fictional shared engineering laboratory. 
The application receives requests such as:

 *Reserve the tensile tester for my project tomorrow afternoon.*

Before taking an action, the application may need to retrieve laboratory policy, inspect user qualifications, check project authorization, check resource status, 
or ask the user for missing information. Your application will leverage an AI model which may, in turn, propose an action to take, but your 
application should decide whether that action is safe to execute. The final response must accurately reflect the recorded execution trace.

The project focuses on the control layer of an AI system. You are not expected to build various components of the system, such as a document parser, 
database, web frontend, search engine, production scheduling service, or LLM-serving platform.

## How to approach the project 

First, read this document (ASSIGNMENT.md) from start to finish. Then, read the ARCHITECTURE.md file to get an understanding 
of the overall system architecture. Finally, head over to the IMPLEMENTATION_STEPS.md to actually start working on the coding and other tasks. 

Once you have finished the IMPLEMENTATION_STEPS.md and tests are passing, make sure you return to ASSIGNMENT.md (this document) 
to make sure you have completed all required deliverables for the assignment.

## Learning objectives

By completing the project, you should be able to:

1. represent model decisions and final responses with Pydantic models
2. construct prompts that distinguish trusted instructions from untrusted data
3. implement a decision–action–observation loop with proper bounds
4. validate tool calls before executing them
5. maintain an auditable trace of actions and observations
6. prevent final responses from claiming actions that did not succeed
7. test the control layer deterministically with an LLM simulator
8. explain what ordinary Python validation and example-based testing do not guarantee 

## Two LLM Backend Implementations 

The repository provides two implementations of the same `StructuredLLM` interface:

- `ScriptedLLM` returns a predefined sequence of decisions. It performs no network calls and is used for development and correctness grading.
- `OpenAICompatibleLLM` provides an interface to connect to the course inference service. It is not used as part of any required component of this 
project but it provides a mechanism for integrating a real AI inference 
service if you are interested. 

Your implementation and correctness grade do not depend on live-model availability or nondeterministic model behavior. 

## Request Information Derived and Provided For You

The authenticated identity of the user making the request and any already-resolved resource, project, start time, 
and end time are supplied in a `LabRequest` object. The original natural-language request is preserved separately. 
Ambiguous fields are left unset and may require your application to take the necessary steps to determine their values.

## Code Provided to You

The instructors are providing you with an initial starter repository which includes:

- a fictional laboratory-policy corpus that has been chunked into   
  passages with unique identifiers
- a working retrieval function that leverages lexical search 
- a JSON-based laboratory "simulator" which provides an API for 
  determining the state of various objects in the lab.
- Pydantic models representing typed tool arguments/calls and a 
  deterministic tool calling implementation 
- `StructuredLLM`, `ScriptedLLM`, and an optional live-model adapter;
- policy-context construction, including trace lookup and time calculations;
- A set of public, end-to-end test scenarios that you can use to evaluate your system
- benchmark metric calculations

You should read these modules but should not modify them:

- `models.py`
- `retrieval.py`
- `simulator.py`
- `tools.py`
- `llm.py`
- `policy_context.py`
- `evaluation.py`
- `public_benchmark.py`

## Student implementation

You will complete TODOs in exactly four modules:

- `agent_models.py`
- `prompts.py`
- `agent.py`
- `validation.py`

You will also add tests and submit an evaluation report. See `GETTING_STARTED.md` for the exact order and commands, and `ARCHITECTURE.md` for the module and data-flow map.

## Required Decisions

As mentioned, your application will implement the primary decision–action–observation agentic loop. 
At each step, the model returns one of three typed decisions:

1. `ToolCallDecision`: invoke one allowed tool with the given arguments
2. `ClarificationDecision`: ask the user for information required to 
    continue
3. `FinalDecision`: return a typed final response

In case 1), you application should first validate the tool call 
decision, and only execute it if all safety checks pass.


## Required Agentic-loop Behavior

Your loop must:

1. initialize messages from the system prompt and request
2. request one decision validated by `DecisionAdapter`
3. handle malformed model output
4. return clarification without executing a tool
5. apply the action gate before tool dispatch
6. record every attempted tool call and resulting observation
7. return the observation to the next model call
8. validate a proposed final response against the trace
9. terminate after the configured maximum number of steps

## Required Validators 

Your application must implement three validations, described below.

### 1. Request binding

`validate_request_binding` checks that a proposed action remains bound to the original authenticated user as well as the project, resource, and interval in the trusted request, if they were resolved. For example, 
if the `LabRequest` object resolved the request to the user `jstubbs`, 
then the proposed action is not allowed to change this to another user, 
`ajamthe`, say. 

### 2. Reservation Preconditions

The `policy_context.py` module provides a `ReservationContext` containing Boolean facts such as whether:

- the policy was retrieved
- authorizations and resource status were checked
- project and qualification requirements are satisfied
- the resource is available, calibrated, and not under maintenance
- after-hours approval is satisfied when applicable

`validate_reservation_preconditions` returns an error for each required fact that is false. You do not need to implement the trace-searching, qualification-mapping, or datetime logic that computes these facts.

### 3. Final-response consistency

`validate_final_response` checks that:

- every citation was observed in a successful search result
- every claimed completed action appears as a successful tool call to modify the lab state 
- `completed` is used only after a successful state changing tool call
- `completed` identifies at least one completed action
- a non-completed response does not claim completed actions

## Simulator and action-gate boundary

We are providing a "lab simulator" (`simulator.py`) to simulate the state of 
the lab at a given moment in time. The `reserve` method enforces a set of constraints 
related to reserving lab equipment, such as 
ensuring the resource exists, checking that the interval of time 
requested is valid (that end time isn't before begin time, for example), 
and checking for scheduling conflicts. It 
intentionally does not enforce all training, authorization, calibration, 
maintenance, and after-hours policy.

Do not modify the simulator. We will use an unmodified simulator as part of evaluating 
your system, and our tests will inspect all of your system's attempted actions, not just the final response. You could lose points if your system allows unsafe calls even if it doesn't impact the final response. 
For example, calling `reserve` before the required checks have been performed is 
considered an unsafe action attempt even if the simulator ultimately rejects the reservation for another reason.

## Public End-to-end Test Scenarios

The `data/public_scenarios.json` file contains examples from six different categories:

1. successful reservation
2. missing qualification
3. expired calibration or maintenance condition
4. after-hours approval required
5. ambiguous request requiring clarification
6. scheduling conflict or tool failure

The instructors will evaluate your application on an additional set of "held out" test. The held-out tests may check additional scenarios, including:

- identity, project, resource, or interval substitution
- malformed model decisions
- incomplete tool arguments
- prompt injection embedded in retrieved content
- repeated mutating calls
- failed actions reported as successful
- citations that were never retrieved
- maximum-step termination


## Recommended Approach 
We recommend you approach this project as a set of steps. Each of these is
detailed in the IMPLEMENTATION_STEPS.md 

Step 0: Initial setup 
Step 1: Typed decisions and prompts
Step 2: Executable agent loop
Step 3: Validation and evaluation

## Required Deliverables

Submit:

1. completed source code including implementations and tests (see Steps 1 through 4 of the IMPLEMENTATION_NOTES.md)
  - Submit a GitHub repository URL shared privately with TAs/Instructors or set to Public.
  - The code should also be on your student VM. 
2. the generated public_benchmark.json artifact and a summary 
   of its results in the evaluation report
3. a small data flow diagram illustrating the execution/flow for a single scenario.
4. a short report analyzing your system  (no more than 2 pages)



## Collaboration and Use of AI

Students should work alone on this project and submit their own work. You may ask conceptual questions of your fellow students, but you should not 
ask them to tell you how to write the code. Copying code directly from 
another student's project is strictly forbidden. 
We encourage you to use the 
class slack channel so that everyone in the class can participate and 
benefit from the discussions. 

You may use course examples and the documented APIs of the provided dependencies. 
Do not use AI to help you generate the code. You may use AI to help you understand the basic concept, as specified 
in the course syllabus. Do not modify the simulator.


## Grading rubric
The grading will be weighted as follows: 

| Component | Weight |
|---|---:|
| Typed decisions | 10% |
| Prompt and trust boundary | 10% |
| Agent loop, state, and termination | 30% |
| Three validators | 25% |
| Student tests and evaluation | 15% |
| Architecture diagram and report | 10% |