import pytest

from carehub.vision.inference import observations_from_detections


@pytest.mark.parametrize("value", ["电话：13800000000", "姓名：张三", "fall\nextra"])
def test_detection_adapter_rejects_pii_or_control_text(value):
    with pytest.raises(ValueError, match="PII"):
        observations_from_detections([{"observation_id": "o-1", "label": value, "confidence": 0.8}])
