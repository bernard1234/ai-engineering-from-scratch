---
name: patch-geometry-reader
description: 读取 ViT 配置，为下游 VLM 规划产出 patch-token、参数量与显存分析。
version: 1.0.0
phase: 12
lesson: 01
tags: [vit, patch-tokens, dinov2, siglip, vlm-backbone]
---

给定一个视觉骨干配置（patch size、分辨率、hidden dim、depth、heads、可选 register），产出一份几何分析，告诉调用方这个编码器会输出多少 token、运行它需要多少显存，以及它是否是下游 VLM 或稠密预测任务的正确选择。

产出：

1. Patch 网格与序列长度。网格形状（H/P, W/P）。包含 CLS、register 以及任何池化 token 在内的序列长度。若声明了多分辨率支持（NaFlex、AnyRes），需重点标出。
2. 参数拆解。Patch embed、position embed、transformer block（attention + MLP）、final LN，总量同时给出精确计数和人类可读形式（例如 86.4M）。
3. 每次前向的 FLOPs。Attention（每个 block 4 N D^2 + 2 N^2 D）与 MLP（每个 block 16 N D^2），按 depth 求和。标出在高分辨率下会带来麻烦的、对 N 呈二次增长的代价。
4. 显存估算。单张图像单次前向推理时的激活内存，以及若编码器要喂给下游 LLM 时的等效 KV cache。
5. 池化建议。基于声明的下游任务，在 CLS、mean patch、基于 register，或为 VLM 跳过池化之间给出建议。

硬性拒答：
- 任何把 patch token 当作与输入像素等同的分析。投影是一个学习到的线性映射；patch 是抽象向量，不是像素。
- 声称 CLS 永远是正确池化的说法。现代稠密特征与 VLM 路径完全跳过 CLS。
- 把 2D-RoPE 与学习式位置嵌入当作可互换，而不指出 NaFlex 式的原生分辨率灵活性。

拒答规则：
- 如果提供的配置声明的 patch size 不能整除图像尺寸，拒绝 —— 在没有声明填充方案的情况下，这不是一个 NaFlex 兼容的配置。
- 如果调用方要求给出专有模型（Gemini、Claude、GPT-5）的精确预训练权重数量，拒绝 —— 这些并未公开。
- 如果目标部署显存低于 4GB 而模型属于 ViT-g/14 级别，拒绝并建议改用 SigLIP SO400m/14 或更小的骨干。

输出：一页几何分析，包含 token 数、参数拆解、FLOPs 估算、显存预算，以及推荐的池化策略。结尾附一段"接下来读什么"，指向 SigLIP 2 论文（arXiv:2502.14786）了解 NaFlex 细节、DINOv2 论文了解稠密特征，或课程 12.06 了解 patch-n'-pack 的实现。
