# 权重初始化

> 好的初始化让网络从一开始就活着。坏的初始化让它根本不开始学。

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 3 Lessons 1-3
**Time:** ~30 minutes

## Learning Objectives

- 说明 Xavier/Glorot 和 Kaiming/He 初始化的公式和直觉
- 为不同激活函数选正确的初始化（ReLU → Kaiming，sigmoid/tanh → Xavier）
- 验证初始化后前几层的激活统计（均值、标准差、零比例）
- 解释为什么零初始化会导致对称问题

## 核心概念

### 为什么初始化重要

初始化决定了前几层激活和梯度的尺度。太大会导致梯度爆炸，太小会导致梯度消失。

### 两种标准初始化

| 初始化 | 公式 | 适用激活 | 直觉 |
|--------|------|----------|------|
| Xavier/Glorot | Var(w) = 2/(fan_in + fan_out) | sigmoid, tanh | 保持前向和反向传播的激活方差 |
| Kaiming/He | Var(w) = 2/fan_in | ReLU, Leaky ReLU, GELU | 为 ReLU 死区调整方差 |

### 零初始化的问题

同一层的所有神经元有相同初始权重，对称打破不了。每个神经元学到相同的东西——网络和单神经元没区别。

### 验证初始化

初始化后立即跑一次前向传播，打印每层激活的均值和标准差。应该均值接近 0，标准差跨层大致一致。

## Build It

### Step 1: 实现 Xavier 和 Kaiming

### Step 2: 对比不同初始化的训练曲线

## Use It

## Exercises

## Key Terms

## Further Reading
