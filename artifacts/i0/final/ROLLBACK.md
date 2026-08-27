# I0 回滚说明

若部署后出现回归，停止发布并回退到本次提交的父提交；随后重新执行 I0 全量回归。回滚不恢复 Mock production fallback，不重放客户端 command，保留 outage evidence 与日志用于追踪。
