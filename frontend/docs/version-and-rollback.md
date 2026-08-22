# CareHub 2.0 老人端 — 版本与回滚说明

## 版本状态

| 项 | 值 |
| --- | --- |
| 当前版本 | `0.1.0`（`apps/elder-terminal/package.json` 与根 `package.json` 一致） |
| 阶段 | E0–E6 完成，全部测试通过，静态构建通过 |
| 数据源 | `MockCoreAdapter`（合成数据）；`CoreApiAdapter` 为 `NOT_IMPLEMENTED` 占位 |
| 运行时 | Node `24.16.0`（`.nvmrc`）、npm `11.13.0`（`packageManager` 锁定） |

## 冻结与不可变项

- **契约单一事实源**：`contracts/*.schema.json`（draft-07）为声明式事实源。
- **共享 DTO/guard**：`apps/shared-contracts/src/`（types、guards、builders、errors）。
- **内容红线**：`SIMULATED_DATA_LABEL = '模拟数据'`、`source.type = 'SIMULATOR'`、
  证据状态仅 `UNKNOWN/SEEN/PENDING`、S-1/S0 告警无前端取消动作。
- **状态矩阵 / 设计 token**：`src/contracts/stateMatrix.ts`、`src/tokens/index.ts`。

上述项在 E 阶段契约冻结后不可随意改动；任何改动须同步更新对应测试断言并回归。

## 变更与版本号规则

版本号 `0.1.0`（`major.minor.patch`）：

1. **patch**（`0.1.x`）：修复 bug、调整文案、测试补齐，不改业务契约。
2. **minor**（`0.x.0`）：新增页面/组件或内部实现，仍不破坏既有契约。
3. **major**（`x.0.0`）：契约（schema、DTO、枚举、路由、错误码）发生变化。

改版本号时同步修改：根 `package.json`、`apps/elder-terminal/package.json`、
`apps/shared-contracts/package.json`，并重新 `npm install` 锁定 `package-lock.json`。

## 回滚方式

> 本项目**当前不是 git 仓库**（无 `.git`），无法用 `git revert` / `git reset` 回滚。

### 推荐：源码快照备份

在每次阶段验收前，对仓库做一次压缩快照：

```bash
# 在 D:\Tool\IdeaProjects\AIGC\careHub 的上一级执行
tar -czf careHub-e6-$(date +%Y%m%d-%H%M%S).tar.gz careHub/
# 回滚：解压覆盖目标目录
tar -xzf careHub-e6-YYYYMMDD-HHMMSS.tar.gz
```

回滚到某次快照后，需清理并重建依赖与产物：

```bash
rm -rf node_modules apps/*/node_modules dist apps/*/dist
npm install
npm run build
npm run test
```

### 备选：建立 git 仓库（后续阶段建议）

```bash
cd D:\Tool\IdeaProjects\AIGC\careHub
git init
git add -A
git commit -m "E0-E6 baseline"
```

此后即可用 `git log` / `git checkout <commit>` / `git revert <commit>` 精确回滚。
（`.gitignore` 已忽略 `node_modules/`、`dist/`、`coverage/`、`*.local`、`~$*`。）

## 干净目录复现（验收用）

在全新目录中复现构建与五条演示场景：

```bash
# 1. 复制仓库（或解压快照）
cp -r careHub careHub-clean && cd careHub-clean

# 2. 安装依赖
npm install

# 3. 类型检查 + 静态构建
npm run build

# 4. 单元测试
npm run test

# 5. 端到端（自动拉起 dev server，Playwright 需已安装 chrome）
npx playwright install chrome
npm run test:e2e
```

验收通过标准：`npm run build` 无类型错误且 `dist/` 含 `sw.js` 与
`manifest.webmanifest`；`npm run test` 全绿；`npm run test:e2e` 全绿且
`test-results/` 生成五条演示场景截图。
