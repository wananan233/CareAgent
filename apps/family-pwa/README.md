# CareHub 家属端 PWA

默认只使用 MockCoreAdapter。CoreApiAdapter 为后续 C0-C4 完成后的契约入口；不得接入真实 Push、硬件或用户数据。

`pnpm --filter @carehub/family-pwa test` 与 `pnpm --filter @carehub/family-pwa build` 用于验证。离线时仅使用本次会话内存快照，Token、健康正文和对话不写入浏览器持久存储。
