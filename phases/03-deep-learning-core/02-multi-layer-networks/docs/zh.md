# 多层网络与前向传播

> 堆一堆感知机。第一层做简单检测，第二层做组合，第三层做复杂分类。

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 3 Lesson 1 (Perceptron), Phase 1 Lesson 12 (Chain Rule)
**Time:** ~60 minutes

## Learning Objectives

- 为多层网络（MLP）手写前向传播：矩阵乘法、激活、多层
- 识别每层形状的维度：输入、权重、输出
- 说明为什么深网络比宽网络用更少的参数表达更复杂的函数
- 列出 MLP 的应用场景（表格数据、嵌入）和不适用场景（图像、序列）

## 核心概念

### 前向传播的数据流

```
输入 x (batch, in_features)
  → Linear(W1, b1): (batch, in_features) × (in_features, h1) + b1 → (batch, h1)
  → Activation (ReLU): 同样形状不变
  → Linear(W2, b2): (batch, h1) × (h1, h2) + b2 → (batch, h2)
  → Activation
  → ...
  → Linear(Wn, bn): 最终输出
  → Loss
```

每层的输出 = 下一层的输入。形状计算是核心技能。

### 宽度 vs 深度

| 架构 | 参数量 | 表达力 | 训练难度 |
|------|--------|--------|----------|
| 单宽层 [256] | 256×in + 256 | 浅但宽 | 简单 |
| 两层 [64, 64] | 64×in + 64 + 64×64 + 64 | 深，层次化 | 稍难 |
| 四层 [32, 32, 32, 32] | 更多乘法 | 更深层次的组合 | 更难 |

深层网络用更少的参数学到更抽象的特征。但也更难训练（梯度消失、梯度爆炸）。

### 形状追踪

对每层都追踪 3 个形状：输入、权重、输出。永远别跳过这个。如果输出形状不匹配预期，就是 bug。

### MLP 的应用

适合：表格数据、嵌入、作为其他架构（CNN、Transformer）的分类头。

不适合：图像（应该用 CNN 以利用局部性和权重共享）、序列（应该用 RNN 或 Transformer）。

## Build It

### Step 1: 手写前向传播（纯 Python）

### Step 2: 手写前向传播（NumPy）

### Step 3: 用 PyTorch 做前向传播

（详见 `code/forward.py`）

## Use It

## Exercises

## Key Terms

## Further Reading
