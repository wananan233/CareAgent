"""UR Fall 特征模型适配器：只产生候选观察，不裁决安全状态。"""
from __future__ import annotations

import hashlib, json
from dataclasses import dataclass
from pathlib import Path
import math

@dataclass(frozen=True)
class FallCandidate:
    label: str
    confidence: float
    model_version: str

class FallFeatureClassifier:
    def __init__(self, model_path: str | Path):
        path = Path(model_path)
        if not path.is_file() or path.is_relative_to(Path.cwd()):
            raise ValueError("model must be an existing external file")
        self.model_version = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        data = json.loads(path.read_text(encoding="utf-8"))
        if len(data.get("weights", [])) != 8 or len(data.get("mean", [])) != 8 or len(data.get("scale", [])) != 8:
            raise ValueError("invalid UR Fall model shape")
        self._w, self._mu, self._sd, self._b = data["weights"], data["mean"], data["scale"], data["bias"]

    def predict(self, features: list[float] | tuple[float, ...]) -> FallCandidate:
        if len(features) != 8 or not all(math.isfinite(float(x)) for x in features):
            raise ValueError("features must contain 8 finite values")
        z = self._b + sum(w * ((float(x) - m) / s) for x, w, m, s in zip(features, self._w, self._mu, self._sd))
        confidence = 1.0 / (1.0 + math.exp(-max(-40.0, min(40.0, z))))
        return FallCandidate("fall_candidate" if confidence >= 0.5 else "not_fall_candidate", confidence, self.model_version)
