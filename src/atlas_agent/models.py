"""Instructor-provided domain models shared by tools and student code."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class LabRequest(BaseModel):
    authenticated_user_id: str
    text: str
    project_id: str | None = None
    resource_id: str | None = None
    start: str | None = None
    end: str | None = None


class PolicyPassage(BaseModel):
    document_id: str
    version: int
    effective_date: str
    document_type: str
    passage_id: str
    text: str
    score: float = 0.0


class ToolObservation(BaseModel):
    ok: bool
    tool: str
    data: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    message: str | None = None


class TraceEvent(BaseModel):
    step: int
    decision: dict[str, Any]
    observation: ToolObservation
    mutating: bool = False


class AgentResponse(BaseModel):
    status: Literal["completed", "blocked", "clarification_required", "failed"]
    message: str
    citations: list[str] = Field(default_factory=list)
    completed_actions: list[str] = Field(default_factory=list)


class AgentRun(BaseModel):
    response: AgentResponse
    trace: list[TraceEvent] = Field(default_factory=list)
    termination_reason: str
