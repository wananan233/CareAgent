"""可由 Event Store 全量重建的当前状态投影。"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass
class Projections:
    alerts: dict[str, dict[str, Any]] = field(default_factory=dict)
    tasks: dict[str, dict[str, Any]] = field(default_factory=dict)
    timeline: list[dict[str, Any]] = field(default_factory=list)

    def apply(self, event: dict[str, Any]) -> None:
        payload = event["payload"]
        event_type = payload["event_type"]
        self.timeline.append({"event_id": event["event_id"], "event_type": event_type, "occurred_at": event["occurred_at"]})
        if event_type == "ALERT_RAISED":
            self.alerts[payload["alert_id"]] = {"status": "ACTIVE", **payload}
        elif event_type == "ALERT_RESOLVED":
            alert = self.alerts.get(payload["alert_id"])
            if alert:
                alert["status"] = "RESOLVED"
        elif event_type == "MEDICATION_DUE":
            self.tasks[event["aggregate"]] = {"status": "DUE", "evidence_state": "UNKNOWN", **payload}
        elif event_type == "PROMPT_REQUESTED":
            task = self.tasks.setdefault(payload["task_ref"], {})
            task["last_prompt_event_id"] = event["event_id"]
        elif event_type == "MEDICATION_EVIDENCE_RECORDED":
            task = self.tasks.setdefault(payload["task_ref"], {})
            task["evidence_state"] = payload["evidence_state"]

    @classmethod
    def rebuild(cls, events: Iterable[dict[str, Any]]) -> "Projections":
        projection = cls()
        for event in events:
            projection.apply(event)
        return projection

    def digest(self) -> str:
        raw = json.dumps({"alerts": self.alerts, "tasks": self.tasks, "timeline": self.timeline}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()
