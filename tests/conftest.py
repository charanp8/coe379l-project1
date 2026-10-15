from pathlib import Path

import pytest

from atlas_agent.simulator import LabSimulator
from atlas_agent.tools import ToolEnvironment

ROOT = Path(__file__).parents[1]


@pytest.fixture
def project_root() -> Path:
    return ROOT


@pytest.fixture
def environment() -> ToolEnvironment:
    simulator = LabSimulator.from_file(ROOT / "data" / "initial_state.json")
    return ToolEnvironment(simulator, ROOT / "corpus" / "policies.json")
