# V0 跌倒特征数据卡片

## 来源与许可

- 数据集：UR Fall Detection Dataset（官方站点）。
- 内容：30 个跌倒序列、40 个日常活动序列；官方深度特征 CSV。
- 标签：`-1` 非躺倒、`0` 过渡姿态、`1` 躺倒；训练时排除 `0`。
- 许可：CC BY-NC-SA 4.0，仅非商业学术研究；商业使用须联系作者。
- 原始文件位置：`/tmp/carehub-urfall`，不提交 Git。

## 文件哈希

```text
urfall-cam0-falls.csv  4ed29af7040098ba0150d1030eeadd97bbfde5c3a4fb9b07df786d673e22a65c
urfall-cam0-adls.csv   e19b2d8379538c16892241aa4cdc9e26a53b296473229c568331c23d7b3cdad1
```

## 训练复现

```bash
python scripts/train_urfall_fall_classifier.py \
  /tmp/carehub-urfall/urfall-cam0-falls.csv \
  /tmp/carehub-urfall/urfall-cam0-adls.csv \
  --out /tmp/carehub-urfall/run-20260825 --seed 20260825
```

按序列分组，固定 20% 序列作为测试集，禁止按帧随机切分。记录的测试指标为
precision `0.9796`、recall `0.7059`；模型 SHA-256 为
`86432063e0ac9745128a1ec914be2dd460744934dce29fca9f9dd310e25d6820`。

模型只能产出 `fall_candidate` 观察，必须经过时序确认和人工复核，不得直接触发报警、
给药或其他高风险动作。
