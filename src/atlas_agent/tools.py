"""Typed tool contracts and deterministic dispatch supplied to students."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from .models import ToolObservation
from .retrieval import PolicyRetriever
from .simulator import LabSimulator


class SearchArguments(BaseModel):
    query: str
    document_types: list[str] | None = None
    top_k: int = Field(default=5, ge=1, le=10)


class AuthorizationArguments(BaseModel):
    user_id: str


class ResourceStatusArguments(BaseModel):
    resource_id: str
    start: str
    end: str


class ReservationArguments(ResourceStatusArguments):
    user_id: str
    project_id: str


ARGUMENT_MODELS: dict[str, type[BaseModel]] = {
    "search_lab_documents": SearchArguments,
    "get_user_authorizations": AuthorizationArguments,
    "get_resource_status": ResourceStatusArguments,
    "reserve_resource": ReservationArguments,
}

MUTATING_TOOLS = {"reserve_resource"}


class ToolEnvironment:
    def __init__(self, simulator: LabSimulator, corpus_path: str | Path):
        self.simulator = simulator
        self.retriever = PolicyRetriever(corpus_path)

    def dispatch(self, tool: str, arguments: dict[str, Any]) -> ToolObservation:
        model = ARGUMENT_MODELS.get(tool)
        if model is None:
            return ToolObservation(ok=False, tool=tool, error_code="unknown_tool")
        try:
            args = model.model_validate(arguments)
        except ValidationError as exc:
            return ToolObservation(
                ok=False,
                tool=tool,
                error_code="invalid_arguments",
                message=str(exc),
            )

        try:
            if isinstance(args, SearchArguments):
                passages = self.retriever.search(
                    args.query,
                    document_types=args.document_types,
                    top_k=args.top_k,
                )
                return ToolObservation(
                    ok=True,
                    tool=tool,
                    data={"passages": [p.model_dump() for p in passages]},
                )
            if isinstance(args, AuthorizationArguments):
                result = self.simulator.user_authorizations(args.user_id)
                if result is None:
                    return ToolObservation(
                        ok=False, tool=tool, error_code="unknown_user"
                    )
                return ToolObservation(ok=True, tool=tool, data=result)
            if isinstance(args, ResourceStatusArguments) and not isinstance(
                args, ReservationArguments
            ):
                result = self.simulator.resource_status(
                    args.resource_id, args.start, args.end
                )
                if result is None:
                    return ToolObservation(
                        ok=False, tool=tool, error_code="unknown_resource"
                    )
                return ToolObservation(ok=True, tool=tool, data=result)
            if isinstance(args, ReservationArguments):
                result = self.simulator.reserve(**args.model_dump())
                return ToolObservation(ok=True, tool=tool, data=result)
        except ValueError as exc:
            return ToolObservation(ok=False, tool=tool, error_code=str(exc))

        return ToolObservation(ok=False, tool=tool, error_code="dispatch_error")
