"""以 G1 合成事件驱动的 G2 交互式聊天演示。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from carehub.core.service import CareCore
from carehub.g2 import ChatService, ChatSession, DeepSeekGenerator
from carehub.simulators.devices import DeviceSimulator


core = CareCore(":memory:")
simulator = DeviceSimulator()
core.ingest(simulator.medication_due("morning", 1))
snapshot = core.build_chat_context(
    subject_id="user:synthetic-01",
    consent_expires_at=(datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
)
session = ChatSession(ChatService(DeepSeekGenerator()), snapshot, max_turns=3)
print("CareHub G2 模拟器聊天已启动。当前含一条模拟服药任务；输入 /exit 结束。")

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

core.close()
