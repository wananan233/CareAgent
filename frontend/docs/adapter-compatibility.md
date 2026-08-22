# MockCoreAdapter 与 CoreApiAdapter 兼容报告

- 日期：2026-08-22
- 契约：`apps/elder-terminal/src/services/adapter.ts`（`ElderTerminalApi`）
- 版本：`0.1.0`

## 结论

两适配器**共享同一契约**，可互相替换而不改变 store/UI/测试契约。当前唯一可用实现为
`MockCoreAdapter`（合成数据）；`CoreApiAdapter` 为 C0-C4 就绪前的占位实现，全部端点返回
`NOT_IMPLEMENTED`，明确表达“OpenAPI 声明 ≠ 已运行接口”。

## 契约一致点

| 项 | 说明 |
| --- | --- |
| 接口 | 两者均实现 `ElderTerminalApi` 的 7 个方法 |
| 返回信封 | 统一 `AdapterResult<T>`（`{ok:true,data}` 或 `{ok:false,error:ErrorEnvelope}`） |
| DTO | 共享 `@carehub/shared-contracts` 的版本化类型（`*V1`） |
| 版本 | `API_VERSION = 'v1'` |
| 错误码 | 统一 `ErrorEnvelope` + `ReasonCode`（`NETWORK_OFFLINE`、`VERSION_CONFLICT`、`NOT_IMPLEMENTED` 等） |
| 写约束 | 每个 `CareRequestV1` 携带 `commandId`/`idempotencyKey`/`expectedVersion` |

## 实现差异

### MockCoreAdapter（当前启用）

- 返回 `scenarios/fixtures.ts` 的合成数据（任务/事件/告警/摘要），`source.type = 'SIMULATOR'`。
- 幂等：按 `idempotencyKey` 去重；乐观并发：`expectedVersion` 不一致返回 `VERSION_CONFLICT`。
- 故障注入：`MockFault`（`none/offline/denied/failed/timeout`）与 `AgentFault`
  （`none/timeout/out_of_bounds/no_source`），用于演示离线、越权、超时、越界/无来源等红线场景。
- 确认语义：`ACKNOWLEDGE_TASK/ALERT` 仅表达“已看到提醒”，证据状态保持 `UNKNOWN`（无“已吞服”）。

### CoreApiAdapter（占位）

- 7 个方法均返回 `NOT_IMPLEMENTED`（`makeError('NOT_IMPLEMENTED','NOT_IMPLEMENTED','该接口尚未接入',false)`）。
- 无网络请求、无数据；接入真实 BFF 前不可用于演示。

## 切换与迁移

- 切换点：`stores/care.ts` 通过适配器实例调用，替换实例即可在 Mock/Core 间切换。
- 迁移路径：C2 BFF 就绪后，在 `CoreApiAdapter` 内以 `VITE_API_BASE_URL`（默认 `/v1`）实现
  HTTP 调用，映射 6 个版本化端点，错误映射沿用现有 `ErrorEnvelope`/`ReasonCode`。
- 无需改动 store、页面组件、测试断言（它们只依赖 `ElderTerminalApi` 契约）。
