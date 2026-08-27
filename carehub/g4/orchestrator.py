"""C4 目的受限编排，只把已授权最小上下文送入受控网关。"""
from __future__ import annotations
import uuid
import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from carehub.core.event_store import EventStore
from carehub.g3 import AuthContext, PolicyRequest, ServerSidePDP
from .gateway import ALLOWED_PURPOSES, ModelGateway, TEMPLATES

class AgentOrchestrator:
    def __init__(self, store: EventStore, pdp: ServerSidePDP, gateway: ModelGateway | None = None) -> None:
        self.store, self.pdp, self.gateway = store, pdp, gateway or ModelGateway()
    def run(self, *, context: AuthContext, household_id: str, subject_id: str, purpose: str, minimal_context: dict[str, Any]) -> dict[str, Any]:
        run_id = f"run-{uuid.uuid4()}"
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        source_refs = sorted({ref for fact in minimal_context.get("facts", []) if isinstance(fact, dict) for ref in fact.get("source_refs", []) if isinstance(ref, str)})
        if purpose not in ALLOWED_PURPOSES:
            return self._reject(run_id=run_id, now=now, context=context, household_id=household_id,
                                subject_id=subject_id, purpose=purpose, reason_code="PURPOSE_DENIED", source_refs=source_refs)
        if purpose == "READ_ONLY_QA" and not source_refs:
            return self._reject(run_id=run_id, now=now, context=context, household_id=household_id,
                                subject_id=subject_id, purpose=purpose, reason_code="INSUFFICIENT_SOURCES", source_refs=[])
        decision = self.pdp.authorize(context, PolicyRequest(household_id, subject_id, "read_authorized_view", purpose, "SENSITIVE", "TERMINAL", "agent_view"))
        if not decision.allowed:
            return self._reject(run_id=run_id, now=now, context=context, household_id=household_id,
                                subject_id=subject_id, purpose=purpose, reason_code="POLICY_DENIED", source_refs=source_refs,
                                policy_version=decision.policy_version)
        self.store.create_agent_run({"agent_run_id":run_id,"subject_id":subject_id,"purpose":purpose,"trigger_event_ids":[],"channel":"TERMINAL","status":"EXECUTING","context_snapshot_id":None,"plan_id":None,"reason_code":None,"correlation_id":f"agent-{uuid.uuid4()}","created_at":now,"updated_at":now,"version":1,"tenant_id":context.tenant_id,"household_id":household_id,"consent_id":decision.consent_id,"consent_version":decision.consent_version,"policy_version":decision.policy_version,"source_refs":source_refs})
        snapshot = hashlib.sha256(json.dumps(minimal_context.get("facts", []), ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        fingerprint = f"{snapshot}:{purpose}:{decision.consent_id}:{decision.consent_version}:{decision.policy_version}"
        result = self.gateway.generate(purpose=purpose, minimal_context=minimal_context, authorization_fingerprint=fingerprint)
        run = self.store.agent_run(run_id)
        self.store.transition_agent_run(run_id, run["version"], status="COMPLETED", reason_code=result["reason_code"], updated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        return {**result, "agent_run_id":run_id, "policy_version":decision.policy_version, "consent_version":decision.consent_version}

    def _reject(self, *, run_id: str, now: str, context: AuthContext, household_id: str, subject_id: str,
                purpose: str, reason_code: str, source_refs: list[str], policy_version: str = "v1") -> dict[str, Any]:
        """拒绝同样留存最小审计记录，并返回可验证的受控模板响应。"""
        self.store.create_agent_run({"agent_run_id":run_id, "subject_id":subject_id, "purpose":purpose,
            "trigger_event_ids":[], "channel":"TERMINAL", "status":"REJECTED", "context_snapshot_id":None,
            "plan_id":None, "reason_code":reason_code, "correlation_id":f"agent-{uuid.uuid4()}",
            "created_at":now, "updated_at":now, "version":1, "tenant_id":context.tenant_id,
            "household_id":household_id, "policy_version":policy_version, "source_refs":source_refs})
        return {"message": TEMPLATES.get(purpose, "当前请求无法处理。"), "facts": [],
                "fallback": "TEMPLATE_FALLBACK", "generator_version": "response-template-g4.v1",
                "agent_run_id":run_id, "policy_version":policy_version, "consent_version":-1,
                "reason_code":reason_code}
