# 优化

> 训练一个神经网络，无非就是找到山谷的谷底。

**Type:** Build
**Language:** Python
**Prerequisites:** Phase 1, Lessons 04-05 (Derivatives, Gradients)
**Time:** ~75 minutes

## 学习目标

- 从零实现普通梯度下降、带动量的 SGD 以及 Adam
- 在 Rosenbrock 函数上比较各优化器的收敛情况，并解释为什么 Adam 会为每个权重自适应地调整学习率
- 区分凸与非凸损失地形，并解释鞍点在高维空间中的作用
- 配置学习率调度（阶梯衰减、余弦退火、预热）以保证训练稳定

## 问题

你有一个损失函数。它告诉你模型错得有多离谱。你有梯度。它们告诉你哪个方向会让损失变得更糟。现在你需要一个「下山」的策略。

朴素的做法很简单：沿梯度的反方向移动，步长由一个叫做学习率的数字控制，然后重复。这就是梯度下降，它确实有效。但「有效」是有前提的。学习率太大会让你完全越过谷底，在两边的坡壁之间来回反弹。学习率太小会让你用成千上万个不必要的步骤慢慢爬向答案。撞上一个鞍点，你还没找到最小值就停住了。

深度学习里的每一个优化器，都是在回答同一个问题：如何更快、更可靠地到达谷底？

## 概念

### 优化是什么意思

优化就是找到使某个函数最小（或最大）的输入值。在机器学习里，这个函数就是损失，输入就是模型的权重。训练就是优化。

```
minimize L(w) where:
  L = loss function
  w = model weights (could be millions of parameters)
```

### 梯度下降（普通版）

最简单的优化器。对每一个权重计算损失关于该权重的梯度，让每个权重沿其梯度反方向移动，步长由学习率缩放。

```
w = w - lr * gradient
```

这就是整个算法。就一行。

```mermaid
graph TD
    A["* Starting point (high loss)"] --> B["Moving downhill along gradient"]
    B --> C["Approaching minimum"]
    C --> D["o Minimum (low loss)"]
```

### 学习率：最重要的超参数

学习率控制步长。它决定了关于收敛的一切。

```mermaid
graph LR
    subgraph TooLarge["Too Large (lr = 1.0)"]
        A1["Step 1"] -->|overshoot| A2["Step 2"]
        A2 -->|overshoot| A3["Step 3"]
        A3 -->|diverging| A4["..."]
    end
    subgraph TooSmall["Too Small (lr = 0.0001)"]
        B1["Step 1"] -->|tiny step| B2["Step 2"]
        B2 -->|tiny step| B3["Step 3"]
        B3 -->|10,000 steps later| B4["Minimum"]
    end
    subgraph JustRight["Just Right (lr = 0.01)"]
        C1["Start"] --> C2["..."] --> C3["Converged in ~100 steps"]
    end
```

正确的学习率没有公式。你得靠实验去找到它。常见的起点：Adam 用 0.001，带动量的 SGD 用 0.01。

### SGD vs 批量 vs 小批量

普通梯度下降在迈出一步之前，要先在整个数据集上计算梯度。这叫做批量梯度下降。它稳定但慢。

随机梯度下降（SGD）在单个随机样本上计算梯度并立即迈步。它噪声大但快。

小批量梯度下降折中了二者。在一个小批量（32、64、128、256 个样本）上计算梯度，然后迈步。这才是所有人实际使用的方案。

| 变体 | 批量大小 | 梯度质量 | 每步速度 | 噪声 |
|---------|-----------|-----------------|---------------|-------|
| 批量 GD | 整个数据集 | 精确 | 慢 | 无 |
| SGD | 1 个样本 | 噪声很大 | 快 | 高 |
| 小批量 | 32-256 | 良好估计 | 均衡 | 中等 |

SGD 和小批量中的噪声不是缺陷。它有助于逃离浅的局部极小值和鞍点。

### 动量：滚下山的球

普通梯度下降只看当前的梯度。如果梯度走之字形（在狭窄的山谷里很常见），进展就很慢。动量通过把过去的梯度累积成一个速度项来解决这个问题。

```
v = beta * v + gradient
w = w - lr * v
```

打个比方：一个滚下山的球。它不会在每一个起伏处停下再重新启动。它在一致的方向上积累速度，并抑制振荡。

```mermaid
graph TD
    subgraph Without["Without Momentum (zigzag, slow)"]
        W1["Start"] -->|left| W2[" "]
        W2 -->|right| W3[" "]
        W3 -->|left| W4[" "]
        W4 -->|right| W5[" "]
        W5 -->|left| W6[" "]
        W6 --> W7["Minimum"]
    end
    subgraph With["With Momentum (smooth, fast)"]
        M1["Start"] --> M2[" "] --> M3[" "] --> M4["Minimum"]
    end
```

`beta`（通常为 0.9）控制保留多少历史。beta 越大，动量越强、路径越平滑，但对方向变化的响应越慢。

### Adam：自适应学习率

不同的权重需要不同的学习率。一个很少得到大梯度的权重，当它终于得到大梯度时，应该迈出更大的步子。一个不断得到巨大梯度的权重，则应该迈出更小的步子。

Adam（自适应矩估计）为每个权重跟踪两个量：

1. 一阶矩 (m)：梯度的滑动平均（类似动量）
2. 二阶矩 (v)：梯度平方的滑动平均（梯度幅度）

```
m = beta1 * m + (1 - beta1) * gradient
v = beta2 * v + (1 - beta2) * gradient^2

m_hat = m / (1 - beta1^t)    bias correction
v_hat = v / (1 - beta2^t)    bias correction

w = w - lr * m_hat / (sqrt(v_hat) + epsilon)
```

除以 `sqrt(v_hat)` 是关键所在。梯度大的权重会被一个大的数除（有效步长小）。梯度小的权重会被一个小的数除（有效步长大）。每个权重都得到自己自适应的学习率。

默认超参数：`lr=0.001, beta1=0.9, beta2=0.999, epsilon=1e-8`。这些默认值对大多数问题都表现良好。

### 学习率调度

固定的学习率是一种妥协。训练早期，你想要大步幅以取得快速进展。训练后期，你想要小步幅在最小值附近精调。

常见的调度：

| 调度 | 公式 | 适用场景 |
|----------|---------|----------|
| 阶梯衰减 | lr = lr * factor every N epochs | 简单、手动控制 |
| 指数衰减 | lr = lr_0 * decay^t | 平滑下降 |
| 余弦退火 | lr = lr_min + 0.5 * (lr_max - lr_min) * (1 + cos(pi * t / T)) | Transformer、现代训练 |
| 预热 + 衰减 | 先线性爬升，再衰减 | 大模型，防止早期不稳定 |

### 凸与非凸

凸函数只有一个最小值。梯度下降总能找到它。像 `f(x) = x^2` 这样的二次函数就是凸的。

神经网络的损失函数是非凸的。它们有许多局部极小值、鞍点和平坦区域。

```mermaid
graph LR
    subgraph Convex["Convex: One valley, one answer"]
        direction TB
        CV1["High loss"] --> CV2["Global minimum"]
    end
    subgraph NonConvex["Non-convex: Multiple valleys, saddle points"]
        direction TB
        NC1["Start"] --> NC2["Local minimum"]
        NC1 --> NC3["Saddle point"]
        NC1 --> NC4["Global minimum"]
    end
```

在实践中，高维神经网络里的局部极小值很少成为问题。大多数局部极小值的损失值都接近全局最小值。鞍点（在某些方向上平坦、在另一些方向上弯曲）才是真正的障碍。动量和来自小批量的噪声有助于逃离它们。

### 损失地形可视化

损失是所有权重的函数。对于一个有 100 万个权重的模型，损失地形存在于 1,000,001 维空间中。我们通过在权重空间里挑两个随机方向、并沿着这些方向绘制损失来可视化它，从而得到一个二维曲面。

```mermaid
graph TD
    HL["High loss region"] --> SP["Saddle point"]
    HL --> LM["Local minimum"]
    SP --> LM
    SP --> GM["Global minimum"]
    LM -.->|"shallow barrier"| GM
    style HL fill:#ff6666,color:#000
    style SP fill:#ffcc66,color:#000
    style LM fill:#66ccff,color:#000
    style GM fill:#66ff66,color:#000
```

尖锐的极小值泛化差。平坦的极小值泛化好。这就是带动量的 SGD 在最终测试精度上常常胜过 Adam 的一个原因：它的噪声防止了陷入尖锐的极小值。

```figure
gradient-descent
```

## Build It

### 步骤 1：定义一个测试函数

Rosenbrock 函数是一个经典的优化基准。它的最小值在 (1, 1)，位于一个狭窄弯曲的山谷中，这个山谷容易找到却难以追踪。

```
f(x, y) = (1 - x)^2 + 100 * (y - x^2)^2
```

```python
def rosenbrock(params):
    x, y = params
    return (1 - x) ** 2 + 100 * (y - x ** 2) ** 2

def rosenbrock_gradient(params):
    x, y = params
    df_dx = -2 * (1 - x) + 200 * (y - x ** 2) * (-2 * x)
    df_dy = 200 * (y - x ** 2)
    return [df_dx, df_dy]
```

### 步骤 2：普通梯度下降

```python
class GradientDescent:
    def __init__(self, lr=0.001):
        self.lr = lr

    def step(self, params, grads):
        return [p - self.lr * g for p, g in zip(params, grads)]
```

### 步骤 3：带动量的 SGD

```python
class SGDMomentum:
    def __init__(self, lr=0.001, momentum=0.9):
        self.lr = lr
        self.momentum = momentum
        self.velocity = None

    def step(self, params, grads):
        if self.velocity is None:
            self.velocity = [0.0] * len(params)
        self.velocity = [
            self.momentum * v + g
            for v, g in zip(self.velocity, grads)
        ]
        return [p - self.lr * v for p, v in zip(params, self.velocity)]
```

### 步骤 4：Adam

```python
class Adam:
    def __init__(self, lr=0.001, beta1=0.9, beta2=0.999, epsilon=1e-8):
        self.lr = lr
        self.beta1 = beta1
        self.beta2 = beta2
        self.epsilon = epsilon
        self.m = None
        self.v = None
        self.t = 0

    def step(self, params, grads):
        if self.m is None:
            self.m = [0.0] * len(params)
            self.v = [0.0] * len(params)

        self.t += 1

        self.m = [
            self.beta1 * m + (1 - self.beta1) * g
            for m, g in zip(self.m, grads)
        ]
        self.v = [
            self.beta2 * v + (1 - self.beta2) * g ** 2
            for v, g in zip(self.v, grads)
        ]

        m_hat = [m / (1 - self.beta1 ** self.t) for m in self.m]
        v_hat = [v / (1 - self.beta2 ** self.t) for v in self.v]

        return [
            p - self.lr * mh / (vh ** 0.5 + self.epsilon)
            for p, mh, vh in zip(params, m_hat, v_hat)
        ]
```

### 步骤 5：运行并比较

```python
def optimize(optimizer, func, grad_func, start, steps=5000):
    params = list(start)
    history = [params[:]]
    for _ in range(steps):
        grads = grad_func(params)
        params = optimizer.step(params, grads)
        history.append(params[:])
    return history

start = [-1.0, 1.0]

gd_history = optimize(GradientDescent(lr=0.0005), rosenbrock, rosenbrock_gradient, start)
sgd_history = optimize(SGDMomentum(lr=0.0001, momentum=0.9), rosenbrock, rosenbrock_gradient, start)
adam_history = optimize(Adam(lr=0.01), rosenbrock, rosenbrock_gradient, start)

for name, history in [("GD", gd_history), ("SGD+M", sgd_history), ("Adam", adam_history)]:
    final = history[-1]
    loss = rosenbrock(final)
    print(f"{name:6s} -> x={final[0]:.6f}, y={final[1]:.6f}, loss={loss:.8f}")
```

预期输出：Adam 收敛最快。带动量的 SGD 走一条更平滑的路径。普通 GD 在狭窄的山谷里进展缓慢。

## Use It

在实践中，使用 PyTorch 或 JAX 的优化器。它们处理参数组、权重衰减、梯度裁剪和 GPU 加速。

```python
import torch

model = torch.nn.Linear(784, 10)

sgd = torch.optim.SGD(model.parameters(), lr=0.01, momentum=0.9)
adam = torch.optim.Adam(model.parameters(), lr=0.001)
adamw = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)

scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(adam, T_max=100)
```

经验法则：

- 从 Adam (lr=0.001) 开始。它无需调参就能处理大多数问题。
- 当你需要最佳的最终精度、并且能承受更多调参时，切换到带动量的 SGD (lr=0.01, momentum=0.9)。
- Transformer 使用 AdamW（带解耦权重衰减的 Adam）。
- 训练超过几个 epoch 时，始终使用学习率调度。
- 如果训练不稳定，就降低学习率。如果训练太慢，就提高它。

## Ship It

本课产出一个用于选择正确优化器的提示词。见 `outputs/prompt-optimizer-guide.md`。

这里构建的优化器类会在第 3 阶段从零训练神经网络时再次出现。

## 练习

1. **学习率扫描。** 用学习率 [0.0001, 0.0005, 0.001, 0.005, 0.01] 在 Rosenbrock 函数上运行普通梯度下降。对每个学习率绘制或打印 5000 步之后的最终损失。找出仍然能收敛的最大学习率。

2. **动量比较。** 用动量值 [0.0, 0.5, 0.9, 0.99] 在 Rosenbrock 函数上运行 SGD。跟踪每一步的损失。哪个动量值收敛最快？哪个会超调？

3. **逃离鞍点。** 定义函数 `f(x, y) = x^2 - y^2`（原点处有一个鞍点）。从 (0.01, 0.01) 出发。比较普通 GD、带动量的 SGD 和 Adam 的表现。哪个能逃离鞍点？

4. **实现学习率衰减。** 给 GradientDescent 类加一个指数衰减调度：`lr = lr_0 * 0.999^step`。在 Rosenbrock 函数上比较有衰减和无衰减的收敛情况。

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|----------------------|
| Gradient descent | 「向下走」 | 通过减去按学习率缩放的梯度来更新权重。最基本的优化器。 |
| Learning rate | 「步长」 | 一个标量，控制每次更新把权重移动多远。太大会发散，太小浪费算力。 |
| Momentum | 「保持滚动」 | 把过去的梯度累积成一个速度向量。抑制振荡，并在一致的方向上加速移动。 |
| SGD | 「随机采样」 | 随机梯度下降。在随机子集上计算梯度，而不是整个数据集。实践中几乎总是指小批量 SGD。 |
| Mini-batch | 「一小块数据」 | 用于估计梯度的一小部分训练数据（32-256 个样本）。在速度和梯度精度之间取得平衡。 |
| Adam | 「默认优化器」 | 自适应矩估计。为每个权重跟踪梯度和梯度平方的滑动平均，从而给每个权重自己的学习率。 |
| Bias correction | 「修正冷启动」 | Adam 的一阶矩和二阶矩被初始化为零。偏差校正通过除以 (1 - beta^t) 来补偿早期步骤。 |
| Learning rate schedule | 「随时间改变 lr」 | 一个在训练过程中调整学习率的函数。早期大步幅，后期小步幅。 |
| Convex function | 「只有一个谷」 | 任何局部极小值都是全局极小值的函数。梯度下降总能找到它。神经网络损失不是凸的。 |
| Saddle point | 「平坦但不是极小值」 | 梯度为零、但在某些方向上是最小值、在另一些方向上是最大值的点。在高维空间中很常见。 |
| Loss landscape | 「地形」 | 绘制在权重空间上的损失函数。通过沿两个随机方向切片来可视化。 |
| Convergence | 「到达了」 | 优化器已达到一个点，进一步的步骤不再有意义地降低损失。 |

## 延伸阅读

- [Sebastian Ruder: An overview of gradient descent optimization algorithms](https://ruder.io/optimizing-gradient-descent/) - 对所有主要优化器的全面综述
- [Why Momentum Really Works (Distill)](https://distill.pub/2017/momentum/) - 动量动力学的交互式可视化
- [Adam: A Method for Stochastic Optimization (Kingma & Ba, 2014)](https://arxiv.org/abs/1412.6980) - Adam 的原始论文，可读性强且篇幅短
- [Visualizing the Loss Landscape of Neural Nets (Li et al., 2018)](https://arxiv.org/abs/1712.09913) - 展示尖锐与平坦极小值的论文
