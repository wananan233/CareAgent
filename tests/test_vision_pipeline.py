from carehub.core.event_store import EventStore
from carehub.vision.pipeline import ingest_detections


def test_ingest_detections_writes_minimal_events(tmp_path):
    store = EventStore(tmp_path / "pipeline.db")
    inserted = ingest_detections(
        store,
        [{"observation_id": "o-1", "label": "fall", "confidence": 0.91}],
        tenant_id="tenant:test", household_id="household:test", subject_id="user:test",
        device_id="camera-synthetic", sequence=1, occurred_at="2026-08-25T10:00:00+00:00",
    )
    assert len(inserted) == 1
    event = list(store.events())[0]
    assert event["aggregate"] == "device:camera-synthetic"
    assert set(event["payload"]) == {"event_type", "observation_id", "label", "confidence_bucket", "temporal_state"}
    assert ingest_detections(store, [{"observation_id": "o-1", "label": "fall", "confidence": 0.91}], tenant_id="tenant:test", household_id="household:test", subject_id="user:test", device_id="camera-synthetic", sequence=1, occurred_at="2026-08-25T10:00:00+00:00") == ()
    assert len(list(store.events())) == 1
    store.close()
