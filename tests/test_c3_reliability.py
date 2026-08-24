from datetime import datetime, timedelta, timezone

from carehub.core.event_store import EventStore
from carehub.core.events import new_event
from carehub.core.reliability import OutboxWorker, ProjectionWorker, SimulatedInbox
from carehub.core.scenario import ScenarioService
from carehub.core.service import CareCore


def test_outbox_ack_is_recoverable_and_simulator_only(tmp_path):
    store = EventStore(tmp_path / "outbox.db"); event = new_event(event_id="evt-outbox", aggregate="device:x", sequence=1, event_type="DEVICE_OFFLINE")
    store.append(event); worker = OutboxWorker(store)
    assert worker.run_once() == "DELIVERED"
    assert worker.inbox.receipts()[0]["simulator"] == "SIMULATOR"
    assert store.connection.execute("SELECT status FROM outbox").fetchone()["status"] == "DELIVERED"
    store.close()


def test_outbox_retries_dlq_and_manual_replay(tmp_path):
    store = EventStore(tmp_path / "retry.db"); store.append(new_event(event_id="evt-retry", aggregate="device:y", sequence=1, event_type="DEVICE_OFFLINE")); worker = OutboxWorker(store, max_attempts=2)
    assert worker.run_once(fail_with="NETWORK_SIMULATED") == "RETRY"
    assert worker.run_once(fail_with="NETWORK_SIMULATED") == "DLQ"
    row = store.connection.execute("SELECT status,attempt FROM outbox").fetchone(); assert (row["status"], row["attempt"]) == ("DLQ", 2)
    assert store.connection.execute("SELECT disposition FROM dead_letter").fetchone()["disposition"] == "OUTBOX_DLQ"
    worker.replay_dlq("evt-retry", "care-sync"); assert worker.run_once() == "DELIVERED"
    store.close()


def test_projection_checkpoint_is_rebuildable_after_restart(tmp_path):
    path = tmp_path / "projection.db"; store = EventStore(path)
    store.append(new_event(event_id="evt-project", aggregate="task:z", sequence=1, event_type="MEDICATION_DUE"))
    worker = ProjectionWorker(store); assert worker.run_once() == 1
    checkpoint = store.connection.execute("SELECT last_global_sequence,hash FROM projection_checkpoint WHERE projection='core-projections'").fetchone()
    assert checkpoint["last_global_sequence"] == 1 and checkpoint["hash"] == worker.projections.digest()
    store.close(); restored = EventStore(path); restarted = ProjectionWorker(restored)
    assert restarted.run_once() == 0 and restarted.rebuild() == checkpoint["hash"]
    restored.close()


def test_simulator_inbox_command_status_and_fixed_scenario(tmp_path):
    core = CareCore(tmp_path / "scenario.db"); published = []; service = ScenarioService(core, publish_view=lambda **event: published.append(event) or 1)
    run = service.run(scenario="DOSE", seed=7, tenant_id="tenant:a", household_id="household:a", subject_id="user:alice")
    assert run.fixed_time.startswith("2026-08-22") and list(core.store.events())[0]["event_id"] == run.emitted_event_ids[0]
    assert [item["view"] for item in published] == ["tasks", "timeline"]
    worker = OutboxWorker(core.store); worker.run_once(); receipt = worker.inbox.receipts()[0]
    worker.inbox.mark_viewed(receipt["event_id"], receipt["destination"]); assert worker.inbox.receipts()[0]["status"] == "VIEWED"
    assert core.store.accept_command(command_id="cmd", idempotency_key="idem", expected_version=1, tenant_id="tenant:a", household_id="household:a", subject_id="user:alice")
    core.store.complete_command(idempotency_key="idem", status="SUCCEEDED"); assert core.store.command_status("idem") == "SUCCEEDED"
    core.close()
