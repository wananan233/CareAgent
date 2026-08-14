"""S-1/S0 与 MVP S1 的确定性规则。无 LLM、无设备直写。"""

from __future__ import annotations

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
        common = {"correlation_id": event["correlation_id"], "causation_id": event["event_id"], "source": "RULE_ENGINE"}
        aggregate = event["aggregate"]
        seq = event["sequence"] + 1
        if event_type == "SOS_PRESSED":
            return self._alert(aggregate, seq, "SOS", "S-1", event, common)
        if event_type in {"SMOKE_DETECTED", "GAS_DETECTED"}:
            return self._alert(aggregate, seq, "SMOKE_GAS", "S-1", event, common)
        if event_type == "FALL_DETECTED" and event["quality"] != "LOW":
            return self._alert(aggregate, seq, "FALL", "S0", event, common)
        if event_type == "INACTIVITY_DETECTED":
            return [new_event(aggregate=aggregate, sequence=seq, event_type="WELLBEING_CHECK_REQUESTED", payload={"template": FIXED_TEMPLATES["INACTIVITY"], "response_window_seconds": 120}, **common)]
        if event_type == "MEDICATION_DUE":
            return [new_event(aggregate=aggregate, sequence=seq, event_type="PROMPT_REQUESTED", payload={"task_ref": aggregate, "template": FIXED_TEMPLATES["MEDICATION"], "action": "request_play_reminder", "evidence_state": "UNKNOWN"}, **common)]
        if event_type == "DEVICE_OFFLINE":
            return [new_event(aggregate=aggregate, sequence=seq, event_type="FIXED_RESPONSE_READY", payload={"template": FIXED_TEMPLATES["DEVICE_OFFLINE"], "safety_level": "S0"}, **common)]
        return []

    def _alert(self, aggregate: str, sequence: int, kind: str, level: str, event: dict[str, Any], common: dict[str, Any]) -> list[dict[str, Any]]:
        alert_id = f"alert-{event['event_id']}"
        return [
            new_event(aggregate=aggregate, sequence=sequence, event_type="ALERT_RAISED", payload={"alert_id": alert_id, "kind": kind, "safety_level": level, "status": "ACTIVE"}, **common),
            new_event(aggregate=f"alert:{alert_id}", sequence=1, event_type="FIXED_RESPONSE_READY", payload={"alert_id": alert_id, "template": FIXED_TEMPLATES[kind], "safety_level": level}, **common),
        ]
