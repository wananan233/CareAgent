# C0 多租户归属与事件正确性 — 验收候选

状态：**READY_FOR_REVIEW**。本文件记录工程证据，不替代项目负责人和安全负责人的正式 ACCEPTED 签收。

## 已完成

- `CareEventV1` 现要求 `tenant_id`、`household_id`、`subject_id`、`aggregate_type` 与 `aggregate_id`；aggregate 三段字段一致性在写入前校验。
- `event_log` 的业务唯一键为 `tenant_id + household_id + aggregate_type + aggregate_id + sequence`；不同家庭或租户可使用相同业务 aggregate ID。
- 相同 `event_id` 使用完整规范化信封指纹比较；不同归属、时间、来源、聚合或 payload 会被隔离为 `EVENT_ID_ENVELOPE_CONFLICT`。
- 已知结构化事件的 payload 通过 registry 校验；缺少 `ALERT_RAISED`、任务、Consent 或用药证据所需字段的输入不会写入主事件链。
- 事件、Outbox、投影、聊天上下文、任务、AgentRun、上下文快照、计划、命令幂等记录、审计和死信记录均带 scope 归属。任务的数据库存储键使用 scope 前缀，避免同名任务冲突。
- 新增 Tenant/Household/Subject/Principal/Membership/SubjectLink/DeviceBinding 关系表和仅用于合成身份的 `register_scope` 仓储入口；它不授予权限。
- 旧版无 tenant 的 `event_log` 与 `outbox` 在打开数据库时重命名为 `legacy_unscoped_*`，不会进入任何当前 scope 读取路径。

## 验证证据

- 契约校验：`python -m scripts.validate_contracts`
- 全量测试：`python -m pytest -q`，最终结果见本阶段交付记录。
- 回归覆盖：跨家庭同名 aggregate、跨 tenant 投影隔离、同 event ID 不同信封、畸形 typed payload、旧库隔离、scope 任务读取、并发同 sequence、重启重放及原子 Outbox。

## 回滚

数据库迁移前应创建只读备份。若需要回滚，恢复 B0 基线的独立干净检出与备份数据库；不得把 `legacy_unscoped_*` 中的记录猜测性重新归属或暴露给会话。

## 交接给 C1

C1 必须以 `TenantScopeV1` 和关系表为身份/角色来源，Bearer 或请求体不得自报 household、subject、role 或 consent scope。C1 负责把现有 scope 过滤升级为统一 PDP 的默认拒绝决策。
