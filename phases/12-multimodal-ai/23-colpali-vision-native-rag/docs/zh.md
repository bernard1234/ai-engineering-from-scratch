# ColPali 与 vision-native 文档 RAG

> 传统 RAG 把 PDF 解析成文本、切成 chunk、给 chunk 做 embedding、再存成向量。每一步都在丢信号：OCR 会漏掉图表数据，chunking 会把表格行切断，文本 embedding 会忽略插图。ColPali（Faysse 等，2024 年 7 月）问了一个更简单的问题：为什么一定要先把文本抽出来？直接用 PaliGemma 对页面图像做 embedding，用 ColBERT 式的 late interaction 做 retrieval，从而保留文档自带的版面、插图、字体和排版信号。已发表的 benchmark 结果：在视觉信息丰富的文档上，端到端准确率比 text-RAG 高 20-40%。ColQwen2、ColSmol 和 VisRAG 延续了这一模式。本课解读 vision-native RAG 的核心论点，并动手实现一个迷你版的 ColPali 式索引器。

**Type:** Build
**Languages:** Python（stdlib，multi-vector 索引器 + MaxSim 打分器）
**Prerequisites:** Phase 11（LLM 工程 —— RAG 基础）、Phase 12 · 05（LLaVA）
**Time:** ~180 分钟

## Learning Objectives

- 解释 bi-encoder retrieval（每篇文档一个向量）与 late-interaction retrieval（每篇文档多个向量）之间的区别。
- 描述 ColBERT 的 MaxSim 运算，以及 ColPali 如何把它从文本 token 推广到图像 patch。
- 构建一个迷你版的 ColPali 式索引器：页面 → patch embedding → 对 query term embedding 做 MaxSim → top-k 页面。
- 在发票 / 财务报告场景中，对比 ColPali + Qwen2.5-VL 生成器与 text-RAG + GPT-4 的表现。

## 问题场景

PDF 上的 text-RAG 丢掉了文档的大部分信息。财务报告里的 Q3 营收增长通常画在图表中；医疗报告里的检查结论写在标注图像上；法律合同的签署区块是一种版面事实，而不是文本事实。

text-RAG 的流水线：

1. PDF 经 OCR / pdftotext 转成文本。
2. 文本切成 300-500 token 的 chunk。
3. chunk 经 bi-encoder 做 embedding（一个向量）。
4. 用户 query → embedding → 余弦相似度 → top-k chunk。
5. chunk + query → LLM。

五个有损步骤。图表没被捕获。表格被 chunk 切断。多栏版面被压平。图中的标注消失。

ColPali 的解决办法：跳过 OCR，直接对页面图像做 embedding。用 ColBERT 式的 late interaction 做 retrieval，让模型在查询时能够关注到细粒度的 patch。

## 核心概念

### ColBERT（2020）

ColBERT（Khattab & Zaharia，arXiv:2004.12832）是一种文本检索方法。它不为每篇文档产生一个向量，而是为每个 token 产生一个向量。查询时：

- query token 各自得到 embedding（N_q 个向量）。
- 文档 token 各自得到 embedding（N_d 个向量，通常已缓存）。
- 得分 = 对所有 query token 取"该 token 与文档 token 余弦相似度的最大值"，再求和：Σ_i max_j cos(q_i, d_j)。

这就是 MaxSim 运算。每个 query token 都"挑选"与自己最匹配的文档 token。最终得分是这些挑选结果之和。

优点：召回强，能处理词级语义。缺点：每篇文档有 N_d 个向量，存储开销大。

### ColPali

ColPali（Faysse 等，arXiv:2407.01449）把 ColBERT 的模式套用到图像上。

- 每个页面由 PaliGemma（ViT + 语言模型）编码为 patch embedding：每页 N_p 个向量。
- 每个用户 query（文本）被编码为 query token embedding：N_q 个向量。
- 得分 = Σ_i max_j cos(q_i, p_j)，也就是在 query 文本 token 与页面图像 patch 之间做 MaxSim。
- 按总得分检索 top-k 页面。

文档入库时：用 PaliGemma 对每一页做 embedding，保存所有 patch embedding。查询时：对 query token 做 embedding，与所有已存页面 embedding 计算 MaxSim，返回 top-k 页面。

优点：在视觉信息丰富的文档上，端到端效果比 text-RAG 高 20-40%。每个 patch 向量都能捕捉局部的版面与内容。

缺点：每页 N_p 个 patch × 4 字节浮点 × D 维向量 = 存储增长很快。可用 PQ / OPQ 量化缓解。

### ColQwen2 与 ColSmol

ColQwen2（illuin-tech，2024-2025）把 PaliGemma 换成 Qwen2-VL。基础编码器更强，检索效果更好。

ColSmol 是面向本地 / 边缘场景的小尺度变体。约 1B 参数的 ColSmol retriever 可以在消费级 GPU 上运行。

### VisRAG

VisRAG（Yu 等，arXiv:2410.10594）是另一种变体：不做 patch 级 MaxSim，而是先用 VLM 把每页池化成一个向量，再做 bi-encoder 检索。索引更快、存储更小，但召回更弱。

质量与成本的权衡：要质量选 ColPali，要规模选 VisRAG。

### M3DocRAG

M3DocRAG（Cho 等，arXiv:2411.04952）把多模态检索扩展到多页、多文档推理。它跨文档检索页面，为 VLM 组合出多页上下文。

### ViDoRe —— 基准

ColPali 的配套 benchmark。ViDoRe 即 Visual Document Retrieval Evaluation。任务涵盖财务报告、科学论文、行政文书、医疗记录、产品手册。指标：nDCG@5。

ColPali-v1 在 ViDoRe 上取得约 80% 的 nDCG@5；在同样这些文档上，text-RAG 只有约 50-60%。

### 端到端 RAG 流水线

对于 vision-native RAG：

1. 入库：PDF → 页面图像 → PaliGemma 编码 → 存储所有 patch embedding。
2. 查询：用户文本 → query token embedding → 与所有已索引页面做 MaxSim → top-k 页面。
3. 生成：top-k 页面图像 + query → VLM（Qwen2.5-VL 或 Claude）→ 答案。

全程没有 OCR。图表、字体、版面都会流入答案。

### 存储估算

一份 50 页的财务报告，每页 729 个 patch、128 维 embedding：

- ColPali：50 * 729 * 128 * 4 bytes ≈ 18 MB 原始大小，PQ 压缩后 ≈ 4 MB。
- Text-RAG：50 个 chunk * 768 维 * 4 bytes ≈ 150 kB。

ColPali 每篇文档的存储约为 text-RAG 的 30 倍。规模上去之后，OPQ / PQ 能把它压到约 5-10 倍，通常可以接受。

### text-RAG 仍然胜出的场景

- 没有任何版面信号的纯文本文档（wiki 文章、聊天日志）。text-RAG 更简单，存储也更省。
- 数百万页级别的档案库，存储就是主要成本。
- 严格的监管要求，必须在检索之外同时保留可抽取的 OCR 文本。

至于 2026 年的其他场景 —— 财务报告、科学论文、法律合同、医疗记录、UX 文档 —— vision-native RAG 都是更优选择。

```figure
mm-maxsim
```

## Use It

`code/main.py`：

- 玩具 patch 编码器：把一个"页面"（小网格的特征向量）映射为一组 patch embedding。
- MaxSim 打分器：在 query token embedding 集合与页面 patch 集合之间计算 ColBERT 式得分。
- 索引 5 个玩具页面，运行 3 个 query，返回带分数的 top-k。

## Ship It

本课产出 `outputs/skill-vision-rag-designer.md`。给定一个文档 RAG 项目，它负责在 ColPali / ColQwen2 / VisRAG / text-RAG 之间做选择，并估算存储规模。

## Exercises

1. 一份 200 页的年度报告，每页 729 个 patch、128 维 emb、4 字节浮点。计算原始存储大小，以及 PQ 压缩（8 倍）后的存储大小。

2. MaxSim 是 Σ_i max_j cos(q_i, p_j)。这个求和相比简单的平均相似度，多捕捉到了什么？

3. ColPali 把页面索引为 patch 集合。如果我们改为在词级别索引（像 ColBERT 那样），会有什么变化？权衡是什么？

4. 为一个 1M 页的语料设计端到端流水线，查询延迟预算为每次 500ms。请选择 ColQwen2 / VisRAG 并给出理由。

5. 阅读 M3DocRAG（arXiv:2411.04952）。描述其多页 attention 模式，以及它与单页 ColPali 检索的差异。

## Key Terms

| 术语 | 常被说成 | 实际含义 |
|------|-----------------|------------------------|
| Late interaction | "ColBERT 式" | 用逐 token 或逐 patch 的 embedding + MaxSim 做检索，而不是单个文档向量 |
| MaxSim | "对 patch 取最大" | 对每个 query token 挑出相似度最高的文档 token，再跨 query 求和 |
| Bi-encoder | "单向量" | 每篇文档一个向量；更快，但丢失粒度 |
| Multi-vector | "每文档多向量" | 每篇文档 / 每页存 N_p 个向量；存储成本上升，召回提升 |
| Patch embedding | "页面特征" | VLM 编码器为每个图像 patch 产生的向量，按页缓存 |
| ViDoRe | "视觉文档基准" | ColPali 配套的视觉文档检索 benchmark 套件 |
| PQ quantization | "乘积量化" | 在保持向量相似度的同时把存储压缩约 8 倍的压缩方法 |

## Further Reading

- [Faysse 等 —— ColPali（arXiv:2407.01449）](https://arxiv.org/abs/2407.01449)
- [Khattab & Zaharia —— ColBERT（arXiv:2004.12832）](https://arxiv.org/abs/2004.12832)
- [Yu 等 —— VisRAG（arXiv:2410.10594）](https://arxiv.org/abs/2410.10594)
- [Cho 等 —— M3DocRAG（arXiv:2411.04952）](https://arxiv.org/abs/2411.04952)
- [illuin-tech/colpali GitHub](https://github.com/illuin-tech/colpali)
