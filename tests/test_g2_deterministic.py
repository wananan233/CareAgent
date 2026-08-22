"""G2 确定性 Agent、策略和 Mock 通道测试。"""
import pytest
from carehub.core.event_store import EventStore
from carehub.g2 import ChannelMocks, DeterministicAgent, PolicyGateway
from carehub.g3 import AuthContext, ConsentLedger

SCOPES={"MEDICATION_REMINDER":["medication_reminder"],"INACTIVITY_CHECK":["safety_check"],"FALL_FOLLOW_UP":["safety_check"],"DAILY_SUMMARY":["daily_summary"],"FAMILY_ESCALATION":["family_notification"]}
@pytest.fixture
def store(tmp_path):
    value=EventStore(tmp_path/"g2.db"); yield value; value.close()
def authorize_planner(store, purpose, channel="TERMINAL"):
    store.register_scope(tenant_id="tenant:synthetic", household_id="household:synthetic-home", subject_id="user:synthetic-01", principal_id="user:synthetic-01", role="SELF")
    store.register_scope(tenant_id="tenant:synthetic", household_id="household:synthetic-home", subject_id="user:synthetic-01", principal_id="system:deterministic-planner", role="DETERMINISTIC_PLANNER")
    consent = ConsentLedger(store).grant(owner="user:synthetic-01", grantee="system:deterministic-planner", household_id="household:synthetic-home", scope=SCOPES[purpose][0], purpose=purpose, channel=channel)
    ConsentLedger(store).activate(consent["consent_id"], actor="user:synthetic-01", expected_version=1)
    return AuthContext("system:deterministic-planner", "tenant:synthetic")
@pytest.mark.parametrize("purpose,channel",[("MEDICATION_REMINDER","TTS"),("INACTIVITY_CHECK","TTS"),("FALL_FOLLOW_UP","TERMINAL"),("DAILY_SUMMARY","TERMINAL"),("FAMILY_ESCALATION","FAMILY")])
def test_five_deterministic_workflows(store,purpose,channel):
    channels=ChannelMocks(); response=DeterministicAgent(store,channels=channels).run(subject_id="user:synthetic-01",purpose=purpose,trigger_event_ids=["evt-g2-01"],channel=channel,auth_context=authorize_planner(store,purpose,channel))
    assert response["fallback"]=="NONE" and response["generator_version"]=="response-template-g2.v1"
    assert store.agent_run(response["agent_run_id"])["status"]=="COMPLETED"
    assert len({"TERMINAL":channels.ui,"TTS":channels.tts,"FAMILY":channels.family}[channel])==1
def test_policy_rejects_missing_consent_and_cross_user(store):
    agent=DeterministicAgent(store); response=agent.run(subject_id="user:synthetic-01",purpose="MEDICATION_REMINDER",trigger_event_ids=["evt"],channel="TTS")
    assert response["fallback"]=="DETERMINISTIC_FALLBACK"
    assert store.agent_run(response["agent_run_id"])["status"]=="DENIED"
    assert PolicyGateway(store).authorize(context=AuthContext("system:deterministic-planner", "tenant:synthetic"),household_id="household:synthetic-home",subject_id="other",capability="play_prompt",purpose="MEDICATION_REMINDER",channel="TTS",idempotency_key="x")[0] is False
def test_executor_idempotency_and_run_version_conflict(store):
    result={"status":"SUCCEEDED","value":"mock"}
    assert store.execute_once(idempotency_key="same",intent_id="intent-one",result=result)[0] is True
    assert store.execute_once(idempotency_key="same",intent_id="intent-two",result={"status":"FAILED"})==(False,result)
    run={"agent_run_id":"run-version","subject_id":"user:synthetic-01","purpose":"DAILY_SUMMARY","trigger_event_ids":["evt"],"channel":"TERMINAL","status":"RECEIVED","context_snapshot_id":None,"plan_id":None,"reason_code":None,"correlation_id":"corr-version","created_at":"2026-01-01T00:00:00+00:00","updated_at":"2026-01-01T00:00:00+00:00","version":1}
    assert store.create_agent_run(run) is True
    with pytest.raises(ValueError,match="版本冲突"): store.transition_agent_run("run-version",2,status="FAILED")

def test_run_persists_task_context_and_plan_across_restart(tmp_path):
    path=tmp_path/"recovery.db"; store=EventStore(path)
    response=DeterministicAgent(store).run(subject_id="user:synthetic-01",purpose="MEDICATION_REMINDER",trigger_event_ids=["evt-recovery"],channel="TTS",auth_context=authorize_planner(store,"MEDICATION_REMINDER", "TTS"))
    run=store.agent_run(response["agent_run_id"]); store.close()
    restored=EventStore(path)
    assert run and run["status"]=="COMPLETED"
    assert restored.context_snapshot(run["context_snapshot_id"])["hash"]
    assert restored.plan(run["plan_id"])["steps"]==[{"skill_id":"request_play_reminder","skill_version":"v1"}]
    assert restored.care_tasks("user:synthetic-01")[0]["kind"]=="MEDICATION_REMINDER"
    restored.close()
