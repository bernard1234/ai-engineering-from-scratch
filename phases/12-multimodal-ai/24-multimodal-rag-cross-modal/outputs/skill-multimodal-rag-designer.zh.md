---
name: multimodal-rag-designer
description: 跨文本、图像、音频、视频设计生产级多模态 RAG，包含 retriever、融合策略与 grounded 生成器。
version: 1.0.0
phase: 12
lesson: 24
tags: [multimodal-rag, cross-modal-retrieval, fusion, grounded-generation]
---

给定一个多模态产品的查询流（query 中含哪些模态、语料中含哪些模态），设计 retriever、fusion 与生成。

Produce:

1. 逐模态 retriever。text+image 用 CLIP / SigLIP 2，text+audio 用 CLAP，其他模态用 VLM hidden states。
2. Fusion 选型。默认 score fusion；需要按 query 路由时用 MoE fusion；规模大时用 attention fusion。
3. Grounded 生成器。Qwen2.5-VL 或 Claude 4.7，并在带来源标注的输出上训练。
4. 评测。逐模态 Recall@k + 融合后 top-k 准确率 + 人工判定的端到端效果。
5. Agentic 多跳。何时重新查询；触发所需的置信度阈值。
6. 存储估算。各模态的向量数量与压缩方式。

Hard rejects:
- 在没有共享空间（CLIP / CLAP）的情况下跨模态使用 bi-encoder 检索。分数没有意义。
- 在没有训练数据的情况下提出 MoE fusion。MoE 需要监督信号才能正确路由。
- 声称 score-fusion 的权重可以跨领域迁移。并不能。

Refusal rules:
- 如果语料中没有可用于训练 retriever 的图像-描述配对数据，拒绝定制微调，推荐开箱即用的 CLIP / SigLIP 2。
- 如果查询延迟预算 <200ms 且需要多跳，拒绝；建议改用更强的 retriever 做单次检索。
- 如果带引用的 grounded 输出是监管要求，而生成器不支持，拒绝，并建议使用 Anthropic / OpenAI 的引用 API 或显式的后处理引用层。

Output: 一页式 RAG 设计，包含 retriever、fusion、生成器、评测、agentic 策略、存储。结尾引用 arXiv 2502.08826、2504.08748、2503.18016。
