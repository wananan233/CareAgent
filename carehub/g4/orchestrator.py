"""C4 目的受限编排，只把已授权最小上下文送入受控网关。"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any
from carehub.core.event_store import EventStore
from carehub.g3 import AuthContext, PolicyRequest, ServerSidePDP
from .gateway import ALLOWED_PURPOSES, ModelGateway

class AgentOrchestrator:
    def __init__(self, store: EventStore, pdp: ServerSidePDP, gateway: ModelGateway | None = None) -> None:
        self.store, self.pdp, self.gateway = store, pdp, gateway or ModelGateway()
    def run(self, *, context: AuthContext, household_id: str, subject_id: str, purpose: str, minimal_context: dict[str, Any]) -> dict[str, Any]:
        if purpose not in ALLOWED_PURPOSES: return {"fallback": "TEMPLATE_FALLBACK", "reason_code": "PURPOSE_DENIED", "facts": []}
        decision = self.pdp.authorize(context, PolicyRequest(household_id, subject_id, "read_authorized_view", purpose, "SENSITIVE", "TERMINAL", "agent_view"))
        if not decision.allowed: return {"fallback": "TEMPLATE_FALLBACK", "reason_code": "POLICY_DENIED", "facts": []}
        run_id = f"run-{uuid.uuid4()}"; now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.store.create_agent_run({"agent_run_id":run_id,"subject_id":subject_id,"purpose":purpose,"trigger_event_ids":[],"channel":"TERMINAL","status":"EXECUTING","context_snapshot_id":None,"plan_id":None,"reason_code":None,"correlation_id":f"agent-{uuid.uuid4()}","created_at":now,"updated_at":now,"version":1,"tenant_id":context.tenant_id,"household_id":household_id,"consent_id":decision.consent_id,"consent_version":decision.consent_version,"policy_version":decision.policy_version,"source_refs":sorted({ref for fact in minimal_context.get("facts", []) if isinstance(fact, dict) for ref in fact.get("source_refs", []) if isinstance(ref, str)})})
        result = self.gateway.generate(purpose=purpose, minimal_context=minimal_context)
        run = self.store.agent_run(run_id)
        self.store.transition_agent_run(run_id, run["version"], status="COMPLETED", reason_code=result["reason_code"], updated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        return {**result, "agent_run_id":run_id, "policy_version":decision.policy_version, "consent_version":decision.consent_version}
