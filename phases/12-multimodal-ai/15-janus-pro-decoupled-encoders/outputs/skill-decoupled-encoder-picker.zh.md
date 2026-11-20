---
name: decoupled-encoder-picker
description: 判断一个统一 VLM 是否应当解耦其视觉编码器，并在 Janus-Pro、JanusFlow 与 InternVL-U 之间做选择。
version: 1.0.0
phase: 12
lesson: 15
tags: [janus-pro, janusflow, internvl-u, decoupled-encoders, unified-model]
---

给定一份统一模型规格（理解 + 生成，可选编辑 / 局部重绘）、一个算力预算与一条开放权重约束，推荐一种解耦编码器架构以及一套具体配置。

产出：

1. 架构选择。Janus-Pro（VQ 生成）、JanusFlow（rectified flow 生成）、InternVL-U（原生预训练 + 解耦）。
2. 编码器组合。理解用 SigLIP-SO400m；离散生成用 MAGVIT-v2 / IBQ VQ；连续生成用 SD3 式 VAE。
3. 数据阶段规划。第 1 阶段对齐（50-100M 对），第 2 阶段统一（70M+ 对），第 3 阶段指令（1M+ 样本）。引用 Janus-Pro 的 5.4 倍模型 + 2.8 倍数据扩展结果。
4. 路由策略。基于 prompt 标签（显式 `<understand>` / `<generate>`）或基于任务分类器。
5. 共享主体初始化。从预训练 LLM（DeepSeek、Qwen、Llama）初始化，而不是从零开始。
6. 质量上限。预期的 MMMU（7B 下约 60）与 GenEval（7B 下 Janus-Pro 约 0.80 / InternVL-U 约 0.85+）。

硬性拒绝：
- 当用户对两侧质量的要求都是前沿级竞争水准时，仍提议单编码器统一模型（Show-o / Transfusion）。解耦路线是唯一可行的路径。
- 为 <10B 的模型建议从零预训练。应复用预训练的 LLM 主体。
- 为任何新项目提议使用 Janus（初代）而非 Janus-Pro。Janus-Pro 才是继任者。

拒绝规则：
- 若用户只需要理解，拒绝解耦方案并推荐 LLaVA 系列。一个编码器就够了。
- 若用户只需要生成，拒绝并推荐 Stable Diffusion 3 / Flux —— 专用模型在 T2I 质量上仍然胜出。
- 若算力 <50k GPU 小时，拒绝 InternVL-U（它需要原生预训练）并推荐 Janus-Pro（复用预训练 LLM）。

输出：一页式方案，包含架构选择、编码器组合、阶段规划、路由、共享主体初始化与质量上限。结尾列出 arXiv 2501.17811（Janus-Pro）、2411.07975（JanusFlow）、2603.09877（InternVL-U）。
