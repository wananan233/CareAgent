# ADR-0001：E0 工程与契约冻结

- 状态：已接受（E0 阶段）
- 日期：2026-08-21
- 范围：老人端 `apps/elder-terminal`

## 背景

任务书要求 E0 创建 Vue3/TS/PWA 工程，并冻结：设计 token、路由、MockCoreAdapter、
严格 DTO guard、合成 fixtures、全局“模拟数据”标识、错误信封与状态矩阵。

## 决策

1. **Monorepo**：npm workspaces（`apps/*`），根 `package.json` 锁定
   `packageManager: npm@11.13.0`，`.nvmrc` 锁定 Node `24.16.0`。
2. **契约单一事实源**：`contracts/*.schema.json`（draft-07）为声明式事实源；
   `apps/shared-contracts` 提供 TS 类型、枚举、运行时 guard 与 mock builders。
3. **运行时校验手写**：不引入 ajv/zod，直接手写 `guards.ts`（“严格 DTO guard”）。
4. **接口先 Mock 后 Core**：`ElderTerminalApi` 契约统一；`MockCoreAdapter` 返回合成数据，
   `CoreApiAdapter` 在 C0-C4 就绪前返回 `NOT_IMPLEMENTED`，两者共享同一 DTO/错误码/版本。
5. **内容红线进代码**：`SIMULATED_DATA_LABEL = '模拟数据'`、`source.type = 'SIMULATOR'`、
   证据状态仅 `UNKNOWN/SEEN/PENDING`（无“已吞服”）、S-1/S0 告警无前端取消动作。

## 后果

- E1-E6 复用同一契约与 token；家属端未来可复用 `shared-contracts`。
- 真实 HTTP 接入需等 C2 BFF；在 C0-C4 就绪前演示只能用 MockCoreAdapter。
- 引入依赖：vue、vue-router、pinia（运行时）；vite、vitest、@vue/test-utils、
  jsdom、typescript、vue-tsc、@vitejs/plugin-vue（开发）。删除方式：从 `package.json`
  移除并 `npm install` 重新锁定。
