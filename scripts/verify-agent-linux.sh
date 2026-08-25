#!/usr/bin/env bash
set -euo pipefail

# 只验证 Agent 契约与离线回归；不读取或打印任何 API 密钥。
PYTHON_BIN="${CAREHUB_PYTHON:-python}"
"$PYTHON_BIN" -m scripts.validate_contracts
"$PYTHON_BIN" -m pytest -q
