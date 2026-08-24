# ADR-0002：与家庭端统一工作区和 Core 契约

- 状态：已接受
- 日期：2026-08-24

## 决策

1. 删除独立的 `frontend/` npm 工作区，老人端迁移到根 `apps/elder-terminal`。
2. 使用远程家庭端的 `pnpm-workspace.yaml`、锁文件、依赖版本和 PWA 工具链。
3. `apps/shared-contracts/src/family.ts` 作为跨端 Core DTO 的规范来源。
4. 老人端展示投影放在 `apps/shared-contracts/src/elder/`，通过 `@carehub/shared-contracts/elder` 使用。
5. 老人端请求、错误、告警、任务与 Agent 字段按家庭端契约收口；端特有状态必须明确标为展示投影。

## 结果

家庭端无需修改其业务契约即可继续通过原有测试，老人端也在同一工具链下通过类型检查、单元测试、端到端测试和生产构建。
