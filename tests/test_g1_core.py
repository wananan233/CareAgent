"""G1 本地事件脊柱、规则与投影的行为测试。"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from carehub.core.errors import EventConflictError
from carehub.core.event_store import EventStore
from carehub.core.events import new_event
from carehub.core.projections import Projections
from carehub.core.rules import FIXED_TEMPLATES, RuleEngine
from carehub.core.service import CareCore
from carehub.simulators.devices import DeviceSimulator


@pytest.fixture
def store(tmp_path: pytest.TempPathFactory) -> Iterator[EventStore]:
    event_store = EventStore(tmp_path / "events.db")
    yield event_store
    event_store.close()


def test_event_store_writes_event_and_outbox_atomically(store: EventStore) -> None:
    event = new_event(aggregate="device:door-01", sequence=1, event_type="DEVICE_OFFLINE")

    assert store.append(event) is True
    assert store.pending_outbox_count() == 1
    assert list(store.events())[0]["event_id"] == event["event_id"]
    assert store.journal_mode().lower() == "wal"


def test_event_store_rejects_same_event_id_with_different_content(store: EventStore) -> None:
    event = new_event(
        aggregate="device:door-01",
        sequence=1,
        event_type="DEVICE_OFFLINE",
        event_id="evt-fixed",
    )
    conflicting = {**event, "payload": {"event_type": "SOS_PRESSED"}, "checksum": "different"}
    store.append(event)

    with pytest.raises(EventConflictError, match="event_id 冲突"):
        store.append(conflicting)

    dead_letter = store.connection.execute(
        "SELECT error_code, disposition FROM dead_letter"
    ).fetchone()
    assert dict(dead_letter) == {
        "error_code": "EVENT_ID_CHECKSUM_CONFLICT",
        "disposition": "QUARANTINED",
    }
    assert len(list(store.events())) == 1
    assert store.pending_outbox_count() == 1


def test_event_store_rejects_reused_aggregate_sequence(store: EventStore) -> None:
    store.append(new_event(aggregate="device:door-01", sequence=1, event_type="DEVICE_OFFLINE"))

    with pytest.raises(ValueError, match="Aggregate sequence 冲突"):
        store.append(new_event(aggregate="device:door-01", sequence=1, event_type="SOS_PRESSED"))

    assert len(list(store.events())) == 1
    assert store.pending_outbox_count() == 1


@pytest.mark.parametrize(
    ("event_type", "quality", "expected_kind", "expected_level"),
    [
        ("SOS_PRESSED", "HIGH", "SOS", "S-1"),
        ("SMOKE_DETECTED", "HIGH", "SMOKE_GAS", "S-1"),
        ("GAS_DETECTED", "HIGH", "SMOKE_GAS", "S-1"),
        ("FALL_DETECTED", "HIGH", "FALL", "S0"),
    ],
)
def test_rule_engine_raises_expected_alerts(
    event_type: str, quality: str, expected_kind: str, expected_level: str
) -> None:
    event = new_event(
        aggregate="device:careport-01",
        sequence=7,
        event_type=event_type,
        quality=quality,
        event_id="evt-source",
        correlation_id="corr-source",
    )

    emitted = RuleEngine().decide(event)

    assert [item["payload"]["event_type"] for item in emitted] == [
        "ALERT_RAISED",
        "FIXED_RESPONSE_READY",
    ]
    alert, response = emitted
    assert alert["aggregate"] == "device:careport-01"
    assert alert["sequence"] == 8
    assert alert["payload"] == {
        "event_type": "ALERT_RAISED",
        "alert_id": "alert-evt-source",
        "kind": expected_kind,
        "safety_level": expected_level,
        "status": "ACTIVE",
    }
    assert response["aggregate"] == "alert:alert-evt-source"
    assert response["sequence"] == 1
    assert response["payload"]["template"] == FIXED_TEMPLATES[expected_kind]
    assert {item["causation_id"] for item in emitted} == {"evt-source"}
    assert {item["correlation_id"] for item in emitted} == {"corr-source"}


def test_low_quality_fall_does_not_raise_alert() -> None:
    event = new_event(
        aggregate="device:radar-01", sequence=1, event_type="FALL_DETECTED", quality="LOW"
    )

    assert RuleEngine().decide(event) == []


@pytest.mark.parametrize(
    ("event_type", "expected_type", "expected_payload"),
    [
        (
            "INACTIVITY_DETECTED",
            "WELLBEING_CHECK_REQUESTED",
            {"response_window_seconds": 120, "template": FIXED_TEMPLATES["INACTIVITY"]},
        ),
        (
            "MEDICATION_DUE",
            "PROMPT_REQUESTED",
            {
                "task_ref": "task:morning",
                "action": "request_play_reminder",
                "evidence_state": "UNKNOWN",
                "template": FIXED_TEMPLATES["MEDICATION"],
            },
        ),
        (
            "DEVICE_OFFLINE",
            "FIXED_RESPONSE_READY",
            {"safety_level": "S0", "template": FIXED_TEMPLATES["DEVICE_OFFLINE"]},
        ),
    ],
)
def test_rule_engine_emits_fixed_safe_workflows(
    event_type: str, expected_type: str, expected_payload: dict[str, object]
) -> None:
    aggregate = "task:morning" if event_type == "MEDICATION_DUE" else "device:radar-01"
    event = new_event(aggregate=aggregate, sequence=3, event_type=event_type)

    emitted = RuleEngine().decide(event)

    assert len(emitted) == 1
    assert emitted[0]["payload"] == {"event_type": expected_type, **expected_payload}
    assert emitted[0]["sequence"] == 4
    assert emitted[0]["causation_id"] == event["event_id"]


def test_care_core_is_idempotent_and_replay_preserves_projection(tmp_path: pytest.TempPathFactory) -> None:
    database = tmp_path / "care.db"
    core = CareCore(database)
    event = DeviceSimulator().medication_due("morning", 1)

    first_emitted = core.ingest(event)
    digest_after_ingest = core.projections.digest()
    duplicate_emitted = core.ingest(event)
    core.close()
    restored_core = CareCore(database)
    replayed = restored_core.replay()

    assert len(first_emitted) == 1
    assert duplicate_emitted == []
    assert len(list(restored_core.store.events())) == 2
    assert restored_core.store.pending_outbox_count() == 2
    assert replayed.digest() == digest_after_ingest
    assert replayed.tasks["task:morning"] == {
        "status": "DUE",
        "evidence_state": "UNKNOWN",
        "event_type": "MEDICATION_DUE",
        "simulator": "Dose",
        "last_prompt_event_id": first_emitted[0]["event_id"],
    }
    restored_core.close()


def test_projection_tracks_alert_resolution_and_medication_evidence() -> None:
    projection = Projections()
    projection.apply(
        new_event(
            aggregate="alert:one",
            sequence=1,
            event_type="ALERT_RAISED",
            payload={"alert_id": "alert-one", "kind": "SOS", "safety_level": "S-1", "status": "ACTIVE"},
        )
    )
    projection.apply(
        new_event(
            aggregate="alert:one",
            sequence=2,
            event_type="ALERT_RESOLVED",
            payload={"alert_id": "alert-one"},
        )
    )
    projection.apply(new_event(aggregate="task:morning", sequence=1, event_type="MEDICATION_DUE"))
    projection.apply(
        new_event(
            aggregate="task:morning",
            sequence=2,
            event_type="MEDICATION_EVIDENCE_RECORDED",
            payload={"task_ref": "task:morning", "evidence_state": "RECORDED"},
        )
    )

    assert projection.alerts["alert-one"]["status"] == "RESOLVED"
    assert projection.tasks["task:morning"]["evidence_state"] == "RECORDED"
    assert [item["event_type"] for item in projection.timeline] == [
        "ALERT_RAISED",
        "ALERT_RESOLVED",
        "MEDICATION_DUE",
        "MEDICATION_EVIDENCE_RECORDED",
    ]


def test_event_store_audit_chain_does_not_store_message_body(store: EventStore) -> None:
    first = store.record_audit(actor="CARE_AGENT", capability="chat_response", decision="ALLOW", reason="CHAT_RESPONSE", resource="chat:user:synthetic-01")
    second = store.record_audit(actor="CARE_AGENT", capability="chat_response", decision="DENY", reason="MODEL_UNAVAILABLE", resource="chat:user:synthetic-01")

    entries = store.audit_entries()
    assert first != second
    assert [entry["decision"] for entry in entries] == ["ALLOW", "DENY"]
    assert all("我现在有什么提醒" not in str(entry) for entry in entries)
