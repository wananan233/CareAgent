# CareHub 2.0 老人端验收报告

- 日期：2026-08-24
- 范围：根 pnpm 工作区中的家庭端、老人端与共享契约
- 结论：通过

## 对齐结果

| 项 | 结果 |
| --- | --- |
| 工作区 | `apps/family-pwa`、`apps/elder-terminal`、`apps/shared-contracts` 位于同一根工作区 |
| 包管理 | 共用 `pnpm-workspace.yaml` 与 `pnpm-lock.yaml` |
| 工具版本 | Vue/Vite/Pinia/Vue Router/Vitest/Playwright/PWA 插件一致 |
| Core DTO | `apps/shared-contracts/src/family.ts` 为规范来源 |
| 老人端扩展 | 仅放在 `apps/shared-contracts/src/elder/`，通过子路径导入 |
| PWA | 两端均由 `vite-plugin-pwa` 生成 manifest 与 Service Worker |

## 验证结果

| 验证 | 结果 |
| --- | --- |
| 共享契约类型检查 | 通过 |
| 共享契约单元测试 | 17/17 通过 |
| 老人端单元/组件测试 | 95/95 通过 |
| 家庭端单元/组件测试 | 32/32 通过 |
| 老人端 Playwright | 22/22 通过 |
| 家庭端 Playwright | 5/5 通过 |
| 老人端生产构建 | 通过，生成 PWA 产物 |
| 家庭端生产构建 | 通过，生成 PWA 产物 |

## 安全与语义边界

- 所有演示数据均为 `SIMULATOR` 合成数据。
- `MEDICATION_DUE` 的证据状态保持 `UNKNOWN`，不得推断已服药。
- `SMOKE_GAS` 告警只能由 `OPEN` 变为 `VIEWED`，前端不能解除或降级 S-1/S0。
- Agent 无来源事实会被 guard 拒绝，回退使用家庭端契约枚举。
- 真实 BFF 已通过 `CoreApiAdapter` 接入；未配置 BFF 的开发模式仍使用 Mock，生产模式不允许静默回落。
