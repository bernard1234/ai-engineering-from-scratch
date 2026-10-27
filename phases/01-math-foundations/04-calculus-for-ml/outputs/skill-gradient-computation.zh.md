---
name: skill-gradient-computation
description: 计算常见 ML 损失函数的梯度，并选择合适的导数方法
version: 1.0.0
phase: 1
lesson: 4
tags: [calculus, gradients, backpropagation]
---

# 面向 ML 的梯度计算

用于计算神经网络中损失函数、激活函数和层运算的梯度的实用参考。

## 决策清单

1. 函数是否由简单原语（幂、exp、log、三角）复合而成？使用解析导数和链式法则。
2. 函数是否是自定义或黑盒运算？使用数值微分：`(f(x+h) - f(x-h)) / (2h)`，h = 1e-7。
3. 函数是否由 PyTorch/JAX 中的张量运算构成？交给 autograd 处理。用数值检查验证。
4. 是否需要标量损失对权重矩阵的梯度？通过计算图逐节点应用链式法则。
5. 是否存在不可微运算（argmax、舍入、采样）？使用直通估计器或重参数化技巧。

## 何时使用每种方法

| 方法 | 何时使用 | 成本 |
|---|---|---|
| 解析（手动推导） | 简单函数，验证 autograd 输出 | 运行时零成本 |
| 数值（有限差分） | 调试、梯度检查、黑盒函数 | n 个参数需 2n 次前向传播 |
| 自动微分 | 任何可微计算图（默认） | 一次反向传播 |
| 符号（SymPy、Mathematica） | 为论文推导闭式梯度 | 仅编译期 |

## 速查：常见导数

| 函数 | f(x) | f'(x) | ML 上下文 |
|---|---|---|---|
| MSE 损失 | (1/n) sum(y_hat - y)^2 | (2/n)(y_hat - y) | 回归 |
| 交叉熵（二分类） | -(y log(p) + (1-y) log(1-p)) | p - y（经 sigmoid 后） | 二分类 |
| 交叉熵（多分类） | -log(p_true_class) | p - one_hot(y)（经 softmax 后） | 多分类 |
| Sigmoid | 1 / (1 + e^(-x)) | sigma(x) * (1 - sigma(x)) | 输出门、二值输出 |
| Tanh | (e^x - e^(-x)) / (e^x + e^(-x)) | 1 - tanh(x)^2 | 隐藏层激活（遗留） |
| ReLU | max(0, x) | 1 如果 x > 0，0 如果 x < 0 | 默认隐藏层激活 |
| Leaky ReLU | max(0.01x, x) | 1 如果 x > 0，0.01 如果 x < 0 | 避免死亡神经元 |
| GELU | x * Phi(x) | Phi(x) + x * phi(x) | Transformer |
| Softmax_i | e^(x_i) / sum(e^(x_j)) | i=j 时 s_i(1 - s_i)，i!=j 时 -s_i*s_j | 输出层（Jacobian） |
| Log-softmax | x_i - log(sum(e^(x_j))) | 第 i 项为 1 - softmax(x_i) | 数值稳定的 CE |
| 线性层 | y = Wx + b | dL/dW = dL/dy * x^T，dL/db = dL/dy | 每一层 |
| L2 正则化 | lambda * sum(w^2) | 2 * lambda * w | 权重衰减 |
| L1 正则化 | lambda * sum(\|w\|) | lambda * sign(w) | 稀疏性 |

## 常见错误

- 忘记批量平均损失（MSE、交叉熵）中的 1/n 因子。梯度会按批量大小缩放。
- 把 softmax 梯度当作向量计算，而它实际上是一个 Jacobian 矩阵。对于交叉熵 + softmax 的组合，梯度简化为 (p - y)，从而避免了完整的 Jacobian。
- 以错误的顺序应用链式法则。从损失向后工作：dL/dW = dL/dy * dy/dW。
- 数值导数使用了过大（h = 0.1）或过小（h = 1e-15）的 h。对于 float64，坚持使用 h = 1e-7。
- 忘记 ReLU 在恰好 x = 0 处梯度未定义。在实践中，把它设为 0 或 0.5。

## 梯度检查配方

```
对每个参数 w：
  numeric_grad = (loss(w + h) - loss(w - h)) / (2h)
  auto_grad = 反向传播的值
  relative_error = |numeric - auto| / max(|numeric|, |auto|, 1e-8)
  assert relative_error < 1e-5
```

相对误差超过 1e-3 意味着有问题。介于 1e-5 和 1e-3 之间，则需要调查。