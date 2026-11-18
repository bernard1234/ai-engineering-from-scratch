# 迷你框架

> 从零造一个微型神经网络框架，理解 PyTorch/JAX 在做什么。

**Type:** Build
**Languages:** Python (NumPy)
**Prerequisites:** Phase 3 Lessons 1-8 (全部核心概念)
**Time:** ~120 分钟

## Learning Objectives

- 用 numpy 手写一个微型 autograd 系统（Variable 类 + 计算图）
- 实现 Linear、ReLU、Sigmoid、CrossEntropy 等 Layer 类
- 实现 SGD 和 Adam 优化器
- 在合成分类问题上训练并与 PyTorch 对比

## 核心概念

### 设计原则

类似 PyTorch：
- Variable 类追踪数据、grad 和 `_backward` 函数
- 操作（加、乘、relu 等）创建计算图节点
- backward 从输出调起，递归对所有参数累加梯度
- Layer 类封装参数和 forward 方法

### 核心类

（Variable/Parameter/Module/Optimizer/Function 类设计）

### 训练循环

```python
for step in range(num_steps):
    pred = model(x_batch)
    loss = criterion(pred, y_batch)
    loss.backward()
    optimizer.step()
    optimizer.zero_grad()
```

### 为什么造它

造完这个框架你会：
- 完全理解 PyTorch 内部在做什么
- 知道为什么需要 `.zero_grad()`、`.backward()`、`.step()`
- 知道 `requires_grad=True` 是什么
- 知道为什么 autograd 慢的时候你需要 jit 编译

## Build It

### Step 1: Variable 和计算图

### Step 2: 操作层（Linear、Activations、Loss）

### Step 3: 优化器（SGD、Adam）

### Step 4: 训练循环 + 与 PyTorch 对比

## Use It

## Exercises

## Key Terms

## Further Reading
