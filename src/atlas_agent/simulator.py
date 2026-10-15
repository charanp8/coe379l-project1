"""JSON-backed laboratory state. The simulator resets for every scenario."""

from __future__ import annotations

import copy
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value)


class LabSimulator:
    def __init__(self, initial_state: dict[str, Any]):
        self._initial_state = copy.deepcopy(initial_state)
        self.state = copy.deepcopy(initial_state)

    @classmethod
    def from_file(cls, path: str | Path) -> LabSimulator:
        return cls(json.loads(Path(path).read_text()))

    def reset(self) -> None:
        self.state = copy.deepcopy(self._initial_state)

    def user_authorizations(self, user_id: str) -> dict[str, Any] | None:
        user = self.state["users"].get(user_id)
        return copy.deepcopy(user) if user else None

    def resource_status(
        self, resource_id: str, start: str, end: str
    ) -> dict[str, Any] | None:
        resource = self.state["resources"].get(resource_id)
        if not resource:
            return None
        requested_start, requested_end = _time(start), _time(end)
        conflicts = []
        for reservation in self.state["reservations"]:
            if (
                reservation["resource_id"] != resource_id
                or reservation["status"] != "confirmed"
            ):
                continue
            if (
                requested_start < _time(reservation["end"])
                and _time(reservation["start"]) < requested_end
            ):
                conflicts.append(reservation["reservation_id"])
        return {
            **copy.deepcopy(resource),
            "resource_id": resource_id,
            "available": not conflicts,
            "conflicting_reservation_ids": conflicts,
            "calibration_current": _time(resource["calibration_expires"])
            >= requested_end,
        }

    def reserve(
        self,
        *,
        user_id: str,
        project_id: str,
        resource_id: str,
        start: str,
        end: str,
    ) -> dict[str, Any]:
        """Enforce mechanics only—not training, approval, or project policy."""
        if resource_id not in self.state["resources"]:
            raise ValueError("unknown_resource")
        if _time(start) >= _time(end):
            raise ValueError("invalid_interval")
        status = self.resource_status(resource_id, start, end)
        if status is None or not status["available"]:
            raise ValueError("reservation_conflict")
        reservation = {
            "reservation_id": f"r-{uuid4().hex[:10]}",
            "user_id": user_id,
            "project_id": project_id,
            "resource_id": resource_id,
            "start": start,
            "end": end,
            "status": "confirmed",
        }
        self.state["reservations"].append(reservation)
        return copy.deepcopy(reservation)
