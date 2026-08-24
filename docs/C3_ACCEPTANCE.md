# C3 可靠事件闭环（READY_FOR_REVIEW）

已实现 Outbox 租约 claim、ACK、重试、DLQ、人工重放、投影 checkpoint/hash 与重建、固定场景事件注入、视图 SSE 发布，以及仅站内 `SIMULATOR` 通知收件箱的 delivered/viewed 回执。

系统不连接真实 Push、短信、电话、BLE、MQTT、GPIO 或外部通知服务。

验证：`python -m pytest -q`（284 passed）与 `scripts/validate_contracts.py` 通过。

正式 ACCEPTED 仍须项目负责人审阅故障注入和场景演示证据。
