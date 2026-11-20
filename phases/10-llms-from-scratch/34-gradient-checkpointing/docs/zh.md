# Gradient Checkpointing 与 Activation Recomputation

> 反向传播会保留每一个中间 activation。在 70B 参数、128K 上下文下，那是每个 rank 3 TB 的 activation。checkpointing 用 FLOPs 换显存：重算而不是保存。问题在于该丢掉哪些分段，而答案并不是“全部”。

**Type:** Build
**Languages:** Python (with numpy, optional torch)
**Prerequisites:** Phase 10 Lesson 04 (Pre-Training Mini-GPT), Phase 10 Lesson 05 (Scaling & Distributed)
**Time:** ~70 分钟

## 问题场景

训练一个 transformer 时，每一层都要为反向传播中被求导的每个算子保存输入：attention 的输入、Q/K/V 投影、softmax 输出、FFN 输入、norm 输出，以及残差流。对一个 hidden size 为 `d`、序列长度为 `L`、批大小为 `B` 的层，每层的量级是 `12 * B * L * d` 个 float。

对 `d=8192, L=8192, B=1`，那是每层 800 MB（BF16）。一个 64 层的模型就是 51 GB 的 activation——而这还没乘上 microbatch 大小，还没加上 attention-softmax 中间量（每个 head `L^2`），也还没算上 tensor-parallel 的部分副本。

两头的账单：BF16 权重加优化器状态也许能装进 80GB，但 activation 会把你顶出去。Gradient checkpointing（又称 activation recomputation）是标准的解法。丢掉大部分 activation；在反向时重做前向把它们拿回来。代价：额外的 FLOPs。收益：显存按“checkpoint 分段数 / 总层数”的比例下降。

做得朴素，checkpointing 大约会让每步的前向 FLOPs 多 33%。做得好——按 Korthikanti 等人的“smart selection”做选择性 checkpointing——你能用不到 5% 的 FLOP 开销省下 5 倍显存。在 FP8 matmul、FSDP offload 以及 expert-parallel MoE 的背景下这真的很重要：显存和浪费的算力你都负担不起。

## 核心概念

### 反向传播实际需要什么

`output = layer(input)`。反向需要 `grad_input` 和 `grad_params`。为了算出它们，它需要：

- `input`（对线性层而言，用来计算 `grad_params = input.T @ grad_output`）
- 一些 activation 的导数中间量（ReLU/GELU/softmax 的导数依赖激活值）

前向会自动把这些存进 autograd 图。每一次 `tensor.retain_grad()` 以及每个需要自己输入的算子都会保留一个引用。

### 朴素的全量 checkpointing

把网络切成 `N` 个分段。前向时只保存每个分段的*输入*。当反向需要中间量时，重跑该分段的前向把它们具体算出来，再做求导。

例子：32 层 transformer 切成 32 个各 1 层的分段。

- 显存：32 个层输入（很小）对比 32 *（每层 activation 体积）（巨大）。
- 额外计算：每分段多一次前向，也就是总前向 FLOPs 多约 33%（因为反向是前向的 2 倍，完整一步变成 1 + 1 + 2 = 4 个单位，而不是 1 + 2 = 3）。

这就是 Chen 等人 2016 的原始配方：每 `sqrt(L)` 层放一个 checkpoint，以平衡显存与计算。对 L=64，就是 8 个 checkpoint。

### 选择性 checkpointing（Korthikanti 2022）

并非所有 activation 成本都一样。attention softmax 输出是 `B*L*L*heads`，随序列长度*二次方*增长。FFN 隐层 activation 是 `B*L*4d`，线性增长。对长序列，softmax 占主导。

选择性 checkpointing 保留存储便宜的 activation（线性投影、残差），只重算昂贵的那些（attention）。你付出极小的 FLOPs 去重算，却省下了 O(L^2) 的显存。

Megatron-Core 把它实现为“selective” activation recomputation。2024 年以后的前沿训练大多使用它。

### Offload（卸载）

重算之外的另一种选择：在前向与反向之间把 activation 运到 CPU RAM。需要 PCIe 带宽；当闲置带宽的收益超过重物化的成本时才有优势。混合策略很常见：对某些层做 checkpoint，对另一些层做 offload。

FSDP2 把 offload 作为一等选项提供。当 GPU 受显存瓶颈限制、而 CPU-GPU 传输还有余量时，offload 表现出色。

### 重算成本模型

在 `L` 层中每 `k` 层做朴素 checkpointing 的每步 FLOPs：

```
flops_fwd_normal = L * f_layer
flops_bwd_normal = 2 * L * f_layer
flops_total_normal = 3 * L * f_layer

flops_fwd_ckpt = L * f_layer
flops_recompute = L * f_layer  # one extra forward per layer in the segment
flops_bwd_ckpt = 2 * L * f_layer
flops_total_ckpt = 4 * L * f_layer
overhead = 4 / 3 - 1 = 0.33 = 33%
```

用选择性 checkpointing 时只重算 attention kernel，而不是整层：

```
flops_recompute_selective = L * f_attention ~= L * f_layer * 0.15
overhead_selective = (3 + 0.15) / 3 - 1 = 0.05 = 5%
```

### 显存节省模型

每层的 activation 体积：`A`。对 `L` 层，总 activation 显存：`L * A`。

全量 checkpoint（分段大小为 1）：只存 `L * input_volume`（标准 transformer 下约为 `L * 1/10 A`）。省下约 `9 * L * A * 1/10`。

每 `k` 层做 checkpoint：存 `L/k * A`，再加上活动分段内 `k-1` 层的量。

在 `k = sqrt(L)` 时，显存与重算成本都随 `sqrt(L)` 缩放——这是等成本层的最优权衡。

### 何时不该做 checkpoint

- pipeline 阶段中最内层、已经 in-flight 的层。它们无论如何都得跑完。
- 如果首尾层在该阶段计算中占主导（在 transformer 中少见）。
- 已经使用 FlashAttention 的 attention kernel——Flash 已经会快速重算 softmax，在其之上再做层级 checkpointing 增益很小。

### 实现模式

1. **函数包装：** 把一段包进 `torch.utils.checkpoint.checkpoint(fn, input)`。PyTorch 只保存 `input`，反向时重算其余一切。

2. **装饰器方式：** 把层标记为可 checkpoint；训练器在配置时决定包装哪些分段。

3. **手工显式重算：** 自己写反向，调用一个自定义的 `recompute_forward`，用保存的输入复现前向。

三者给出的功能结果相同。包装是标准写法。

### 与 TP / PP / FP8 的交互

- **Tensor parallel：** checkpoint 的输入在重算时必须 gather 或重新 scatter；要处理相应的通信成本。
- **Pipeline parallel：** 典型模式是对每个 pipeline 阶段的前向做 checkpoint，以便逆序的 microbatch 复用 activation 显存。
- **FP8 重算：** 重算过程中更新的 amax 历史必须与原始前向的一致，否则 FP8 的 scale 会漂移。大多数框架会快照 scale。

```figure
activation-recompute
```

## Build It

### 第 1 步：一个带分段的玩具模型

```python
import numpy as np


def linear_forward(x, w, b):
    return x @ w + b


def relu(x):
    return np.maximum(x, 0)


def layer_forward(x, w1, b1, w2, b2):
    h = relu(linear_forward(x, w1, b1))
    return linear_forward(h, w2, b2)


def model_forward(x, params):
    activations = [x]
    h = x
    for w1, b1, w2, b2 in params:
        h = layer_forward(h, w1, b1, w2, b2)
        activations.append(h)
    return h, activations
```

### 第 2 步：需要全部 activation 的朴素反向

```python
def model_backward(grad_output, activations, params):
    grads = [None] * len(params)
    g = grad_output
    for i in range(len(params) - 1, -1, -1):
        w1, b1, w2, b2 = params[i]
        x_in = activations[i]
        h_pre = linear_forward(x_in, w1, b1)
        h = relu(h_pre)
        gh = g @ w2.T
        gw2 = h.T @ g
        gb2 = g.sum(axis=0)
        g_pre = gh * (h_pre > 0)
        gx = g_pre @ w1.T
        gw1 = x_in.T @ g_pre
        gb1 = g_pre.sum(axis=0)
        grads[i] = (gw1, gb1, gw2, gb2)
        g = gx
    return g, grads
```

### 第 3 步：每 k 层 checkpoint 的显存

```python
def model_forward_checkpointed(x, params, k=4):
    saved_inputs = [x]
    h = x
    for i, (w1, b1, w2, b2) in enumerate(params):
        h = layer_forward(h, w1, b1, w2, b2)
        if (i + 1) % k == 0:
            saved_inputs.append(h)
    return h, saved_inputs


def model_backward_checkpointed(grad_output, saved_inputs, params, k=4):
    grads = [None] * len(params)
    g = grad_output
    segments = [(j * k, min((j + 1) * k, len(params))) for j in range(len(saved_inputs))]
    for seg_idx in range(len(saved_inputs) - 1, -1, -1):
        start, end = segments[seg_idx]
        if start >= end:
            continue
        x_in = saved_inputs[seg_idx]
        _, seg_acts = model_forward(x_in, params[start:end])
        g, seg_grads = model_backward(g, seg_acts, params[start:end])
        for j, gr in enumerate(seg_grads):
            grads[start + j] = gr
    return g, grads
```

### 第 4 步：成本模型

```python
def checkpoint_cost(n_layers, segment_size, flops_per_layer=1.0):
    fwd = n_layers * flops_per_layer
    recompute = n_layers * flops_per_layer
    bwd = 2 * n_layers * flops_per_layer
    return {
        "fwd": fwd,
        "recompute": recompute,
        "bwd": bwd,
        "total": fwd + recompute + bwd,
        "overhead_vs_no_ckpt": (fwd + recompute + bwd) / (fwd + bwd) - 1.0,
    }


def selective_checkpoint_cost(n_layers, attention_fraction=0.15,
                              flops_per_layer=1.0):
    fwd = n_layers * flops_per_layer
    recompute = n_layers * attention_fraction * flops_per_layer
    bwd = 2 * n_layers * flops_per_layer
    return {
        "fwd": fwd,
        "recompute": recompute,
        "bwd": bwd,
        "total": fwd + recompute + bwd,
        "overhead_vs_no_ckpt": (fwd + recompute + bwd) / (fwd + bwd) - 1.0,
    }
```

### 第 5 步：显存估计器

```python
def activation_memory_mb(n_layers, hidden=8192, seq=8192,
                        batch=1, bytes_per_value=2):
    per_layer = 12 * batch * seq * hidden * bytes_per_value
    return n_layers * per_layer / 1e6


def memory_after_checkpoint(n_layers, segment_size, hidden=8192,
                           seq=8192, batch=1, bytes_per_value=2):
    n_seg = max(1, n_layers // segment_size)
    saved = (n_seg + segment_size) * 1 * batch * seq * hidden * bytes_per_value
    return saved / 1e6
```

### 第 6 步：最优分段大小

```python
def optimal_segment(n_layers):
    return int(round(np.sqrt(n_layers)))
```

### 第 7 步：选择性 checkpoint 决策

```python
def should_recompute(layer_type, activation_bytes, recompute_flops_ratio):
    if layer_type == "attention" and activation_bytes > 100 * 1e6:
        return True
    if layer_type == "ffn" and activation_bytes > 500 * 1e6:
        return recompute_flops_ratio < 0.1
    return False
```

## Use It

- **torch.utils.checkpoint**：`from torch.utils.checkpoint import checkpoint`——PyTorch 中的标准包装器。包装一个函数；只存输入，反向时重算。
- **Megatron-Core activation recomputation**：支持 `selective`、`full` 和 `block` 模式。2024 年以后前沿训练的标准做法。
- **FSDP2 offload**：在 FSDP2 中用带 `offload_policy` 的 `module.to_empty(device="cpu")` 把 activation 分片到 CPU，而不是重算。
- **DeepSpeed ZeRO-Offload**：对优化器状态和 activation 做 CPU offload，补充 checkpointing。

## Ship It

本课产出 `outputs/prompt-activation-recompute-policy.md`——一个提示词，接收你的模型配置（层数、hidden、seq、batch）与可用的 GPU 显存，输出一套逐层的重算策略（none / selective / full / offload）。

## Exercises

1. 验证正确性。运行 `model_forward` + `model_backward`（全量 activation）对比 `model_forward_checkpointed` + `model_backward_checkpointed`（分段）。参数梯度必须在机器精度上完全一致。

2. 把分段大小 `k` 从 1 扫到 `L`。画出 FLOP 开销与显存。找出曲线的拐点。

3. 实现选择性 checkpointing：保存 attention 模块的输入但不保存它的中间量。在 seq=8192 的 32 层模型上衡量相对全层 checkpointing 的 FLOP 开销。

4. 加入 offload。把分段输入保存到一个模拟的“CPU 缓冲区”（另一个列表）。把“PCIe 带宽”度量为 bytes/时间，找出 offload 与重算之间的盈亏平衡点。

5. 对一个真实的 PyTorch transformer 在有/无 `torch.utils.checkpoint` 时做基准测试。测量显存（通过 `torch.cuda.max_memory_allocated`）与步时间。

## Key Terms

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|----------------------|
| Gradient checkpointing | “靠重做前向来省显存” | 只保存分段输入；反向时重算中间量，以获得支撑梯度的张量 |
| Activation recomputation | “和 checkpointing 一样” | 同一技术的 HPC 风格叫法 |
| Segment size (k) | “每个 checkpoint 多少层” | 中间量被丢弃并一起重物化的层数 |
| Selective checkpointing | “Korthikanti 的招数” | 只重算存储昂贵的 activation（attention softmax）；保留便宜的 |
| Full checkpointing | “朴素版本” | 重算每个分段内每一层的中间量 |
| Block checkpointing | “粗粒度” | 对整个 transformer 块做 checkpoint；粒度最大 |
| FLOP overhead | “计算税” | 每步额外 FLOPs =（重算 FLOPs）/（fwd + bwd FLOPs）；朴素 33%，选择性 5% |
| Activation offload | “运到 CPU” | 在 forward->backward 之间把 activation 移到 CPU RAM；重算的替代方案 |
| sqrt-L rule | “经典最优” | 对等成本层，最优 checkpoint 间距是 sqrt(L) 层 |
| Attention-softmax volume | “那个 O(L^2) 问题” | L^2 * heads * batch 个 float；在长上下文下主导 activation 显存 |

## Further Reading

- [Chen et al., 2016 -- "Training Deep Nets with Sublinear Memory Cost"](https://arxiv.org/abs/1604.06174) —— 形式化 gradient checkpointing 的原始论文
- [Korthikanti et al., 2022 -- "Reducing Activation Recomputation in Large Transformer Models"](https://arxiv.org/abs/2205.05198) —— 选择性 activation recomputation 与形式化成本分析
- [Pudipeddi et al., 2020 -- "Training Large Neural Networks with Constant Memory using a New Execution Algorithm"](https://arxiv.org/abs/2002.05645) —— 通过反向模式重物化实现常数显存的替代路线
- [Ren et al., 2021 -- "ZeRO-Offload: Democratizing Billion-Scale Model Training"](https://arxiv.org/abs/2101.06840) —— 大规模下的 activation offload
- [PyTorch torch.utils.checkpoint docs](https://pytorch.org/docs/stable/checkpoint.html) —— 标准 API
- [Megatron Bridge activation recomputation documentation](https://docs.nvidia.com/nemo/megatron-bridge/latest/training/activation-recomputation.html) —— selective、full 与 block 模式
