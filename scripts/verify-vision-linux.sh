#!/usr/bin/env bash
set -euo pipefail

# 视觉验证只使用合成像素，不下载权重、不读取视频、不写入仓库。
PYTHON_BIN="${CAREHUB_VISION_PYTHON:-/home/ziyi/anaconda3/envs/carehub-research/bin/python}"
"$PYTHON_BIN" - <<'PY'
import cv2
import numpy as np
import onnxruntime
import torch
import ultralytics

image = np.zeros((32, 32, 3), dtype=np.uint8)
image[8:24, 8:24] = 255
resized = cv2.resize(image, (16, 16), interpolation=cv2.INTER_AREA)
assert resized.shape == (16, 16, 3)
assert torch.zeros(1, device="cuda" if torch.cuda.is_available() else "cpu").numel() == 1
print({
    "opencv": cv2.__version__,
    "torch": torch.__version__,
    "cuda_available": bool(torch.cuda.is_available()),
    "gpu_count": torch.cuda.device_count(),
    "ultralytics": ultralytics.__version__,
    "onnxruntime": onnxruntime.__version__,
    "onnx_providers": onnxruntime.get_available_providers(),
    "synthetic_smoke": "passed",
})
PY
