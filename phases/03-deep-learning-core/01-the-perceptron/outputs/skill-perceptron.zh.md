---
name: skill-perceptron
description: 理解感知机模式以及何时需要单层 vs 多层架构
version: 1.0.0
phase: 3
lesson: 1
tags: [perceptron, neural-networks, classification, deep-learning]
---

# 感知机模式

一个感知机计算输入的加权和加偏置，然后通过阶跃函数产生二元输出。它是神经网络的基本单元。

```
output = step(w1*x1 + w2*x2 + ... + wn*xn + bias)
```

## 单个感知机够用的场景

- 问题线性可分：一条直线（或超平面）能完美分隔两类
- 逻辑门：AND、OR、NOT、NAND
- 简单阈值决策："分数是否高于 X？"
- 数据聚类成两个不重叠区域的二元分类器

## 需要多层的场景

- 问题非线性可分：一条直线无法分隔类别
- XOR 和奇偶性问题
- 任何需要 "是 A 但不是 B" 推理的任务（条件组合）
- 真实世界分类：图像、文本、音频——几乎总是非线性

## 决策检查清单

1. 画出或检查数据。能在类别之间画一条直的边界吗？
   - 能：单个感知机就行
   - 不能：至少需要两层
2. 问题能分解成更简单线性决策的 AND/OR 组合吗？
   - 这个分解告诉你最小网络结构
   - XOR = (A OR B) AND (NOT (A AND B)) = 两层三个感知机
3. 超过两个类的问题，每个类需要一个输出节点

## 训练规则

```
error = expected - predicted
weight_new = weight_old + learning_rate * error * input
bias_new = bias_old + learning_rate * error
```

预测正确则什么都不变。预测错误，权重移动以减小误差。这只对单层感知机有效。多层网络需要反向传播。

## 常见错误

- 想用单个感知机学习非线性模式（永远不会收敛）
- 学习率设太高（权重震荡）或太低（训练慢到天荒地老）
- 忘了偏置项（没有偏置，决策边界必须过原点）
- 混淆感知机收敛（线性可分数据保证收敛）和一般神经网络收敛（不保证）
