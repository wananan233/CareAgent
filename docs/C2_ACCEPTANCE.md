# C2 BFF / REST + SSE（READY_FOR_REVIEW）

已实现唯一 BFF 读取入口、认证与 PDP 复核、家庭/主体隔离的视图 DTO、ETag/snapshot、统一错误信封、同意命令的版本与幂等处理，以及带 Last-Event-ID 和撤销复核的 SSE。

验证：`python -m pytest -q`（284 passed）与 `scripts/validate_contracts.py` 通过。

正式 ACCEPTED 仍须项目负责人完成 API 契约和双端 Adapter 审阅。
