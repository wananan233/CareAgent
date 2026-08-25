import hashlib
import json

import pytest

from scripts.validate_vision_dataset import validate


def test_validate_external_manifest(tmp_path):
    root = tmp_path / "dataset"
    root.mkdir()
    sample = root / "synthetic.bin"
    sample.write_bytes(b"synthetic")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"samples": [{"path": "synthetic.bin", "sha256": hashlib.sha256(b"synthetic").hexdigest()}]}))
    assert validate(manifest, root) == 1


def test_validate_rejects_identity_field(tmp_path):
    root = tmp_path / "dataset"
    root.mkdir()
    (root / "x").write_bytes(b"x")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"samples": [{"path": "x", "sha256": hashlib.sha256(b"x").hexdigest(), "face_id": "secret"}]}))
    with pytest.raises(ValueError, match="forbidden"):
        validate(manifest, root)
