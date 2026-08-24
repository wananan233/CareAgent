"""SQLite WAL 追加事件库与 Transactional Outbox。"""

from __future__ import annotations

import json
import hashlib
import sqlite3
from threading import RLock
from pathlib import Path
from typing import Any, Iterable, Sequence

from jsonschema import Draft202012Validator, FormatChecker

from .errors import EventConflictError
from .events import checksum


PAYLOAD_REQUIRED_FIELDS: dict[str, frozenset[str]] = {
    "ALERT_RAISED": frozenset({"alert_id", "kind", "safety_level", "status"}),
    "ALERT_RESOLVED": frozenset({"alert_id"}),
    "TASK_CREATED": frozenset({"task_id"}),
    "TASK_UPDATED": frozenset({"task_id"}),
    "CONSENT_CHANGED": frozenset({"consent_id", "status"}),
    "MEDICATION_EVIDENCE_RECORDED": frozenset({"task_ref", "evidence_state"}),
    "PROMPT_REQUESTED": frozenset({"task_ref", "action", "evidence_state"}),
}


class EventStore:
    def __init__(self, database_path: str | Path) -> None:
        self.path = str(database_path)
        self._lock = RLock()
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self._migrate()
        schema_path = Path(__file__).resolve().parents[2] / "contracts" / "schemas" / "care-event.v1.json"
        self._event_validator = Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8")), format_checker=FormatChecker())

    def close(self) -> None:
        with self._lock:
            self.connection.close()

    def _migrate(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS event_log (
               global_sequence INTEGER PRIMARY KEY AUTOINCREMENT,
               event_id TEXT NOT NULL UNIQUE,
               tenant_id TEXT NOT NULL,
               subject_id TEXT NOT NULL,
               household_id TEXT NOT NULL,
               aggregate TEXT NOT NULL,
               aggregate_type TEXT NOT NULL,
               aggregate_id TEXT NOT NULL,
              aggregate_sequence INTEGER NOT NULL,
              occurred_at TEXT NOT NULL,
              received_at TEXT NOT NULL,
              source TEXT NOT NULL,
              quality TEXT NOT NULL,
              privacy TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              checksum TEXT NOT NULL,
              envelope_fingerprint TEXT NOT NULL,
              correlation_id TEXT NOT NULL,
              causation_id TEXT,
              trace_id TEXT,
              UNIQUE(tenant_id, household_id, aggregate_type, aggregate_id, aggregate_sequence)
            );
            CREATE TABLE IF NOT EXISTS outbox (
              event_id TEXT NOT NULL,
              destination TEXT NOT NULL,
              attempt INTEGER NOT NULL DEFAULT 0,
              next_retry_at TEXT,
              status TEXT NOT NULL DEFAULT 'PENDING',
              PRIMARY KEY(event_id, destination),
              FOREIGN KEY(event_id) REFERENCES event_log(event_id)
            );
            CREATE TABLE IF NOT EXISTS projection_checkpoint (
              projection TEXT PRIMARY KEY,
              last_global_sequence INTEGER NOT NULL,
              hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS command_inbox (
              command_id TEXT PRIMARY KEY,
              expected_version INTEGER NOT NULL,
              idempotency_key TEXT NOT NULL UNIQUE,
              status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS dead_letter (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              raw_input TEXT NOT NULL,
              error_code TEXT NOT NULL,
              first_seen_at TEXT NOT NULL,
              last_seen_at TEXT NOT NULL,
              disposition TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_entry (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              actor TEXT NOT NULL,
              capability TEXT NOT NULL,
              decision TEXT NOT NULL,
              reason TEXT NOT NULL,
              resource TEXT NOT NULL,
              hash_chain TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS agent_run (
              agent_run_id TEXT PRIMARY KEY, subject_id TEXT NOT NULL, purpose TEXT NOT NULL,
              trigger_event_ids_json TEXT NOT NULL, channel TEXT NOT NULL, status TEXT NOT NULL,
              context_snapshot_id TEXT, plan_id TEXT, reason_code TEXT, correlation_id TEXT NOT NULL,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL, version INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS care_task (
              task_id TEXT PRIMARY KEY, subject_id TEXT NOT NULL, kind TEXT NOT NULL, status TEXT NOT NULL,
              safety_level TEXT NOT NULL, source_event_ids_json TEXT NOT NULL, reschedulable INTEGER NOT NULL,
              max_delay_seconds INTEGER, version INTEGER NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS intent_execution (
              idempotency_key TEXT PRIMARY KEY, intent_id TEXT NOT NULL, status TEXT NOT NULL, result_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS context_snapshot (snapshot_id TEXT PRIMARY KEY, subject_id TEXT NOT NULL, purpose TEXT NOT NULL, hash TEXT NOT NULL, snapshot_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS agent_plan (plan_id TEXT PRIMARY KEY, agent_run_id TEXT NOT NULL, plan_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS tenant (
              tenant_id TEXT PRIMARY KEY, display_name TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS household (
              tenant_id TEXT NOT NULL, household_id TEXT NOT NULL, display_name TEXT NOT NULL,
              PRIMARY KEY(tenant_id, household_id), FOREIGN KEY(tenant_id) REFERENCES tenant(tenant_id)
            );
            CREATE TABLE IF NOT EXISTS subject (
              tenant_id TEXT NOT NULL, subject_id TEXT NOT NULL, household_id TEXT NOT NULL,
              PRIMARY KEY(tenant_id, subject_id),
              FOREIGN KEY(tenant_id, household_id) REFERENCES household(tenant_id, household_id)
            );
            CREATE TABLE IF NOT EXISTS principal (
              tenant_id TEXT NOT NULL, principal_id TEXT NOT NULL, kind TEXT NOT NULL,
              PRIMARY KEY(tenant_id, principal_id), FOREIGN KEY(tenant_id) REFERENCES tenant(tenant_id)
            );
            CREATE TABLE IF NOT EXISTS membership (
              tenant_id TEXT NOT NULL, household_id TEXT NOT NULL, principal_id TEXT NOT NULL, role TEXT NOT NULL,
              PRIMARY KEY(tenant_id, household_id, principal_id),
              FOREIGN KEY(tenant_id, household_id) REFERENCES household(tenant_id, household_id),
              FOREIGN KEY(tenant_id, principal_id) REFERENCES principal(tenant_id, principal_id)
            );
            CREATE TABLE IF NOT EXISTS subject_link (
              tenant_id TEXT NOT NULL, subject_id TEXT NOT NULL, principal_id TEXT NOT NULL, relation TEXT NOT NULL,
              PRIMARY KEY(tenant_id, subject_id, principal_id),
              FOREIGN KEY(tenant_id, subject_id) REFERENCES subject(tenant_id, subject_id),
              FOREIGN KEY(tenant_id, principal_id) REFERENCES principal(tenant_id, principal_id)
            );
            CREATE TABLE IF NOT EXISTS device_binding (
              tenant_id TEXT NOT NULL, household_id TEXT NOT NULL, subject_id TEXT NOT NULL, device_id TEXT NOT NULL,
              PRIMARY KEY(tenant_id, household_id, device_id),
              FOREIGN KEY(tenant_id, subject_id) REFERENCES subject(tenant_id, subject_id)
            );
            """
        )
        columns = {row["name"] for row in self.connection.execute("PRAGMA table_info(event_log)")}
        if "tenant_id" not in columns:
            # The old global aggregate uniqueness rule cannot safely represent two
            # households. Preserve it as an explicitly unreadable legacy table
            # instead of guessing ownership during a migration.
            self.connection.execute("ALTER TABLE event_log RENAME TO legacy_unscoped_event_log")
            self.connection.execute("ALTER TABLE outbox RENAME TO legacy_unscoped_outbox")
            self.connection.executescript(
                """
                CREATE TABLE event_log (
                  global_sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                  event_id TEXT NOT NULL UNIQUE, tenant_id TEXT NOT NULL,
                  subject_id TEXT NOT NULL, household_id TEXT NOT NULL,
                  aggregate TEXT NOT NULL, aggregate_type TEXT NOT NULL, aggregate_id TEXT NOT NULL,
                  aggregate_sequence INTEGER NOT NULL, occurred_at TEXT NOT NULL, received_at TEXT NOT NULL,
                  source TEXT NOT NULL, quality TEXT NOT NULL, privacy TEXT NOT NULL, payload_json TEXT NOT NULL,
                  checksum TEXT NOT NULL, envelope_fingerprint TEXT NOT NULL, correlation_id TEXT NOT NULL,
                  causation_id TEXT, trace_id TEXT,
                  UNIQUE(tenant_id, household_id, aggregate_type, aggregate_id, aggregate_sequence)
                );
                CREATE TABLE outbox (
                  event_id TEXT NOT NULL, destination TEXT NOT NULL, attempt INTEGER NOT NULL DEFAULT 0,
                  next_retry_at TEXT, status TEXT NOT NULL DEFAULT 'PENDING', PRIMARY KEY(event_id, destination),
                  FOREIGN KEY(event_id) REFERENCES event_log(event_id)
                );
                """
            )
        # C0 adds an ownership triple to every operational record. Old records
        # are retained under an explicitly unreadable legacy scope; no current
        # request path can infer or adopt their ownership.
        for table, required in {
            "outbox": ("tenant_id", "household_id", "subject_id"),
            "projection_checkpoint": ("tenant_id", "household_id", "subject_id"),
            "command_inbox": ("tenant_id", "household_id", "subject_id"),
            "dead_letter": ("tenant_id", "household_id", "subject_id"),
            "audit_entry": ("tenant_id", "household_id", "subject_id"),
            "agent_run": ("tenant_id", "household_id"),
            "care_task": ("tenant_id", "household_id"),
            "intent_execution": ("tenant_id", "household_id", "subject_id"),
            "context_snapshot": ("tenant_id", "household_id"),
            "agent_plan": ("tenant_id", "household_id", "subject_id"),
        }.items():
            existing = {row["name"] for row in self.connection.execute(f"PRAGMA table_info({table})")}
            for column in required:
                if column not in existing:
                    fallback = "user:legacy-unscoped" if column == "subject_id" else f"{column.removesuffix('_id')}:legacy-unscoped"
                    self.connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT NOT NULL DEFAULT '{fallback}'")
        audit_columns = {row["name"] for row in self.connection.execute("PRAGMA table_info(audit_entry)")}
        for column in ("policy_version", "consent_version", "correlation_id"):
            if column not in audit_columns:
                self.connection.execute(f"ALTER TABLE audit_entry ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")
        task_columns = {row["name"] for row in self.connection.execute("PRAGMA table_info(care_task)")}
        if "business_task_id" not in task_columns:
            self.connection.execute("ALTER TABLE care_task ADD COLUMN business_task_id TEXT")
            self.connection.execute("UPDATE care_task SET business_task_id=task_id WHERE business_task_id IS NULL")
        self.connection.commit()

    def append(self, event: dict[str, Any], destination: str = "care-sync") -> bool:
        """原子写入 event_log 与 outbox；重复的同内容事件为幂等成功。"""
        with self._lock:
            return bool(self._append_batch_locked([event], destination))

    def append_batch(self, events: Sequence[dict[str, Any]], destination: str = "care-sync") -> tuple[str, ...]:
        """在同一事务内落库输入事件及其确定性派生事件。

        返回本次真正插入的 event_id。重复提交同一批事件安全返回空元组；如果旧进程
        曾在派生事件前异常退出，重放同一确定性批次会补齐缺失事件。
        """
        if not events:
            return ()
        with self._lock:
            return self._append_batch_locked(events, destination)

    def _validate_event(self, event: dict[str, Any]) -> None:
        errors = sorted(self._event_validator.iter_errors(event), key=lambda item: list(item.path))
        if errors:
            raise ValueError(f"事件不符合 CareEventV1: {errors[0].message}")
        if event["checksum"] != checksum(event["payload"]):
            raise ValueError("事件 checksum 不匹配")
        if event["aggregate"] != f"{event['aggregate_type']}:{event['aggregate_id']}":
            raise ValueError("aggregate 与 aggregate_type/aggregate_id 不一致")
        event_type = event["payload"].get("event_type")
        if not isinstance(event_type, str):
            raise ValueError("事件 payload 缺少 event_type")
        missing = PAYLOAD_REQUIRED_FIELDS.get(event_type, frozenset()).difference(event["payload"])
        if missing:
            raise ValueError(f"{event_type} payload 缺少字段: {', '.join(sorted(missing))}")

    @staticmethod
    def _envelope_fingerprint(event: dict[str, Any]) -> str:
        canonical = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _append_batch_locked(self, events: Sequence[dict[str, Any]], destination: str) -> tuple[str, ...]:
        for event in events:
            self._validate_event(event)
        event_ids = [event["event_id"] for event in events]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("同一事件批次包含重复 event_id")
        for event in events:
            existing = self.connection.execute(
                "SELECT envelope_fingerprint FROM event_log WHERE event_id = ?", (event["event_id"],)
            ).fetchone()
            if existing and existing["envelope_fingerprint"] != self._envelope_fingerprint(event):
                with self.connection:
                    self._dead_letter(event, "EVENT_ID_ENVELOPE_CONFLICT")
                raise EventConflictError(f"event_id 冲突: {event['event_id']}")

        inserted: list[str] = []
        try:
            with self.connection:
                for event in events:
                    existing = self.connection.execute(
                        "SELECT envelope_fingerprint FROM event_log WHERE event_id = ?", (event["event_id"],)
                    ).fetchone()
                    if existing:
                        continue
                    self.connection.execute(
                        """INSERT INTO event_log(event_id, tenant_id, subject_id, household_id, aggregate, aggregate_type, aggregate_id,
                           aggregate_sequence, occurred_at, received_at, source, quality, privacy, payload_json, checksum,
                           envelope_fingerprint, correlation_id, causation_id, trace_id)
                           VALUES(:event_id, :tenant_id, :subject_id, :household_id, :aggregate, :aggregate_type, :aggregate_id, :sequence,
                           :occurred_at, :received_at, :source, :quality, :privacy, :payload_json, :checksum, :envelope_fingerprint,
                           :correlation_id, :causation_id, :trace_id)""",
                        {**event, "payload_json": json.dumps(event["payload"], ensure_ascii=False, sort_keys=True), "envelope_fingerprint": self._envelope_fingerprint(event)},
                    )
                    self.connection.execute(
                        "INSERT INTO outbox(event_id, destination, tenant_id, household_id, subject_id) VALUES(?, ?, ?, ?, ?)",
                        (event["event_id"], destination, event["tenant_id"], event["household_id"], event["subject_id"]),
                    )
                    inserted.append(event["event_id"])
            return tuple(inserted)
        except sqlite3.IntegrityError as error:
            raise ValueError(f"Aggregate sequence 冲突: {event['tenant_id']}/{event['household_id']}/{event['aggregate']}#{event['sequence']}") from error

    def _dead_letter(self, event: dict[str, Any], code: str) -> None:
        received_at = event.get("received_at", "unknown")
        summary = {
            "event_id": event.get("event_id"),
            "tenant_id": event.get("tenant_id"),
            "subject_id": event.get("subject_id"),
            "household_id": event.get("household_id"),
            "checksum": event.get("checksum"),
        }
        self.connection.execute(
            "INSERT INTO dead_letter(raw_input, error_code, first_seen_at, last_seen_at, disposition, tenant_id, household_id, subject_id) VALUES(?,?,?,?,?,?,?,?)",
            (json.dumps(summary, ensure_ascii=False, sort_keys=True), code, received_at, received_at, "QUARANTINED", event.get("tenant_id", "tenant:legacy-unscoped"), event.get("household_id", "household:legacy-unscoped"), event.get("subject_id", "user:legacy-unscoped")),
        )

    def events(self) -> Iterable[dict[str, Any]]:
        with self._lock:
            rows = self.connection.execute("SELECT * FROM event_log ORDER BY global_sequence").fetchall()
        for row in rows:
            yield {
                "event_id": row["event_id"], "subject_id": row["subject_id"], "household_id": row["household_id"],
                "tenant_id": row["tenant_id"], "aggregate": row["aggregate"], "aggregate_type": row["aggregate_type"],
                "aggregate_id": row["aggregate_id"], "sequence": row["aggregate_sequence"],
                "occurred_at": row["occurred_at"], "received_at": row["received_at"], "source": row["source"],
                "quality": row["quality"], "privacy": row["privacy"], "payload": json.loads(row["payload_json"]),
                "checksum": row["checksum"], "correlation_id": row["correlation_id"], "causation_id": row["causation_id"], "trace_id": row["trace_id"],
            }

    def events_for_scope(self, *, tenant_id: str, household_id: str, subject_id: str) -> Iterable[dict[str, Any]]:
        """Read-model boundary for C0 callers; legacy and cross-scope rows are unreachable."""
        return (
            event for event in self.events()
            if event["tenant_id"] == tenant_id and event["household_id"] == household_id and event["subject_id"] == subject_id
        )

    def register_scope(self, *, tenant_id: str, household_id: str, subject_id: str, principal_id: str, role: str, device_id: str | None = None) -> None:
        """C0 relationship repository for synthetic identities only; it grants no access."""
        with self._lock, self.connection:
            self.connection.execute("INSERT OR IGNORE INTO tenant VALUES(?, ?)", (tenant_id, tenant_id))
            self.connection.execute("INSERT OR IGNORE INTO household VALUES(?, ?, ?)", (tenant_id, household_id, household_id))
            self.connection.execute("INSERT OR IGNORE INTO subject VALUES(?, ?, ?)", (tenant_id, subject_id, household_id))
            self.connection.execute("INSERT OR IGNORE INTO principal VALUES(?, ?, 'SYNTHETIC')", (tenant_id, principal_id))
            self.connection.execute("INSERT OR IGNORE INTO membership VALUES(?, ?, ?, ?)", (tenant_id, household_id, principal_id, role))
            self.connection.execute("INSERT OR IGNORE INTO subject_link VALUES(?, ?, ?, 'CARE_RECIPIENT')", (tenant_id, subject_id, principal_id))
            if device_id:
                self.connection.execute("INSERT OR IGNORE INTO device_binding VALUES(?, ?, ?, ?)", (tenant_id, household_id, subject_id, device_id))

    def scope_registered(self, *, tenant_id: str, household_id: str, subject_id: str) -> bool:
        with self._lock:
            return self.connection.execute(
                "SELECT 1 FROM subject WHERE tenant_id=? AND household_id=? AND subject_id=?",
                (tenant_id, household_id, subject_id),
            ).fetchone() is not None

    def pending_outbox_count(self) -> int:
        with self._lock:
            return self.connection.execute("SELECT COUNT(*) FROM outbox WHERE status='PENDING'").fetchone()[0]

    def journal_mode(self) -> str:
        with self._lock:
            return self.connection.execute("PRAGMA journal_mode").fetchone()[0]

    def record_audit(self, *, actor: str, capability: str, decision: str, reason: str, resource: str,
                     tenant_id: str = "tenant:synthetic", household_id: str = "household:synthetic-home",
                     subject_id: str = "user:synthetic-01", policy_version: str = "",
                     consent_version: str = "", correlation_id: str = "") -> str:
        """追加不含请求正文的审计记录，并返回不可变哈希链节点。"""
        with self._lock, self.connection:
            previous = self.connection.execute("SELECT hash_chain FROM audit_entry ORDER BY id DESC LIMIT 1").fetchone()
            material = json.dumps(
                {"previous": previous["hash_chain"] if previous else "", "actor": actor, "capability": capability,
                 "decision": decision, "reason": reason, "resource": resource},
                ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            )
            hash_chain = hashlib.sha256(material.encode("utf-8")).hexdigest()
            self.connection.execute(
                "INSERT INTO audit_entry(actor, capability, decision, reason, resource, hash_chain, tenant_id, household_id, subject_id, policy_version, consent_version, correlation_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (actor, capability, decision, reason, resource, hash_chain, tenant_id, household_id, subject_id, policy_version, consent_version, correlation_id),
            )
            return hash_chain

    def audit_entries(self) -> list[dict[str, str]]:
        with self._lock:
            rows = self.connection.execute("SELECT actor, capability, decision, reason, resource, hash_chain FROM audit_entry ORDER BY id").fetchall()
        return [dict(row) for row in rows]

    def create_agent_run(self, run: dict[str, Any]) -> bool:
        with self._lock, self.connection:
            if self.connection.execute("SELECT 1 FROM agent_run WHERE agent_run_id=?", (run["agent_run_id"],)).fetchone():
                return False
            self.connection.execute(
                """INSERT INTO agent_run(agent_run_id, subject_id, purpose, trigger_event_ids_json, channel, status,
                   context_snapshot_id, plan_id, reason_code, correlation_id, created_at, updated_at, version, tenant_id, household_id)
                   VALUES(:agent_run_id,:subject_id,:purpose,:trigger_event_ids_json,:channel,:status,:context_snapshot_id,:plan_id,
                   :reason_code,:correlation_id,:created_at,:updated_at,:version,:tenant_id,:household_id)""",
                {**run, "tenant_id": run.get("tenant_id", "tenant:synthetic"), "household_id": run.get("household_id", "household:synthetic-home"), "trigger_event_ids_json": json.dumps(run["trigger_event_ids"], ensure_ascii=False)},
            )
            return True

    def agent_run(self, agent_run_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.connection.execute("SELECT * FROM agent_run WHERE agent_run_id=?", (agent_run_id,)).fetchone()
        if not row:
            return None
        value = dict(row); value["trigger_event_ids"] = json.loads(value.pop("trigger_event_ids_json")); return value

    def agent_run_for_scope(self, agent_run_id: str, *, tenant_id: str, household_id: str, subject_id: str) -> dict[str, Any] | None:
        value = self.agent_run(agent_run_id)
        if not value or (value["tenant_id"], value["household_id"], value["subject_id"]) != (tenant_id, household_id, subject_id):
            return None
        return value

    def transition_agent_run(self, agent_run_id: str, expected_version: int, **changes: Any) -> dict[str, Any]:
        with self._lock, self.connection:
            assignments = ", ".join(f"{key}=?" for key in changes)
            updated = self.connection.execute(f"UPDATE agent_run SET {assignments}, version=? WHERE agent_run_id=? AND version=?", [*changes.values(), expected_version + 1, agent_run_id, expected_version]).rowcount
            if updated != 1:
                raise ValueError("AgentRun 版本冲突或不存在")
        result = self.agent_run(agent_run_id); assert result; return result

    def upsert_care_task(self, task: dict[str, Any]) -> None:
        with self._lock, self.connection:
            tenant_id = task.get("tenant_id", "tenant:synthetic")
            household_id = task.get("household_id", "household:synthetic-home")
            storage_id = f"{tenant_id}|{household_id}|{task['task_id']}"
            self.connection.execute(
                """INSERT INTO care_task(task_id, business_task_id, subject_id, kind, status, safety_level, source_event_ids_json, reschedulable,
                   max_delay_seconds, version, updated_at, tenant_id, household_id)
                   VALUES(:storage_id,:business_task_id,:subject_id,:kind,:status,:safety_level,:source_event_ids_json,:reschedulable,:max_delay_seconds,
                   :version,:updated_at,:tenant_id,:household_id)
                   ON CONFLICT(task_id) DO UPDATE SET status=excluded.status, source_event_ids_json=excluded.source_event_ids_json,
                   version=excluded.version, updated_at=excluded.updated_at""",
                {**task, "storage_id": storage_id, "business_task_id": task["task_id"], "tenant_id": tenant_id, "household_id": household_id, "source_event_ids_json": json.dumps(task["source_event_ids"], ensure_ascii=False), "reschedulable": int(task.get("reschedulable", False))},
            )

    def care_tasks(self, subject_id: str, *, tenant_id: str = "tenant:synthetic", household_id: str = "household:synthetic-home") -> list[dict[str, Any]]:
        with self._lock:
            rows = self.connection.execute("SELECT * FROM care_task WHERE tenant_id=? AND household_id=? AND subject_id=? ORDER BY task_id", (tenant_id, household_id, subject_id)).fetchall()
        return [{**dict(row), "task_id": row["business_task_id"], "source_event_ids": json.loads(row["source_event_ids_json"]), "reschedulable": bool(row["reschedulable"])} for row in rows]

    def accept_command(self, *, command_id: str, idempotency_key: str, expected_version: int,
                       tenant_id: str, household_id: str, subject_id: str) -> bool:
        """C2 命令入口：相同幂等键不会再次执行业务副作用。"""
        if not command_id or not idempotency_key or expected_version < 1:
            raise ValueError("命令元数据无效")
        with self._lock, self.connection:
            try:
                self.connection.execute("INSERT INTO command_inbox(command_id, expected_version, idempotency_key, status, tenant_id, household_id, subject_id) VALUES(?,?,?,?,?,?,?)", (command_id, expected_version, idempotency_key, "ACCEPTED", tenant_id, household_id, subject_id))
                return True
            except sqlite3.IntegrityError:
                return False

    def complete_command(self, *, idempotency_key: str, status: str) -> None:
        if status not in {"SUCCEEDED", "DENIED", "FAILED"}:
            raise ValueError("命令结束状态无效")
        with self._lock, self.connection:
            self.connection.execute("UPDATE command_inbox SET status=? WHERE idempotency_key=? AND status='ACCEPTED'", (status, idempotency_key))

    def command_status(self, idempotency_key: str) -> str | None:
        row = self.connection.execute("SELECT status FROM command_inbox WHERE idempotency_key=?", (idempotency_key,)).fetchone()
        return row["status"] if row else None

    def execute_once(self, *, idempotency_key: str, intent_id: str, result: dict[str, Any], tenant_id: str = "tenant:synthetic", household_id: str = "household:synthetic-home", subject_id: str = "user:synthetic-01") -> tuple[bool, dict[str, Any]]:
        with self._lock, self.connection:
            row = self.connection.execute("SELECT result_json FROM intent_execution WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            if row: return False, json.loads(row["result_json"])
            self.connection.execute("INSERT INTO intent_execution(idempotency_key, intent_id, status, result_json, tenant_id, household_id, subject_id) VALUES(?,?,?,?,?,?,?)", (idempotency_key, intent_id, result["status"], json.dumps(result, ensure_ascii=False), tenant_id, household_id, subject_id))
            return True, result

    def save_context_snapshot(self, snapshot: dict[str, Any]) -> None:
        with self._lock, self.connection:
            self.connection.execute("INSERT OR IGNORE INTO context_snapshot(snapshot_id, subject_id, purpose, hash, snapshot_json, tenant_id, household_id) VALUES(?,?,?,?,?,?,?)", (snapshot["snapshot_id"], snapshot["subject_id"], snapshot["purpose"], snapshot["hash"], json.dumps(snapshot, ensure_ascii=False, sort_keys=True), snapshot.get("tenant_id", "tenant:synthetic"), snapshot.get("household_id", "household:synthetic-home")))
    def context_snapshot(self, snapshot_id: str, *, tenant_id: str = "tenant:synthetic", household_id: str = "household:synthetic-home", subject_id: str = "user:synthetic-01") -> dict[str, Any] | None:
        with self._lock: row = self.connection.execute("SELECT snapshot_json FROM context_snapshot WHERE snapshot_id=? AND tenant_id=? AND household_id=? AND subject_id=?", (snapshot_id, tenant_id, household_id, subject_id)).fetchone()
        return json.loads(row["snapshot_json"]) if row else None
    def save_plan(self, plan: dict[str, Any]) -> None:
        with self._lock, self.connection: self.connection.execute("INSERT OR IGNORE INTO agent_plan(plan_id, agent_run_id, plan_json, tenant_id, household_id, subject_id) VALUES(?,?,?,?,?,?)", (plan["plan_id"], plan["agent_run_id"], json.dumps(plan, ensure_ascii=False, sort_keys=True), plan.get("tenant_id", "tenant:synthetic"), plan.get("household_id", "household:synthetic-home"), plan.get("subject_id", "user:synthetic-01")))
    def plan(self, plan_id: str, *, tenant_id: str = "tenant:synthetic", household_id: str = "household:synthetic-home", subject_id: str = "user:synthetic-01") -> dict[str, Any] | None:
        with self._lock: row = self.connection.execute("SELECT plan_json FROM agent_plan WHERE plan_id=? AND tenant_id=? AND household_id=? AND subject_id=?", (plan_id, tenant_id, household_id, subject_id)).fetchone()
        return json.loads(row["plan_json"]) if row else None
