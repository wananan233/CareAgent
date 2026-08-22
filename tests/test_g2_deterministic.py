"""G2 确定性 Agent、策略和 Mock 通道测试。"""
import pytest
from carehub.core.event_store import EventStore
from carehub.g2 import ChannelMocks, DeterministicAgent, PolicyGateway

SCOPES={"MEDICATION_REMINDER":["medication_reminder"],"INACTIVITY_CHECK":["safety_check"],"FALL_FOLLOW_UP":["safety_check"],"DAILY_SUMMARY":["daily_summary"],"FAMILY_ESCALATION":["family_notification"]}
@pytest.fixture
def store(tmp_path):
    value=EventStore(tmp_path/"g2.db"); yield value; value.close()
@pytest.mark.parametrize("purpose,channel",[("MEDICATION_REMINDER","TTS"),("INACTIVITY_CHECK","TTS"),("FALL_FOLLOW_UP","TERMINAL"),("DAILY_SUMMARY","TERMINAL"),("FAMILY_ESCALATION","FAMILY")])
def test_five_deterministic_workflows(store,purpose,channel):
    channels=ChannelMocks(); response=DeterministicAgent(store,channels=channels).run(subject_id="user:synthetic-01",purpose=purpose,trigger_event_ids=["evt-g2-01"],channel=channel,consent_scopes=SCOPES[purpose])
    assert response["fallback"]=="NONE" and response["generator_version"]=="response-template-g2.v1"
    assert store.agent_run(response["agent_run_id"])["status"]=="COMPLETED"
    assert len({"TERMINAL":channels.ui,"TTS":channels.tts,"FAMILY":channels.family}[channel])==1
def test_policy_rejects_missing_consent_and_cross_user(store):
    agent=DeterministicAgent(store); response=agent.run(subject_id="user:synthetic-01",purpose="MEDICATION_REMINDER",trigger_event_ids=["evt"],channel="TTS",consent_scopes=[])
    assert response["fallback"]=="DETERMINISTIC_FALLBACK"
    assert store.agent_run(response["agent_run_id"])["status"]=="DENIED"
    assert PolicyGateway().authorize(actor="DETERMINISTIC_PLANNER",subject_id="other",capability="play_prompt",consent_scopes=["medication_reminder"],idempotency_key="x")[0] is False
def test_executor_idempotency_and_run_version_conflict(store):
    result={"status":"SUCCEEDED","value":"mock"}
    assert store.execute_once(idempotency_key="same",intent_id="intent-one",result=result)[0] is True
    assert store.execute_once(idempotency_key="same",intent_id="intent-two",result={"status":"FAILED"})==(False,result)
    run={"agent_run_id":"run-version","subject_id":"user:synthetic-01","purpose":"DAILY_SUMMARY","trigger_event_ids":["evt"],"channel":"TERMINAL","status":"RECEIVED","context_snapshot_id":None,"plan_id":None,"reason_code":None,"correlation_id":"corr-version","created_at":"2026-01-01T00:00:00+00:00","updated_at":"2026-01-01T00:00:00+00:00","version":1}
    assert store.create_agent_run(run) is True
    with pytest.raises(ValueError,match="版本冲突"): store.transition_agent_run("run-version",2,status="FAILED")

def test_run_persists_task_context_and_plan_across_restart(tmp_path):
    path=tmp_path/"recovery.db"; store=EventStore(path)
    response=DeterministicAgent(store).run(subject_id="user:synthetic-01",purpose="MEDICATION_REMINDER",trigger_event_ids=["evt-recovery"],channel="TTS",consent_scopes=["medication_reminder"])
    run=store.agent_run(response["agent_run_id"]); store.close()
    restored=EventStore(path)
    assert run and run["status"]=="COMPLETED"
    assert restored.context_snapshot(run["context_snapshot_id"])["hash"]
    assert restored.plan(run["plan_id"])["steps"]==[{"skill_id":"request_play_reminder","skill_version":"v1"}]
    assert restored.care_tasks("user:synthetic-01")[0]["kind"]=="MEDICATION_REMINDER"
    restored.close()
