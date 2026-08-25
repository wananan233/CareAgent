# 老人端 Adapter 兼容说明

`MockCoreAdapter` 与 `CoreApiAdapter` 均实现 `apps/elder-terminal/src/services/adapter.ts` 中的 `ElderTerminalApi`。

## 共享边界

- 返回值统一为 `AdapterResult<T>`。
- DTO 从 `@carehub/shared-contracts/elder` 导入；该入口复用家庭端 Core DTO。
- 请求使用 snake_case 字段，并携带幂等键与预期版本。
- 失败使用家庭端规范的扁平 `ErrorEnvelope`；版本冲突返回 `code = VERSION_CONFLICT`。
- 告警确认将状态从 `OPEN` 变为 `VIEWED`，回执状态为 `RECORDED`。
- Agent 事实必须带非空字符串 `source_refs`，否则运行时 guard 拒绝渲染。

## 实现状态

`MockCoreAdapter` 提供纯合成 fixtures、幂等处理、版本冲突和故障注入。`CoreApiAdapter` 已通过受保护的家庭/主体 BFF 路由读取 dashboard、tasks、alerts、timeline 和日报 Agent，并通过同一 BFF 边界提交确认命令、按 scope 定位并撤销真实 consent。HTTP 失败统一映射为 `NETWORK_OFFLINE` 或 BFF 的扁平错误信封；不完整 DTO 显式返回 `SCHEMA_INVALID`。

运行时仅在 `VITE_DEMO_MODE=mock` 或开发环境未配置 BFF 时使用 Mock。真实 BFF 模式需要 `VITE_CAREHUB_BFF_URL`、`VITE_CAREHUB_TOKEN` 与 `VITE_CAREHUB_HOUSEHOLD_ID`；生产构建不会静默回落到 Mock。
