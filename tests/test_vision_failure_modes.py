import pytest
from carehub.vision.preprocess import preprocess_bgr
from carehub.vision.fall import FallFeatureClassifier

def test_invalid_timestamp_rejected():
    with pytest.raises(ValueError, match="ISO-8601"):
        preprocess_bgr(object(), camera_simulator_id="cam", frame_timestamp="not-a-time")

def test_model_replacement_changes_version(tmp_path):
    payload = '{"weights":[0,0,0,0,0,0,0,0],"mean":[0,0,0,0,0,0,0,0],"scale":[1,1,1,1,1,1,1,1],"bias":0}'
    first = tmp_path / "a.json"; second = tmp_path / "b.json"
    first.write_text(payload, encoding="utf-8"); second.write_text(payload + " ", encoding="utf-8")
    assert FallFeatureClassifier(first).model_version != FallFeatureClassifier(second).model_version
