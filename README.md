# CareAgent

CareHub 2.0 的本地优先照护建议编排器。它不是设备控制器、医疗诊断系统或自治急救决策器。

## 当前 Gate：G2.3（受控基础聊天与本地网页界面）

G1 已实现 SQLite WAL 事件库、Transactional Outbox、确定性规则、状态投影与合成设备模拟器。G2 在其上增加只读、契约约束的基础聊天层：默认使用 FakeLLM，也可通过 `DEEPSEEK_API_KEY` 接入 DeepSeek；只接收 `ContextSnapshotV1`，仅输出 `AgentResponseV1`，不接入硬件或外部通知服务。G2.3 提供仅监听本机回环地址的 HTTP API 和网页聊天界面。

## 能力概览

- **G1 事件闭环**：模拟器事件经过 Event Store、确定性 Rule Engine、Projection 与 Transactional Outbox，可完整重放。
- **G2 安全聊天**：模型只能接收经过授权、最小化且带来源引用的上下文快照，不能访问数据库、设备或 Skill。
- **G2.1 状态问答**：G1 的活动告警、服药任务和未知状态可转换为可追溯的聊天事实。
- **G2.2 本地 API**：`POST /v1/users/{id}/chat` 使用 Bearer Token 绑定用户，服务只监听 `127.0.0.1`。
- **G2.3 网页界面**：浏览器端最多保留三轮历史；令牌和历史不写入数据库或磁盘。

### 已冻结的边界

- S-1/S0 安全链路不经过 LLM 或 Planner；模型不能直连 SQLite、MQTT、BLE、GPIO、Shell、任意 HTTP 或 Skill。
- 所有有副作用的动作先表示为 `ActionIntentV1`；它不是执行结果。
- `CareEventV1` 是事实记录；所有时间必须是带时区的 RFC3339 字符串。
- 健康观察必须同时带 `source`、`quality`、`measured_at`；不确定信息使用 `UNKNOWN` 与原因，不用猜测或零值代替。
- G0 默认使用合成 fixture 与 FakeLLM；不保存原始音视频或真实健康数据。

## 目录

```text
contracts/schemas/     JSON Schema 唯一契约源
openapi/               API 边界
policies/              RBAC + ABAC + Consent 能力矩阵
skills/                白名单 Skill Manifest
fixtures/golden/       固定时钟、纯合成测试数据
carehub/core/          Event Store、Rule Engine、Projection、Replay
carehub/g2/            只读聊天服务、上下文快照与 FakeLLM
carehub/simulators/    Dose/Safe/Radar/Vision 等合成事件适配器
docs/adr/              已决架构决策
docs/threat-model/     安全与隐私威胁模型
scripts/               契约校验脚本
tests/                 G0 自动校验
```

## 验证

```bash
cd /home/ziyi/Desktop/Careagent
env -u PYTHONPATH conda run -n carehub-research python -m pytest -q
env -u PYTHONPATH conda run -n carehub-research python -m scripts.run_g1_demo
```

当前测试套件覆盖契约、事件幂等、死信隔离、规则安全分支、投影回放、G1→G2 授权快照、DeepSeek 适配器与本地 HTTP API。

## 快速开始：本地网页聊天

需要 Python 3.11、Conda 环境 `carehub-research` 与可选的 DeepSeek API 密钥。仅使用 FakeLLM 运行测试不需要网络或模型密钥。

```bash
cd /home/ziyi/Desktop/Careagent
export DEEPSEEK_API_KEY='新生成的密钥'
export CAREHUB_API_TOKEN='自行生成的本地随机令牌'
env -u PYTHONPATH conda run --no-capture-output -n carehub-research python -m scripts.run_g2_simulator_api
```

随后访问 [http://127.0.0.1:8080/](http://127.0.0.1:8080/)，输入用户 ID `synthetic-01` 和同一 `CAREHUB_API_TOKEN`。该服务只使用合成模拟器数据，按 `Ctrl+C` 可停止。

### DeepSeek（可选）

先在 DeepSeek 控制台撤销任何已泄露的密钥，并在当前终端设置新密钥（不要写进仓库）：

```bash
export DEEPSEEK_API_KEY='新生成的密钥'
```

创建聊天服务时注入 `ChatService(DeepSeekGenerator())` 即使用 `deepseek-v4-flash`。适配器只调用无工具的 Chat Completions 接口，且最终回复仍会经过本地契约与来源校验。

配置后可运行一次只读连通性演示：

```bash
env -u PYTHONPATH conda run -n carehub-research python -m scripts.run_g2_deepseek_demo
```

启动本地交互式聊天（最近 3 轮只存在内存，输入 `/exit` 结束）：

```bash
env -u PYTHONPATH conda run --no-capture-output -n carehub-research python -m scripts.run_g2_chat_cli
```

启动带 G1 模拟器状态的聊天（内置一条合成服药任务）：

```bash
env -u PYTHONPATH conda run --no-capture-output -n carehub-research python -m scripts.run_g2_simulator_chat_cli
```

### G2.2 本地 HTTP API（模拟器）

服务仅监听 `127.0.0.1`。在两个终端分别执行：

```bash
export CAREHUB_API_TOKEN='自行生成的本地随机令牌'
env -u PYTHONPATH conda run --no-capture-output -n carehub-research python -m scripts.run_g2_simulator_api
```

```bash
curl -sS -X POST 'http://127.0.0.1:8080/v1/users/synthetic-01/chat' \
  -H "Authorization: Bearer $CAREHUB_API_TOKEN" \
  -H 'Content-Type: application/json' \
  --data '{"message":"我现在有什么提醒？"}'
```

令牌绑定 `user:synthetic-01`，不能访问其他用户；请求内容和对话历史不会写入事件库或磁盘。

服务启动后，在浏览器打开 [http://127.0.0.1:8080/](http://127.0.0.1:8080/)，填写相同的 `CAREHUB_API_TOKEN` 即可使用网页聊天。网页中的令牌和最近三轮历史只存于当前页面内存。

## G0 未决项

见 [docs/G0_DECISIONS.md](docs/G0_DECISIONS.md)。已按你的批准以纯合成数据进入 G1；服药暂缓窗口、长时间静止阈值、服药证据矩阵及产品化合规适用性尚未制度性签字，因此不接入真实用药、告警或硬件服务。
