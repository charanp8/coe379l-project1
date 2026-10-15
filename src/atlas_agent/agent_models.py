"""Typed decisions the model is allowed to return."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from .models import AgentResponse

ToolName = Literal[
    "search_lab_documents",
    "get_user_authorizations",
    "get_resource_status",
    "reserve_resource",
]


class DecisionModel(BaseModel):
    """All decision variants reject fields not declared by their schema."""

    model_config = ConfigDict(extra="forbid")


class ToolCallDecision(DecisionModel):
    """Worked example: a typed proposal to call one allowed tool."""

    kind: Literal["tool_call"]
    tool: ToolName
    arguments: dict[str, Any]
    reasoning_summary: str


class ClarificationDecision(DecisionModel):
    """A request for information the trusted envelope did not resolve."""

    kind: Literal["clarification"]
    question: str
    missing_fields: list[str]


class FinalDecision(DecisionModel):
    """A proposed final response, still subject to trace consistency checks."""

    kind: Literal["final"]
    response: AgentResponse


AgentDecision = Annotated[
    ToolCallDecision | ClarificationDecision | FinalDecision,
    Field(discriminator="kind"),
]

DecisionAdapter = TypeAdapter(AgentDecision)
