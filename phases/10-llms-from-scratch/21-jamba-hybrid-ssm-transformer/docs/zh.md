# Jamba —— 混合 SSM-Transformer

> 状态空间模型（SSM）和 transformer 想要的东西不一样。Transformer 以二次方的代价通过 attention 换来质量。SSM 通过一个递归换来线性时间推理与常数显存，但质量落后。AI21 的 Jamba（2024 年 3 月）和 Jamba 1.5（2024 年 8 月）把它们放进同一个模型：每 7 个 Mamba 层配 1 个 Transformer 层，每隔一个块启用 MoE，还有一个能在单张 80GB GPU 上装下的 256k 上下文窗口。Mamba-3（ICLR 2026）用复值状态空间和 MIMO 投影把 SSM 这一侧又收紧了一步。本课从头到尾通读这两套架构，并解释为什么这种混合配方在纯 SSM 与纯 Transformer 的长上下文尝试都失败的情况下，依然挺过了三年的规模化考验。

**Type:** Learn
**Languages:** Python (stdlib, layer-mix calculator)
**Prerequisites:** Phase 10 · 14 (open-model architectures), Phase 10 · 17 (native sparse attention)
**Time:** ~60 分钟

## Learning Objectives

- 解释 Jamba 块中的三个原语——Transformer 层、Mamba 层、MoE——以及 1:7:隔层交错这套配方。
- 在高层次上说出 SSM 的递归长什么样，以及它为什么能实现常数显存推理。
- 计算 Jamba 模型在 256k 上下文下的 KV cache 占用，并与纯 Transformer 模型所需的做比较。
- 说出 Mamba-3 的三项创新（指数-梯形离散化、复值状态更新、MIMO）以及每一项针对的问题。

## 问题场景

Attention 对序列长度是二次方的。状态空间模型是线性的。这种差异会累积：在 256k token 时，一个 Transformer 的 attention map 每个 head 有 65B 个条目；而一个 SSM 的递归状态无论序列多长都是固定大小。

纯 SSM 模型（Mamba、Mamba-2）在小规模上能匹配 Transformer 的 perplexity，但在状态跟踪任务上落后，并且在某些类别的上下文内检索上会失败。直觉是：SSM 把历史压缩进一个固定状态，当历史很长时，信息会泄漏。Attention 精确记住一切，但要付出二次方代价。

显而易见的修法：两个都用。把 Transformer 层放在精确召回重要的地方。其他地方用 SSM 层。调整比例。Jamba 是第一个大规模交付这套混合配方的生产级模型（总量 52B，激活 12B，256k 上下文，单张 80GB GPU）。Jamba 1.5 把这个家族扩展到总量 398B / 激活 94B。Mamba-3（ICLR 2026）是当前最好的纯 SSM 基线，混合模型可以围绕它重建。

本课通读这三篇论文，并给出“挑对比例”的心智模型。

## 核心概念

### 一页说清 SSM

状态空间模型通过一个固定大小的状态 `h` 处理序列 `x_1, ..., x_N`：

```
h_t = A h_{t-1} + B x_t
y_t = C h_t
```

每一步，状态通过线性动力学 `A` 演化，接收输入 `B x_t`，并输出 `C h_t`。`A, B, C` 都是可学习的。注意这个关键性质：计算 `y_t` 只需要 `h_{t-1}` 和 `x_t`，不需要任何更早的 `x`。显存是常数。推理时每个 token 是 O(1)。

建模质量的关键在于 `A` 的结构。S4（Gu 2021）使用一个高度结构化的矩阵，训练时可以高效地当作长卷积求值。Mamba（Gu, Dao 2023）把固定的 `A, B, C` 换成数据相关的（这就是“选择性”部分）。Mamba-2（2024）进一步简化了结构。Mamba-3（2026）在特定位置重新加回了复杂度。

关键性质：对于一个 decoder LLM，SSM 层是 attention 层的即插即用替代品，用固定大小的逐层状态取代不断增长的 KV cache。

### Jamba 块

一个 Jamba 块按照两个数字交错排列各层：

- `l`：attention 与 Mamba 的比例。Jamba 用 `l = 8`，意思是每 7 个 Mamba 层配 1 个 Transformer 层（7 个 Mamba + 1 个 Attention = 每组 8 层）。
- `e`：MoE 频率。Jamba 用 `e = 2`，意思是每隔一层应用 MoE。

一个块内的层序列：

```
M  M  M  M  M  M  M  A    (7 Mamba + 1 Attention)
|  M  |  M  |  M  |  M    (where | marks MoE applied)
```

每个 Jamba 块是 8 层。在 4 个块深（总共 32 层）时，你得到 28 个 Mamba 层和 4 个 Attention 层。其中 16 层使用 MoE。

### 为什么是 1:7 的比例

AI21 做了消融实验：在他们长上下文评测上，什么样的 attention 与 Mamba 比例能给出最佳的“每参数量 perplexity”以及上下文内召回？

- attention 太多（1:1）：质量上升，但显存和速度退化。
- attention 太少（1:15）：显存很棒，但上下文内检索失败。
- 甜点区：1:7 或 1:8。

直觉是：Transformer 层负责精确召回和状态跟踪。Mamba 层负责廉价的批量处理。

### 位置编码

Mamba 层本身（通过递归）就是位置感知的。在早期基于 Mamba 的混合模型中，attention 层不使用 RoPE——位置信息由 SSM 层提供。Jamba 1.5 为 attention 层加上了 RoPE，以获得更长上下文的泛化能力，这是基于经验性长上下文评测的事后改进。

### 显存预算

对于一个 Jamba-1 形状（32 层：28 个 Mamba + 4 个 Attention，hidden 4096，32 个 attention head）：

- KV cache（仅 attention 层）：256k BF16 下 `2 * 4 * 32 * 128 * 256k * 2 = 8.4 GB`。只有那 4 个 attention 层有贡献。
- SSM 状态：每 token 前缀 `28 * hidden * state_size`，但这是每层的固定大小，不随序列长度缩放。典型 Mamba 状态是每个特征 16，hidden 4096：合计 `28 * 4096 * 16 * 2 = 3.7 MB`。

与 32 层、相同 hidden、32 个 head 全 MHA 的纯 Transformer 相比：256k BF16 下 `2 * 32 * 32 * 128 * 256k * 2 = 128 GB`。KV cache 缩减 8 倍。即使与大多数 2024 年模型使用的 GQA(8) 基线（`2 * 32 * 8 * 128 * 256k * 2 = 32 GB`）相比，Jamba 的 1:7 混合在 16 GB 下仍然小 2 倍。

这就是 AI21 所说的“单张 80GB GPU 上的 256k 上下文”。全 MHA 纯 Transformer 的 KV cache 根本装不下；即使 GQA 基线也留不出空间给权重和 activation；Jamba 可以。

### Mamba-3：2026 年的纯 SSM 基线

Mamba-3（ICLR 2026，arXiv:2603.15569）在纯 SSM 这一侧引入了三项创新：

1. **指数-梯形离散化。** 用更有表达力的递归取代 Mamba-2 中的欧拉法离散化。卷积式操作施加在核心递归内部的状态-输入上，而不是作为 `x_t` 上的外层卷积。

2. **复值状态更新。** 以往的 Mamba 把状态矩阵从复数（S4）简化为实对角（Mamba），再简化为缩放单位阵（Mamba-2）。Mamba-3 重新加回复值——等价于对状态施加数据相关的旋转嵌入。这恢复了此前实值简化所损失的状态跟踪能力。

3. **多输入多输出（MIMO）投影。** 不用逐特征的标量投影，而用矩阵值投影。提升了建模能力与推理时的硬件利用率，同时不增加 decode 延迟。

在 1.5B 参数下，Mamba-3 相对 Gated DeltaNet 将下游平均准确率提升 0.6 个点；MIMO 变体再增加 1.2，合计提升 1.8 个点。在相同状态大小下，Mamba-3 用一半的状态就能匹配 Mamba-2。

Mamba-3 尚未在大规模生产级混合模型中交付——但它是下一代 Jamba 级模型 SSM 侧的明显候选。

### 何时应当选择混合架构

混合架构胜出的场景：

- 上下文长到纯 Transformer 的 KV cache 变得痛苦（64k+）。
- 任务混合了短程结构（适合 SSM）与长程召回（需要 Transformer）。
- 你想部署在单 GPU 显存预算内，而仅 Transformer 的 KV cache 就装不下。

混合架构落败的场景：

- 上下文很短（16k 以下）。SSM 的开销被浪费；纯 Transformer 就够了。
- 任务需要处处对处处的 attention（深度推理、多文档交叉引用）。混合模型中 attention 层的稀疏性会造成损害。
- 你要扩展到万亿参数的前沿模型。纯 Transformer + MLA + MoE（DeepSeek-V3 风格）目前正在能力竞赛中领先。

### 竞争格局

| 模型 | 家族 | 规模 | 独特主张 |
|-------|--------|------|-------------|
| Mamba-2 | 纯 SSM | 3B | 线性时间，常数显存 |
| Jamba | 混合 | 52B/12B | 80GB 上跑 256k |
| Jamba 1.5 Large | 混合 | 398B/94B | 企业级长上下文 |
| Mamba-3 | 纯 SSM | 1.5B（论文） | 状态跟踪能力恢复 |
| DeepSeek-V3 | 纯 Transformer + MoE | 671B/37B | 前沿能力 |

2026 年的格局：纯 Transformer MoE 主导前沿，但混合架构占据 256k 以上的上下文利基。Mamba-3 在状态跟踪上的胜利，可能推动下一代的混合比例变低（更多 SSM，更少 attention）。

```figure
swiglu-ffn
```

## Use It

`code/main.py` 是一个混合架构的显存计算器。给定一个 SSM-Transformer 比例以及 hidden-size / 层数配置，它计算：

- 目标上下文下的 KV cache。
- SSM 状态显存。
- 一系列模型形状在上下文 N 下的总显存。

计算器支持：

- 纯 Transformer 基线（KV cache 随 N 增长）。
- Jamba 风格的 1:7 混合。
- 纯 SSM（完全没有 KV cache）。

对已发布的形状，数字直接来自 Jamba-1 和 Jamba-1.5 论文；对假想变体则是外推。

真实部署的集成考虑：

- 大多数生产推理服务器（vLLM、SGLang）支持 Jamba 和 Mamba。请核对具体版本。
- 在 256k 上下文下，Jamba 的显存优势体现在并发请求吞吐上。同样的 VRAM 里，你装下的 Jamba 序列比 Transformer 序列更多。
- Mamba-3 作为独立模型尚未在生产中交付——目前是 1.5B 的研究预览。

## Ship It

本课产出 `outputs/skill-hybrid-picker.md`。给定一份工作负载规格（上下文长度画像、任务组合、显存预算），它在纯 Transformer、Jamba 风格混合以及纯 SSM 之间给出推荐，并明确论证显存与质量的权衡。

## Exercises

1. 运行 `code/main.py`，计算 32 层纯 Transformer（hidden 4096，32 个 head）和相同形状的 Jamba-1 混合在 256k 上下文下的 KV cache。验证 AI21 论文声称的约 8 倍显存缩减。

2. 修改计算器，为 1:3 混合（4 个 Mamba : 1 个 Attention）和 1:15 混合（14 个 Mamba : 1 个 Attention）建模。画出 KV cache 随比例变化的曲线。在什么比例下 KV cache 等于 SSM 状态显存？

3. 阅读 Jamba 论文（arXiv:2403.19887）的 Section 3。解释为什么 AI21 使用 Mamba-1 而不是更快的 Mamba-2。提示：混合消融那一节记录了这一点。

4. 计算 Jamba 1.5 Large（总量 398B，激活 94B）中“每隔一层 MoE”带来的参数开销。把激活比例与 DeepSeek-V3（37B/671B）对比，并解释为什么 Jamba 的架构会推高激活比例。

5. 阅读 Mamba-3 论文（arXiv:2603.15569）的 Section 3。用三句话解释为什么复值状态更新等价于数据相关的旋转嵌入。把答案与 Phase 7 · 第 04 课的 RoPE 推导联系起来。

## Key Terms

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| State space model (SSM) | “带固定状态的递归” | 一个具有可学习递归 `h_t = A h_{t-1} + B x_t` 的层；每 token 显存为常数 |
| Selective SSM | “Mamba 的招数” | 数据相关的 A、B、C 参数，在线性时间下给模型类似门控的选择性 |
| Attention-to-Mamba ratio | “有多少 attention 层” | 在 Jamba 中，`l = 8` 表示每 7 个 Mamba 层配 1 个 attention 层 |
| Jamba block | “那个 8 层组” | 一个 attention + 七个 Mamba + 在交替位置上的 MoE |
| SSM state | “隐藏缓冲区” | 固定大小的逐层状态，在 Mamba 层取代 KV cache |
| 256k context | “Jamba 的招牌数字” | Jamba-1 能在单张 80GB GPU 上装下的序列长度；纯 Transformer 在该尺寸下做不到 |
| Mamba-3 | “2026 年的纯 SSM” | 当前最好的纯 SSM 架构，带复值状态 + MIMO；混合模型围绕它重建 |
| MIMO | “多输入多输出” | Mamba-3 的创新，用矩阵值投影取代逐特征标量 |
| Exponential-trapezoidal discretization | “Mamba-3 的递归” | 更有表达力的递归，涵盖了 Mamba-2 的欧拉法离散化 |
| Hybrid architecture | “混合 attention 与 SSM” | 任何交错 Transformer 层与 SSM 层的模型；Jamba 是生产级的原型 |

## Further Reading

- [Lieber et al. — Jamba: A Hybrid Transformer-Mamba Language Model (arXiv:2403.19887)](https://arxiv.org/abs/2403.19887) —— 原始的 Jamba 论文、比例消融、256k 上下文主张
- [AI21 — Jamba 1.5: Hybrid Transformer-Mamba at Scale (arXiv:2408.12570)](https://arxiv.org/abs/2408.12570) —— 扩展后的家族，398B/94B 与 12B/52B 的公开版本
- [Gu, Dao — Mamba: Linear-Time Sequence Modeling with Selective State Spaces (arXiv:2312.00752)](https://arxiv.org/abs/2312.00752) —— Jamba 所构建其上的选择性 SSM 论文
- [Dao, Gu — Mamba-2 (arXiv:2405.21060)](https://arxiv.org/abs/2405.21060) —— 简化后的结构化状态空间后继
- [Lahoti et al. — Mamba-3 (arXiv:2603.15569, ICLR 2026)](https://arxiv.org/abs/2603.15569) —— 复值状态、MIMO、2026 年的纯 SSM 前沿
- [Gu et al. — Efficiently Modeling Long Sequences with Structured State Spaces (arXiv:2111.00396)](https://arxiv.org/abs/2111.00396) —— S4 论文，SSM 谱系进入 LLM 领域的起点
