"""使用环境变量中的 DeepSeek 密钥运行一次 G2 只读聊天演示。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from carehub.g2 import ChatService, DeepSeekGenerator, build_context_snapshot


snapshot = build_context_snapshot(
    subject_id="user:synthetic-01",
    source_event_ids=["evt-synthetic-g2-demo"],
    consent_scopes=["chat"],
    consent_expires_at=(datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
    unknowns=[{"field": "current_task", "reason": "SYNTHETIC_DEMO_HAS_NO_TASK_DATA"}],
)
response = ChatService(DeepSeekGenerator()).respond(
    message="你好，请说明你目前能帮我做什么。",
    context_snapshot=snapshot,
)
print(response)
