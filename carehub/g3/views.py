"""C1 受保护投影视图：先判定、后取数，并裁剪为面向客户端的 DTO。"""
from __future__ import annotations

from typing import Any

from .policy import AuthContext, PolicyRequest, ServerSidePDP


class AuthorizedProjectionReader:
    def __init__(self, pdp: ServerSidePDP, projections: Any) -> None:
        self.pdp, self.projections = pdp, projections

    def read(self, *, context: AuthContext, household_id: str, subject_id: str, kind: str,
             purpose: str, channel: str = "TERMINAL", resource_version: str = "") -> dict[str, Any]:
        if kind not in {"alerts", "tasks", "timeline"}:
            return {"items": [], "reason_code": "POLICY_DENIED", "allowed_actions": []}
        decision = self.pdp.authorize(context, PolicyRequest(household_id, subject_id, "read_authorized_view",
            purpose, "SENSITIVE", channel, "view", resource_version))
        if not decision.allowed:
            return {"items": [], "reason_code": "POLICY_DENIED", "allowed_actions": []}
        loader = getattr(self.projections, f"{kind}_for")
        raw = loader(tenant_id=context.tenant_id, household_id=household_id, subject_id=subject_id)
        values = raw.values() if isinstance(raw, dict) else raw
        # 不返回原始 payload、关联 ID 或未为该视图定义的字段。
        fields = {
            "alerts": ("alert_id", "kind", "safety_level", "status", "occurred_at", "version", "quality", "source_refs"),
            "tasks": ("task_ref", "status", "evidence_state", "scheduled_at", "version", "quality", "source_refs"),
            "timeline": ("event_id", "event_type", "occurred_at"),
        }[kind]
        return {"items": [{field: item[field] for field in fields if field in item} for item in values],
                "reason_code": "ALLOW", "allowed_actions": list(decision.allowed_actions),
                "policy_version": decision.policy_version, "consent_version": decision.consent_version,
                "resource_version": decision.resource_version}
