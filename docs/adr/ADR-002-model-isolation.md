# ADR-002：模型网关隔离

- 状态：已接受
- 决策：模型只能经独立 `care-model-gateway` 接收最小化 Context 副本并返回固定 Schema。
- 禁止：模型访问数据库、设备凭证、MQTT、BLE、GPIO、Shell、任意 HTTP、Skill 执行和 Alert/Medication 状态机。
- 后果：模型超时、非法 JSON、越界内容或不可用时，Response Engine 必须转入模板降级。

