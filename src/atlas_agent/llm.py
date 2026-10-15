"""Provider-neutral structured-generation interface and deterministic test double."""

from __future__ import annotations

import copy
import json
from collections.abc import Iterable
from typing import Any, Protocol

from pydantic import TypeAdapter


class StructuredLLM(Protocol):
    def generate(
        self, *, messages: list[dict[str, str]], response_model: TypeAdapter[Any]
    ) -> Any:
        """Return one object validated against response_model."""


class ScriptedLLM:
    """Return predefined decisions, enabling deterministic agent-loop tests."""

    def __init__(self, decisions: Iterable[dict[str, Any]]):
        self._decisions = iter(decisions)
        self.calls: list[list[dict[str, str]]] = []

    def generate(
        self, *, messages: list[dict[str, str]], response_model: TypeAdapter[Any]
    ) -> Any:
        self.calls.append(copy.deepcopy(messages))
        try:
            raw = next(self._decisions)
        except StopIteration as exc:
            raise RuntimeError("scripted_model_exhausted") from exc
        return response_model.validate_python(raw)


class OpenAICompatibleLLM:
    """Small optional adapter for an OpenAI-compatible chat-completions server."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout: float = 60.0,
        client: Any | None = None,
    ):
        if client is None:
            try:
                import httpx
            except ImportError as exc:  # pragma: no cover - depends on optional extra
                raise RuntimeError(
                    "Install the live extra: uv sync --extra live"
                ) from exc
            client = httpx.Client(timeout=timeout)
        self.client = client
        self.url = f"{base_url.rstrip('/')}/chat/completions"
        self.model = model
        self.api_key = api_key

    def generate(
        self, *, messages: list[dict[str, str]], response_model: TypeAdapter[Any]
    ) -> Any:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "agent_decision",
                    "strict": True,
                    "schema": response_model.json_schema(),
                },
            },
        }
        response = self.client.post(self.url, headers=headers, json=payload)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            content = json.dumps(content)
        return response_model.validate_json(content)
