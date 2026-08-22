# CareHub 2.0 老人端 — E5-E6 验收报告

- 日期：2026-08-22
- 范围：`apps/elder-terminal`（老人端）
- 结论：**通过**。所有单元/组件/端到端测试通过，静态 PWA 构建成功，干净目录复现成功。

## 一、交付物清单（E5-E6）

| 项 | 路径 | 状态 |
| --- | --- | --- |
| 五条演示场景 e2e | `tests/e2e/scenarios.spec.ts` | 通过（含 8 张截图） |
| 无障碍基线 e2e | `tests/e2e/accessibility.spec.ts` | 通过 |
| 日志脱敏静态扫描 | `tests/unit/logRedaction.test.ts` | 通过（3 项红线） |
| PWA 注册单测 | `tests/unit/pwa.test.ts` | 通过 |
| 离线门控单测 | `tests/unit/offline.test.ts` | 通过 |
| 环境变量模板 | `apps/elder-terminal/.env.example` | 已交付 |
| 环境变量类型 | `src/env.d.ts`（`ImportMetaEnv`） | 已交付 |
| 老人端 README | `apps/elder-terminal/README.md` | 已交付 |
| 根 README（一键启动） | `README.md` | 已交付 |
| 版本/回滚说明 | `docs/version-and-rollback.md` | 已交付 |
| 适配器兼容报告 | `docs/adapter-compatibility.md` | 已交付 |
| 关键场景/宽度截图 | `docs/screenshots/`（10 张） | 已交付 |
| 静态 PWA 构建产物 | `dist/`（含 `sw.js`、`manifest.webmanifest`） | 通过 |

## 二、测试结果

### 单元 / 组件（Vitest）

| 工作区 | 文件数 | 用例数 | 结果 |
| --- | --- | --- | --- |
| `shared-contracts` | 2 | 17 | 全通过 |
| `elder-terminal` | 23 | 95 | 全通过 |
| **合计** | **25** | **112** | **全通过** |

### 端到端（Playwright，channel=chrome）

| 文件 | 用例数 | 覆盖 |
| --- | --- | --- |
| `scenarios.spec.ts` | 5 | 五条演示场景闭环 |
| `accessibility.spec.ts` | 9 | h1/导航/可访问名称/表单标签/非颜色状态 |
| `keyboard.spec.ts` | 2 | Tab 焦点/跳转链接/focus-visible |
| `settings.spec.ts` | 2 | 字号缩放 |
| `shell.spec.ts` | 2 | 1024/1280 壳截图 |
| `typography.spec.ts` | 2 | 正文≥20px/主任务≥30px/触控≥56px |
| **合计** | **22** | **全通过** |

### 关键截图（`docs/screenshots/`）

| 场景 | 截图 |
| --- | --- |
| 场景 1 · CareDose 服药提醒闭环 | `1a-home.png`、`1b-task-detail.png` |
| 场景 2 · CareSafe 烟雾/燃气告警 | `2a-global-safety.png`、`2b-alert-detail.png` |
| 场景 3 · CareRadar 低质量活动数据 | `3-timeline.png` |
| 场景 4 · CareAgent DAILY_SUMMARY | `4-agent.png` |
| 场景 5 · 网络断开与离线壳（离线演示记录） | `5a-offline.png`、`5b-blocked.png` |
| 适老终端壳宽度 | `shell-1024.png`、`shell-1280.png` |

## 三、干净目录复现

在 `D:\Tool\IdeaProjects\AIGC\careHub-clean\`（源码快照，排除 `node_modules/dist/test-results`）：

| 步骤 | 结果 |
| --- | --- |
| `npm install` | 204 包，3s |
| `npm run build`（vue-tsc + vite build） | 成功，`dist/` 含 `sw.js` + `manifest.webmanifest` |
| `npm run test`（根，两工作区） | 112 用例全通过 |
| `npm run test:e2e` | 22 用例全通过 |

复现结果与主目录一致，证明构建与演示场景可离线复现。

## 四、构建与版本信息

| 项 | 值 |
| --- | --- |
| 版本号 | `0.1.0`（根 `package.json` 与各工作区一致） |
| 构建产物 hash（Vite 内容寻址） | JS `index-C7x133H6.js`、CSS `index-wHfeTgmS.css` |
| 运行时 | Node `24.16.0`、npm `11.13.0` |
| 契约版本 | `API_VERSION = 'v1'` |

源码版本 hash 以 git 提交 SHA 为准（`git rev-parse HEAD`）。

## 五、合规确认（无真实依赖）

已核对源码、fixtures、依赖与配置，确认：

- **无真实硬件**：无硬件 SDK/驱动/串口接入，数据仅来自 `MockCoreAdapter`。
- **无真实账号**：演示主体为合成 ID（`DEMO_SUBJECT_ID`），无登录、无真实用户会话。
- **无真实医疗数据**：`fixtures.ts` 全部合成，`source.type === 'SIMULATOR'`。
- **无真实密钥**：无 `.env`、无私钥/证书文件；日志脱敏静态扫描（`logRedaction.test.ts`）通过，
  源码无凭据/Token 标识。
- **无公网通知服务依赖**：无 SMS/邮件/推送/第三方通知 SDK，告警仅在本地 UI 呈现，不调用外部通知服务。

## 六、提交清单核对（任务书 6-10）

| # | 要求 | 对应交付物 |
| --- | --- | --- |
| 6 | 可运行源码、锁文件、环境变量模板、演示数据、一键启动 | `apps/*`、`package-lock.json`、`.env.example`、`scenarios/fixtures.ts`、根 `README.md`（`npm run dev`） |
| 7 | 路由清单、接口映射、状态矩阵、设计 token、可访问性、已知限制 | `apps/elder-terminal/README.md` |
| 8 | 测试结果、关键场景截图、宽度截图、离线演示记录 | 本报告 + `docs/screenshots/` |
| 9 | 版本号、构建 hash、Mock/Core 兼容报告、回滚方法 | 本报告 + `docs/adapter-compatibility.md` + `docs/version-and-rollback.md` |
| 10 | 干净目录复现、无真实依赖确认 | 本报告第三、五节 |

## 七、未解决问题

1. **真实 Core/BFF 接入（C0-C4）未实现**：`CoreApiAdapter` 全部返回 `NOT_IMPLEMENTED`。
   当前演示唯一数据源为 `MockCoreAdapter`（合成数据）。属后续阶段工作，非本阶段缺陷。
2. **PWA 用手写 `sw.js` 而非 `vite-plugin-pwa`**：因网络受限未引入该依赖；
   离线壳、缓存、更新检测均已手写覆盖并单测通过。
3. **环境变量未接入业务逻辑**：`VITE_API_BASE_URL` / `VITE_DEMO_MODE` 仅声明类型与模板，
   供未来 C2 BFF 使用；当前不改业务契约。

## 八、回滚方式

见 `docs/version-and-rollback.md`。当前版本 `0.1.0`；git 仓库已初始化，可用
`git log` / `git checkout <commit>` / `git revert <commit>` 精确回滚；也可用源码快照覆盖。
