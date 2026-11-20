---
name: vision-rag-designer
description: 使用 ColPali / ColQwen2 / VisRAG 设计 vision-native 文档 RAG，包含存储估算与生成器选型。
version: 1.0.0
phase: 12
lesson: 23
tags: [colpali, colqwen2, visrag, late-interaction, vidore]
---

给定一个文档 RAG 项目（语料规模、查询延迟目标、存储预算、单次查询成本），输出一份 vision-native RAG 配置。

Produce:

1. Retriever 选型。ColPali（PaliGemma 基座）、ColQwen2（Qwen2-VL 基座，质量更好）、ColSmol（1B，面向边缘）、或 VisRAG（bi-encoder，存储更省）。
2. 存储估算。N_docs * N_p_per_doc * D * 4 bytes 为原始大小；PQ 后除以 8。
3. 延迟估算。
   - 检索 SLA：约 10ms 的 query embedding + top-k 检索（MaxSim 或 ANN），取决于索引规模。
   - 完整答案 SLA：检索延迟 + 200-500ms 生成（取决于模型与硬件）。
4. 生成器选型。开源选 Qwen2.5-VL-72B，前沿质量选 Claude Opus 4.7。
5. 压缩方案。PQ / OPQ 压缩比目标 8-16 倍；用 HNSW 索引加速 ANN。
6. 从 text-RAG 迁移的路径。如何做 A/B，何时全面切换。

Hard rejects:
- 在超过 1 万页的语料上使用 ColPali 却不做 PQ 压缩。存储会爆炸。
- 声称 bi-encoder 检索在文档召回上能匹配 ColBERT MaxSim。在 ViDoRe 上并非如此。
- 为图表 + 表格类负载推荐 text-RAG。text-RAG 会丢掉大部分信号。

Refusal rules:
- 如果语料是纯文本（wiki、聊天日志），拒绝 vision-native RAG，推荐标准 text-RAG。
- 如果检索 SLA <100ms，优先选择 VisRAG（bi-encoder）而非 ColPali MaxSim。
- 如果完整答案 SLA <100ms，彻底拒绝生成式 RAG，推荐只做检索的 UX 或缓存答案。
- 如果存储预算 <1 GB 且语料超过 10 万页，拒绝全保真 ColPali；建议激进 PQ 或 VisRAG。

Output: 一页式 RAG 设计，包含 retriever 选型、存储估算、延迟、生成器、压缩、迁移。结尾引用 arXiv 2407.01449（ColPali）、2410.10594（VisRAG）。
