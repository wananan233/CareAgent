# 老人端版本与回滚

## 当前基线

- 版本：`0.1.0`
- 工作区：根级 pnpm monorepo（`apps/*`）
- 契约规范来源：`apps/shared-contracts/src/family.ts`
- 老人端投影：`apps/shared-contracts/src/elder/`
- 数据源：`MockCoreAdapter`；真实 BFF 尚未接入

## 版本规则

- patch：实现或文案修复，不改变共享契约。
- minor：增加兼容功能或展示投影。
- major：修改共享 Core DTO、路由或错误边界。

版本调整后必须更新 `pnpm-lock.yaml`，并重新执行类型检查、单元测试、端到端测试和构建。

## 回滚

优先使用可审计的 Git 回滚：

```bash
git log --oneline
git revert <commit>
pnpm install --frozen-lockfile
pnpm --filter @carehub/elder-terminal test
pnpm --filter @carehub/elder-terminal build
```

不要用 `git reset --hard` 覆盖未提交的本地修改。

## 干净复现

```bash
pnpm install --frozen-lockfile
pnpm --filter @carehub/shared-contracts typecheck
pnpm --filter @carehub/elder-terminal test
pnpm --filter @carehub/elder-terminal test:e2e
pnpm --filter @carehub/elder-terminal build
```
