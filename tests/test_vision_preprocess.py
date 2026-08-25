import pytest

cv2 = pytest.importorskip("cv2")
import numpy as np

from carehub.vision.preprocess import preprocess_bgr


def test_preprocess_returns_metadata_without_persisting_frame():
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    frame[:, 50:150] = 255
    resized, metadata = preprocess_bgr(frame, camera_simulator_id="camera-synthetic", frame_timestamp="2026-08-25T20:00:00+00:00", target_size=64)
    assert resized.shape == (32, 64, 3)
    assert metadata.quality == "HIGH"
    assert len(metadata.frame_sha256) == 64


def test_preprocess_rejects_invalid_frame_contract():
    with pytest.raises(ValueError, match="uint8 BGR"):
        preprocess_bgr(np.zeros((10, 10), dtype=np.uint8), camera_simulator_id="camera", frame_timestamp="2026-08-25T20:00:00+00:00")
