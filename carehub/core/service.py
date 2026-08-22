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
        """原事件和确定性派生事件在同一事务内写入，重放不会丢失安全分支。"""
        emitted = self.rules.decide(event)
        batch = [event, *emitted]
        inserted_ids = set(self.store.append_batch(batch))
        for item in batch:
            if item["event_id"] in inserted_ids:
                self.projections.apply(item)
        return [item for item in emitted if item["event_id"] in inserted_ids]

    def replay(self) -> Projections:
        self.projections = Projections.rebuild(self.store.events())
        return self.projections

    def build_chat_context(
        self, *, tenant_id: str = "tenant:synthetic", subject_id: str, household_id: str = "household:synthetic-home", consent_expires_at: str
    ) -> dict[str, Any]:
        """从当前 G1 投影构造只读、可追溯的 G2 聊天快照。"""
        from carehub.g2.context import build_chat_context_from_g1

        return build_chat_context_from_g1(
            projections=self.projections,
            events=self.store.events(),
            tenant_id=tenant_id,
            subject_id=subject_id,
            household_id=household_id,
            consent_expires_at=consent_expires_at,
        )
