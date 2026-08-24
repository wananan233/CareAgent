"""将 G1 投影转换为模型可读、可追溯的最小授权聊天快照。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from carehub.core.projections import Projections

from .chat import build_context_snapshot


def build_chat_context_from_g1(
    *,
    projections: Projections,
    events: Iterable[dict[str, Any]],
    tenant_id: str,
    subject_id: str,
    household_id: str,
    consent_expires_at: str,
) -> dict[str, Any]:
    """仅从活动告警和服药任务生成带事件出处的事实，不传递原始 payload。"""
    event_list = [
        event for event in events
        if event["tenant_id"] == tenant_id and event["subject_id"] == subject_id and event["household_id"] == household_id
    ]
    alert_sources = {
        event["payload"].get("alert_id"): event["event_id"]
        for event in event_list
        if event["payload"].get("event_type") == "ALERT_RAISED"
    }
    task_sources = {
        event["aggregate"]: event["event_id"]
        for event in event_list
        if event["payload"].get("event_type") == "MEDICATION_DUE"
    }
    facts: list[dict[str, Any]] = []
    unknowns: list[dict[str, str]] = []

    for alert_id, alert in sorted(projections.alerts_for(tenant_id=tenant_id, subject_id=subject_id, household_id=household_id).items()):
        if alert.get("status") != "ACTIVE" or alert_id not in alert_sources:
            continue
        facts.append(
            {
                "text": f"活动安全告警：{alert['kind']}，安全等级 {alert['safety_level']}。",
                "source_refs": [alert_sources[alert_id]],
            }
        )

    for task_ref, task in sorted(projections.tasks_for(tenant_id=tenant_id, subject_id=subject_id, household_id=household_id).items()):
        source_event_id = task_sources.get(task_ref)
        if not source_event_id:
            continue
        facts.append(
            {
                "text": f"服药任务 {task_ref} 当前状态：{task.get('status', 'UNKNOWN')}；证据状态：{task.get('evidence_state', 'UNKNOWN')}。",
                "source_refs": [source_event_id],
            }
        )
        if task.get("evidence_state", "UNKNOWN") == "UNKNOWN":
            unknowns.append({"field": f"medication_evidence:{task_ref}", "reason": "UNKNOWN"})

    source_event_ids = [source for fact in facts for source in fact["source_refs"]]
    if not source_event_ids:
        raise ValueError("当前 G1 投影没有可授权给聊天的事实")
    return build_context_snapshot(
        subject_id=subject_id,
        source_event_ids=source_event_ids,
        consent_scopes=["chat"],
        consent_expires_at=consent_expires_at,
        unknowns=unknowns,
        facts=facts,
        as_of=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
