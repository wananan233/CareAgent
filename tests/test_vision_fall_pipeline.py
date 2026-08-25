from carehub.core.event_store import EventStore
from carehub.vision.fall import FallCandidate
from carehub.vision.fall_pipeline import ingest_fall_candidate


def test_fall_candidate_is_minimal_and_idempotent(tmp_path):
    store = EventStore(tmp_path / "fall.db")
    candidate = FallCandidate("fall_candidate", 0.91, "sha256:test")
    kwargs = dict(observation_id="obs-fall-1", tenant_id="tenant:t", household_id="household:h", subject_id="user:u", device_id="cam-1", sequence=1, occurred_at="2026-08-25T10:00:00+00:00")
    assert len(ingest_fall_candidate(store, candidate, **kwargs)) == 1
    assert ingest_fall_candidate(store, candidate, **kwargs) == ()
    event = list(store.events())[0]
    assert set(event["payload"]) == {"event_type", "observation_id", "label", "confidence_bucket", "temporal_state"}
    assert "video" not in str(event).lower()
    store.close()
