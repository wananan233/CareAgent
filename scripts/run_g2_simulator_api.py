"""运行由 G1 合成状态驱动的 G2.2 本地 HTTP 聊天服务。"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from carehub.core.service import CareCore
from carehub.g2 import (
    ChatHttpApi,
    ChatService,
    DeepSeekGenerator,
    StaticTokenAuthenticator,
    serve_local,
)
from carehub.simulators.devices import DeviceSimulator


token = os.environ.get("CAREHUB_API_TOKEN")
if not token:
    raise RuntimeError("请设置 CAREHUB_API_TOKEN 后再启动本地 HTTP 服务")
user_id = os.environ.get("CAREHUB_USER_ID", "synthetic-01")
subject_id = f"user:{user_id}"
core = CareCore(":memory:")
core.ingest(DeviceSimulator().medication_due("morning", 1))
expires_at = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
api = ChatHttpApi(
    chat_service=ChatService(DeepSeekGenerator()),
    authenticator=StaticTokenAuthenticator({token: subject_id}),
    context_provider=lambda authenticated_subject: core.build_chat_context(
        subject_id=authenticated_subject, consent_expires_at=expires_at
    ),
)
server = serve_local(api)
print(f"CareHub G2.2 已监听 http://127.0.0.1:8080/v1/users/{user_id}/chat", flush=True)
try:
    server.serve_forever()
except KeyboardInterrupt:
    print("\n服务已停止。")
finally:
    server.server_close()
    core.close()
