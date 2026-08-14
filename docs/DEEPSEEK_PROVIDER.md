# DeepSeek Provider 配置

G4 的 `DeepSeekProvider` 只供“今日状态”和“日报”调用。它不接收 EventStore、设备、Skill、完整身份/家庭信息、原始事件或聊天历史；API 请求不包含 `tools`。

## 配置

请在独立的 `care-model-gateway` 进程环境中设置密钥，不要写入仓库、`.env`、终端历史或日志：

```bash
read -rsp 'DeepSeek API Key: ' DEEPSEEK_API_KEY; export DEEPSEEK_API_KEY; echo
```

然后由部署代码创建：

```python
from carehub.g4 import DeepSeekProvider, ModelGateway

gateway = ModelGateway(DeepSeekProvider())
```

默认模型为 `deepseek-v4-flash`，端点为 `https://api.deepseek.com/chat/completions`，超时 2 秒。若未配置密钥或网络/服务异常，网关会返回固定模板且不展示模型原文。

密钥不得传给 Care Core、浏览器、日志、数据库、事件、审计或测试 fixture。已在聊天中暴露的密钥应立即在供应商控制台撤销并更换。
