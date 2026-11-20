---
name: mtp-planner
description: 为新的 pre-training 运行规划 multi-token prediction 集成。
version: 1.0.0
phase: 10
lesson: 18
tags: [mtp, multi-token-prediction, deepseek-v3, pre-training, speculative-decoding]
---

给定一份 pre-training 运行规格（模型规模、hidden size、层数、数据 token 预算、GPU 拓扑、目标部署）和一个明确目标（更密集的训练信号 vs speculative-decoding draft vs 两者兼要），产出 MTP 集成方案。

产出：

1. 深度 D。选择 1 或 2。DeepSeek-V3 使用 D=1，并报告第一深度 speculative-decoding 接受率达到 80%+。对大多数运行而言，D=2 已进入收益递减区间。结合计算预算论证选择 —— 每增加一个深度，每个训练步大约增加一个 transformer block 的计算量。
2. Lambda 调度。默认：训练前 10% 为 0.3，之后为 0.1。小模型（7B 以下）因为更密集的信号更重要，可早期上调到 0.5；如果观察到 MTP loss 压过主 loss，则下调。
3. 参数预算。按模块报告参数量及其相对主模型的比例。确认开销低于主参数的 5%（稠密）或低于 3%（MoE）。
4. 显存和计算开销。量化每步额外的 forward-pass FLOPs（约为 `D * transformer_block_cost`）、额外的 backward-pass 显存（D 个模块的 activation 显存）以及额外的峰值 VRAM（共享的 embedding 和 head 不计入，projection 和 transformer block 计入）。
5. 推理时接线。描述推理时如何把 MTP 模块当作 speculative-decoding draft 来使用。指明 Leviathan 规则的集成路径和 KV-rollback 记账。确认与目标推理栈（vLLM、SGLang、TensorRT-LLM）兼容。

硬拒绝条件：
- 在未带 MTP 预训练的稠密模型上加 MTP。无法改造 —— MTP 模块没有经过训练。
- 首次集成就用 D > 2。相对 D=1 的收益很小，复杂度却增长很快。
- 在激活参数低于 1B 的模型上使用 MTP。在这个规模上，信号弱于开销成本。
- 目标是 speculative decoding 时却使用并行（Gloeckle 风格）head。它们不按因果链式衔接。

拒绝规则：
- 如果 pre-training 数据以短序列为主（2k 以下），拒绝。MTP 的收益假设序列足够长，depth-2 监督才有意义。
- 如果目标推理栈完全不支持 speculative decoding，指出 MTP 仍能带来更密集的训练信号并继续，但要标记这一不匹配。
- 如果用户在现有稠密 checkpoint 上继续 pre-training 且没有 MTP，拒绝，并建议只在全新训练运行的起点或干净的数据边界重置处加入 MTP。

输出：一页集成方案，列出 D、lambda 调度、参数开销（绝对值和百分比）、计算开销（每个训练步的百分比），以及推理时 speculative-decoding 的接线方案。最后用一段 "成功标准"，指出证明保留 MTP 合理的实测指标：训练 50B tokens 后 depth 1 的接受率必须高于 70%，否则应回退该架构。
