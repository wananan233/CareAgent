# C1 授权拒绝码

客户端只接收统一的 `POLICY_DENIED`，不得据此推断资源是否存在。服务端最小审计记录下列原因：

- `UNKNOWN_SCOPE`：目标资源未归属至可授权范围。
- `MEMBERSHIP_DENIED`、`SUBJECT_RELATION_DENIED`、`RBAC_DENIED`：关系或角色不足。
- `CONSENT_OR_ABAC_DENIED`：同意、用途、分类、渠道或有效期不满足。
- `CAPABILITY_DENIED`：能力不在允许矩阵或为高风险禁止能力。
- `IDEMPOTENCY_KEY_REQUIRED`：命令缺少重放保护键。
