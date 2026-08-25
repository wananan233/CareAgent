# CareHub 2.0 老人端

面向老年人的大屏 PWA 演示端。项目只使用合成数据，不接入真实硬件、账号或医疗数据。

## 与家庭端统一的工程基线

- 根工作区由 `pnpm-workspace.yaml` 管理，老人端和家庭端均位于 `apps/`。
- 两端使用相同的 Vue、Vite、Pinia、Vue Router、Vitest、Playwright 和 `vite-plugin-pwa` 版本。
- `@carehub/shared-contracts` 的根导出由 `src/family.ts` 定义，是两端 Core DTO 的规范来源。
- 老人端专属展示投影从 `@carehub/shared-contracts/elder` 导入，不重复声明家庭端 DTO。
- PWA 清单与 Service Worker 由 `vite-plugin-pwa` 生成；`src/pwa/register.ts` 仅观察更新状态。

## 启动与验证

在仓库根目录执行：

```bash
pnpm install --frozen-lockfile
pnpm --filter @carehub/elder-terminal dev
pnpm --filter @carehub/elder-terminal typecheck
pnpm --filter @carehub/elder-terminal test
pnpm --filter @carehub/elder-terminal test:e2e
pnpm --filter @carehub/elder-terminal build
```

## 契约规则

- 任务：`kind = MEDICATION_DUE`，Core 状态为 `DUE | REMINDING`，证据始终为 `UNKNOWN`。
- 告警：`kind = SMOKE_GAS`，状态为 `OPEN | VIEWED`，确认只表示“已查看”，不能解除告警。
- 请求字段统一使用 `command_id`、`idempotency_key`、`expected_version`、`reason_code`。
- 错误使用扁平 `ErrorEnvelope`：`code`、`message`、`correlation_id`。
- Agent 回复严格采用 `AgentResponseV1`，事实使用 `text` 和字符串 `source_refs`，回退使用枚举值。

老人端保留一个明确的本地展示状态 `ACKNOWLEDGED`，仅表示“已看到服药提醒”，不属于 Core 服药证据，也不代表已经服药。

## 目录

```text
apps/elder-terminal/
├── src/
│   ├── components/
│   ├── contracts/
│   ├── pages/
│   ├── scenarios/
│   ├── services/
│   └── stores/
├── tests/unit/
├── tests/e2e/
├── package.json
├── playwright.config.ts
├── tsconfig.json
└── vite.config.ts
```

`CoreApiAdapter` 已接入受保护 BFF 的 dashboard、tasks、alerts、timeline、日报 Agent、受控确认命令和按 scope 撤销授权路由。开发环境未配置 BFF 时仍使用 `MockCoreAdapter`；生产构建缺少 BFF 配置会显式失败，不会静默回落。所有数据仍限合成演示数据。
