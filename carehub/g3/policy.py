"""C1 的服务端 PDP：身份只标识调用者，授权范围由关系库和同意账本推导。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from carehub.core.event_store import EventStore

if TYPE_CHECKING:
    from .service import ConsentLedger, PrivacyAccessRequest


@dataclass(frozen=True)
class AuthContext:
    """认证层输出；不得包含由客户端声明的角色、家庭或同意范围。"""
    actor_id: str
    tenant_id: str
    token_id: str = ""


@dataclass(frozen=True)
class PolicyRequest:
    household_id: str
    subject_id: str
    capability: str
    purpose: str
    classification: str
    channel: str
    consent_scope: str
    resource_version: str = ""
    correlation_id: str = ""


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    policy_version: str = "v1"
    consent_version: int = -1
    consent_id: str = ""
    resource_version: str = ""
    allowed_actions: tuple[str, ...] = ()


class ServerSidePDP:
    """默认拒绝的 RBAC + ABAC + Consent 判定点。"""
    # 这是产品端可执行的最小权限表；未列出的能力一律拒绝。
    role_capabilities = {
        "SELF": frozenset({"read_authorized_view", "memory_manage", "memory_revoke", "delete_personal_data"}),
        "FAMILY": frozenset({"read_authorized_view"}),
        "CARE_TEAM": frozenset({"read_authorized_view"}),
        "DETERMINISTIC_PLANNER": frozenset({"play_prompt", "request_safety_check", "notify_family", "read_timeline"}),
    }
    denied_capabilities = frozenset({"database_write", "mqtt_publish", "ble_control", "gpio_control", "shell", "arbitrary_http", "mark_medication_taken", "change_dose", "trigger_sos"})

    def __init__(self, store: EventStore, ledger: "ConsentLedger") -> None:
        self.store, self.ledger = store, ledger

    def authorize(self, context: AuthContext, request: PolicyRequest) -> PolicyDecision:
        if request.capability in self.denied_capabilities:
            return self._audit(context, request, False, "CAPABILITY_DENIED")
        if not self.store.scope_registered(tenant_id=context.tenant_id, household_id=request.household_id, subject_id=request.subject_id):
            return self._audit(context, request, False, "UNKNOWN_SCOPE")
        row = self.store.connection.execute(
            "SELECT m.role, s.principal_id FROM membership m LEFT JOIN subject_link s "
            "ON s.tenant_id=m.tenant_id AND s.subject_id=? AND s.principal_id=m.principal_id "
            "WHERE m.tenant_id=? AND m.household_id=? AND m.principal_id=?",
            (request.subject_id, context.tenant_id, request.household_id, context.actor_id),
        ).fetchone()
        if not row:
            return self._audit(context, request, False, "MEMBERSHIP_DENIED")
        role = row["role"]
        if request.capability not in self.role_capabilities.get(role, frozenset()):
            return self._audit(context, request, False, "RBAC_DENIED")
        if not row["principal_id"]:
            return self._audit(context, request, False, "SUBJECT_RELATION_DENIED")
        from .service import PrivacyAccessRequest
        access = PrivacyAccessRequest(context.actor_id, request.subject_id, request.household_id, role,
                                      request.consent_scope, request.purpose, request.classification,
                                      request.channel, context.tenant_id)
        consent = self.ledger.active_consent(access)
        if not consent:
            return self._audit(context, request, False, "CONSENT_OR_ABAC_DENIED")
        return self._audit(context, request, True, "ALLOW", consent_version=int(consent["version"]), consent_id=str(consent["consent_id"]), allowed_actions=self.role_capabilities.get(role, frozenset()))

    def _audit(self, context: AuthContext, request: PolicyRequest, allowed: bool, reason: str, consent_version: int = -1, consent_id: str = "", allowed_actions: frozenset[str] = frozenset()) -> PolicyDecision:
        self.store.record_audit(actor=context.actor_id, capability=request.capability,
                                decision="ALLOW" if allowed else "DENY", reason=reason,
                                resource=f"subject:{request.subject_id}", tenant_id=context.tenant_id,
                                household_id=request.household_id, subject_id=request.subject_id,
                                policy_version="v1", consent_version=str(consent_version), correlation_id=request.correlation_id)
        return PolicyDecision(allowed, reason, consent_version=consent_version, consent_id=consent_id, resource_version=request.resource_version,
                              allowed_actions=tuple(sorted(allowed_actions)) if allowed else ())
