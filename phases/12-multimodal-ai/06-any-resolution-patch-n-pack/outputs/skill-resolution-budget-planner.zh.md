---
name: resolution-budget-planner
description: 为混合宽高比的 VLM 工作负载在 square-resize、AnyRes、M-RoPE 和 NaFlex 之间做选择，并输出一份逐任务的 token 预算方案。
version: 1.0.0
phase: 12
lesson: 06
tags: [vlm, patch-n-pack, naflex, anyres, m-rope, token-budget]
---

给定一个工作负载——描述 VLM 将会看到的图像（OCR 文档、图表、UI 截图、自然照片、视频帧）以及每个请求的总 token 预算——为每个图像类别挑选一种分辨率策略，并产出一份可运行的配置。

产出：

1. 逐图像类别的策略。对每个声明的类别（OCR、图表、UI、照片、视频帧），从 {square-resize, AnyRes, M-RoPE, NaFlex} 中挑一个。用一句话说明理由，指出该任务对分辨率的敏感程度。
2. 每张图像的 token 预算。包含 min_pixels、max_pixels（Qwen2.5-VL 风格）以及在所选策略下的预期序列长度。如果任何单张图像超过 LLM 上下文的 40%，要标记出来。
3. batch 打包方案。如果请求会被批处理，说明该用 `cu_seqlens`（FlashAttn varlen）、稠密块对角掩码，还是不批处理的单图推理。当 batch 内宽高比差异超过 2 倍时，注明 varlen 节省的 FLOP。
4. 编码器推荐。混合负载用 SigLIP 2 NaFlex；agent UI 用 Qwen2.5-VL 原生模式；冻结编码器部署用 CLIP-336 + AnyRes；纯照片路径用 224 的原始 ViT。
5. 失败模式预警。所选配置下的每图 token 数；30 tok/s prefill 下的延迟成本；上下文填充百分比；在典型 OCR benchmark 上相对 square-resize 的预期准确率差异。

硬性拒绝：
- 为 OCR 或图表任务推荐 square-resize，却不说明用户会损失哪个 benchmark 数字。
- 提出一种会产生超过 LLM 上下文容量的 token 数的策略。始终按声明的上下文窗口来规划预算。
- 把 AnyRes 当成万能答案——它的倍数级切块开销可能在单张图像编码完之前就超出 LLM 上下文。

拒答规则：
- 如果用户声明的 token 预算低于每图 256 个 token，那么除纯照片的语义任务外一律拒绝——在那种预算下，再多池化也换不回 OCR 准确率。
- 如果用户想要稠密预测输出（分割、深度），而编码器中没有 ViT register token，拒绝并指向启用了 register 的 DINOv2 / SigLIP 2。
- 如果用户的 LLM 上下文小于 8k，而工作负载包含文档或截图，拒绝并建议使用更大的上下文，或采用 OCR 优先的流水线。

输出：一页预算方案，包含逐类别策略表、batch 打包方案、编码器推荐和预警清单。结尾给出供后续阅读的相关 arXiv 论文——NaViT 用 2307.06304，SigLIP 2 / NaFlex 用 2502.14786，Qwen2.5-VL 用 2502.13923。
