"""C3 可靠事件闭环：可恢复 Outbox、ACK、DLQ 与仅站内的模拟通知。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

from .event_store import EventStore
from .projections import Projections


def now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SimulatedInbox:
    """仅 SQLite 站内收件箱，永久标识为 SIMULATOR。"""
    def __init__(self, store: EventStore) -> None:
        self.store = store
        self.store.connection.execute("""CREATE TABLE IF NOT EXISTS notification_receipt(
          receipt_id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL, destination TEXT NOT NULL,
          status TEXT NOT NULL, simulator TEXT NOT NULL, delivered_at TEXT NOT NULL, UNIQUE(event_id,destination))""")
        self.store.connection.commit()

    def deliver(self, event_id: str, destination: str) -> None:
        with self.store.connection:
            self.store.connection.execute("INSERT OR IGNORE INTO notification_receipt(event_id,destination,status,simulator,delivered_at) VALUES(?,?,?,?,?)", (event_id, destination, "DELIVERED", "SIMULATOR", now_text()))

    def receipts(self) -> list[dict[str, str]]:
        return [dict(row) for row in self.store.connection.execute("SELECT event_id,destination,status,simulator,delivered_at FROM notification_receipt ORDER BY receipt_id")]

    def mark_viewed(self, event_id: str, destination: str) -> None:
        with self.store.connection:
            self.store.connection.execute("UPDATE notification_receipt SET status='VIEWED' WHERE event_id=? AND destination=? AND status='DELIVERED'", (event_id, destination))


class OutboxWorker:
    def __init__(self, store: EventStore, *, inbox: SimulatedInbox | None = None, max_attempts: int = 3,
                 clock: Callable[[], str] = now_text) -> None:
        self.store, self.inbox, self.max_attempts, self.clock = store, inbox or SimulatedInbox(store), max_attempts, clock
        self.store.connection.execute("""CREATE TABLE IF NOT EXISTS outbox_delivery(
          event_id TEXT NOT NULL, destination TEXT NOT NULL, lease_until TEXT, last_error TEXT,
          PRIMARY KEY(event_id,destination))""")
        self.store.connection.commit()

    def claim(self, *, lease_seconds: int = 30) -> dict[str, str] | None:
        now = self.clock(); lease = (datetime.fromisoformat(now) + timedelta(seconds=lease_seconds)).isoformat(timespec="seconds")
        with self.store._lock, self.store.connection:
            row = self.store.connection.execute("SELECT o.* FROM outbox o LEFT JOIN outbox_delivery d ON d.event_id=o.event_id AND d.destination=o.destination WHERE o.status='PENDING' OR (o.status='IN_FLIGHT' AND d.lease_until<?) ORDER BY o.event_id LIMIT 1", (now,)).fetchone()
            if not row: return None
            self.store.connection.execute("UPDATE outbox SET status='IN_FLIGHT' WHERE event_id=? AND destination=?", (row["event_id"], row["destination"]))
            self.store.connection.execute("INSERT INTO outbox_delivery(event_id,destination,lease_until,last_error) VALUES(?,?,?,NULL) ON CONFLICT(event_id,destination) DO UPDATE SET lease_until=excluded.lease_until", (row["event_id"], row["destination"], lease))
            return dict(row)

    def ack(self, event_id: str, destination: str) -> None:
        with self.store._lock, self.store.connection:
            self.inbox.deliver(event_id, destination)
            self.store.connection.execute("UPDATE outbox SET status='DELIVERED' WHERE event_id=? AND destination=?", (event_id, destination))
            self.store.connection.execute("DELETE FROM outbox_delivery WHERE event_id=? AND destination=?", (event_id, destination))

    def fail(self, event_id: str, destination: str, error_code: str) -> None:
        with self.store._lock, self.store.connection:
            row = self.store.connection.execute("SELECT attempt,tenant_id,household_id,subject_id FROM outbox WHERE event_id=? AND destination=?", (event_id, destination)).fetchone()
            if not row: raise KeyError(event_id)
            attempt = row["attempt"] + 1
            if attempt >= self.max_attempts:
                self.store.connection.execute("UPDATE outbox SET attempt=?,status='DLQ' WHERE event_id=? AND destination=?", (attempt, event_id, destination))
                self.store.connection.execute("INSERT INTO dead_letter(raw_input,error_code,first_seen_at,last_seen_at,disposition,tenant_id,household_id,subject_id) VALUES(?,?,?,?,?,?,?,?)", (f"outbox:{event_id}:{destination}", error_code, self.clock(), self.clock(), "OUTBOX_DLQ", row["tenant_id"], row["household_id"], row["subject_id"]))
            else:
                self.store.connection.execute("UPDATE outbox SET attempt=?,status='PENDING',next_retry_at=? WHERE event_id=? AND destination=?", (attempt, self.clock(), event_id, destination))
            self.store.connection.execute("DELETE FROM outbox_delivery WHERE event_id=? AND destination=?", (event_id, destination))

    def run_once(self, *, fail_with: str | None = None) -> str | None:
        item = self.claim()
        if not item: return None
        if fail_with:
            self.fail(item["event_id"], item["destination"], fail_with); return "RETRY" if item["attempt"] + 1 < self.max_attempts else "DLQ"
        self.ack(item["event_id"], item["destination"]); return "DELIVERED"

    def replay_dlq(self, event_id: str, destination: str) -> None:
        with self.store._lock, self.store.connection:
            self.store.connection.execute("UPDATE outbox SET status='PENDING',attempt=0,next_retry_at=NULL WHERE event_id=? AND destination=? AND status='DLQ'", (event_id, destination))


class ProjectionWorker:
    """投影进度和摘要哈希持久化；可在重启后从 checkpoint 继续。"""
    def __init__(self, store: EventStore, *, name: str = "core-projections") -> None:
        self.store, self.name, self.projections = store, name, Projections()
        row = self.store.connection.execute("SELECT last_global_sequence FROM projection_checkpoint WHERE projection=?", (name,)).fetchone()
        self.last_sequence = int(row["last_global_sequence"]) if row else 0
        # 进程重启时以权威 EventStore 重建内存投影，checkpoint 仍用于可审计进度。
        self.projections = Projections.rebuild(store.events())

    def run_once(self) -> int:
        events = list(self.store.events())
        pending = list(enumerate(events[self.last_sequence:], self.last_sequence + 1))
        if not pending: return 0
        for sequence, event in pending:
            # 重启初始化已重建全部投影，故只更新 checkpoint；首次 worker 则重建确保幂等。
            self.last_sequence = sequence
        digest = self.projections.digest()
        with self.store.connection:
            self.store.connection.execute("INSERT INTO projection_checkpoint(projection,last_global_sequence,hash,tenant_id,household_id,subject_id) VALUES(?,?,?,?,?,?) ON CONFLICT(projection) DO UPDATE SET last_global_sequence=excluded.last_global_sequence,hash=excluded.hash", (self.name, self.last_sequence, digest, "tenant:system", "household:system", "user:system"))
        return len(pending)

    def rebuild(self) -> str:
        self.projections = Projections.rebuild(self.store.events()); self.last_sequence = len(list(self.store.events()))
        with self.store.connection:
            self.store.connection.execute("INSERT INTO projection_checkpoint(projection,last_global_sequence,hash,tenant_id,household_id,subject_id) VALUES(?,?,?,?,?,?) ON CONFLICT(projection) DO UPDATE SET last_global_sequence=excluded.last_global_sequence,hash=excluded.hash", (self.name, self.last_sequence, self.projections.digest(), "tenant:system", "household:system", "user:system"))
        return self.projections.digest()
