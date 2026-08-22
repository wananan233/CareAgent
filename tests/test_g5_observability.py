import os
import sqlite3
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import pytest

from carehub.core.events import new_event
from carehub.core.service import CareCore
from carehub.g3 import PrivacyAccessRequest
from carehub.g4 import FakeProvider, ModelGateway
from carehub.g5 import Metrics, TraceRecorder, replay_report
from carehub.simulators.devices import DeviceSimulator


def test_trace_metrics_are_minimal_and_quantified():
    trace = TraceRecorder()
    for index in range(100):
        trace.record(trace_id=f"trace-{index}", operation="normalize_to_rule", duration_ms=1 + index / 100, outcome="ALLOW", reason_code="OK")
    snapshot = Metrics(trace).snapshot()["normalize_to_rule"]
    assert snapshot["count"] == 100
    assert snapshot["p95_ms"] < 2
    assert all("message" not in span.__dict__ for span in trace.spans())


def test_500_safety_event_replay_is_deterministic_and_has_no_duplicates(tmp_path):
    core = CareCore(tmp_path / "g5-replay.db")
    for index in range(500):
        core.ingest(new_event(aggregate=f"device:careport-{index}", sequence=1, event_type="SMOKE_DETECTED", quality="HIGH", event_id=f"evt-safety-{index}"))
    first = replay_report(core.store.events())
    restored = CareCore(tmp_path / "g5-replay.db")
    second = replay_report(restored.store.events())
    assert first.event_count == 1500  # 每条安全输入产生 ALERT_RAISED 与固定响应
    assert first == second
    assert first.duplicate_event_ids == 0 and first.safety_alerts == 500
    core.close(); restored.close()


def test_duplicate_restart_offline_backlog_and_model_fault_are_recoverable(tmp_path):
    path = tmp_path / "g5-fault.db"; core = CareCore(path)
    event = DeviceSimulator().medication_due("morning", 1)
    assert len(core.ingest(event)) == 1
    assert core.ingest(event) == []  # 重复输入无副作用
    expected = core.projections.digest(); assert core.store.pending_outbox_count() == 2  # 断网时积压
    core.close()
    restored = CareCore(path); assert restored.replay().digest() == expected  # 模拟进程重启
    model = ModelGateway(FakeProvider(malformed=True)).generate(purpose="TODAY_STATUS", minimal_context={"facts": []})
    assert model["fallback"] == "TEMPLATE_FALLBACK"
    restored.close()


def test_sigkill_after_committed_ingest_recovers_from_wal(tmp_path):
    database = tmp_path / "sigkill.db"
    child = (
        "from carehub.core.events import new_event; from carehub.core.service import CareCore; "
        f"core=CareCore({str(database)!r}); "
        "core.ingest(new_event(aggregate='device:kill', sequence=1, event_type='SMOKE_DETECTED', quality='HIGH', event_id='evt-kill')); "
        "print('COMMITTED', flush=True); import time; time.sleep(30)"
    )
    process = subprocess.Popen([sys.executable, "-c", child], cwd=Path(__file__).parents[1], stdout=subprocess.PIPE, text=True)
    try:
        assert process.stdout and process.stdout.readline().strip() == "COMMITTED"
        os.kill(process.pid, 9)
        assert process.wait(timeout=5) != 0
    finally:
        if process.poll() is None:
            process.kill()
    restored = CareCore(database)
    report = replay_report(restored.store.events())
    assert (report.event_count, report.safety_alerts, report.duplicate_event_ids) == (3, 1, 0)
    restored.close()


def test_sqlite_page_limit_causes_atomic_disk_pressure_rollback(tmp_path):
    core = CareCore(tmp_path / "disk-full.db")
    pages = core.store.connection.execute("PRAGMA page_count").fetchone()[0]
    core.store.connection.execute(f"PRAGMA max_page_count={pages}")
    oversized = new_event(aggregate="device:disk", sequence=1, event_type="DEVICE_OFFLINE", payload={"blob": "x" * 2_000_000})
    with pytest.raises(sqlite3.OperationalError, match="full"):
        core.ingest(oversized)
    assert list(core.store.events()) == []
    assert core.store.pending_outbox_count() == 0
    core.close()
