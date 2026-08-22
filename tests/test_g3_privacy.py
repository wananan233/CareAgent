from datetime import datetime, timedelta, timezone

import pytest

from carehub.core.event_store import EventStore
from carehub.g3 import G3Service, PrivacyAccessRequest, scan_sensitive_logs


class Clock:
    def __init__(self): self.now = datetime(2026, 8, 14, tzinfo=timezone.utc)
    def __call__(self): return self.now


@pytest.fixture
def g3(tmp_path):
    clock = Clock(); store = EventStore(tmp_path / "g3.db"); service = G3Service(store, clock)
    yield service, store, clock
    store.close()


def activate(service, item):
    for target in ("POLICY_ACCEPTED", "CONFIRMED", "ACTIVE"):
        item = service.transition_memory(item["memory_id"], actor="user:alice", household_id="home-a", role="SELF", target=target, expected_version=item["version"])
    return item


def test_memory_requires_source_ttl_and_never_directly_active(g3):
    service, _, clock = g3
    with pytest.raises(ValueError):
        service.propose_memory(owner="user:alice", household_id="home-a", memory_type="PREFERENCE", value="小护", source_event_ids=[], confidence=.8, sensitivity="SENSITIVE", consent_scope="timeline", expires_at=clock() + timedelta(days=1))
    item = service.propose_memory(owner="user:alice", household_id="home-a", memory_type="ADDRESS_FORM", value="王阿姨", source_event_ids=["evt-1"], confidence=.9, sensitivity="SENSITIVE", consent_scope="timeline", expires_at=clock() + timedelta(days=1))
    assert item["status"] == "CANDIDATE"
    with pytest.raises(ValueError):
        service.transition_memory(item["memory_id"], actor="user:alice", household_id="home-a", role="SELF", target="ACTIVE", expected_version=1)
    assert activate(service, item)["status"] == "ACTIVE"


def test_consent_revoke_is_immediate_and_cross_household_is_denied(g3):
    service, _, clock = g3
    item = activate(service, service.propose_memory(owner="user:alice", household_id="home-a", memory_type="PREFERENCE", value="晨间提醒", source_event_ids=["evt-2"], confidence=.8, sensitivity="SENSITIVE", consent_scope="timeline", expires_at=clock() + timedelta(days=1)))
    consent = service.ledger.grant(owner="user:alice", grantee="user:bob", household_id="home-a", scope="timeline", purpose="memory", expires_at=clock() + timedelta(minutes=1))
    allowed = PrivacyAccessRequest("user:bob", "user:alice", "home-a", "FAMILY", "timeline", "memory", "SENSITIVE", "TERMINAL")
    wrong_home = PrivacyAccessRequest("user:bob", "user:alice", "home-b", "FAMILY", "timeline", "memory", "SENSITIVE", "TERMINAL")
    assert service.active_memories(allowed)[0]["memory_id"] == item["memory_id"]
    assert service.active_memories(wrong_home) == []
    service.ledger.revoke(consent["consent_id"], actor="user:alice", expected_version=1)
    assert service.active_memories(allowed) == []


def test_working_memory_ttl_erasure_and_sensitive_log_scan(g3):
    service, store, clock = g3
    memory_id = service.put_working(owner="user:alice", value={"turn": 1}, ttl_seconds=1)
    assert service.get_working(memory_id, owner="user:alice")["value"] == {"turn": 1}
    clock.now += timedelta(seconds=2)
    assert service.get_working(memory_id, owner="user:alice") is None
    item = service.propose_memory(owner="user:alice", household_id="home-a", memory_type="HABIT", value="午睡", source_event_ids=["evt-3"], confidence=.7, sensitivity="SENSITIVE", consent_scope="timeline", expires_at=clock() + timedelta(days=1))
    service.register_artifact(owner="user:alice", kind="ASR_AUDIO", storage_ref="volatile://audio-1", expires_at=clock() + timedelta(seconds=60))
    assert service.delete_personal_data(owner="user:alice", actor="user:alice") == {"memories_revoked": 1, "artifacts_deleted": 1}
    assert service.memory(item["memory_id"])["status"] == "REVOKED"
    assert scan_sensitive_logs(["decision=ALLOW", "duration_ms=12"]) == []
    assert scan_sensitive_logs(["decision=ALLOW", "电话: 13800000000", "Bearer secret"]) == ["line:2", "line:3"]
    assert all("138" not in entry["resource"] for entry in store.audit_entries())
