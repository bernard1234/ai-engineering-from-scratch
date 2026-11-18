# JAX 入门

> JAX 把自动微分、向量化、编译和并行变成一等公民。DeepMind 用它做研究。

**Type:** Learn + Use
**Languages:** Python (JAX)
**Prerequisites:** Phase 3 Lessons 1-10 (全部核心概念)
**Time:** ~60 minutes

## Learning Objectives

- 理解 JAX 的函数式编程模型（纯函数、不可变数组、PRNG key）
- 用 grad、jit、vmap、pmap 四个核心变换改写训练代码
- 用 Optax 写 JAX 优化器链
- 对比 JAX 和 PyTorch 的编程模型差异和各自优势

## 核心概念

### JAX 的世界观

PyTorch 是 imperative + hybrid autograd。JAX 是 **pure functional**：

- 数组不可变（用 `x.at[i].set(v)` 代替 `x[i] = v`）
- 函数无副作用（不用全局状态，PRNG key 显式传入）
- 变换：`jax.grad(f)` 产生 f 的导数，`jax.jit(f)` 编译 f，`jax.vmap(f)` 向量化 f

### 四个核心变换

| 变换 | 做什么 | 输入 | 输出 |
|------|--------|------|------|
| `grad` | 函数求导 | 函数 → 函数 | f(x) → d/dx f(x) |
| `jit` | XLA 编译函数 | 函数 → 编译函数 | f(x) → 编译版 f(x) |
| `vmap` | 沿轴向量化 | 函数 → batch 函数 | f(x) → f(xs) |
| `pmap` | 跨设备并行 | 函数 → 并行函数 | f(x) → f(x) on N devices |

### 何时用 JAX

- TPU 上训练（JAX 是 DeepMind 和 Google TPU 的原生框架）
- 需要高阶导数（Hessian、Fisher 信息）
- 需要 per-example 梯度（差分隐私）
- 团队在 DeepMind/Anthropic

### 何时用 PyTorch

- 最大的生态（HuggingFace、Lightning、TorchServe）
- 调试简单胜过原始速度
- 更多开源模型和教程
- 多 GPU 数据并行更成熟（DDP、FSDP）

## Build It + Use It

（JAX 实际代码示例）

## Exercises

## Key Terms

## Further Reading
