# G0 决策与停止条件

| ID | 未决决策 | Owner | 状态 |
|---|---|---|---|
| D-G0-01 | 药物级最大暂缓窗口、升级计时和禁延规则 | 医疗/产品负责人 | OPEN |
| D-G0-02 | 长时间静止的安全级别、询问时限与升级条件 | 安全/产品负责人 | OPEN |
| D-G0-03 | 开仓、重量、确认、离线冲突到 Medication 状态的确定性矩阵 | Medication 负责人 | OPEN |
| D-G0-04 | 产品化时的拟人化服务合规评估与备案边界 | 法务/合规负责人 | OPEN |

G0 Gate 通过条件：全部 Schema/fixture/OpenAPI/策略/Skill 校验通过，且所有 P0 未决项有明确 owner 与状态。D-G0-01 至 D-G0-04 未批准前，不进入实现真实 Medication、Alert 或模型调用的 G1/G2。
