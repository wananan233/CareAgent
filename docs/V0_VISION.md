# V0 Linux 视觉 AI 说明

## 边界

V0 只把视觉推理的最小观察写入 `CareEventV1`：`label`、置信度桶和时间状态。
事件挂在已绑定的 `device:` 聚合下，不保存原始视频、帧、路径、坐标框、人脸或身份信息。
视觉模块不裁决 S-1/S0，不关闭或升级告警，不给药，也不触发外部通知；最终状态由 Core
确定性规则和人工复核决定。

## Linux 环境

默认环境为 `/home/ziyi/anaconda3/envs/carehub-research`，依赖版本如下：

- OpenCV `5.0.0`
- PyTorch `2.13.0+cu130`
- Ultralytics `8.3.166`
- ONNX Runtime `1.22.1`

使用 `scripts/bootstrap-ai-linux.sh --check-only` 检查依赖，使用
`scripts/verify-vision-linux.sh` 运行合成像素 smoke。当前 ONNX Runtime 仅提供
`AzureExecutionProvider` 与 `CPUExecutionProvider`，不能宣称 ONNX CUDA 加速。

## 事件管线

`observations_from_detections()` 先拒绝媒体、身份、坐标和 PII 字段，再由
`ingest_detections()` 生成确定性 `event_id` 并写入 EventStore。相同设备、序号和观察
重复提交时不会产生重复事件。

测试数据只能使用合成标签和时间；数据集、权重、训练 runs、原始视频和临时缓存必须放在
仓库外的批准数据卷，且不得提交 Git。
