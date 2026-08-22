# G3 验收证据：Memory、Consent 与隐私

当前 Gate：G3 已实现，使用纯合成用户和事件数据。

## 实现范围

- `carehub/g3/service.py`：Working Memory（仅内存、最长 1 小时）、Structured Memory 状态机，以及由 Event Store 投影重建的 Episodic View 边界。
- 长期记忆只能遵循 `CANDIDATE → POLICY_ACCEPTED → CONFIRMED → ACTIVE`；候选必须含 `source_event_ids`、置信度、敏感级别、同意范围、数据主体、有效期及撤销方式。
- `ConsentLedger` 将同意写入 SQLite；每一次读取均查询活动同意及 ABAC 属性（主体、家庭、目的、分类、通道、有效期），所以撤销提交后下一次访问立即拒绝，远小于 5 秒 Gate。
- 原始 ASR 音频、视频片段和对话文本只登记可删除的存储引用，不把内容写进 Event Store、记忆表或审计记录。删除请求撤销全部长期记忆并标记这些引用删除。
- 审计记录仅保留 actor、能力、结果、原因和资源标识；敏感日志扫描只返回命中行号，避免二次泄露。

## 已运行证据

```text
python -m pytest -q tests/test_g3_privacy.py tests/test_contracts.py
7 passed

python -m pytest -q
51 passed

git diff --check
通过（无输出）
```

`tests/test_g3_privacy.py` 覆盖：来源/TTL、禁止直接 ACTIVE、撤销即时生效、跨家庭拒绝、Working Memory TTL、音频删除、个人数据删除及敏感日志扫描。

## 已知边界

本轮是本地单体 MVP：`privacy_artifact.storage_ref` 是用于对接实际安全擦除器的引用，不存储原始音视频。备份轮转、用户级加密密钥销毁和生产身份认证需要在部署层接入后做端到端演练。
