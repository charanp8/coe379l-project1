"""Ungraded preflight: inspect the supplied tools without an LLM."""

from __future__ import annotations

import json
from pathlib import Path

from .simulator import LabSimulator
from .tools import ToolEnvironment


def main() -> None:
    root = Path(__file__).parents[2]
    environment = ToolEnvironment(
        LabSimulator.from_file(root / "data" / "initial_state.json"),
        root / "corpus" / "policies.json",
    )
    examples = [
        ("get_user_authorizations", {"user_id": "alice"}),
        (
            "get_resource_status",
            {
                "resource_id": "tensile-01",
                "start": "2026-10-15T10:00:00",
                "end": "2026-10-15T11:00:00",
            },
        ),
        (
            "search_lab_documents",
            {"query": "tensile tester training requirements", "top_k": 3},
        ),
    ]
    for tool, arguments in examples:
        result = environment.dispatch(tool, arguments)
        print(f"\n{tool}")
        print(json.dumps(result.model_dump(), indent=2))


if __name__ == "__main__":
    main()
