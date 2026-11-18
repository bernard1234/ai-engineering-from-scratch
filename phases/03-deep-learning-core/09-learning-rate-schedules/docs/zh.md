# 学习率调度

> 学习率不应该是常数。它应该随训练进度调整。

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 3 Lessons 3-6
**Time:** ~30 minutes

## Learning Objectives

- 列出五种常见调度：恒定、Step、Cosine、Warmup + Cosine、1cycle
- 说明 Transformer 为什么需要 Warmup（前几步学习率从 0 爬升）
- 为从头训练、微调、快速实验选正确的调度
- 实现 Cosine annealing 和 Linear warmup

## 核心概念

### 为什么需要调度

训练初期：参数远离最优，大的学习率快速逼近。
训练后期：接近最优，小的学习率精细调整。

### 五种调度

| 调度 | 形状 | 何时用 |
|------|------|--------|
| 恒定 | 直线 | 快速实验 |
| Step decay | 阶梯 | ResNet 训练（epoch 30/60/90 除以 10） |
| Cosine annealing | 余弦曲线降 | 现代默认 |
| Warmup + Cosine | 先爬升再余弦降 | Transformer/LLM 训练标准 |
| 1cycle | 爬升 + 快速下降 | 固定预算下最快收敛 |

### Warmup 的作用

Transformer 有大量层，早期梯度方向不稳定。warmup 阶段从很小的 LR 线性爬升，让模型安全启动。

## Build It

### Step 1: 实现 Cosine 和 Warmup + Cosine

### Step 2: 对比调度的收敛速度

## Use It

## Exercises

## Key Terms

## Further Reading
