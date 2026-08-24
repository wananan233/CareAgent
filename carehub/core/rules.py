"""S-1/S0 与 MVP S1 的确定性规则。无 LLM、无设备直写。"""

from __future__ import annotations

import hashlib
from typing import Any

from .events import new_event


FIXED_TEMPLATES = {
    "SOS": "已收到您的紧急求助，正在按本地安全流程处理。",
    "SMOKE_GAS": "检测到烟雾或燃气风险，请立即远离危险区域并按本地告警指引行动。",
    "FALL": "检测到可能跌倒。请您确认是否需要帮助。",
    "INACTIVITY": "您好，检测到您较长时间没有活动。请您确认是否安好。",
    "MEDICATION": "到服药提醒时间了。请按您的既定用药计划确认。",
    "DEVICE_OFFLINE": "设备连接异常，系统将继续使用可用的本地安全功能。",
}


class RuleEngine:
    def decide(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        """返回待追加的派生事实；所有分支均可确定性重放。"""
        event_type = event["payload"]["event_type"]
        common = {
            "tenant_id": event["tenant_id"],
            "subject_id": event["subject_id"],
            "household_id": event["household_id"],
            "correlation_id": event["correlation_id"],
            "causation_id": event["event_id"],
            # Derived events must be byte-for-byte stable on replay so the
            # event-id fingerprint provides true idempotency rather than a
            # timestamp/trace-dependent false conflict.
            "occurred_at": event["occurred_at"],
            "received_at": event["received_at"],
            "trace_id": event.get("trace_id"),
            "source": "RULE_ENGINE",
        }
        if event_type == "SOS_PRESSED":
            return self._alert("SOS", "S-1", event, common)
        if event_type in {"SMOKE_DETECTED", "GAS_DETECTED"}:
            return self._alert("SMOKE_GAS", "S-1", event, common)
        if event_type == "FALL_DETECTED" and event["quality"] != "LOW":
            return self._alert("FALL", "S0", event, common)
        if event_type == "INACTIVITY_DETECTED":
            return [self._rule_event(event, "wellbeing", "WELLBEING_CHECK_REQUESTED", {"template": FIXED_TEMPLATES["INACTIVITY"], "response_window_seconds": 120}, common)]
        if event_type == "MEDICATION_DUE":
            return [self._rule_event(event, "prompt", "PROMPT_REQUESTED", {"task_ref": event["aggregate"], "template": FIXED_TEMPLATES["MEDICATION"], "action": "request_play_reminder", "evidence_state": "UNKNOWN"}, common)]
        if event_type == "DEVICE_OFFLINE":
            return [self._rule_event(event, "offline", "FIXED_RESPONSE_READY", {"template": FIXED_TEMPLATES["DEVICE_OFFLINE"], "safety_level": "S0"}, common)]
        return []

    @staticmethod
    def _derived_id(event_id: str, discriminator: str) -> str:
        digest = hashlib.sha256(f"{event_id}:{discriminator}".encode("utf-8")).hexdigest()[:24]
        return f"evt-rule-{digest}"

    def _rule_event(self, event: dict[str, Any], discriminator: str, event_type: str, payload: dict[str, Any], common: dict[str, Any]) -> dict[str, Any]:
        return new_event(
            event_id=self._derived_id(event["event_id"], discriminator),
            aggregate=f"rule:{self._derived_id(event['event_id'], discriminator).removeprefix('evt-rule-')}",
            sequence=1,
            event_type=event_type,
            payload=payload,
            **common,
        )

    def _alert(self, kind: str, level: str, event: dict[str, Any], common: dict[str, Any]) -> list[dict[str, Any]]:
        alert_id = f"alert-{event['event_id']}"
        return [
            new_event(event_id=self._derived_id(event["event_id"], "alert"), aggregate=f"alert:{event['event_id']}", sequence=1, event_type="ALERT_RAISED", payload={"alert_id": alert_id, "kind": kind, "safety_level": level, "status": "ACTIVE"}, **common),
            new_event(event_id=self._derived_id(event["event_id"], "alert-response"), aggregate=f"alert:{event['event_id']}", sequence=2, event_type="FIXED_RESPONSE_READY", payload={"alert_id": alert_id, "template": FIXED_TEMPLATES[kind], "safety_level": level}, **common),
        ]
