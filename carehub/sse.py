"""C2 内存态 SSE 演示流；只分发视图变更 DTO，不分发原始事件 payload。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from carehub.g3 import AuthContext, PolicyRequest, ServerSidePDP


@dataclass(frozen=True)
class StreamEvent:
    event_id: int
    tenant_id: str
    household_id: str
    subject_id: str
    event: str
    data: dict[str, str]


class AuthorizedStateStream:
    def __init__(self, pdp: ServerSidePDP, *, max_events: int = 256) -> None:
        self.pdp, self.max_events, self._events, self._next_id = pdp, max_events, [], 1

    def publish(self, *, tenant_id: str, household_id: str, subject_id: str, view: str, snapshot_id: str) -> int:
        if view not in {"tasks", "alerts", "timeline", "dashboard", "consent"}:
            raise ValueError("不支持的 SSE 视图")
        event = StreamEvent(self._next_id, tenant_id, household_id, subject_id, "view.updated", {"view": view, "snapshot_id": snapshot_id})
        self._events.append(event); self._events = self._events[-self.max_events:]; self._next_id += 1
        return event.event_id

    def read(self, *, context: AuthContext, household_id: str, subject_id: str, last_event_id: int | None = None) -> list[StreamEvent]:
        # 每次 read 都重新查询关系与 Consent，撤销无需等待连接重建。
        decision = self.pdp.authorize(context, PolicyRequest(household_id, subject_id, "read_authorized_view", "stream", "SENSITIVE", "SSE", "view"))
        if not decision.allowed:
            return []
        start = last_event_id or 0
        events = [item for item in self._events if item.event_id > start and item.tenant_id == context.tenant_id and item.household_id == household_id and item.subject_id == subject_id]
        # 空流仍产生心跳，且不携带任何状态或事件正文。
        if not events:
            return [StreamEvent(self._next_id, context.tenant_id, household_id, subject_id, "heartbeat", {"server_time": datetime.now(timezone.utc).isoformat()})]
        return events

    @staticmethod
    def encode(event: StreamEvent) -> str:
        """SSE wire 格式；data 仅为公开 view DTO 元数据。"""
        import json
        return f"id: {event.event_id}\nevent: {event.event}\ndata: {json.dumps(event.data, separators=(',', ':'))}\n\n"
