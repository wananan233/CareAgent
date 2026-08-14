"""SQLite WAL 追加事件库与 Transactional Outbox。"""

from __future__ import annotations

import json
import hashlib
import sqlite3
from threading import RLock
from pathlib import Path
from typing import Any, Iterable

from .errors import EventConflictError


class EventStore:
    def __init__(self, database_path: str | Path) -> None:
        self.path = str(database_path)
        self._lock = RLock()
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    def close(self) -> None:
        with self._lock:
            self.connection.close()

    def _migrate(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS event_log (
              global_sequence INTEGER PRIMARY KEY AUTOINCREMENT,
              event_id TEXT NOT NULL UNIQUE,
              aggregate TEXT NOT NULL,
              aggregate_sequence INTEGER NOT NULL,
              occurred_at TEXT NOT NULL,
              received_at TEXT NOT NULL,
              source TEXT NOT NULL,
              quality TEXT NOT NULL,
              privacy TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              checksum TEXT NOT NULL,
              correlation_id TEXT NOT NULL,
              causation_id TEXT,
              trace_id TEXT,
              UNIQUE(aggregate, aggregate_sequence)
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
            """
        )
        self.connection.commit()

    def append(self, event: dict[str, Any], destination: str = "care-sync") -> bool:
        """原子写入 event_log 与 outbox；重复的同内容事件为幂等成功。"""
        with self._lock:
            return self._append_locked(event, destination)

    def _append_locked(self, event: dict[str, Any], destination: str) -> bool:
        required = {"event_id", "aggregate", "sequence", "occurred_at", "received_at", "source", "quality", "privacy", "payload", "checksum", "correlation_id"}
        missing = required.difference(event)
        if missing:
            raise ValueError(f"事件缺少字段: {sorted(missing)}")
        existing = self.connection.execute(
            "SELECT checksum FROM event_log WHERE event_id = ?", (event["event_id"],)
        ).fetchone()
        if existing:
            if existing["checksum"] == event["checksum"]:
                return False
            with self.connection:
                self._dead_letter(event, "EVENT_ID_CHECKSUM_CONFLICT")
            raise EventConflictError(f"event_id 冲突: {event['event_id']}")
        try:
            with self.connection:
                self.connection.execute(
                    """INSERT INTO event_log(event_id, aggregate, aggregate_sequence, occurred_at, received_at,
                       source, quality, privacy, payload_json, checksum, correlation_id, causation_id, trace_id)
                       VALUES(:event_id, :aggregate, :sequence, :occurred_at, :received_at, :source, :quality,
                       :privacy, :payload_json, :checksum, :correlation_id, :causation_id, :trace_id)""",
                    {**event, "payload_json": json.dumps(event["payload"], ensure_ascii=False, sort_keys=True)},
                )
                self.connection.execute("INSERT INTO outbox(event_id, destination) VALUES(?, ?)", (event["event_id"], destination))
                return True
        except sqlite3.IntegrityError as error:
            raise ValueError(f"Aggregate sequence 冲突: {event['aggregate']}#{event['sequence']}") from error

    def _dead_letter(self, event: dict[str, Any], code: str) -> None:
        received_at = event["received_at"]
        self.connection.execute(
            "INSERT INTO dead_letter(raw_input, error_code, first_seen_at, last_seen_at, disposition) VALUES(?,?,?,?,?)",
            (json.dumps(event, ensure_ascii=False), code, received_at, received_at, "QUARANTINED"),
        )

    def events(self) -> Iterable[dict[str, Any]]:
        with self._lock:
            rows = self.connection.execute("SELECT * FROM event_log ORDER BY global_sequence").fetchall()
        for row in rows:
            yield {
                "event_id": row["event_id"], "aggregate": row["aggregate"], "sequence": row["aggregate_sequence"],
                "occurred_at": row["occurred_at"], "received_at": row["received_at"], "source": row["source"],
                "quality": row["quality"], "privacy": row["privacy"], "payload": json.loads(row["payload_json"]),
                "checksum": row["checksum"], "correlation_id": row["correlation_id"], "causation_id": row["causation_id"], "trace_id": row["trace_id"],
                "global_sequence": row["global_sequence"],
            }

    def pending_outbox_count(self) -> int:
        with self._lock:
            return self.connection.execute("SELECT COUNT(*) FROM outbox WHERE status='PENDING'").fetchone()[0]

    def journal_mode(self) -> str:
        with self._lock:
            return self.connection.execute("PRAGMA journal_mode").fetchone()[0]

    def record_audit(self, *, actor: str, capability: str, decision: str, reason: str, resource: str) -> str:
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
                "INSERT INTO audit_entry(actor, capability, decision, reason, resource, hash_chain) VALUES(?,?,?,?,?,?)",
                (actor, capability, decision, reason, resource, hash_chain),
            )
            return hash_chain

    def audit_entries(self) -> list[dict[str, str]]:
        with self._lock:
            rows = self.connection.execute("SELECT actor, capability, decision, reason, resource, hash_chain FROM audit_entry ORDER BY id").fetchall()
        return [dict(row) for row in rows]
