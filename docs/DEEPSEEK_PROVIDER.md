# DeepSeek Provider 配置

G4 的 `DeepSeekProvider` 只供“今日状态”和“日报”调用。它不接收 EventStore、设备、Skill、完整身份/家庭信息、原始事件或聊天历史；API 请求不包含 `tools`。

## 平台交接红线

Windows 工作区只用于契约、单元测试和离线 `FakeProvider` 验证。开始真实 Agent 模型联调、真实模型验收，或任何 OpenCV/YOLO 训练前，必须切换到 Linux 开发环境；密钥、模型权重、原始视频和训练数据不得进入 Windows 工作区或 Git 仓库。

## 配置

请在独立的 `care-model-gateway` 进程环境中设置密钥，不要写入仓库、`.env`、终端历史或日志：

```bash
read -rsp 'DeepSeek API Key: ' DEEPSEEK_API_KEY; export DEEPSEEK_API_KEY; echo
```

Linux 部署进程显式选择 Provider（默认值始终为离线 FakeProvider）：

```bash
export CAREHUB_MODEL_PROVIDER=deepseek
export CAREHUB_DEEPSEEK_MODEL=deepseek-v4-flash
export CAREHUB_DEEPSEEK_TIMEOUT_SECONDS=2
```

然后由部署代码创建并注入 BFF：

```python
from carehub.bff import CareBff
from carehub.g4 import create_model_gateway_from_env

gateway = create_model_gateway_from_env()
bff = CareBff(core=core, authenticator=authenticator, model_gateway=gateway)
```

默认模型为 `deepseek-v4-flash`，端点为 `https://api.deepseek.com/chat/completions`，超时 2 秒。若未配置密钥或网络/服务异常，网关会返回固定模板且不展示模型原文。

`DEEPSEEK_API_KEY` 仍只在 `DeepSeekProvider` 实际请求时从该 Linux 进程环境读取；它不得传给 Care Core、BFF 构造参数、浏览器、日志、数据库、事件、审计或测试 fixture。未设置密钥或网络/服务异常均只返回固定模板。已在聊天中暴露的密钥应立即在供应商控制台撤销并更换。
