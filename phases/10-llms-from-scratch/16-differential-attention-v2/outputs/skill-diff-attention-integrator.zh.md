---
name: diff-attention-integrator
description: 把 Differential Attention V2 集成到新的 pre-training 运行或 LoRA 微调中的方案。
version: 1.0.0
phase: 10
lesson: 16
tags: [differential-attention, diff-transformer, long-context, flash-attention, pre-training, lora]
---

给定一个模型架构（hidden、heads、KV heads、layers、d_head）、一个目标上下文长度、一个幻觉或长上下文画像（你现有 eval 上的失败模式）以及一个训练预算（可用 tokens、GPU-hours），产出 DIFF V2 的集成方案。

产出：

1. 集成模式。从头 pre-training、mid-training 架构替换，或对 Q 投影做 LoRA 微调。结合训练预算和可用的现有权重论证选择。
2. 架构 diff。逐字段的具体改动清单：哪些投影变大、哪些保持不变、新增多少参数，以及减法在 attention block 中放在哪里。包含按层深设置的 `lambda_init` 调度（`0.8 - 0.6 * exp(-0.3 * (depth - 1))` 是论文默认值；如果逐层遥测显示不稳定，按深度调整）。
3. Kernel 选择。鉴于 V2 的头数翻倍，确认 FlashAttention 2 或 3 的支持。除非用户明确需要 V1 的自定义 kernel 路径以保证可复现性，否则拒绝该路径。
4. 显存预算。KV cache 保持在基线（KV heads 不变）。计算每 token 的 activation 显存增量（额外的 Q heads、额外的计算）。报告目标上下文下的绝对数值。
5. 训练稳定性方案。描述需要监控什么：每层的 `lambda` 漂移、每个 head 的 attention 熵、Q 投影上的梯度方差。明确指出当遥测显示发散时，应触发回退到基线 attention 的具体指标。

硬拒绝条件：
- 在没有继续 pre-training 的情况下，把 DIFF attention 加到已预训练的模型上。输出分布会漂移 —— 这不是即插即用的修复。
- 2026 年 4 月之后的任何新运行使用 DIFF V1。在所有测量维度上 V2 都严格更优。
- 集成 DIFF 却不同时启用长上下文训练数据。收益只在 32k 以上才显现。
- 没有受控实验就把 `lambda_init` 改成负值。负初值减去的量超过噪声基底，会让训练崩塌。

拒绝规则：
- 如果目标上下文低于 16k，拒绝集成并推荐标准 attention。新增参数成本无法用噪声基底的论点来证明合理。
- 如果用户无法提供长上下文评估数据（RULER、needle-in-haystack、MultiNeedle），拒绝并要求先提供校准数据。
- 如果用户的技术栈早于 FlashAttention-2，拒绝，并在尝试集成之前建议升级技术栈。

输出：一页集成方案，列出模式、参数增量、KV cache 影响、FlashAttention 确认、`lambda` 调度，以及一个 3 指标监控面板。最后用一段 "成功标准" 指出具体的长上下文 eval 数值（RULER 64k 或等价 benchmark 上的百分点差异），该数值将决定在架构中保留 DIFF V2 还是回退。
