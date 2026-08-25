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
    tenant_id: str = "tenant:synthetic"


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
        columns = {row["name"] for row in self.store.connection.execute("PRAGMA table_info(consent_ledger)")}
        if "tenant_id" not in columns:
            self.store.connection.execute("ALTER TABLE consent_ledger ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'tenant:legacy-unscoped'")
        for column in ("granted_by", "activated_by", "source"):
            if column not in columns:
                self.store.connection.execute(f"ALTER TABLE consent_ledger ADD COLUMN {column} TEXT NOT NULL DEFAULT 'LEGACY'")
        self.store.connection.commit()

    def grant(self, *, owner: str, grantee: str, household_id: str, scope: str,
              purpose: str, classification: str = "SENSITIVE", channel: str = "TERMINAL",
              expires_at: datetime | None = None, tenant_id: str = "tenant:synthetic", actor: str | None = None,
              source: str = "LOCAL_DEMO") -> dict[str, Any]:
        now = self.clock()
        value = {"consent_id": f"consent-{uuid.uuid4()}", "owner": owner, "grantee": grantee,
                 "household_id": household_id, "scope": scope, "purpose": purpose,
                 "classification": classification, "channel": channel, "status": "GRANTED",
                 "issued_at": stamp(now), "expires_at": stamp(expires_at or now + timedelta(days=30)),
                 "revoked_at": None, "version": 1, "tenant_id": tenant_id,
                 "granted_by": actor or owner, "activated_by": "", "source": source}
        fields = tuple(value)
        with self.store.connection:
            self.store.connection.execute(
                f"INSERT INTO consent_ledger ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})",
                [value[field] for field in fields],
            )
        return value

    def activate(self, consent_id: str, *, actor: str, expected_version: int) -> dict[str, Any]:
        """将主体已授予的同意显式生效，避免创建记录即被当作可用授权。"""
        row = self.store.connection.execute("SELECT * FROM consent_ledger WHERE consent_id=?", (consent_id,)).fetchone()
        if not row or row["owner"] != actor:
            raise PermissionError("只有数据主体可以激活同意")
        with self.store.connection:
            updated = self.store.connection.execute(
                "UPDATE consent_ledger SET status='ACTIVE', activated_by=?, version=? WHERE consent_id=? AND version=? AND status='GRANTED'",
                (actor, expected_version + 1, consent_id, expected_version),
            ).rowcount
        if updated != 1:
            raise ValueError("同意状态或版本冲突")
        value = self.get(consent_id)
        self.store.record_audit(actor=actor, capability="activate_consent", decision="ALLOW", reason="ACTIVE", resource=f"consent:{consent_id}", tenant_id=value["tenant_id"], household_id=value["household_id"], subject_id=value["owner"])
        return value

    def revoke(self, consent_id: str, *, actor: str, expected_version: int) -> dict[str, Any]:
        row = self.store.connection.execute("SELECT * FROM consent_ledger WHERE consent_id=?", (consent_id,)).fetchone()
        if not row or row["owner"] != actor:
            raise PermissionError("只有数据主体可以撤销同意")
        with self.store.connection:
            updated = self.store.connection.execute(
                "UPDATE consent_ledger SET status='REVOKED', revoked_at=?, version=? WHERE consent_id=? AND version=? AND status IN ('GRANTED','ACTIVE')",
                (stamp(self.clock()), expected_version + 1, consent_id, expected_version),
            ).rowcount
        if updated != 1:
            raise ValueError("同意已撤销或版本冲突")
        value = self.get(consent_id)
        self.store.record_audit(actor=actor, capability="revoke_consent", decision="ALLOW", reason="REVOKED", resource=f"consent:{consent_id}", tenant_id=value["tenant_id"], household_id=value["household_id"], subject_id=value["owner"])
        return value

    def get(self, consent_id: str) -> dict[str, Any]:
        row = self.store.connection.execute("SELECT * FROM consent_ledger WHERE consent_id=?", (consent_id,)).fetchone()
        if not row:
            raise KeyError(consent_id)
        return dict(row)

    def allows(self, request: PrivacyAccessRequest) -> bool:
        return self.active_consent(request) is not None

    def active_consent(self, request: PrivacyAccessRequest) -> dict[str, Any] | None:
        rows = self.store.connection.execute(
            "SELECT * FROM consent_ledger WHERE tenant_id=? AND owner=? AND grantee=? AND scope=?",
            (request.tenant_id, request.owner, request.actor, request.scope),
        ).fetchall()
        now = self.clock()
        for row in rows:
            if row["status"] == "ACTIVE" and parse_time(row["expires_at"]) <= now:
                with self.store.connection:
                    self.store.connection.execute("UPDATE consent_ledger SET status='EXPIRED', version=version+1 WHERE consent_id=? AND status='ACTIVE'", (row["consent_id"],))
                continue
            if (row["status"] == "ACTIVE" and row["household_id"] == request.household_id
                    and row["purpose"] == request.purpose and row["classification"] == request.classification
                    and row["channel"] == request.channel and parse_time(row["expires_at"]) > now):
                return dict(row)
        return None


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
        # C1 主路径经 PDP；保留 PrivacyAccessRequest 接口只为既有内部调用兼容。
        from .policy import ServerSidePDP
        self.pdp = ServerSidePDP(store, self.ledger)
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
        for table in ("memory_item", "privacy_artifact"):
            columns = {row["name"] for row in self.store.connection.execute(f"PRAGMA table_info({table})")}
            if "tenant_id" not in columns:
                self.store.connection.execute(f"ALTER TABLE {table} ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'tenant:legacy-unscoped'")
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
                       consent_scope: str, expires_at: datetime, tenant_id: str = "tenant:synthetic") -> dict[str, Any]:
        if memory_type not in {"PREFERENCE", "HABIT", "ADDRESS_FORM"} or not source_event_ids or not 0 <= confidence <= 1 or expires_at <= self.clock():
            raise ValueError("候选记忆必须包含有效类型、来源、置信度和 TTL")
        now = stamp(self.clock())
        value = {"memory_id": f"memory-{uuid.uuid4()}", "tenant_id": tenant_id, "owner": owner, "household_id": household_id,
                 "type": memory_type, "value": value, "source_event_ids": source_event_ids,
                 "confidence": confidence, "sensitivity": sensitivity, "consent_scope": consent_scope,
                 "status": "CANDIDATE", "valid_from": now, "expires_at": stamp(expires_at),
                 "revoke_method": "OWNER_REVOKE", "version": 1, "updated_at": now}
        with self.store.connection:
            self.store.connection.execute("""INSERT INTO memory_item(memory_id, owner, household_id, type, value_json,
              source_event_ids_json, confidence, sensitivity, consent_scope, status, valid_from, expires_at, revoke_method,
              version, updated_at, tenant_id) VALUES
              (:memory_id,:owner,:household_id,:type,:value_json,:source_event_ids_json,:confidence,:sensitivity,
               :consent_scope,:status,:valid_from,:expires_at,:revoke_method,:version,:updated_at,:tenant_id)""",
              {**value, "value_json": json.dumps(value["value"], ensure_ascii=False), "source_event_ids_json": json.dumps(value["source_event_ids"])})
        return value

    def memory(self, memory_id: str, *, tenant_id: str = "tenant:synthetic") -> dict[str, Any]:
        row = self.store.connection.execute("SELECT * FROM memory_item WHERE memory_id=? AND tenant_id=?", (memory_id, tenant_id)).fetchone()
        if not row:
            raise KeyError(memory_id)
        item = dict(row)
        item["value"] = json.loads(item.pop("value_json")); item["source_event_ids"] = json.loads(item.pop("source_event_ids_json"))
        return item

    def transition_memory(self, memory_id: str, *, actor: str, household_id: str, role: str,
                          target: str, expected_version: int, tenant_id: str = "tenant:synthetic") -> dict[str, Any]:
        item = self.memory(memory_id, tenant_id=tenant_id)
        if target not in self.transitions.get(item["status"], set()):
            raise ValueError("非法记忆状态转换")
        scope = "memory_revoke" if target == "REVOKED" else "memory_manage"
        request = PrivacyAccessRequest(actor, item["owner"], household_id, role, scope, "memory", item["sensitivity"], "TERMINAL", tenant_id)
        if not self.ledger.allows(request):
            self.store.record_audit(actor=actor, capability=scope, decision="DENY", reason="CONSENT_OR_ABAC_DENIED", resource=f"memory:{memory_id}")
            raise PermissionError("RBAC+ABAC 或同意校验拒绝访问")
        with self.store.connection:
            updated = self.store.connection.execute(
                "UPDATE memory_item SET status=?, updated_at=?, version=? WHERE memory_id=? AND tenant_id=? AND version=?",
                (target, stamp(self.clock()), expected_version + 1, memory_id, tenant_id, expected_version),
            ).rowcount
        if updated != 1:
            raise ValueError("记忆版本冲突")
        self.store.record_audit(actor=actor, capability=scope, decision="ALLOW", reason=target, resource=f"memory:{memory_id}")
        return self.memory(memory_id, tenant_id=tenant_id)

    def active_memories(self, request: PrivacyAccessRequest) -> list[dict[str, Any]]:
        if not self.ledger.allows(request):
            self.store.record_audit(actor=request.actor, capability=request.scope, decision="DENY", reason="CONSENT_OR_ABAC_DENIED", resource=f"owner:{request.owner}")
            return []
        rows = self.store.connection.execute("SELECT memory_id FROM memory_item WHERE tenant_id=? AND owner=? AND household_id=? AND status='ACTIVE'", (request.tenant_id, request.owner, request.household_id)).fetchall()
        active = []
        for row in rows:
            item = self.memory(row["memory_id"], tenant_id=request.tenant_id)
            if parse_time(item["expires_at"]) <= self.clock():
                self.transition_memory(item["memory_id"], actor=item["owner"], household_id=item["household_id"], role="SELF", target="EXPIRED", expected_version=item["version"], tenant_id=request.tenant_id)
            elif item["consent_scope"] == request.scope:
                active.append(item)
        return active

    def authorized_active_memories(self, context: "Any", policy_request: "Any") -> list[dict[str, Any]]:
        """面向入口层的 C1 主路径，拒绝客户端传入的角色或家庭授权声明。"""
        decision = self.pdp.authorize(context, policy_request)
        if not decision.allowed:
            return []
        row = self.store.connection.execute(
            "SELECT role FROM membership WHERE tenant_id=? AND household_id=? AND principal_id=?",
            (context.tenant_id, policy_request.household_id, context.actor_id),
        ).fetchone()
        request = PrivacyAccessRequest(context.actor_id, policy_request.subject_id, policy_request.household_id,
                                      row["role"], policy_request.consent_scope, policy_request.purpose,
                                      policy_request.classification, policy_request.channel, context.tenant_id)
        return self.active_memories(request)

    def episodic_view(self, request: PrivacyAccessRequest) -> list[dict[str, Any]]:
        """从 Event Store 的事实事件构建只读历史视图；不把它当作新的权威记忆。"""
        if not self.ledger.allows(request):
            return []
        return [{"event_id": event["event_id"], "occurred_at": event["occurred_at"], "source": event["source"], "quality": event["quality"]}
                for event in self.store.events_for_scope(tenant_id=request.tenant_id, household_id=request.household_id, subject_id=request.owner)]

    def register_artifact(self, *, owner: str, kind: str, storage_ref: str, expires_at: datetime, tenant_id: str = "tenant:synthetic") -> None:
        if kind not in {"ASR_AUDIO", "VIDEO_CLIP", "DIALOGUE_TEXT"}:
            raise ValueError("不支持的数据类别")
        with self.store.connection:
            self.store.connection.execute("INSERT INTO privacy_artifact(artifact_id, owner, kind, storage_ref, expires_at, deleted_at, tenant_id) VALUES(?,?,?,?,?,NULL,?)", (f"artifact-{uuid.uuid4()}", owner, kind, storage_ref, stamp(expires_at), tenant_id))

    def delete_personal_data(self, *, owner: str, actor: str, tenant_id: str = "tenant:synthetic") -> dict[str, int]:
        if actor != owner:
            raise PermissionError("删除请求仅限数据主体")
        now = stamp(self.clock())
        with self.store.connection:
            memories = self.store.connection.execute("UPDATE memory_item SET status='REVOKED', updated_at=?, version=version+1 WHERE tenant_id=? AND owner=? AND status NOT IN ('REVOKED','EXPIRED')", (now, tenant_id, owner)).rowcount
            artifacts = self.store.connection.execute("UPDATE privacy_artifact SET deleted_at=? WHERE tenant_id=? AND owner=? AND deleted_at IS NULL", (now, tenant_id, owner)).rowcount
        self.store.record_audit(actor=actor, capability="delete_personal_data", decision="ALLOW", reason="ERASURE_REQUEST", resource=f"owner:{owner}", tenant_id=tenant_id, household_id="household:erasure", subject_id=owner)
        return {"memories_revoked": memories, "artifacts_deleted": artifacts}


_sensitive = re.compile(r"(?i)(bearer\s+\S+|api[_-]?key\s*[=:]\s*\S+|(?:患者|姓名|电话|身份证|病历|处方|药量)\s*[=:：]\s*\S+)")

def scan_sensitive_logs(lines: Iterable[str]) -> list[str]:
    """只返回行号，避免扫描报告再次泄露敏感内容。"""
    return [f"line:{number}" for number, line in enumerate(lines, 1) if _sensitive.search(line)]
