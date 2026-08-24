# C1 鉴权与同意授权验收（READY_FOR_REVIEW）

本阶段已建立 C1 的最小可执行安全边界：

- `AuthContext` 只保存认证方解析出的调用者与租户，不接受客户端提供角色、家庭、被照护人或同意范围。
- `ServerSidePDP` 默认拒绝；从 `membership`、`subject_link` 和 `ConsentLedger` 服务端表解析 RBAC、ABAC 与实时同意状态。
- 高风险能力（写库、设备控制、剂量变更、SOS 等）在 PDP 层固定拒绝。
- G3 新入口 `authorized_active_memories` 只接收 `AuthContext` 与受保护的资源请求，并审计每一个 PDP 决策。
- G2 确定性编排已移除 `consent_scopes` 授权参数，转而将工作流能力、用途和渠道提交给 PDP；系统编排主体亦必须同时具备服务端成员关系和未过期同意。
- 本地聊天 API 在启用 PDP 时，Bearer 令牌只解析为调用者与租户；目标主体的家庭范围由服务端查询，家属读取必须经实时同意授权，撤销立即生效。
- 同意账本使用 `GRANTED → ACTIVE → REVOKED/EXPIRED` 状态机；只有 `ACTIVE` 且未过期的同意可授权，首次读取到期记录会持久化为 `EXPIRED`。
- 演示身份提供方支持由部署注入密钥的短期 HMAC Bearer 令牌；令牌篡改或到期一律拒绝，密钥和令牌正文不写入仓库或审计。
- 授权审计保留 actor、受保护资源、策略版本、同意版本与 correlation ID；受保护投影视图仅返回字段白名单及服务端计算的 `allowed_actions`。

## C1 结论

本阶段实现已覆盖 C1-01 至 C1-08 的模拟环境范围。验证命令：`python -m pytest -q`（277 passed）及 `scripts/validate_contracts.py`（通过）。正式 OIDC/JWKS 与密钥托管属于后续生产化工作，不是当前模拟演示范围；其边界和替换要求应在 C2 部署配置中落实。

项目负责人尚未签署本阶段正式 ACCEPTED；在签署前，状态为 `READY_FOR_REVIEW`。
