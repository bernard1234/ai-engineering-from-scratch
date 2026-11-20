# 原生稀疏注意力（DeepSeek NSA）

> 在 64k 个 token 时，attention 吃掉 70-80% 的解码延迟。每个开源模型实验室都有修复它的计划。DeepSeek 的 NSA（ACL 2025 最佳论文）是真正站住脚的那个：三条并行 attention 分支——压缩后的粗粒度 token、选择性保留的细粒度 token，以及为局部上下文服务的滑动窗口——通过一个学出来的 gate 组合。它与硬件对齐（对 kernel 友好）、原生可训练（在预训练中生效，而不是推理时才外挂上去），在 64k 解码上比 FlashAttention 更快，同时质量持平或超过 full attention。本课端到端构建三条分支，并说明为什么这种稀疏性可以端到端求导。

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 7 · 12 (KV cache, flash-attention), Phase 7 · 15 (attention variants), Phase 10 · 16 (differential attention)
**Time:** ~60 分钟
## Learning Objectives

- 陈述 NSA 的三条 attention 分支，以及每条各自捕捉什么。
- 解释为什么 NSA 是“原生可训练”的，而此前的稀疏 attention 方法只能在推理阶段使用。
- 在 64k 上下文下，把 NSA 相对 full attention 的 attention 计算节省表达为压缩块大小与 selection top-k 的函数并计算。
- 用 stdlib Python 在一条短的合成序列上实现三分支组合，并验证 gate 权重的行为。

## 问题场景

在序列长度 N 上做 full attention，时间为 `O(N^2)`，每层的 KV cache 为 `O(N)`。在 64k 个 token 时，计算量和内存带宽的数字都是灾难性的。NSA 论文给出的实测理论估计：在 64k 时 attention 占全部解码延迟的 70-80%。下游的一切——TTFT、每秒 token 数、每百万 token 成本——都被 attention 成本主导。

稀疏 attention 是显而易见的答案。此前的尝试分两类。固定模式的稀疏（滑动窗口、跨步、块局部）直接扔掉信息，在长程召回任务上失败。推理时的稀疏（KV cache 剪枝、H2O、StreamingLLM）被施加在一个用稠密 attention 预训练好的模型上，只能捞回潜在加速的一小部分，因为模型从未被要求把信息路由到稀疏模式里去。

Native Sparse Attention（Yuan et al., DeepSeek + PKU + UW, ACL 2025 最佳论文, arXiv:2502.11089）两件事都做到了：一个模型在预训练期间学到的稀疏模式，实现为与 kernel 对齐的算法，在推理时真正兑现计算节省。两年之后，NSA 或其直系后裔会成为每一个前沿长上下文模型的默认 attention。

## 核心概念

### 三条并行分支

对每个 query，NSA 跑三次 attention，针对 KV cache 的三种不同视图：

1. **压缩分支。** token 被分组为大小为 `l` 的块（通常是 32 或 64）。每个块通过一个小型可学习 MLP 压缩成一个摘要 token。query 在这些压缩 token 上做 attention，得到整条序列的粗粒度视图。

2. **选择分支。** 利用压缩分支的 attention 分数，找出与当前 query 最相关的 top-k 个块。从这些块中读取细粒度（未压缩）token，query 在它们全部之上做 attention。可以把压缩分支的 attention 理解为 selection 的路由信号。

3. **滑动窗口分支。** query 对最近 `W` 个 token（通常是 512）做 attention，以获取局部上下文。这条分支捕捉另外两条可能漏掉的结构性强的短程模式（语法、局部指代）。

三条分支的输出通过一个学出来的逐位置 gate 组合：

```
out = g_cmp * out_cmp + g_sel * out_sel + g_win * out_win
```

`g_cmp, g_sel, g_win` 是 query 经过一个小 MLP 得到的 gate 权重。它们不必加和为 1——可以独立地为各分支加权。

### 为什么它是“原生可训练”的

selection 这一步（top-k 块）是离散的。离散操作会切断梯度流。此前的稀疏 attention 工作要么跳过 selection 的反向传播（限制了训练），要么使用连续松弛，在推理时拿不到真正的稀疏性。

NSA 绕开了这一点：压缩分支的 attention 本身就是整条序列上一个可微的粗粒度 attention。top-k 操作只是复用压缩分支的 top attention 分数来决定加载哪些细粒度块。梯度流经压缩分支的分数（它们既影响压缩输出，也影响 selection 逻辑），被选中块对最终输出的贡献同样是可微的。不可微的 `top_k` 操作在前向计算图上是个空操作——它只决定从内存中加载哪些块。

这就是 NSA 能端到端用于预训练的原因。模型学会联合地让信息流经三条分支，产出的稀疏模式在推理时真正兑现了承诺的加速。

### 硬件对齐的 kernel

NSA 的 kernel 为现代 GPU 内存层级而设计。kernel 按 GQA 组加载 query（外层循环），按组取出对应的稀疏 KV 块（内层循环），在 SRAM 上跑 attention。因为每个 query 组看到的是同一批被选中的块（selection 是按 query 组做的，不是按 query head），KV 加载在组内被摊销。算术强度保持在高位。

论文报告 Triton kernel 在 64k 解码上比 FlashAttention 快 9x，且加速比随序列长度增长。前向和反向 kernel 都提供了。

### 计算预算

令 `N` 为序列长度，`l` 为压缩块大小，`k` 为 top-k 选择的数量，`w` 为滑动窗口，`b` 为被选中块的大小（通常等于 `l`）。

- 压缩分支：每个 query `O(N/l)` 个 key，所以总计 `O(N * N / l)`。
- 选择分支：每个 query `O(k * b)` 个 key，所以 `O(N * k * b)`。
- 滑动分支：每个 query `O(w)` 个 key，所以 `O(N * w)`。

合计：`O(N * (N/l + k*b + w))`。

在 `N = 64k, l = 64, k = 16, b = 64, w = 512` 时：每个 query 的成本是 `1000 + 1024 + 512 = 2536 keys`。full attention 是 `64000 keys`。计算量减少 25x。

在 `N = 128k, l = 64, k = 16, b = 64, w = 512` 时：每个 query 的成本是 `2000 + 1024 + 512 = 3536 keys`。full attention 是 `128000 keys`。减少 36x。收益随序列长度增长，这正是关键所在。

### 对比如何

| 方法 | 可微 | 真实的推理加速 | 长程召回 |
|--------|---------------|----------------------|-------------------|
| 仅滑动窗口 | 是 | 是 | 失败 |
| 跨步 / 块稀疏 | 是 | 是 | 部分 |
| KV 剪枝（H2O、StreamingLLM） | N/A（推理时） | 是 | 部分 |
| MoBA (Moonshot) | 部分 | 是 | 好 |
| NSA | 是（原生） | 是（64k 下 9x） | 匹配 full attention |

MoBA（Moonshot, arXiv:2502.13189）同期发表，采用了类似的“三个胜过一”的思路，把 MoE 的原则应用到 attention 块上。NSA 和 MoBA 是 2026 年长上下文预训练必须知道的两种架构。

```figure
sliding-window-attention
```

## Build It

`code/main.py` 在一条短的合成序列上实现三条分支，并展示：

- 压缩 MLP（为了教学清晰使用了简单的 mean-pool 基线；真实的 NSA 使用可学习 MLP）。
- 由压缩分支分数驱动的 top-k 块选择。
- 最后 `w` 个 token 上的滑动窗口 attention。
- 带 gate 的组合。
- 与 full attention 对比的计算计数打印输出。

### 第 1 步：把 token 压缩成块

```python
def compress(K, l):
    n = len(K)
    n_blocks = (n + l - 1) // l
    out = []
    for b in range(n_blocks):
        start, end = b * l, min((b + 1) * l, n)
        block = K[start:end]
        summary = [sum(row[d] for row in block) / len(block) for d in range(len(K[0]))]
        out.append(summary)
    return out
```

### 第 2 步：压缩分支的 attention

让 query 对压缩后的 key 跑 softmax attention。压缩分支的分数同时充当 top-k 选择的信号。

### 第 3 步：top-k 块选择

选出得分最高的 `k` 个压缩块的索引。从这些块中加载原始的未压缩 token，并在它们之上跑 attention。

### 第 4 步：滑动窗口 attention

取最后 `w` 个 token，对它们跑标准 attention。

### 第 5 步：gate + 组合

query 经过一个小 MLP 产出三个 gate 权重。最终输出是三条分支输出的加权和。

### 第 6 步：计算计数

为每条分支打印每个 query 参与的 key 数量，以及总数。与 `N`（full attention）对比。在一条 1024 token 的合成序列上，`l = 32, k = 4, w = 128` 时，NSA 每个 query 看到 `32 + 128 + 128 = 288` 个 key，而 full attention 是 1024 个——少 3.5x。

## Use It

NSA 已在 DeepSeek 自己的长上下文预训练流水线中出货。截至 2026 年 4 月，公开推理栈的集成状况：

- **DeepSeek 内部**：原生支持，公开权重使用 NSA 或其继任者 DSA（Deepseek Sparse Attention）。
- **vLLM**：针对 DeepSeek-V3.x 权重的实验性 NSA 支持在开发中。
- **SGLang**：NSA benchmark 已发布；生产路径跟随 vLLM。
- **llama.cpp / CPU**：不支持；在 CPU 吞吐下，kernel 分解的开销不划算。

什么时候该用 NSA：

- 瞄准 64k 以上上下文、且有可观计算预算的预训练或持续训练任务。
- 推理 DeepSeek 自己的长上下文 checkpoint。这些权重是 NSA 原生的。

什么时候不用：

- 服务一个已有的稠密 attention 预训练模型。不做持续训练就无法把 NSA 改装上去。
- 上下文在 16k 以下。三分支的开销压过了节省。
- batch-1 的交互式聊天。对延迟敏感的解码能受益，但只在长上下文下才成立。

## Ship It

本课产出 `outputs/skill-nsa-integrator.md`。给定一次长上下文预训练任务的规格，它产出 NSA 集成方案：压缩块大小、top-k、滑动窗口、gate MLP 宽度、kernel 选型，以及能够证明这次架构改动合理性的具体长上下文评估项。

## Exercises

1. 在一条 1024 token 的合成序列上运行 `code/main.py`。在三种预设下扫描 `(l, k, w)` 并打印计算计数。找出在 needle-in-haystack 测试中对 full attention 保持 95% 召回的同时、每个 query key 数最低的预设。

2. 把 mean-pool 压缩器换成一个小的可学习 MLP（2 层，hidden 32）。在一个信号为块平均值的合成任务上训练它。在留出数据上测量它与 mean-pool 基线的 perplexity 差距。

3. 实现 gate MLP。它以 query 为输入，输出三个标量。说明 gate 行为合理：在随机 query 上权重接近均匀，当 query 命中一个靠后的块时，被选择的分支获得大权重。

4. 计算一个启用 NSA 的 70B 模型在 128k 上下文下的 KV cache 内存预算。KV head 为 8，head dim 为 128，BF16。与 full attention 以及 MLA 对比（Phase 10 · 14 给出了 MLA 的数字）。找出 NSA 的细粒度分支 KV cache 等于 full attention 的那个序列长度。

5. 读 NSA 论文（arXiv:2502.11089）的第 4 节，用三句话解释为什么复用压缩分支的 attention 分数做 top-k 选择，而不是另算一个路由分数。把答案与梯度流联系起来。

## Key Terms

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| Compressed branch | “粗粒度视图” | 在块平均后的 key 上做 attention，以每个 query O(N/l) 个 key 提供全局上下文 |
| Selected branch | “top-k 块” | 在压缩分支分数最高的 `k` 个块上做细粒度 attention |
| Sliding window | “局部上下文” | 在最近 `W` 个 token 上做 attention，用于短程模式 |
| Native trainability | “带着稀疏性预训练” | 稀疏模式在预训练期间学到，而不是在推理时外挂 |
| Compression block size l | “粗粒度视图的分组大小” | 有多少 token 被合并成一个摘要；典型为 32-64 |
| Top-k | “保留多少块” | 有多少个压缩块的未压缩 token 会被读取；典型为 16 |
| Sliding window W | “局部 attention 半径” | 通常为 512；更短会损害局部连贯性，更长则浪费计算 |
| Branch gate | “三条怎么混合” | 逐位置的 MLP 输出，为三条分支的贡献加权 |
| Hardware alignment | “对 kernel 友好的稀疏性” | 选择一种稀疏模式，使真实的 GPU kernel 能达到理论加速 |
| DSA | “NSA 的继任者” | Deepseek Sparse Attention，DeepSeek 谱系中继 NSA 之后的架构 |

## Further Reading

- [Yuan et al. — Native Sparse Attention: Hardware-Aligned and Natively Trainable Sparse Attention (arXiv:2502.11089, ACL 2025 Best Paper)](https://arxiv.org/abs/2502.11089) -- 论文本身
- [DeepSeek-V3 Technical Report (arXiv:2412.19437)](https://arxiv.org/abs/2412.19437) -- NSA 所针对的架构家族
- [Moonshot AI — MoBA: Mixture of Block Attention for Long-Context LLMs (arXiv:2502.13189)](https://arxiv.org/abs/2502.13189) -- 同期工作，MoE 风格的块级 attention
- [Beltagy et al. — Longformer: The Long-Document Transformer (arXiv:2004.05150)](https://arxiv.org/abs/2004.05150) -- 滑动窗口的源头
- [Xiao et al. — StreamingLLM: Efficient Streaming Language Models with Attention Sinks (arXiv:2309.17453)](https://arxiv.org/abs/2309.17453) -- NSA 所改进的推理时稀疏基线
- [Dao et al. — FlashAttention-2 (arXiv:2307.08691)](https://arxiv.org/abs/2307.08691) -- NSA 的 kernel 在 64k 下所击败的 full attention 基线
