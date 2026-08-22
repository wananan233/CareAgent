"""可由 Event Store 全量重建的当前状态投影。"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Iterable


IdentityKey = tuple[str, str, str, str]


@dataclass
class Projections:
    # 所有内部键都包含 tenant、household 与 subject；客户端必须经 *_for 方法读取。
    alerts: dict[IdentityKey, dict[str, Any]] = field(default_factory=dict)
    tasks: dict[IdentityKey, dict[str, Any]] = field(default_factory=dict)
    timeline: list[dict[str, Any]] = field(default_factory=list)

    @staticmethod
    def _key(event: dict[str, Any], resource_id: str) -> IdentityKey:
        return (event["tenant_id"], event["subject_id"], event["household_id"], resource_id)

    def apply(self, event: dict[str, Any]) -> None:
        payload = event["payload"]
        event_type = payload["event_type"]
        self.timeline.append({"event_id": event["event_id"], "event_type": event_type, "occurred_at": event["occurred_at"], "tenant_id": event["tenant_id"], "subject_id": event["subject_id"], "household_id": event["household_id"]})
        if event_type == "ALERT_RAISED":
            self.alerts[self._key(event, payload["alert_id"])] = {"status": "ACTIVE", "occurred_at": event["occurred_at"], "version": 1, "quality": event["quality"], "source_refs": [event["event_id"]], **payload}
        elif event_type == "ALERT_RESOLVED":
            alert = self.alerts.get(self._key(event, payload["alert_id"]))
            if alert:
                alert["status"] = "RESOLVED"
        elif event_type == "MEDICATION_DUE":
            self.tasks[self._key(event, event["aggregate"])] = {"status": "DUE", "evidence_state": "UNKNOWN", "scheduled_at": event["occurred_at"], "version": 1, "quality": event["quality"], "source_refs": [event["event_id"]], **payload}
        elif event_type == "PROMPT_REQUESTED":
            task = self.tasks.setdefault(self._key(event, payload["task_ref"]), {})
            task["last_prompt_event_id"] = event["event_id"]
        elif event_type == "MEDICATION_EVIDENCE_RECORDED":
            task = self.tasks.setdefault(self._key(event, payload["task_ref"]), {})
            task["evidence_state"] = payload["evidence_state"]

    def alerts_for(self, *, tenant_id: str = "tenant:synthetic", subject_id: str, household_id: str) -> dict[str, dict[str, Any]]:
        return {
            alert_id: dict(alert)
            for (item_tenant, item_subject, item_household, alert_id), alert in self.alerts.items()
            if item_tenant == tenant_id and item_subject == subject_id and item_household == household_id
        }

    def tasks_for(self, *, tenant_id: str = "tenant:synthetic", subject_id: str, household_id: str) -> dict[str, dict[str, Any]]:
        return {
            task_ref: dict(task)
            for (item_tenant, item_subject, item_household, task_ref), task in self.tasks.items()
            if item_tenant == tenant_id and item_subject == subject_id and item_household == household_id
        }

    def timeline_for(self, *, tenant_id: str = "tenant:synthetic", subject_id: str, household_id: str) -> list[dict[str, Any]]:
        return [dict(item) for item in self.timeline if item["tenant_id"] == tenant_id and item["subject_id"] == subject_id and item["household_id"] == household_id]

    @classmethod
    def rebuild(cls, events: Iterable[dict[str, Any]]) -> "Projections":
        projection = cls()
        for event in events:
            projection.apply(event)
        return projection

    def digest(self) -> str:
        raw = json.dumps({"alerts": sorted((list(key), value) for key, value in self.alerts.items()), "tasks": sorted((list(key), value) for key, value in self.tasks.items()), "timeline": self.timeline}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()
