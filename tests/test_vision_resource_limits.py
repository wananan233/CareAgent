import pytest
from carehub.vision.bounded import bounded_observations

def test_detection_batch_resource_limit():
    detections = ({"observation_id": str(i), "label": "fall", "confidence": .5} for i in range(3))
    with pytest.raises(ValueError, match="resource limit"):
        bounded_observations(detections, max_detections=2)
