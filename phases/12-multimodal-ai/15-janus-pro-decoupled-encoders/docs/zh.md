# Janus-Pro：面向统一多模态模型的解耦编码器

> 统一多模态模型存在一个无法回避的矛盾。理解任务想要语义特征——SigLIP 或 DINOv2 输出的、富含概念级信息的向量。生成任务想要利于重建的编码——能够重新组合成清晰像素的 VQ token。这两个目标在单个编码器中并不兼容。Janus（DeepSeek，2024 年 10 月）与 Janus-Pro（DeepSeek，2025 年 1 月）主张，解法就是不再强求统一：把两个编码器解耦。在任务之间共享 transformer 主体，但让理解走 SigLIP、生成走 VQ tokenizer。在 7B 规模下，Janus-Pro 在 GenEval 上超过 DALL-E 3，同时在 MMMU 上与 LLaVA 持平。本节课解读为什么两个编码器能做到一个编码器做不到的事。

**Type:** Build
**Languages:** Python（标准库，双编码器路由 + 共享主体信号）
**Prerequisites:** Phase 12 · 13（Transfusion）、Phase 12 · 14（Show-o）
**Time:** ~120 分钟

## Learning Objectives

- 解释为什么单一共享编码器会牺牲理解质量或生成质量。
- 描述 Janus-Pro 的路由方式：理解侧输入端使用 SigLIP 特征，生成侧在输入与输出两端都使用 VQ token。
- 梳理让 Janus-Pro 在 Janus 失败之处取得成功的数据配比扩展。
- 比较解耦式（Janus-Pro）、耦合连续式（Transfusion）与耦合离散式（Show-o）三种架构。

## 问题场景

统一模型在理解与生成之间共享一个 transformer 主体。此前的尝试（Chameleon、Show-o、Transfusion）在两个方向上使用同一个视觉 tokenizer。这个 tokenizer 本身就是妥协的产物：

- 为重建（生成）优化：VQ-VAE 能捕捉细粒度像素细节，但产出的 token 语义连贯性很弱。
- 为语义（理解）优化：SigLIP embedding 会把"猫"的图像聚集在"猫"token 附近，但不允许良好的重建。

Show-o 和 Transfusion 为此在某个方向上付出了肉眼可见的质量代价。Janus-Pro 提出一个问题：既然两个任务需求不同，为什么要强制只用一个 tokenizer？

## 核心概念

### 解耦的视觉编码

Janus-Pro 的架构把两个编码器分开：

- 理解路径。输入图像 → SigLIP-SO400m → 2 层 MLP → transformer 主体。
- 生成路径。输入图像（如果要以已有图像为条件）→ VQ tokenizer → token ID → transformer 主体。
- 输出生成。由 transformer 预测的图像 token → VQ 解码器 → 像素。

transformer 主体是共享的。主体上游与下游的一切都是任务专属的。

输入通过 prompt 格式来区分：`<understand>` 标签走 SigLIP；`<generate>` 标签走 VQ。或者路由直接由任务隐式决定。

### 为什么这样可行

理解损失拿到的是 SigLIP 特征，而 CLIP 式预训练正是为语义相似度调校过这类特征。模型在感知类 benchmark 上优于 Show-o / Transfusion，因为输入特征更适合这项任务。

生成损失拿到的是 VQ token，而 tokenizer 正是为重建调校过这类编码。图像质量优于 Show-o，因为 VQ 编码能干净地重新组合回像素。

共享的 transformer 主体会看到两种输入分布（SigLIP 与 VQ），并学会同时处理它们。其主张是：数据足够多、参数足够大时，主体就能吸收这种切换。

### 数据扩展 —— Janus 与 Janus-Pro 的对比

Janus（初代，arXiv 2410.13848）提出了解耦思路，但规模很小（1.3B 参数，数据有限）。Janus-Pro（arXiv 2501.17811）做了扩展：

- 7B 参数（对比 1.3B）。
- 第 1 阶段（对齐）使用 90M 图文对，从 72M 提升而来。
- 第 2 阶段（统一）使用 72M，从 26M 提升而来。
- 第 3 阶段新增 200k 条图像生成指令样本。

结果是：Janus-Pro-7B 在 MMMU 上追平 LLaVA（60.3 对约 58），并在 GenEval 上击败 DALL-E 3（0.80 对 0.67）。一个开源模型，在统一光谱的两端都具有竞争力。

### JanusFlow —— rectified flow 变体

JanusFlow（arXiv 2411.07975）把 VQ 生成路径换成 rectified-flow 生成路径（连续式）。划分变成 SigLIP-负责理解 + rectified-flow-负责生成。质量上限进一步提升。架构依然是解耦编码器 + 共享主体。

### 共享主体的职责

transformer 主体处理统一序列，但面对两种输入分布。它的职责是：

- 理解时：消费 SigLIP 特征 + 文本 token → 自回归地输出文本。
- 生成时：消费文本 token +（可选的图像 VQ token）→ 自回归地输出图像 VQ token。

主体没有任何按块划分的模态专属权重。它就是你会在 Qwen 或 Llama 内部看到的那种文本式 transformer，再加上两个输入适配器。

有意思的是，这意味着 Janus-Pro 的主体可以从预训练 LLM 初始化。Janus-Pro 确实从 DeepSeek-MoE-7B 初始化。这个选择很关键：LLM 贡献了推理能力，而纯从零训练的统一模型很难达到这一水平。

### 与 InternVL-U 的比较

InternVL-U（第 12.10 课）是 2026 年的后续工作。它结合了：

- 原生多模态预训练（InternVL3 主干）。
- 解耦编码器路由（输入 SigLIP，输出 VQ + diffusion 头）。
- 统一的理解 + 生成 + 编辑。

InternVL-U 把 Janus-Pro 的架构选择纳入了一个更大的框架。解耦编码器的思路如今已成为大规模统一模型的默认做法。

### 局限性

解耦编码器增加了架构复杂度。要训练两个 tokenizer、维护两条输入路径、处理两组失效模式。对于不需要生成的产品，Janus-Pro 属于过度设计——选一个 LLaVA 系的理解模型就好。

对于不需要理解的产品，Janus-Pro 属于大材小用——选一个 Stable Diffusion 3 / Flux 模型就好。

对于两者都需要的产品，Janus-Pro 目前是参考级的开源架构。

```figure
l5-janus-decouple
```

## Use It

`code/main.py` 模拟了 Janus-Pro 的路由：

- 两个 mock 编码器：类 SigLIP（产出 256 维语义向量）与类 VQ（产出整数编码）。
- 一个 prompt 路由器，依据任务标签选择编码器。
- 一个共享主体（占位实现），无论 token 序列由哪个编码器产生都能处理。
- 一个从第 1 阶段（对齐）切换到第 3 阶段（指令微调）的加权采样调度。

为 3 个示例打印路由路径：图像问答、T2I、图像编辑。

## Ship It

本节课产出 `outputs/skill-decoupled-encoder-picker.md`。给定一个希望以准前沿质量同时具备统一生成 + 理解的产品，它会挑选 Janus-Pro、JanusFlow 或 InternVL-U，并给出具体的数据规模建议。

## Exercises

1. Janus-Pro-7B 在 GenEval 上击败 DALL-E 3。请解释为什么一个 7B 开源模型能在生成上匹配前沿闭源模型，却在理解上做不到。

2. 实现一个路由函数：给定 prompt 文本，将其分类为 `understand` 或 `generate`。你会如何处理"先描述再画出来"这类模糊 prompt？

3. JanusFlow 用 rectified flow 替换了 VQ 路径。此时 transformer 主体输出什么？损失函数中有什么变化？

4. 再提出一个 Janus-Pro 架构只多加一个解耦编码器就能处理的第四类任务。示例：图像分割（DINO 式）、深度（MiDaS 式）。

5. 阅读 Janus-Pro 第 4.2 节关于数据扩展的内容。哪个数据阶段对相对 Janus 的 T2I 质量提升贡献最大？

## Key Terms

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|------------------------|
| 解耦编码 | “两个视觉编码器” | 每个方向使用独立的 tokenizer 或编码器：理解用语义型，生成用重建型 |
| 共享主体 | “一个 transformer” | 单个 transformer 处理任一编码器的输出；没有模态专属权重 |
| SigLIP 用于理解 | “语义特征” | CLIP 系视觉塔，提供丰富的概念特征但重建能力差 |
| VQ 用于生成 | “重建编码” | 向量量化 token，能干净地解码回像素 |
| JanusFlow | “rectified-flow 变体” | 用连续 flow-matching 生成头代替 VQ 的 Janus-Pro |
| 路由标签 | “任务标签” | prompt 标记（`<understand>` / `<generate>`），用于挑选输入编码器 |

## Further Reading

- [Wu et al. — Janus (arXiv:2410.13848)](https://arxiv.org/abs/2410.13848)
- [Chen et al. — Janus-Pro (arXiv:2501.17811)](https://arxiv.org/abs/2501.17811)
- [Ma et al. — JanusFlow (arXiv:2411.07975)](https://arxiv.org/abs/2411.07975)
- [InternVL-U (arXiv:2603.09877)](https://arxiv.org/abs/2603.09877)
- [Dong et al. — DreamLLM (arXiv:2309.11499)](https://arxiv.org/abs/2309.11499)
