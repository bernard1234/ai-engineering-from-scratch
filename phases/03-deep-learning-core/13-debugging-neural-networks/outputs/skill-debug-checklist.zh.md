---
name: skill-debug-checklist
description: 调试神经网络训练失败的决策树检查清单
version: 1.0.0
phase: 3
lesson: 13
tags: [debugging, neural-networks, training, diagnostics, deep-learning]
---

# 神经网络调试清单

训练出问题时的系统调试流程。按顺序走——大部分 bug 在前 3 步被抓到。

## 训练之前（预防 bug）

1. 打印模型架构和参数量。大小对数据来说合理吗？
2. 用随机输入跑一次前向传播。输出形状匹配目标形状吗？
3. 检查标签是正确的 dtype（CrossEntropyLoss 需要 Long，BCELoss 需要 Float）
4. 验证数据归一化：输入应有均值接近 0、std 接近 1
5. 打印 5 对随机（input, label）。标签符合预期吗？
6. 确认 train/test 切分没有重复样本

## 单 batch 过拟合测试（60 秒，能抓到 80% 的 bug）

1. 从训练集取 8–32 个样本
2. 用合理学习率训练 200 步
3. Loss 应该趋近 0。训练准确率应该到 100%
4. 如果失败：bug 在你的模型、损失函数或训练循环里——不在数据或超参数
5. 如果通过：继续完整训练

## Loss 不下降

1. 检查学习率。试 3 个值：当前值除以 10、当前、当前乘以 10
2. 打印每层梯度范数。全零意味着死网络或断开的图
3. 检查参数上 `requires_grad=True`。检查 `loss.backward()` 被调了
4. 检查 `loss.backward()` 之前调了 `optimizer.zero_grad()`
5. 检查 `loss.backward()` 之后调了 `optimizer.step()`
6. 验证模型参数传给了优化器：`optimizer = Adam(model.parameters())`

## Loss 是 NaN 或 Inf

1. 学习率降 10 倍
2. 所有 log() 调用加 epsilon：`torch.log(x + 1e-7)`
3. 所有除法加 epsilon：`x / (y + 1e-8)`
4. BCE loss 之前 clamp 预测：`torch.clamp(pred, 1e-7, 1 - 1e-7)`
5. 用 `torch.autograd.detect_anomaly()` 找具体操作
6. 检查输入数据里的 NaN：`assert not torch.isnan(x).any()`

## Loss 震荡

1. 学习率降 3–10 倍
2. 增大 batch size（减小梯度噪声）
3. 加梯度裁剪：`torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)`
4. 从 SGD 换成 Adam（每个参数自适应 LR）
5. 训练前 5–10% 步加学习率 warmup

## 过拟合（训练 acc 高、测试 acc 低）

1. 加 dropout（从 p=0.1 开始，增到 0.5）
2. 优化器加 weight decay：`Adam(params, weight_decay=1e-4)`
3. 缩小模型（更少层或更窄层）
4. 加数据增强
5. 用早停：验证 loss 增加 5+ epochs 就停
6. 检查 train/test 切分之间的数据泄露

## 欠拟合（训练和测试 acc 都低）

1. 增加模型容量（更多层、更宽层）
2. 训练更多 epochs
3. 增加学习率（小心）
4. 临时去掉正则化来验证模型能学
5. 检查模型对任务来说表达能力够不够

## 死 ReLU 神经元

1. 检查每层零激活的比例。>50% 有问题
2. 换成 LeakyReLU(0.01) 或 GELU
3. 权重用 Kaiming 初始化
4. 降低学习率（大更新能把神经元推入死亡区）
5. 激活函数之前加 batch normalization

## 速查：学习率起点

| 优化器 | 任务 | 起始 LR |
|--------|------|---------|
| Adam | 从头训练 | 1e-3 |
| Adam | 微调预训练 | 1e-5 |
| SGD + momentum | 从头训练 | 1e-1 |
| SGD + momentum | 微调预训练 | 1e-3 |
| AdamW | Transformer 训练 | 3e-4 |

## 速查：batch size 效果

| Batch size | 梯度噪声 | 内存 | 泛化 |
|------------|----------|------|------|
| 8-16 | 高（噪声大） | 低 | 通常更好 |
| 32-64 | 中等 | 中等 | 好默认 |
| 128-256 | 低（平滑） | 高 | 可能需要 warmup |
| 512+ | 很低 | 很高 | 需要 LR 缩放 |

## 什么都不行时

1. 简化模型到 1 个隐藏层。能学吗？
2. 简化数据到 100 个样本。能过拟合吗？
3. 把 loss 换成 MSE。能收敛吗？
4. 把优化器换成 SGD(lr=0.01)。有进展吗？
5. 把数据换成合成数据（比如 y = x[0] > 0）。能学吗？
6. 如果这些都不行：bug 在你没在看的代码里（数据加载、预处理、tensor 形状）
