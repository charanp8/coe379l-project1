"""Deterministic public benchmark driven entirely by ScriptedLLM."""

from __future__ import annotations

import json
from pathlib import Path

from .agent import run_agent
from .evaluation import EvaluatedScenario, summarize
from .llm import ScriptedLLM
from .models import LabRequest
from .simulator import LabSimulator
from .tools import ToolEnvironment


def run_public_benchmark(root: str | Path) -> list[EvaluatedScenario]:
    root = Path(root)
    scenarios = json.loads((root / "data" / "public_scenarios.json").read_text())
    scripts = json.loads((root / "data" / "public_scripts.json").read_text())
    records: list[EvaluatedScenario] = []

    for scenario in scenarios:
        environment = ToolEnvironment(
            LabSimulator.from_file(root / "data" / "initial_state.json"),
            root / "corpus" / "policies.json",
        )
        run = run_agent(
            LabRequest.model_validate(scenario["request"]),
            llm=ScriptedLLM(scripts[scenario["scenario_id"]]),
            environment=environment,
        )
        records.append(
            EvaluatedScenario(
                scenario_id=scenario["scenario_id"],
                category=scenario["category"],
                expected_status=scenario["expected_status"],
                run=run,
            )
        )
    return records


def main() -> None:
    root = Path(__file__).parents[2]
    records = run_public_benchmark(root)
    output = {
        "summary": summarize(records),
        "scenarios": [record.model_dump() for record in records],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
