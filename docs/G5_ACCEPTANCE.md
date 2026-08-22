# G5 验收证据：可观测性、重放与故障注入

当前 Gate：G5。所有数据为合成数据；结果按实际执行状态列出。

## 新增能力

- [可观测性模块](/home/ziyi/Desktop/Careagent/carehub/g5/observability.py) 记录最小化 Trace（trace ID、操作、耗时、结果、原因码），不保存消息、健康文本或令牌；`Metrics` 输出计数、P95、最大耗时。
- `replay_report` 只从 append-only Event Store 重建投影，输出事件数、投影摘要、重复 event ID 和 S-1/S0 告警数；重放不调用规则、不产生副作用。

## 已运行

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| 500 条烟雾 S-1 输入确定性重放 | PASS | 生成 1500 条事件（输入、告警、固定响应），两次重建摘要相同，安全告警 500，重复 ID 0 |
| 重复输入 | PASS | 第二次 `ingest` 返回空派生事件 |
| 离线积压 | PASS（本地模拟） | Outbox 维持 2 条 `PENDING` 事件，未丢失 |
| 重启恢复 | PASS（真实 SIGKILL） | 子进程写入并确认提交后被 SIGKILL，WAL 重开后完整重放 3 条事件 |
| 磁盘压力 | PASS（SQLite 页数上限） | 超大事件触发 database or disk is full，Event 与 Outbox 均为 0 条，确认事务回滚 |
| 模型故障 | PASS | G4 malformed provider 进入固定模板 |
| 授权撤销 | PASS | G3 测试验证撤销后下一次读取立即拒绝 |
| Trace/Metrics | PASS | 100 个合成 span，P95 < 2ms；无敏感正文字段 |

```text
python -m pytest -q tests/test_g5_observability.py
5 passed

python -m pytest -q
262 passed

git diff --check
通过（无输出）
```

## NOT_RUN：需要部署环境的演练

- 实际 72 小时断网及恢复后与远端 Outbox 对账。
- 真实 Provider 网络超时、积压和进程隔离。

这些项未运行，不能据此标记生产稳定性 Gate 通过；需要在可隔离的集成环境完成。
