# 激活函数

> ReLU、sigmoid、tanh、GELU——每个都有自己的形状和故事。

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 3 Lesson 1-3 (Perceptron through Backprop)
**Time:** ~60 minutes

## Learning Objectives

- 画出每个主要激活函数及其导数，说明饱和区域
- 实现四个激活函数及其反向传播
- 说明 sigmoid 和 tanh 在深层网络中造成梯度消失的原因
- 选择合适激活：sigmoid（二分类输出）、softmax（多分类输出）、ReLU/GELU（隐藏层）

## 核心概念

### 主要激活函数

| 函数 | 公式 | 输出范围 | 导数 | 什么时候用 |
|------|------|----------|------|------------|
| Sigmoid | 1/(1+e^(-x)) | (0, 1) | sigmoid(x)*(1-sigmoid(x)) | 二分类输出层 |
| Tanh | (e^x - e^(-x))/(e^x + e^(-x)) | (-1, 1) | 1 - tanh²(x) | RNN 隐藏状态 |
| ReLU | max(0, x) | [0, ∞) | x > 0 → 1, x < 0 → 0 | 隐藏层默认 |
| Leaky ReLU | max(0.01x, x) | (-∞, ∞) | x > 0 → 1, x < 0 → 0.01 | 防死 ReLU |
| GELU | x * Φ(x) ≈ 0.5x(1 + erf(x/√2)) | ≈ (-0.17, ∞) | 光滑 | Transformer 隐藏层 |

### 梯度消失问题

sigmoid 和 tanh 的导数最大值分别是 0.25 和 1.0。深层网络中梯度沿层传播时被连续乘上这些值。5 层 ReLU 梯度可能衰减 4×，而 sigmoid 衰减 1024×。

### ReLU 死亡问题

输入持续为负的 ReLU 输出 0，梯度也是 0，永远学不到东西。Leaky ReLU 和 GELU 用小斜率或光滑函数缓解。

### 输出层约束

- 二分类概率（0 到 1）：sigmoid
- 多分类概率分布（加和为 1）：softmax
- 回归实数：线性（无激活）

## Build It

### Step 1: 实现所有激活函数和它们的反向传播

### Step 2: 可视化饱和区域

### Step 3: 对比 ReLU vs sigmoid 训练速度

## Use It

## Exercises

## Key Terms

## Further Reading
