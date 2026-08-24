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

`MockCoreAdapter` 提供纯合成 fixtures、幂等处理、版本冲突和故障注入。`CoreApiAdapter` 当前返回 `UNAVAILABLE`，并通过扩展原因 `NOT_IMPLEMENTED` 表示真实 BFF 尚未接入。
