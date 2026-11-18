# 损失函数

> 损失告诉你模型 "有多错"。对不同任务有不同的损失。

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 3 Lesson 3 (Backpropagation), Phase 1 Lesson 5 (Entropy & Cross-Entropy)
**Time:** ~75 minutes

## Learning Objectives

- 实现 MSE、交叉熵和 Huber 损失，包括它们的梯度
- 解释为什么 MSE 不适合分类任务（sigmoid + MSE 的非凸损失）
- 从伯努利分布的负对数似然推导二元交叉熵
- 为分类（二分类、多分类、不平衡）和回归任务选择正确的损失

## 核心概念

### 常见损失

| 任务 | 损失 | 公式 | 特点 |
|------|------|------|------|
| 回归 | MSE | (1/n)Σ(y_pred - y)² | 异常值敏感 |
| 回归 | MAE | (1/n)Σ|y_pred - y| | 鲁棒但不可导于 0 |
| 回归 | Huber | MSE 或 MAE（阈值附近平滑切换） | 两者的最好 |
| 二分类 | BCE | -Σ[y log p + (1-y) log(1-p)] | 输出 logit 时用 BCEWithLogitsLoss |
| 多分类 | CE | -ΣΣ y_k log p_k | 内部包含 softmax |
| 嵌入 | InfoNCE | -log exp(s_pos/τ) / Σ exp(s_neg/τ) | 自监督对比学习 |

### 为什么分类不用 MSE

Sigmoid + MSE 产生非凸损失曲面（有局部极小值），而 CE + sigmoid 是凸的，保证全局最优。另外 MSE 的梯度在饱和区因 sigmoid 导数变平而消失。

### BCE 的推导

二元交叉熵来自观察 Bernoulli 分布的负对数似然：

```
L(θ) = -Σ y_i log p(y_i | x_i, θ)
     = -[y log p + (1-y) log(1-p)]
```

## Build It

### Step 1: 实现所有损失 + 梯度

### Step 2: 数值梯度检查

### Step 3: 对比 BCE vs MSE 在分类上的表现

## Use It

## Exercises

## Key Terms

## Further Reading
