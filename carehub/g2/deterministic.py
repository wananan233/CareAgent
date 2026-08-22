"""G2 确定性 CareAgent：无模型、无真实副作用。"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any
from carehub.core.event_store import EventStore
from carehub.g3 import AuthContext, ConsentLedger, PolicyRequest, ServerSidePDP
from .chat import build_context_snapshot
from .response import ResponseEngine

def _now() -> str: return datetime.now(timezone.utc).isoformat(timespec="seconds")
WORKFLOWS = {
    "MEDICATION_REMINDER": ("request_play_reminder", "play_prompt", "到服药提醒时间了。请按既定用药计划确认。"),
    "INACTIVITY_CHECK": ("request_wellbeing_check", "request_safety_check", "您好，检测到较长时间没有活动。请确认是否安好。"),
    "FALL_FOLLOW_UP": ("request_wellbeing_check", "request_safety_check", "检测到可能跌倒。请确认是否需要帮助。"),
    "DAILY_SUMMARY": ("draft_daily_summary", "read_timeline", "这是基于当前已确认记录的今日摘要。"),
    "FAMILY_ESCALATION": ("send_authorized_notification", "notify_family", "已生成经授权的家属通知请求。"),
}
class PolicyGateway:
    """G2 对 C1 PDP 的窄适配层，已不信任调用方提交的 consent_scopes。"""
    required_scopes = {"play_prompt":"medication_reminder", "request_safety_check":"safety_check", "notify_family":"family_notification", "read_timeline":"daily_summary"}
    def __init__(self, store: EventStore) -> None:
        self.store = store; self.ledger = ConsentLedger(store); self.pdp = ServerSidePDP(store, self.ledger)
    def authorize(self, *, context: AuthContext, household_id: str, subject_id: str, capability: str, purpose: str, channel: str, idempotency_key: str) -> tuple[bool, str]:
        if not idempotency_key:
            return False, "IDEMPOTENCY_KEY_REQUIRED"
        scope = self.required_scopes.get(capability)
        if not scope:
            return False, "CAPABILITY_DENIED"
        decision = self.pdp.authorize(context, PolicyRequest(household_id, subject_id, capability, purpose, "SENSITIVE", channel, scope))
        return decision.allowed, decision.reason
class MockSkillExecutor:
    def __init__(self, store: EventStore) -> None: self.store = store
    def invoke(self, intent: dict[str, Any]) -> dict[str, Any]:
        result={"schema_version":"SkillInvocationResultV1","invocation_id":f"inv-{uuid.uuid4()}","intent_id":intent["intent_id"],"skill_id":intent["skill_id"],"skill_version":"v1","status":"SUCCEEDED","evidence_event_ids":intent["source_event_ids"]}
        return self.store.execute_once(idempotency_key=intent["idempotency_key"],intent_id=intent["intent_id"],result=result)[1]
class ChannelMocks:
    def __init__(self) -> None: self.ui=[]; self.tts=[]; self.family=[]
    def deliver(self, channel: str, response: dict[str, Any]) -> None: {"TERMINAL":self.ui,"TTS":self.tts,"FAMILY":self.family}[channel].append(response)
class DeterministicAgent:
    def __init__(self, store: EventStore, policy: PolicyGateway|None=None, executor: MockSkillExecutor|None=None, channels: ChannelMocks|None=None) -> None:
        self.store=store; self.policy=policy or PolicyGateway(store); self.executor=executor or MockSkillExecutor(store); self.channels=channels or ChannelMocks(); self.response_engine=ResponseEngine()
    def run(self, *, subject_id: str, purpose: str, trigger_event_ids: list[str], channel: str,
            tenant_id: str="tenant:synthetic", household_id: str="household:synthetic-home",
            auth_context: AuthContext|None=None) -> dict[str, Any]:
        if purpose not in WORKFLOWS or not trigger_event_ids: raise ValueError("不支持的工作流或缺少触发事件")
        run_id=f"run-{uuid.uuid4()}"; now=_now(); self.store.create_agent_run({"agent_run_id":run_id,"subject_id":subject_id,"purpose":purpose,"trigger_event_ids":trigger_event_ids,"channel":channel,"status":"RECEIVED","context_snapshot_id":None,"plan_id":None,"reason_code":None,"correlation_id":f"corr-{uuid.uuid4()}","created_at":now,"updated_at":now,"version":1})
        run=self.store.transition_agent_run(run_id,1,status="CONTEXT_BUILDING",updated_at=_now()); skill,capability,template=WORKFLOWS[purpose]
        task={"task_id":f"task-{run_id}","subject_id":subject_id,"kind":purpose,"status":"DUE","safety_level":"S0" if purpose in {"INACTIVITY_CHECK","FALL_FOLLOW_UP"} else "S1","source_event_ids":trigger_event_ids,"reschedulable":purpose=="DAILY_SUMMARY","max_delay_seconds":300 if purpose=="DAILY_SUMMARY" else 0,"version":1,"updated_at":_now()}; self.store.upsert_care_task(task)
        snapshot=build_context_snapshot(subject_id=subject_id,purpose=purpose,source_event_ids=trigger_event_ids,consent_scopes=[],consent_expires_at="2099-01-01T00:00:00+00:00",facts=[{"text":f"任务 {task['task_id']} 状态：DUE。","source_refs":trigger_event_ids}]); self.store.save_context_snapshot(snapshot)
        run=self.store.transition_agent_run(run_id,run["version"],status="CONTEXT_READY",context_snapshot_id=snapshot["snapshot_id"],updated_at=_now()); run=self.store.transition_agent_run(run_id,run["version"],status="PLANNING",updated_at=_now())
        plan={"schema_version":"PlanV1","plan_id":f"plan-{uuid.uuid4()}","agent_run_id":run_id,"context_snapshot_id":snapshot["snapshot_id"],"goal":purpose,"safety_level":"S1" if purpose not in {"INACTIVITY_CHECK","FALL_FOLLOW_UP"} else "S1","steps":[{"skill_id":skill,"skill_version":"v1"}],"approval_required":False,"expires_at":"2099-01-01T00:00:00+00:00","planner_version":"deterministic-g2.v1"}; self.store.save_plan(plan); run=self.store.transition_agent_run(run_id,run["version"],status="PLAN_PROPOSED",plan_id=plan["plan_id"],updated_at=_now()); run=self.store.transition_agent_run(run_id,run["version"],status="POLICY_CHECKING",updated_at=_now()); intent={"intent_id":f"intent-{uuid.uuid4()}","skill_id":skill,"capability":capability,"source_event_ids":trigger_event_ids,"idempotency_key":f"{run_id}:{skill}"}
        context=auth_context or AuthContext("system:deterministic-planner", tenant_id)
        allowed,reason=self.policy.authorize(context=context,household_id=household_id,subject_id=subject_id,capability=capability,purpose=purpose,channel=channel,idempotency_key=intent["idempotency_key"])
        if not allowed: self.store.transition_agent_run(run_id,run["version"],status="DENIED",reason_code=reason,updated_at=_now()); return self._respond(run_id,channel,template,trigger_event_ids,"DETERMINISTIC_FALLBACK",reason)
        run=self.store.transition_agent_run(run_id,run["version"],status="EXECUTING",updated_at=_now()); result=self.executor.invoke(intent); self.store.transition_agent_run(run_id,run["version"],status="COMPLETED",reason_code=result["status"],updated_at=_now()); return self._respond(run_id,channel,template,trigger_event_ids,"NONE",result["status"])
    def _respond(self,run_id:str,channel:str,message:str,refs:list[str],fallback:str,reason:str)->dict[str,Any]:
        response=self.response_engine.render(agent_run_id=run_id,channel=channel,template=message,facts=[{"text":reason,"source_refs":refs}])
        if fallback != "NONE": response["fallback"]=fallback
        self.channels.deliver(channel,response); return response
