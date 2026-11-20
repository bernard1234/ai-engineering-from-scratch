---
name: hybrid-picker
description: 针对给定工作负载，在纯 Transformer、Jamba 风格 hybrid 与纯 SSM 之间做选择。
version: 1.0.0
phase: 10
lesson: 21
tags: [jamba, mamba, ssm, hybrid, long-context, memory-budget, architecture]
---

给定工作负载规格（上下文长度分布 p50/p99、任务组合、每 GPU 内存预算、目标吞吐、质量与速度的优先级），在纯 Transformer（+MoE +MLA）、Jamba 风格 hybrid 与纯 Mamba 模型之间给出推荐。

产出：

1. 上下文长度分桶。短（16k 以下）、中（16k-64k）、长（64k-256k）或超长（256k 以上）。决定第一轮决策。
2. 架构推荐。从纯 Transformer、1:7 hybrid、1:3 hybrid、1:15 hybrid 或纯 Mamba 中挑一个。结合上下文分桶以及任务的 in-context 召回需求给出理由。
3. 内存预算核对。在目标上下文下计算 KV cache + SSM state。在计入权重与 activation 内存（通常是在权重与 KV cache 之上再加 10-20 GB）后，确认它能装进目标加速器。
4. 质量权衡披露。记录所选稀疏程度带来的质量代价。低于 1:7 比例的 hybrid 在 in-context 检索上会有可测量的退化；纯 Mamba 在某些 state-tracking 任务上会失败。
5. 推理栈兼容性。确认所选架构受目标栈支持（vLLM、TensorRT-LLM、SGLang、llama.cpp）。hybrid 的工具链覆盖比纯 Transformer 薄。

硬性拒绝：
- 16k 以下上下文使用 Jamba 风格 hybrid。架构开销不合理。
- 推理密集型或跨文档交叉引用任务使用纯 Mamba。state-tracking 的限制会造成影响。
- 低于 1:15 的 hybrid 比例。低于此，in-context 召回不可靠。
- 任何在指定加速器上装不进所计算内存预算的推荐。

拒绝规则：
- 如果工作负载确实是短上下文与长上下文混合，拒绝 hybrid 推荐，改为推荐纯 Transformer（尽可能带 MLA）——hybrid 的优势专门体现在长上下文工作负载上。
- 如果加速器是消费级（24GB 或更少），拒绝 hybrid 规模的模型，并推荐蒸馏的小型 hybrid 或量化的纯 Transformer。
- 如果工作负载是对延迟敏感的 batch-1 生成，且模型是新的（没有现成部署路径），拒绝，并推荐一个支持良好的纯 Transformer 配合 speculative decoding（Phase 10 · 15）作为更简单的路径。

输出：一页纸的推荐，列出上下文分桶、架构选择、目标上下文下的 KV cache、质量权衡披露与推理栈兼容性。结尾用一段“需要监控什么”，点名具体的长上下文评测（RULER、LongBench、needle-in-haystack），用于在前 10k 次生产请求中验证该推荐。
