"""校验仓库外视觉数据集清单；不下载、不复制、不读取媒体内容。"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


FORBIDDEN_FIELDS = {"face", "face_id", "person_id", "name", "identity", "raw_video"}


def validate(manifest_path: Path, dataset_root: Path) -> int:
    if not dataset_root.is_dir() or (dataset_root / ".git").exists():
        raise ValueError("dataset_root must be an external non-git directory")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    samples = data.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("manifest.samples must be a non-empty list")
    for sample in samples:
        if not isinstance(sample, dict) or FORBIDDEN_FIELDS.intersection(sample):
            raise ValueError("manifest contains forbidden identity/media fields")
        rel = sample.get("path")
        expected = sample.get("sha256")
        if not isinstance(rel, str) or Path(rel).is_absolute() or not isinstance(expected, str) or len(expected) != 64:
            raise ValueError("each sample needs a relative path and SHA-256")
        path = (dataset_root / rel).resolve()
        if dataset_root.resolve() not in path.parents:
            raise ValueError("sample path escapes dataset_root")
        if not path.is_file():
            raise ValueError(f"missing sample: {rel}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected.lower():
            raise ValueError(f"checksum mismatch: {rel}")
    return len(samples)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("dataset_root", type=Path)
    args = parser.parse_args()
    print(f"validated_samples={validate(args.manifest, args.dataset_root)}")


if __name__ == "__main__":
    main()
