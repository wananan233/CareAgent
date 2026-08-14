# ADR-001：本地优先与降级

- 状态：已接受
- 决策：`care-core` 是本地业务真源；SQLite WAL Event Store 与 Transactional Outbox 承担离线事实记录。
- 后果：网络、云端、Family Care 或模型不可用时，S-1/S0 安全任务、提醒、记录与重放继续工作；云端仅消费 Outbox。

