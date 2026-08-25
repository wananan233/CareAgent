import pytest

from carehub.vision.inference import observations_from_detections


def test_detection_adapter_keeps_only_minimal_fields():
    result = observations_from_detections([{"observation_id": "o-1", "label": "fall", "confidence": 0.91}])
    assert result[0].confidence_bucket == "HIGH"
    assert result[0].temporal_state == "CANDIDATE"


@pytest.mark.parametrize("field", ["frame", "video_path", "face_id", "bbox", "person_id"])
def test_detection_adapter_rejects_media_and_identity_fields(field):
    with pytest.raises(ValueError, match="forbidden"):
        observations_from_detections([{"observation_id": "o-1", "label": "fall", "confidence": 0.9, field: "secret"}])


def test_detection_adapter_rejects_invalid_confidence():
    with pytest.raises(ValueError, match="confidence"):
        observations_from_detections([{"observation_id": "o-1", "label": "fall", "confidence": 2}])
