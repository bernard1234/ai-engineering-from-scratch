# 感知机

> 感知机是神经网络的原子。把它拆开，里面就是权重、偏置和一个决策。

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 1 (Linear Algebra Intuition)
**Time:** ~60 minutes

## Learning Objectives

- 用 Python 从零实现感知机，包括权重更新规则和阶跃激活函数
- 解释为什么单个感知机只能解决线性可分问题，并演示 XOR 失败案例
- 通过组合 OR、NAND 和 AND 门构建多层感知机来解决 XOR
- 用 sigmoid 激活和反向传播训练两层网络，自动学习 XOR

## 问题场景

你知道向量和点积。你知道矩阵把输入变换成输出。但机器是怎么**学到**该用哪个变换的？

感知机回答了这个问题。它是最简单的学习机器：取几个输入，乘以权重，加偏置，做一个二元决策。然后调整。就这么多。每一个曾经构建的神经网络都是把这个想法堆叠在一起。

理解感知机就是理解代码里 "学习" 实际是什么意思：调整数字，直到输出匹配现实。

## 核心概念

### 一个神经元，一个决策

感知机取 n 个输入，每个乘以一个权重，求和，加偏置，结果通过一个激活函数。

（mermaid 图保留）

阶跃函数很粗暴：加权和加偏置 >= 0 则输出 1，否则输出 0。

```
step(z) = 1  if z >= 0
           0  if z < 0
```

这是一个线性分类器。权重和偏置定义了一条线（高维中是超平面），把输入空间分成两个区域。

### 决策边界

对于两个输入，感知机在 2D 空间画一条线：

（ASCII 图保留）

线的一侧全部输出 0，另一侧全部输出 1。训练就是移动这条线直到它正确分隔类别。

### 学习规则

感知机学习规则很简单：

```
对每个训练样本 (x, y_true):
    y_pred = predict(x)
    error = y_true - y_pred

    对每个权重：
        w_i = w_i + learning_rate * error * x_i
    bias = bias + learning_rate * error
```

预测正确，error = 0，什么都不变。预测 0 但应该是 1，权重增大。预测 1 但应该是 0，权重减小。学习率控制每次调整的幅度。

### XOR 问题

这就是它破防的地方。看这些逻辑门：

（真值表保留）

AND 和 OR 线性可分：可以画一条线把 0 和 1 分开。XOR 不行。没有一条线能把 [0,1] 和 [1,0] 跟 [0,0] 和 [1,1] 分开。

（ASCII 图保留）

这是一个根本限制。单个感知机只能解决线性可分问题。Minsky 和 Papert 在 1969 年证明了这一点，它几乎杀死了整个神经网络研究达十年。

修复：把感知机堆叠成层。多层感知机能把两个线性决策组合成一个非线性决策，从而解决 XOR。

（figure 块保留）

## Build It

### 第 1 步：Perceptron 类

（Python 代码逐字保留）

### 第 2 步：在逻辑门上训练

（Python 代码逐字保留）

### 第 3 步：观察 XOR 失败

（Python 代码逐字保留）

它永远不会收敛。这是硬证明——单个感知机学不了 XOR。

### 第 4 步：用两层解决 XOR

技巧：XOR = (x1 OR x2) AND NOT (x1 AND x2)。组合三个感知机：

（mermaid 图保留）

（Python 代码逐字保留）

四种情况全部正确。把感知机堆叠成层，就能产生单个感知机无法做到的决策边界。

### 第 5 步：训练两层网络

第 4 步是手工设权重。对 XOR 可行，但对真实问题（你预先不知道正确权重的）不行。修复：把阶跃函数换成 sigmoid，通过反向传播自动学习权重。

（Python 代码逐字保留）

和第 4 步的两个关键区别。第一，sigmoid 替换了阶跃函数——它光滑，所以梯度存在。第二，`train` 方法把误差从输出层反向传播到隐藏层，按每个权重对误差的贡献比例来调整它。这就是 20 行代码版的反向传播。

这是通往第 3 课的桥梁。`d_output` 和 `hidden_deltas` 背后的数学是把链式法则应用到网络图上。我们会在那里正式推导。

## Use It

你刚从零构建的全部东西，一行 import 就有：

（Python 代码逐字保留）

生产级网络发生了什么变化：

- 阶跃函数换成 sigmoid、ReLU 或其他光滑激活
- 权重通过反向传播自动学习（第 3 课）
- 层变得更深：3 层、10 层、100+ 层
- 同一个原则：每一层都从前一层的输出中构造新特征

单个感知机只能画直线。把它们堆起来，就能画任意形状。

## Ship It

本课产出：
- `outputs/skill-perceptron.md`——涵盖何时需要单层 vs 多层架构的 skill

## Exercises

1. 在 NAND 门（通用门——任何逻辑电路都能用 NAND 构建）上训练感知机。验证它的权重和偏置形成一个有效决策边界。
2. 修改 Perceptron 类，追踪每个 epoch 的决策边界（w1*x1 + w2*x2 + b = 0）。打印 AND 门训练过程中这条线怎么移动。
3. 构建一个 3 输入感知机，仅当 3 个输入中至少 2 个为 1 时输出 1（多数投票函数）。这个函数线性可分吗？为什么？

## Key Terms

| 术语 | 人们常说 | 实际含义 |
|------|----------|----------|
| Perceptron | "假神经元" | 线性分类器：输入和权重的点积加偏置，再过阶跃函数 |
| Weight | "一个输入有多重要" | 缩放每个输入对决策贡献的乘数 |
| Bias | "阈值" | 移动决策边界的常数，让感知机即使零输入也能触发 |
| Activation function | "那个把值压扁的东西" | 加权和之后应用的函数——感知机用阶跃函数，现代网络用 sigmoid/ReLU |
| Linearly separable | "能在中间画条线" | 一个数据集存在单个超平面能完美分隔类别 |
| XOR problem | "感知机做不了的那个" | 证明单层网络学不了非线性可分函数的例子 |
| Decision boundary | "分类器切换的地方" | 超平面 w*x + b = 0，把输入空间分成两类 |
| Multi-layer perceptron | "真正的神经网络" | 感知机堆叠成层，每层的输出喂给下一层 |

## Further Reading

- Frank Rosenblatt, "The Perceptron: A Probabilistic Model for Information Storage and Organization in the Brain" (1958) — 一切的起点，原始论文
- Minsky & Papert, "Perceptrons" (1969) — 证明单层网络解不了 XOR 的书，杀死了感知机研究达十年
- Michael Nielsen, "Neural Networks and Deep Learning", Chapter 1 (http://neuralnetworksanddeeplearning.com/) — 免费在线，感知机组合成网络的最佳视觉化解释
