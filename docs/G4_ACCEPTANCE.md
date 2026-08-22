# G4 验收证据：Model Gateway 与可信 Response

当前 Gate：G4，本轮只开放 `TODAY_STATUS` 与 `DAILY_SUMMARY`。

## 实现

- [ModelGateway](/home/ziyi/Desktop/Careagent/carehub/g4/gateway.py) 是独立、无状态的 provider 边界；它不接收 EventStore、设备、Skill、网络凭证或完整上下文。
- 默认 `FakeProvider` 仅用于离线 CI。真实 provider 必须实现同一最小接口，不能接收工具定义。
- 传入 provider 前只保留带 `source_refs` 的最小事实；丢弃主体、家庭、原始事件、对话和原始音视频字段。
- 输出必须严格为 `message` 和 `fact_indexes`。未知字段、非 JSON、空/超长文本、越界引用、超时和 I/O 故障都使用固定模板。
- 安全扫描拦截诊断、处方、剂量、改药、服药断言、紧急处置与工具调用语句；原模型文本不展示。

## 证据

```text
python -m pytest -q tests/test_g4_gateway.py
204 passed

python -m pytest -q
255 passed
```

`tests/test_g4_gateway.py` 覆盖 FakeProvider、最小化上下文、乱 JSON、Schema/来源越界、超时、安全红线、未批准 purpose 与提示注入文本。

## 仍受限的边界

G2 的通用只读聊天兼容接口保持原样，未被接入 G4 网关；G4 只为“今日状态”和“日报”提供可信生成路径。接入真实 provider 前，需在独立进程/系统用户运行，并加入不少于 200 条红线回归语料。
