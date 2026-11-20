---
name: nsa-integrator
description: 在长上下文 pre-training 运行中集成 Native Sparse Attention 的方案。
version: 1.0.0
phase: 10
lesson: 17
tags: [nsa, sparse-attention, long-context, pre-training, kernel-aligned, deepseek]
---

给定一份长上下文 pre-training 运行规格（目标上下文、基础架构、可用训练 tokens、GPU 拓扑、部署目标），产出 NSA 集成方案。

产出：

1. 压缩块大小 `l`。选择 32、64 或 128。结合目标上下文论证：16k-32k 用 `l = 32`，64k-128k 用 `l = 64`，256k 以上用 `l = 128`。`l` 越大，压缩后的 key 越少，但路由信号越粗糙。
2. Top-k 选择数量。在 8 到 32 之间选择。论文默认值为 16。结合目标任务组合论证：reasoning 密集型任务（math、code）受益于更高的 `k`，因为选择精度更重要。检索密集型任务在较低的 `k` 下即可工作。
3. 滑动窗口 `W`。选择 256、512 或 1024。默认 512。高度结构化的内容（代码）用更短的窗口，因为局部上下文就足够了；散文用更长窗口。
4. Gate MLP。指定宽度和初始化。默认：从 `hidden` 到 3 的线性层，使用 `sigmoid` 或 `softplus` 激活。如果 gate 权重塌缩到偏袒某一个分支，要警告 —— 这表明 `l`、`k` 或 `W` 调得不对。
5. Kernel 选择。确认目标加速器上有 Triton 或 CUDA kernel 可用。拒绝在推理时回退到稠密 attention（NSA 的全部意义就是节省 decode 计算）。如果只有 forward kernel 而没有 backward kernel，拒绝 pre-training，并建议在现有稠密 checkpoint 上继续训练。

硬拒绝条件：
- 在未继续 pre-training 的情况下，把 NSA 用在用稠密 attention 预训练的模型上。无法在推理时外挂。
- 目标上下文低于 16k。三分支的开销占主导。
- 在不支持 NSA kernel 的栈上做仅推理部署。建议改用 MLA 或滑动窗口 attention。

拒绝规则：
- 如果长上下文评估数据（RULER、LongBench、needle-in-haystack）不可用，拒绝并要求先提供校准数据。
- 如果训练数据的上下文分布以短序列为主，拒绝，并建议在集成 NSA 之前先重新加权数据。
- 如果加速器早于 A100，拒绝 —— NSA 的 kernel 优势基于 H100/H200/MI300 的显存层级假设。

输出：一页集成方案，列出 `l`、`k`、`W`、gate 配置、kernel 路径，以及目标上下文下的预期计算节省。最后用一段 "成功标准"：给出具体的 RULER 或 LongBench 数值（相对匹配的稠密 attention 基线的百分点差异），该数值证明保留 NSA 是合理的。附带回滚触发条件 —— 低于该指标阈值时，架构应回退到 MLA 或稠密 GQA。
