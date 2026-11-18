# 反向传播

> 链式法则。从损失值开始，向每一层传播 "我该调整多少"。

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 1 Lesson 12 (Chain Rule), Phase 3 Lesson 2 (Forward Propagation)
**Time:** ~90 minutes

## Learning Objectives

- 对 MLP 的损失相对于每个权重的梯度完整推导链式法则
- 从零手写反向传播（NumPy），验证梯度和数值梯度匹配
- 说明什么让 sigmoid 饱和导致梯度消失，以及 ReLU 如何缓解
- 构建一个带前向/反向传播的两层网络，并在合成数据上训练

## 核心概念

### 核心思想

反向传播 = 链式法则 + 动态规划。从输出层开始，依次计算每一层每个权重对损失的贡献。

### 推导（两层例子）

（链式法则推导逐字保留）

### 计算图

用计算图可视化依赖关系。每个节点是一个操作，边表示数据依赖。反向传播就是沿图反向走，给每条边分配梯度。

### 梯度消失

sigmoid 导数最大值 = 0.25。深层网络中每多一层乘一个 0.25，梯度指数级缩小。ReLU 导数 = 0 或 1，没这个问题。

### 梯度检查

用有限差分数值近似验证你的梯度实现：

```
dL/dw ≈ (L(w + eps) - L(w - eps)) / (2 * eps)
```

如果解析梯度和数值梯度差距 < 1e-5，实现正确。

## Build It

### Step 1: 计算图追踪（纯 Python）

### Step 2: 反向传播（NumPy）

### Step 3: 梯度检查

### Step 4: 用反向传播训练 XOR

（详见 `code/backprop.py`）

## Use It

## Exercises

## Key Terms

## Further Reading
