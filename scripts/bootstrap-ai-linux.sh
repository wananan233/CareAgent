#!/usr/bin/env bash
set -euo pipefail

# Linux AI 依赖引导。虚拟环境、缓存和数据卷由调用方通过环境变量指定；
# 本脚本不处理 API 密钥，不下载数据集、视频或模型权重。
PYTHON_BIN="${CAREHUB_VISION_PYTHON:-/home/ziyi/anaconda3/envs/carehub-research/bin/python}"
CHECK_ONLY=0
if [[ "${1:-}" == "--check-only" ]]; then
  CHECK_ONLY=1
fi

"$PYTHON_BIN" - <<'PY'
import importlib.util
import sys

required = ("cv2", "torch", "ultralytics", "onnxruntime")
missing = [name for name in required if importlib.util.find_spec(name) is None]
if missing:
    print("missing=" + ",".join(missing))
    sys.exit(2)
print("vision_dependencies=ready")
PY

if (( CHECK_ONLY )); then
  exit 0
fi

"$PYTHON_BIN" -m pip install \
  'opencv-python-headless==4.12.0.88' \
  'ultralytics==8.3.166' \
  'onnxruntime==1.22.1'
