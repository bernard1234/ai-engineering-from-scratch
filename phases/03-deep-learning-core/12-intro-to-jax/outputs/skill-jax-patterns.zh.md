---
name: skill-jax-patterns
description: JAX 中的函数式编程模式——何时及如何使用 grad、jit、vmap 和 pmap
version: 1.0.0
phase: 3
lesson: 12
tags: [jax, functional-programming, autodiff, compilation, vectorization]
---

# JAX 函数式模式

JAX 变换纯函数。下面每个模式遵循一个规则：写一个取输入返回输出、没有副作用的函数。然后变换它。

## 四个变换

### grad——函数求导

（代码逐字保留）

使用场景：需要梯度做优化。
约束：函数必须返回标量。非标量输出用 `jax.jacobian`。

### jit——编译函数

（代码逐字保留）

使用场景：函数将用相同形状的输入被调用多次。
约束：不要有依赖 traced 值的 Python 控制流。条件用 `jax.lax.cond`，循环用 `jax.lax.scan`。

### vmap——向量化函数

（代码逐字保留）

使用场景：你为单个样本写了一个函数，需要它对 batch 工作。
`in_axes` 指定沿哪个参数轴做 batch。`None` 表示不 batch（广播）。

### pmap——跨设备并行

（代码逐字保留）

使用场景：你有多 GPU/TPU 且想要数据并行。
函数内部用 `jax.lax.pmean(x, 'devices')` 跨设备平均。

## 组合规则

变换可组合。顺序很重要：

```python
per_example_grads = jax.jit(jax.vmap(jax.grad(loss_fn), in_axes=(None, 0, 0)))
```

从右往左读：loss_fn 取梯度，对样本向量化，编译结果。

## 参数管理模式

JAX 参数是 pytrees（嵌套 dict 数组）：

（代码逐字保留）

## PRNG Key 管理

JAX 需要显式的随机 key：

（代码逐字保留）

## 常见错误

1. **jit 内修改数组**：JAX 数组不可变。用 `x.at[i].set(v)` 代替 `x[i] = v`
2. **jit 内用 Python print**：`print` 在 tracing 期间运行，不是执行期间。用 `jax.debug.print("{}", x)`
3. **jit 内对 traced 值用 Python if/for**：用 `jax.lax.cond`、`jax.lax.switch`、`jax.lax.scan`、`jax.lax.fori_loop`
4. **忘了 `.block_until_ready()`**：JAX 用异步 dispatch。benchmark 时调 `.block_until_ready()` 等实际完成
5. **重用 PRNG key**：两个操作用相同 key 会产生相同的 "随机" 值。永远先 split
6. **jit 函数中的全局状态**：全局变量在 trace 时捕获。trace 之后的改动不可见。所有东西都作为参数传入

## 决策检查清单

1. 函数被调用不止一次？加 `@jax.jit`
2. 需要梯度？用 `jax.grad` 或 `jax.value_and_grad` 包装
3. 处理一个样本但有 batch？用 `jax.vmap` 包装
4. 多设备？用 `jax.pmap` 包装
5. 用到随机性？显式把 PRNG key 传进传出
6. 对数组值有 Python 控制流？换成 `jax.lax` 原语

## 何时用 JAX

用 JAX：
- 需要 per-example 梯度（差分隐私、Fisher 信息）
- 在 TPU 上训练（JAX 是原生框架）
- 需要高阶导数（Hessian、Jacobian）
- 想把整个训练步骤编译成单个 kernel
- 团队在 Google DeepMind 或 Anthropic

用 PyTorch：
- 想要最大的生态（HuggingFace、torchvision、Lightning）
- 调试容易胜过原始速度
- 用 TorchServe/Triton 部署到 NVIDIA GPU
- 在招人（更多 PyTorch 开发者）
- 想在新架构上快速迭代
