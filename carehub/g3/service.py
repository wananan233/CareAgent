"""G3 的最小化记忆、Consent Ledger、RBAC+ABAC 与数据权利服务。"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Iterable

from carehub.core.event_store import EventStore


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def stamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass(frozen=True)
class PrivacyAccessRequest:
    actor: str
    owner: str
    household_id: str
    role: str
    scope: str
    purpose: str
    classification: str
    channel: str


class ConsentLedger:
    """同意在每次访问时从账本读取，撤销无需依赖缓存刷新。"""

    def __init__(self, store: EventStore, clock: Callable[[], datetime] = utc_now) -> None:
        self.store, self.clock = store, clock
        self.store.connection.executescript("""
        CREATE TABLE IF NOT EXISTS consent_ledger (
          consent_id TEXT PRIMARY KEY, owner TEXT NOT NULL, grantee TEXT NOT NULL,
          household_id TEXT NOT NULL, scope TEXT NOT NULL, purpose TEXT NOT NULL,
          classification TEXT NOT NULL, channel TEXT NOT NULL, status TEXT NOT NULL,
          issued_at TEXT NOT NULL, expires_at TEXT NOT NULL, revoked_at TEXT, version INTEGER NOT NULL
        );
        """)
        self.store.connection.commit()

    def grant(self, *, owner: str, grantee: str, household_id: str, scope: str,
              purpose: str, classification: str = "SENSITIVE", channel: str = "TERMINAL",
              expires_at: datetime | None = None) -> dict[str, Any]:
        now = self.clock()
        value = {"consent_id": f"consent-{uuid.uuid4()}", "owner": owner, "grantee": grantee,
                 "household_id": household_id, "scope": scope, "purpose": purpose,
                 "classification": classification, "channel": channel, "status": "ACTIVE",
                 "issued_at": stamp(now), "expires_at": stamp(expires_at or now + timedelta(days=30)),
                 "revoked_at": None, "version": 1}
        fields = tuple(value)
        with self.store.connection:
            self.store.connection.execute(
                f"INSERT INTO consent_ledger ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})",
                [value[field] for field in fields],
            )
        return value

    def revoke(self, consent_id: str, *, actor: str, expected_version: int) -> dict[str, Any]:
        row = self.store.connection.execute("SELECT * FROM consent_ledger WHERE consent_id=?", (consent_id,)).fetchone()
        if not row or row["owner"] != actor:
            raise PermissionError("只有数据主体可以撤销同意")
        with self.store.connection:
            updated = self.store.connection.execute(
                "UPDATE consent_ledger SET status='REVOKED', revoked_at=?, version=? WHERE consent_id=? AND version=? AND status='ACTIVE'",
                (stamp(self.clock()), expected_version + 1, consent_id, expected_version),
            ).rowcount
        if updated != 1:
            raise ValueError("同意已撤销或版本冲突")
        self.store.record_audit(actor=actor, capability="revoke_consent", decision="ALLOW", reason="REVOKED", resource=f"consent:{consent_id}")
        return self.get(consent_id)

    def get(self, consent_id: str) -> dict[str, Any]:
        row = self.store.connection.execute("SELECT * FROM consent_ledger WHERE consent_id=?", (consent_id,)).fetchone()
        if not row:
            raise KeyError(consent_id)
        return dict(row)

    def allows(self, request: PrivacyAccessRequest) -> bool:
        if request.actor == request.owner:
            return request.role == "SELF"
        rows = self.store.connection.execute(
            "SELECT * FROM consent_ledger WHERE owner=? AND grantee=? AND scope=?",
            (request.owner, request.actor, request.scope),
        ).fetchall()
        now = self.clock()
        return any(
            row["status"] == "ACTIVE" and row["household_id"] == request.household_id
            and row["purpose"] == request.purpose and row["classification"] == request.classification
            and row["channel"] == request.channel and parse_time(row["expires_at"]) > now
            for row in rows
        )


class G3Service:
    """长期记忆只能由候选经策略、确认后变为 ACTIVE。"""

    transitions = {
        "CANDIDATE": {"POLICY_ACCEPTED", "REVOKED"},
        "POLICY_ACCEPTED": {"CONFIRMED", "REVOKED"},
        "CONFIRMED": {"ACTIVE", "REVOKED"},
        "ACTIVE": {"REVOKED", "EXPIRED"},
    }

    def __init__(self, store: EventStore, clock: Callable[[], datetime] = utc_now) -> None:
        self.store, self.clock = store, clock
        self.ledger = ConsentLedger(store, clock)
        self.working: dict[str, tuple[dict[str, Any], datetime]] = {}
        self.store.connection.executescript("""
        CREATE TABLE IF NOT EXISTS memory_item (
          memory_id TEXT PRIMARY KEY, owner TEXT NOT NULL, household_id TEXT NOT NULL,
          type TEXT NOT NULL, value_json TEXT NOT NULL, source_event_ids_json TEXT NOT NULL,
          confidence REAL NOT NULL, sensitivity TEXT NOT NULL, consent_scope TEXT NOT NULL,
          status TEXT NOT NULL, valid_from TEXT NOT NULL, expires_at TEXT NOT NULL,
          revoke_method TEXT NOT NULL, version INTEGER NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS privacy_artifact (
          artifact_id TEXT PRIMARY KEY, owner TEXT NOT NULL, kind TEXT NOT NULL,
          storage_ref TEXT NOT NULL, expires_at TEXT NOT NULL, deleted_at TEXT
        );
        """)
        self.store.connection.commit()

    def put_working(self, *, owner: str, value: dict[str, Any], ttl_seconds: int = 300) -> str:
        if not 1 <= ttl_seconds <= 3600:
            raise ValueError("Working Memory TTL 必须在 1 秒到 1 小时内")
        memory_id = f"working-{uuid.uuid4()}"
        self.working[memory_id] = ({"memory_id": memory_id, "owner": owner, "value": value}, self.clock() + timedelta(seconds=ttl_seconds))
        return memory_id

    def get_working(self, memory_id: str, *, owner: str) -> dict[str, Any] | None:
        record = self.working.get(memory_id)
        if not record or record[0]["owner"] != owner or record[1] <= self.clock():
            self.working.pop(memory_id, None)
            return None
        return dict(record[0])

    def propose_memory(self, *, owner: str, household_id: str, memory_type: str, value: Any,
                       source_event_ids: list[str], confidence: float, sensitivity: str,
                       consent_scope: str, expires_at: datetime) -> dict[str, Any]:
        if memory_type not in {"PREFERENCE", "HABIT", "ADDRESS_FORM"} or not source_event_ids or not 0 <= confidence <= 1 or expires_at <= self.clock():
            raise ValueError("候选记忆必须包含有效类型、来源、置信度和 TTL")
        now = stamp(self.clock())
        value = {"memory_id": f"memory-{uuid.uuid4()}", "owner": owner, "household_id": household_id,
                 "type": memory_type, "value": value, "source_event_ids": source_event_ids,
                 "confidence": confidence, "sensitivity": sensitivity, "consent_scope": consent_scope,
                 "status": "CANDIDATE", "valid_from": now, "expires_at": stamp(expires_at),
                 "revoke_method": "OWNER_REVOKE", "version": 1, "updated_at": now}
        with self.store.connection:
            self.store.connection.execute("""INSERT INTO memory_item VALUES
              (:memory_id,:owner,:household_id,:type,:value_json,:source_event_ids_json,:confidence,:sensitivity,
               :consent_scope,:status,:valid_from,:expires_at,:revoke_method,:version,:updated_at)""",
              {**value, "value_json": json.dumps(value["value"], ensure_ascii=False), "source_event_ids_json": json.dumps(value["source_event_ids"])})
        return value

    def memory(self, memory_id: str) -> dict[str, Any]:
        row = self.store.connection.execute("SELECT * FROM memory_item WHERE memory_id=?", (memory_id,)).fetchone()
        if not row:
            raise KeyError(memory_id)
        item = dict(row)
        item["value"] = json.loads(item.pop("value_json")); item["source_event_ids"] = json.loads(item.pop("source_event_ids_json"))
        return item

    def transition_memory(self, memory_id: str, *, actor: str, household_id: str, role: str,
                          target: str, expected_version: int) -> dict[str, Any]:
        item = self.memory(memory_id)
        if target not in self.transitions.get(item["status"], set()):
            raise ValueError("非法记忆状态转换")
        scope = "memory_revoke" if target == "REVOKED" else "memory_manage"
        request = PrivacyAccessRequest(actor, item["owner"], household_id, role, scope, "memory", item["sensitivity"], "TERMINAL")
        if not self.ledger.allows(request):
            self.store.record_audit(actor=actor, capability=scope, decision="DENY", reason="CONSENT_OR_ABAC_DENIED", resource=f"memory:{memory_id}")
            raise PermissionError("RBAC+ABAC 或同意校验拒绝访问")
        with self.store.connection:
            updated = self.store.connection.execute(
                "UPDATE memory_item SET status=?, updated_at=?, version=? WHERE memory_id=? AND version=?",
                (target, stamp(self.clock()), expected_version + 1, memory_id, expected_version),
            ).rowcount
        if updated != 1:
            raise ValueError("记忆版本冲突")
        self.store.record_audit(actor=actor, capability=scope, decision="ALLOW", reason=target, resource=f"memory:{memory_id}")
        return self.memory(memory_id)

    def active_memories(self, request: PrivacyAccessRequest) -> list[dict[str, Any]]:
        if not self.ledger.allows(request):
            self.store.record_audit(actor=request.actor, capability=request.scope, decision="DENY", reason="CONSENT_OR_ABAC_DENIED", resource=f"owner:{request.owner}")
            return []
        rows = self.store.connection.execute("SELECT memory_id FROM memory_item WHERE owner=? AND status='ACTIVE'", (request.owner,)).fetchall()
        active = []
        for row in rows:
            item = self.memory(row["memory_id"])
            if parse_time(item["expires_at"]) <= self.clock():
                self.transition_memory(item["memory_id"], actor=item["owner"], household_id=item["household_id"], role="SELF", target="EXPIRED", expected_version=item["version"])
            elif item["consent_scope"] == request.scope:
                active.append(item)
        return active

    def episodic_view(self, request: PrivacyAccessRequest) -> list[dict[str, Any]]:
        """从 Event Store 的事实事件构建只读历史视图；不把它当作新的权威记忆。"""
        if not self.ledger.allows(request):
            return []
        return [{"event_id": event["event_id"], "occurred_at": event["occurred_at"], "source": event["source"], "quality": event["quality"]}
                for event in self.store.events() if event["aggregate"].startswith(request.owner)]

    def register_artifact(self, *, owner: str, kind: str, storage_ref: str, expires_at: datetime) -> None:
        if kind not in {"ASR_AUDIO", "VIDEO_CLIP", "DIALOGUE_TEXT"}:
            raise ValueError("不支持的数据类别")
        with self.store.connection:
            self.store.connection.execute("INSERT INTO privacy_artifact VALUES(?,?,?,?,?,NULL)", (f"artifact-{uuid.uuid4()}", owner, kind, storage_ref, stamp(expires_at)))

    def delete_personal_data(self, *, owner: str, actor: str) -> dict[str, int]:
        if actor != owner:
            raise PermissionError("删除请求仅限数据主体")
        now = stamp(self.clock())
        with self.store.connection:
            memories = self.store.connection.execute("UPDATE memory_item SET status='REVOKED', updated_at=?, version=version+1 WHERE owner=? AND status NOT IN ('REVOKED','EXPIRED')", (now, owner)).rowcount
            artifacts = self.store.connection.execute("UPDATE privacy_artifact SET deleted_at=? WHERE owner=? AND deleted_at IS NULL", (now, owner)).rowcount
        self.store.record_audit(actor=actor, capability="delete_personal_data", decision="ALLOW", reason="ERASURE_REQUEST", resource=f"owner:{owner}")
        return {"memories_revoked": memories, "artifacts_deleted": artifacts}


_sensitive = re.compile(r"(?i)(bearer\s+\S+|api[_-]?key\s*[=:]\s*\S+|(?:患者|姓名|电话|身份证|病历|处方|药量)\s*[=:：]\s*\S+)")

def scan_sensitive_logs(lines: Iterable[str]) -> list[str]:
    """只返回行号，避免扫描报告再次泄露敏感内容。"""
    return [f"line:{number}" for number, line in enumerate(lines, 1) if _sensitive.search(line)]
