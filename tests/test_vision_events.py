from carehub.core.event_store import EventStore
from carehub.vision import VisionObservation, build_vision_event, confirm_observation
from carehub.vision.events import append_vision_observation


def test_temporal_confirmation_is_deterministic():
    assert confirm_observation(["fall", "fall"]) == "CANDIDATE"
    assert confirm_observation(["fall", "fall", "fall"]) == "CONFIRMED"
    assert confirm_observation(["fall", "other", "fall"]) == "CANDIDATE"
    assert confirm_observation([]) == "REJECTED"


def test_vision_event_contains_no_media_or_identity_fields(tmp_path):
    event = build_vision_event(
        VisionObservation("obs-1", "fall", "MEDIUM", "CONFIRMED"),
        tenant_id="tenant:test", household_id="household:test", subject_id="user:test",
        aggregate_id="camera-synthetic", sequence=1, occurred_at="2026-08-25T10:00:00+00:00",
    )
    payload = event["payload"]
    assert set(payload) == {"event_type", "observation_id", "label", "confidence_bucket", "temporal_state"}
    assert "video" not in str(event).lower()
    assert "frame" not in str(event).lower()
    store = EventStore(tmp_path / "vision.db")
    assert append_vision_observation(store, event)
    assert list(store.events())[0]["payload"]["event_type"] == "VISION_OBSERVATION"
    store.close()
