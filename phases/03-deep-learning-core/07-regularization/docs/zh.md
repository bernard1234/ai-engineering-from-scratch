# 正则化

> 正则化是泛化的艺术：不是让模型在训练集上尽可能好，而是让它在新数据上也好。

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 3 Lessons 1-6, Phase 1 Lesson 8 (Optimization)
**Time:** ~60 minutes

## Learning Objectives

- 从零实现 L1/L2 正则化（权重衰减），说明它们的区别：L1 产生稀疏解
- 从零实现 Dropout，训练时随机置零神经元，推理时不启用
- 对比 L1、L2 和 Dropout 的正则化强度随网络深度的变化
- 实现 Early Stopping（早停），用验证损失监控何时停止训练

## 核心概念

### 四种正则化

| 方法 | 怎么做 | 效果 | 何时用 |
|------|--------|------|--------|
| L2 权重衰减 | 损失 + λ·Σw² | 缩小权重 | 几乎任何地方 |
| L1 权重衰减 | 损失 + λ·Σ|w| | 稀疏化（置零） | 特征选择 |
| Dropout | 训练时 p 概率置零神经元 | 防止共适应 | 深隐藏层 |
| 早停 | 验证损失连续 N epoch 不降就停 | 截断过拟合 | 永远 |

### L1 vs L2

L1（Lasso）产生稀疏解（很多权重精确为 0），自然完成特征选择。L2（Ridge）只缩小权重不会精确置零。

### Dropout 的机制

训练时：每个神经元以概率 p 输出 0。这迫使其不能依赖任何一个输入（它会被随机置零）。推理时：所有神经元都参与，权重按 p 缩放（保持期望输出不变）。

### 早停的实施

监控验证损失。当它在前 N 个 epoch 内没有下降时停止。保存最好的 checkpoint，而不是最后一个。

## Build It

### Step 1: 带正则化的损失函数

### Step 2: 手写 Dropout

### Step 3: 早停 checkpoint 保存

## Use It

## Exercises

## Key Terms

## Further Reading
