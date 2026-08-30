# F0 回滚说明

如 F0 部署后发现 BFF DTO 映射、授权或降级展示回归，停止发布并回退到本提交的父提交。不要通过浏览器直连 Provider、不要重放写命令、不要恢复任何生产 Mock 回退。

回滚后保留 `correlation_id`、BFF 审计记录和本目录 manifest，按 F0 回归重新验证 consent revoke、跨家庭拒绝、离线恢复、AI fallback 与幂等写入。
