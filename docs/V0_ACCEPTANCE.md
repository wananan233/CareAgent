# V0 Linux 视觉 AI 验收记录

## 已完成

- Linux 隔离环境：OpenCV、PyTorch、Ultralytics、ONNX Runtime 已锁定。
- OpenCV 内存预处理与 ISO-8601 时间戳校验。
- YOLO 隔离推理边界，原始媒体不写入事件或日志。
- Home Fire 室内烟雾/火灾模型训练与外部权重哈希记录。
- UR Fall 跌倒特征数据卡片、按序列分组训练与时序回放评估。
- `fall_candidate` 接入 CareEventV1、连续帧确认和人工复核队列。
- 重复事件幂等、低置信度待复核、时间戳异常、模型替换哈希变化、批次资源上限验证。

## 安全边界

视觉模型只产生候选观察，不直接改变 S-1/S0 状态，不自动报警、给药或通知；业务状态由
Core 确定性规则和授权人工复核决定。原始视频、帧、人脸、身份信息、训练数据和权重均
不得提交 Git。

## 验证命令

```bash
python -m scripts.validate_contracts
PYTHONPATH=. /home/ziyi/anaconda3/envs/carehub-research/bin/python -m pytest -q
```

最近一次回归：`317 passed`。
