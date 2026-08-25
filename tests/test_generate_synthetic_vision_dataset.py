import pytest
pytest.importorskip("cv2")
from scripts.generate_synthetic_vision_dataset import generate


def test_generate_dataset_is_reproducible_shape(tmp_path):
    generate(tmp_path / "dataset", count=4)
    assert len(list((tmp_path / "dataset/images/train").glob("*.png"))) == 4
    assert len(list((tmp_path / "dataset/labels/val").glob("*.txt"))) == 2
    assert "synthetic_observation" in (tmp_path / "dataset/dataset.yaml").read_text()
