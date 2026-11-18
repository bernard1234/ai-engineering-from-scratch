# 优化器

> SGD 是基础。Adam 是默认。了解每个优化器的原理和何时用它。

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 3 Lesson 3 (Backpropagation), Phase 1 Lesson 8 (Optimization)
**Time:** ~60 minutes

## Learning Objectives

- 从零实现 SGD、SGD+Momentum 和 Adam，追踪每个参数的状态
- 说明动量如何加速收敛、RMSProp 如何自适应每参数学习率
- 对比各优化器在收敛速度、泛化和内存上的权衡
- 为 Transformer、CNN、GAN 和微调场景选择正确的优化器

## 核心概念

### SGD 家族

| 优化器 | 更新规则 | 特点 |
|--------|----------|------|
| SGD | w -= lr * grad | 最简单、有噪声、泛化好 |
| SGD + Momentum | v = β*v + grad; w -= lr*v | 加速收敛，抑制震荡 |
| Nesterov | 先做 momentum 再算 grad | 前瞻，更快 |
| Adam | 结合 Momentum + RMSProp | 默认优化器，收敛快 |
| AdamW | Adam + 解耦的 weight decay | Transformer 标准 |

### Adam 的内部状态

每个参数维护两个 moving average：
- 一阶矩 m：β₁=0.9 的指数平均 → 梯度方向
- 二阶矩 v：β₂=0.999 的指数平均 → 梯度幅度

偏差修正：前几步 m 和 v 有初始化偏差（靠近 0）。`m_hat = m / (1-β₁ᵗ)`。

### 优化器选择

| 场景 | 优化器 | 起始 LR |
|------|--------|---------|
| 原型/小模型 | Adam | 1e-3 |
| 从头训练 Transformer | AdamW | 1e-4 – 3e-4 |
| 微调 | AdamW | 1e-5 – 5e-5 |
| CNN | SGD + Momentum | 0.1 |
| GAN | Adam（β₁=0.0） | 1e-4 |

## Build It

### Step 1: 从零实现 SGD、Momentum、Adam

### Step 2: 在合成数据上对比收敛曲线

## Use It

## Exercises

## Key Terms

## Further Reading
