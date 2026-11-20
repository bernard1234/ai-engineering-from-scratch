# Flamingo 与面向 few-shot VLM 的门控 cross-attention

> DeepMind 的 Flamingo（2022）做了两件前人都没做过的事。它证明单个模型可以处理任意交错的图像、视频与文本序列。它还证明 VLM 可以 in-context 学习——给出含三个 (image, caption) 样例的 few-shot prompt，模型无需任何梯度步就能为新图像生成描述。机制是门控 cross-attention 层：插在冻结 LLM 既有层之间，配一个可学习的 tanh 门，初值为零，从而在初始化时保住 LLM 的文本能力。本课走一遍 Flamingo 的 Perceiver resampler 与门控 cross-attention 架构——它是 Gemini 交错输入与 Idefics2 视觉 token 的祖先。

**Type:** Learn
**Languages:** Python（标准库，门控 cross-attention + Perceiver resampler 演示）
**Prerequisites:** Phase 12 · 03（BLIP-2 Q-Former）
**Time:** ~120 分钟

## Learning Objectives

- 解释门控 cross-attention 如何借助 tanh(gate) = 0 在初始化时保住冻结 LLM 的文本能力。
- 梳理 Perceiver resampler：N 个图像 patch → 通过 cross-attention 得到 K 个固定的 "latent" query。
- 描述 Flamingo 如何处理图像-文本交错序列，其因果掩码尊重图像所在位置。
- 复现 few-shot 多模态 prompt 结构（3 个图像-描述样例，再接一个待查询图像）。

## 问题场景

BLIP-2 把 32 个视觉 token 送入冻结 LLM 的输入层。每个 prompt 一张图时可行。但如果你想喂入大量图像并与文本交错，比如 "这是图 A，描述它；这是图 B，描述它；现在这是图 C，描述它"，该怎么办？LLM 的 self-attention 需要在单一流里处理图像 token 与文本 token，而哪些位置能关注哪些图像这个问题会变得很麻烦。

Flamingo 的答案：完全不改 LLM 的输入流。在既有 LLM 块之间插入额外的 cross-attention 层。文本 token 仍照旧流过 LLM 的因果 self-attention。每隔几个 LLM 块，文本 token 还会通过一个新的门控层对图像特征做 cross-attention。门初值为零，这意味着第 0 步时新层是空操作——模型行为与预训练 LLM 完全一致。随着训练推进，门逐渐打开，视觉信息开始流入。

Flamingo 回答的第二个问题：如何处理每个 prompt 中数量可变的图像（0 张、1 张或多张）？Perceiver resampler——一个小型 cross-attention 模块，不管你手上有多少 patch，都产出固定数量的视觉 latent token。无论 prompt 中有几张图，LLM 的 cross-attention 层看到的形状都一样。

## 核心概念

### 冻结的 LLM

Flamingo 从一个冻结的 Chinchilla 70B LLM 起步。全部 70B 权重原封不动。既有的文本 self-attention 与 FFN 照常工作。

### Perceiver resampler

对 prompt 中的每张图，ViT 产生 N 个 patch token。Perceiver resampler 拥有 K 个固定的可学习 latent（Flamingo 使用 K=64）。每个 resampler 块包含两个子步骤：

1. Cross-attention：K 个 latent 对 N 个 patch token 做注意力（Q 来自 latent，K/V 来自 patch）。
2. latent 内部的 self-attention + FFN。

经过 6 个 resampler 块后，输出是 K=64 个维度为 1024 的视觉 token，无论 ViT 产生了多少 patch。224x224 的图像（196 个 patch）与 480x480 的图像（900 个 patch）都输出 64 个 resampler token。

对视频而言，resampler 沿时间维度应用：每帧的 patch 产出 64 个 latent，时间位置编码让模型能区分 t=0 与 t=N。整段视频就成为 T * 64 个视觉 token。

### 门控 cross-attention

在冻结 LLM 每 M 层之间（Flamingo 使用 M=4），插入一个新的门控 cross-attention 块：

```
x_after_llm_block = llm_block(x_before)
cross = cross_attn(x_after, resampler_output)
gated = tanh(alpha) * cross + x_after
x_before_next_block = gated
```

- `alpha` 是可学习标量，初始化为零。
- `tanh(0) = 0`，所以初始化时门控分支的贡献为零。
- 当 `alpha` 远离零，cross-attention 的贡献平滑增长。
- 残差连接意味着即使门完全打开，也不会覆盖 LLM 的文本表征；它只是在上面叠加视觉信息。

这是 Flamingo 最重要的一个设计选择：视觉条件化是加性的、门控的，且初始化时为零。第 0 步的 Flamingo 在纯文本输入上就是一个完美的 Chinchilla 70B。

### 面向交错输入的掩码 cross-attention

在形如 "<image A> caption A <image B> caption B <image C> ?" 的 prompt 中，每个文本 token 只应看到在序列中先于它出现的图像。cross-attention 掩码强制：位于位置 `t` 的文本 token 只关注图像索引 `i < i_t` 的 resampler token，其中 `i_t` 是位置 `t` 之前最近的那张图。"只看最近一张前置图像" 与 "看所有前置图像" 都是有效选择；Flamingo 选了前者。

### In-context few-shot 学习

一个 Flamingo prompt 形如：

```
<image1> A photo of a cat. <image2> A photo of a dog. <image3> A photo of a
```

模型看到这个补全模式并输出 "bird"（或 image3 实际所示之物）。没有梯度步。冻结 LLM 的 in-context 学习能力通过门控 cross-attention 得以延续——这是论文的点睛之笔，也是它重要的原因。

### 训练数据

Flamingo 在三个数据集上训练：

1. MultiModal MassiveWeb (M3W)：43M 个含交错图像与文本的网页，按阅读顺序重建。
2. Image-Text Pairs (ALIGN + LTIP)：4.4B 对。
3. Video-Text Pairs (VTP)：27M 段短视频。

OBELICS（2023）是交错网页语料的开放复现，Idefics、Idefics2 以及大多数开放的 "类 Flamingo" 模型都在它上面训练。

### OpenFlamingo 与 Otter

OpenFlamingo（2023）是开放复现。架构完全一致（Perceiver resampler + 在冻结 LLaMA 或 MPT 上的门控 cross-attention）。checkpoint 有 3B、4B、9B。质量落后于 Flamingo，因为基座 LLM 更小、数据更少。

Otter（2023）在 OpenFlamingo 之上用 MIMIC-IT（一个多模态指令数据集）做指令微调，表明门控 cross-attention 对指令跟随同样有效。

### 后裔

- Idefics / Idefics2 / Idefics3：Hugging Face 的门控 cross-attention 谱系，逐步简化（Idefics2 放弃了 resampler，改用直接 patch token 加 adaptive pooling）。
- 从 Flamingo 到 Chameleon 的转向：到 2024 年许多团队转向 early-fusion（第 12.11 课）；在必须冻结骨干网络的场合，Flamingo 式门控 cross-attention 仍在生产中使用。
- Gemini 的交错输入：概念上继承了 Flamingo 的交错格式灵活性，尽管具体机制是专有的。

### 与 BLIP-2 的对比

| | BLIP-2 | Flamingo |
|---|---|---|
| 视觉桥 | 输入端一次 Q-Former | 每 M 层插一个门控 cross-attention |
| 视觉 token | 每图 32 个 | 每个 cross-attn 层每图 64 个 |
| 冻结 LLM | 是 | 是 |
| Few-shot in-context | 弱 | 强——论文的核心亮点 |
| 交错输入 | 无原生支持 | 支持，正是设计目标 |
| 训练数据 | 130M 对 | 1.3B 对 + 43M 交错网页 |
| 参数量 | 训练 188M | 训练约 10B（cross-attn 层） |
| 算力 | 8 卡 A100 数天 | 数千 TPUv4 数周 |

预算有限、只做单图 VQA 时选 BLIP-2。需要交错输入、few-shot 或多图推理时选 Flamingo/Idefics2。

```figure
cross-attention-fusion
```

## Use It

`code/main.py` 演示：

1. 在 36 个伪造 patch token 上用 8 个可学习 latent 运行的 Perceiver resampler（纯 Python cross-attention）。
2. 一次门控 cross-attention 步骤：`alpha = 0` → 输出等于输入（LLM 不变），然后 `alpha = 2.0` → 视觉贡献被混入。
3. 一个交错掩码构造器，为 "(image 1) (text 1) (image 2) (text 2)" 序列生成 2D attention mask。

## Ship It

本课产出 `outputs/skill-gated-bridge-diagnostic.md`。给定一个开放 VLM 的配置（有无 resampler、cross-attn 频率、门控方案），它能识别出属于 Flamingo 谱系的要素，并解释其冻结策略。在排查 "微调后文本性能为何下降" 时很有用（答案：门开得太宽太快）。

## Exercises

1. 计算 Flamingo-9B 的视觉参数量：9B LLM + 1.4B 门控 cross-attention 层 + 64M resampler。训练部分占总参数的多少比例？

2. 用 PyTorch 实现门控残差 `y = tanh(alpha) * cross + x`。用实验表明在 `alpha=0` 时初始化阶段 `y==x` 严格成立。

3. 阅读 OpenFlamingo 第 3.2 节（arXiv:2308.01390）关于一个 batch 中各 prompt 图像数量不同时的处理方式。描述其 padding 策略。

4. 为什么 Flamingo 的 cross-attention 掩码让文本 token 只关注*最近一张*前置图像，而不是所有前置图像？阅读 Flamingo 论文第 2.4 节并解释这一权衡。

5. In-context few-shot：为一个新的 Flamingo 变体构造包含 4 个 "图像 → 主体物体颜色" 样例的 prompt。描述当样例数从 0 增加到 8 时，预期的准确率变化模式。

## Key Terms

| Term | What people say | What it actually means |
|------|----------------|------------------------|
| Perceiver resampler | "固定 latent 的 cross-attention" | 从可变数量的输入 patch 中产出 K 个固定 token 的模块 |
| Gated cross-attention | "Tanh 门控桥" | 残差层 `y = tanh(alpha)*cross + x`，alpha 可学习，初值为 0 |
| Interleaved input | "混合序列" | 图像与文本按阅读顺序自由混排的 prompt 格式 |
| Frozen LLM | "LLM 无梯度" | 文本 LLM 的权重不更新；只有 resampler 与 cross-attn 层参与训练 |
| Few-shot | "In-context 样例" | 在 prompt 中给出若干 (image, answer) 样例；模型不用微调就能泛化 |
| OBELICS | "交错网页语料" | 141M 个按阅读顺序排列图文网页的开放数据集 |
| Chinchilla | "70B 冻结基座" | Flamingo 使用的冻结文本 LLM，来自 DeepMind 的 Chinchilla 论文 |
| Gate schedule | "alpha 如何移动" | 训练中 cross-attention 门打开的速度 |
| Cross-attn frequency | "每 M 层" | 门控 cross-attention 块插入的间隔；Flamingo 使用 M=4 |
| OpenFlamingo | "开放复现" | MosaicML/LAION 的开放 checkpoint，3-9B，架构与 Flamingo 一致 |

## Further Reading

- [Alayrac et al. — Flamingo (arXiv:2204.14198)](https://arxiv.org/abs/2204.14198) — 原始论文。
- [Awadalla et al. — OpenFlamingo (arXiv:2308.01390)](https://arxiv.org/abs/2308.01390) — 开放复现。
- [Laurençon et al. — OBELICS (arXiv:2306.16527)](https://arxiv.org/abs/2306.16527) — 交错网页语料。
- [Jaegle et al. — Perceiver IO (arXiv:2107.14795)](https://arxiv.org/abs/2107.14795) — 通用 Perceiver 架构。
- [Li et al. — Otter (arXiv:2305.03726)](https://arxiv.org/abs/2305.03726) — 指令微调的 Flamingo 后裔。
- [Laurençon et al. — Idefics2 (arXiv:2405.02246)](https://arxiv.org/abs/2405.02246) — Flamingo 路线的现代简化版。
