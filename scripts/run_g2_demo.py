"""G2 确定性 MVP 演示：不联网、不调用真实模型或设备。"""
from pathlib import Path
from carehub.core.event_store import EventStore
from carehub.g2 import ChannelMocks, DeterministicAgent

database=Path("var/g2-demo.db"); database.parent.mkdir(exist_ok=True)
if database.exists(): database.unlink()
store=EventStore(database); channels=ChannelMocks(); agent=DeterministicAgent(store,channels=channels)
cases=[("MEDICATION_REMINDER","TTS",["medication_reminder"]),("INACTIVITY_CHECK","TTS",["safety_check"]),("FALL_FOLLOW_UP","TERMINAL",["safety_check"]),("DAILY_SUMMARY","TERMINAL",["daily_summary"]),("FAMILY_ESCALATION","FAMILY",["family_notification"])]
responses=[agent.run(subject_id="user:synthetic-01",purpose=purpose,trigger_event_ids=[f"evt-{purpose.lower()}"],channel=channel,consent_scopes=scopes) for purpose,channel,scopes in cases]
print({"runs":[item["agent_run_id"] for item in responses],"fallbacks":[item["fallback"] for item in responses],"ui":len(channels.ui),"tts":len(channels.tts),"family":len(channels.family),"tasks":len(store.care_tasks("user:synthetic-01")),"outbox_pending":store.pending_outbox_count()})
store.close()
