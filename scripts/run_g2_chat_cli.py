"""G2 本地交互式聊天：最近三轮仅存于当前进程内存。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from carehub.g2 import ChatService, ChatSession, DeepSeekGenerator, build_context_snapshot


snapshot = build_context_snapshot(
    subject_id="user:synthetic-01",
    source_event_ids=["evt-synthetic-g2-cli"],
    consent_scopes=["chat"],
    consent_expires_at=(datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
    unknowns=[{"field": "care_data", "reason": "CLI_DEMO_USES_SYNTHETIC_CONTEXT"}],
)
session = ChatSession(ChatService(DeepSeekGenerator()), snapshot, max_turns=3)
print("CareHub G2 已启动。输入 /exit 结束；最近 3 轮仅保存在内存中。")

while True:
    try:
        message = input("你> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n会话已结束，本地历史已丢弃。")
        break
    if message in {"/exit", "/quit"}:
        print("会话已结束，本地历史已丢弃。")
        break
    if not message:
        continue
    try:
        response = session.ask(message)
        print(f"CareHub> {response['message']}")
    except (RuntimeError, ValueError) as error:
        print(f"CareHub> 请求未完成：{error}")
