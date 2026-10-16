# COE 379L Fall 2026 Midterm Project 

This repository contains the provided infrastructure and staged public tests for the 
 COE 379L Fall 2026 midterm project. 
 Read `ASSIGNMENT.md`, then follow `IMPLEMENTATION_STEPS.md` in order. 
 `ARCHITECTURE.md` explains the modules and data flow.

## Submission notes

Implemented in `agent_models.py`, `prompts.py`, `agent.py`, and `validation.py`.
The provided modules are unmodified.

```bash
uv sync --extra dev
uv run pytest                                      # 29 tests
uv run atlas-evaluate-scripted > public_benchmark.json
```

- `public_benchmark.json` — benchmark artifact, 6/6 scenarios at the expected status
- `tests/test_student_cases.py` — my own tests (Step 4)
- `data_flow_diagram.md` — data flow diagram for the `success_tensile` scenario (Step 6)
- `report.tex` — report source; compile to PDF for submission (Step 7)
