"""G1 业务门面：接收事件、运行规则、投影和回放。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .event_store import EventStore
from .projections import Projections
from .rules import RuleEngine


class CareCore:
    def __init__(self, database_path: str | Path) -> None:
        self.store = EventStore(database_path)
        self.rules = RuleEngine()
        self.projections = Projections.rebuild(self.store.events())

    def close(self) -> None:
        self.store.close()

    def ingest(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        """规则仅处理本次新事件；同 event_id 重放不会制造重复副作用。"""
        inserted = self.store.append(event)
        if not inserted:
            return []
        self.projections.apply(event)
        emitted = self.rules.decide(event)
        for derived in emitted:
            if self.store.append(derived):
                self.projections.apply(derived)
        return emitted

    def replay(self) -> Projections:
        self.projections = Projections.rebuild(self.store.events())
        return self.projections

    def build_chat_context(
        self, *, subject_id: str, consent_expires_at: str
    ) -> dict[str, Any]:
        """从当前 G1 投影构造只读、可追溯的 G2 聊天快照。"""
        from carehub.g2.context import build_chat_context_from_g1

        return build_chat_context_from_g1(
            projections=self.projections,
            events=self.store.events(),
            subject_id=subject_id,
            consent_expires_at=consent_expires_at,
        )
