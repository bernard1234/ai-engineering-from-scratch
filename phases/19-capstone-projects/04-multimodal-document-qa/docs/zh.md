# Capstone 04 — 多模态文档问答（视觉优先：PDF、表格、图表）

> 2026 年文档问答的前沿已经从“先 OCR 再转文本”转向视觉优先的 late interaction。ColPali、ColQwen2.5 和 ColQwen3-omni 把每一页 PDF 当作图像，用多向量 late interaction 做 embedding，让查询直接 attend 到 patch 上。在金融 10-K、科学论文和手写笔记上，这种模式大幅胜过先 OCR 的做法。在 1 万页规模上端到端构建这条流水线，并发布与“先 OCR 再转文本”的对比。

**Type:** Capstone
**Languages:** Python（pipeline）、TypeScript（viewer UI）
**Prerequisites:** 第 4 阶段（computer vision）、第 5 阶段（NLP）、第 7 阶段（transformers）、第 11 阶段（LLM engineering）、第 12 阶段（multimodal）、第 17 阶段（infrastructure）
**Phases exercised:** P4 · P5 · P7 · P11 · P12 · P17
**Time:** 30 小时

## 问题场景

企业里堆着被 OCR 流水线糟蹋的 PDF：带旋转表格的扫描版 10-K、满是公式的科学论文、只有当作图像才说得通的图表、手写批注。把它们当作文本优先处理，就等于丢掉一半的信号。2026 年的答案是在原始页面图像上做 late-interaction 多向量检索。ColPali（Illuin Tech）开创了这一路线；ColQwen2.5-v0.2 和 ColQwen3-omni 进一步提升了准确率。在 ViDoRe v3 上，视觉优先检索的得分明显高于先 OCR 再转文本——而且在图表、表格和手写内容上差距还会拉大。

代价是存储和延迟。一页 ColQwen embedding 约 2048 个 patch 向量，而不是一个 1024 维向量。裸存储急剧膨胀。DocPruner（2026）带来了 50% 的剪枝而不产生可测量的精度损失。你要索引 1 万页，测量 ViDoRe v3 nDCG@5，在 2s 内给出答案，并直接与“先 OCR 再转文本”的基线对比。

## 核心概念

Late interaction 的意思是每个 query token 对每个 patch token 打分，然后把每个 query token 的最高分求和。这样你无需单一的池化向量就能得到细粒度匹配。多向量索引（Vespa、Qdrant multi-vector 或 AstraDB）存储每个 patch 的 embedding，并在检索时执行 MaxSim。

作答器是一个视觉语言模型，把查询加上 top-k 检索到的页面作为图像输入，写出带证据区域（bounding box 或页面引用）的答案。Qwen3-VL-30B、Gemini 2.5 Pro 和 InternVL3 是 2026 年的前沿选择。对于公式和科学记号，会把 OCR 兜底（Nougat、dots.ocr）作为可选的文本通道拼接进来。

评测是一个二维矩阵。一个轴是内容类型（纯文本段落、密集表格、柱状/折线图表、手写笔记、公式）。另一个轴是检索方式（视觉优先 late interaction vs 先 OCR 再转文本 vs 混合）。每个格子给出 nDCG@5 和答案准确率。这份报告就是交付物。

## 架构

```
PDFs -> page renderer (PyMuPDF, 180 DPI)
           |
           v
  ColQwen2.5-v0.2 embed (multi-vector per page, ~2048 patches)
           |
           +------> DocPruner 50% compression
           |
           v
   multi-vector index (Vespa or Qdrant multi-vector)
           |
query ----+----> retrieve top-k pages (MaxSim)
           |
           v
  VLM answerer: Qwen3-VL-30B | Gemini 2.5 Pro | InternVL3
    inputs: query + top-k page images + optional OCR text
           |
           v
  answer with cited page numbers + evidence regions
           |
           v
  Streamlit / Next.js viewer: highlighted boxes on source page
```

## 技术栈

- 页面渲染：PyMuPDF（fitz），180 DPI，纵向归一化
- Late-interaction 模型：ColQwen2.5-v0.2 或 ColQwen3-omni（Hugging Face 上的 vidore 团队）
- 索引：Vespa 多向量字段，或 Qdrant multi-vector，或 AstraDB 配 MaxSim
- 剪枝：DocPruner 2026 策略（保留高方差 patch，50% 压缩，精度损失 < 0.5%）
- OCR 兜底（公式 / 密集表格）：dots.ocr 或 Nougat
- VLM 作答器：自托管 Qwen3-VL-30B 或托管 Gemini 2.5 Pro；InternVL3 作为兜底
- 评测：ViDoRe v3 benchmark，多页推理用 M3DocVQA
- Viewer UI：Next.js 15，canvas 叠加证据区域

```figure
ce-late-interaction
```

## Build It

1. **摄入。** 遍历 1 万个 PDF 页面，覆盖 10-K、科学论文和扫描件。把每页渲染成 1536x2048 的 PNG。持久化 `{doc_id, page_num, image_path}`。

2. **Embed。** 对每页图像跑 ColQwen2.5-v0.2。输出形状约为 2048 个、维度 128 的 patch embedding。应用 DocPruner 保留信号最强的一半。写入 Vespa 多向量字段或 Qdrant multi-vector。

3. **查询。** 对每个到来的查询，用 query tower 做 embedding（token 级 embedding）。对索引执行 MaxSim：对每个 query token，取页面 patch embedding 上的最大点积，再求和。返回 top-k 页面。

4. **综合。** 带着查询和 top-5 页面图像调用 Qwen3-VL-30B。提示词：“仅使用提供的页面作答。每条论断都按 (doc_id, page) 引用，并指明区域（figure、table、paragraph）。”

5. **证据区域。** 后处理答案以抽取被引用的区域。如果 VLM 输出 bounding box（Qwen3-VL 会），就在 viewer 中把它们渲染成叠加层。

6. **OCR 兜底。** 对被判定为公式密集的页面（基于图像方差的启发式规则），运行 Nougat 或 dots.ocr，把 OCR 文本作为额外通道与图像一同传入。

7. **Eval。** 跑 ViDoRe v3（检索 nDCG@5）和 M3DocVQA（多页问答准确率）。同时在同一语料上、用同一个综合器跑“先 OCR 再转文本”流水线。产出一个“内容类型 × 方法”矩阵。

8. **UI。** 先做 Streamlit 原型；再做 Next.js 15 生产版 viewer，支持逐页的证据区域叠加。

## Use It

```
$ doc-qa ask "what was the 2024 operating margin change for segment EMEA?"
[retrieve]   top-5 pages in 320ms (ColQwen2.5, MaxSim, Vespa)
[synth]      qwen3-vl-30b, 1.4s, cited (form-10k-2024, p. 88) + (..., p. 92)
answer:
  EMEA operating margin moved from 18.2% to 16.8%, a 140bp decline.
  cited: 10-K-2024.pdf p.88 (Table 4, Segment Operating Margin)
         10-K-2024.pdf p.92 (MD&A, Operating Performance)
[viewer]     open with highlighted bounding boxes overlaid on p.88 Table 4
```

## Ship It

`outputs/skill-doc-qa.md` 描述了交付物：一个面向特定语料调优的视觉优先多模态文档问答系统，并针对 ViDoRe v3 与“先 OCR 再转文本”基线做评测。

| Weight | Criterion | How it is measured |
|:-:|---|---|
| 25 | ViDoRe v3 / M3DocVQA 准确率 | 与先 OCR 转文本基线及公开榜单对比的 benchmark 数字 |
| 20 | 证据区域定位 | 被引用区域中真正包含答案跨度的比例 |
| 20 | 存储与延迟工程 | DocPruner 压缩比、索引 p95、答案 p95 |
| 20 | 多页推理 | 手工标注的 100 题多页集合上的准确率 |
| 15 | 溯源查看 UX | Viewer 清晰度、叠加保真度、并排对比工具 |
| **100** | | |

## Exercises

1. 在同一语料上对比 ColQwen2.5-v0.2 与 ColQwen3-omni。哪些页面一个答对另一个漏掉？给索引加一个 “content class” 标记，按类型路由。

2. 激进剪枝 embedding（75%、90%）。找到压缩悬崖：ViDoRe nDCG@5 跌到 OCR 基线以下的那个点。

3. 构建混合方案：并行跑“先 OCR 再转文本”和 ColQwen，用 RRF 融合，再用 cross-encoder 重排。混合方案是否胜过任一单独方案？在哪些地方帮助最大？

4. 把 Qwen3-VL-30B 换成更小的 VLM（Qwen2.5-VL-7B）。测量“每美元准确率”曲线。

5. 增加手写笔记支持。渲染手写语料，用 ColQwen 做 embedding，测量检索效果。与手写 OCR 流水线对比。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Late interaction | “ColPali 式检索” | query token 各自对页面 patch 打分；MaxSim 做聚合 |
| Multi-vector | “按 patch 的 embedding” | 每个文档有许多向量，而不是一个池化向量 |
| MaxSim | “late-interaction 打分” | 对每个 query token 取文档向量上的最大相似度再求和 |
| DocPruner | “patch 压缩” | 2026 年的剪枝方法，保留 50% 的 patch 而精度损失可忽略 |
| ViDoRe v3 | “文档检索 benchmark” | 衡量视觉文档检索的 2026 年标准 |
| Evidence region | “引用的 bounding box” | 源页面上的一个 bbox，用来定位答案跨度 |
| OCR fallback | “公式通道” | 对公式或表格密集页面与视觉并用的文本流水线 |

## Further Reading

- [ColPali (Illuin Tech) repository](https://github.com/illuin-tech/colpali) — late-interaction 文档检索参考
- [ColPali paper (arXiv:2407.01449)](https://arxiv.org/abs/2407.01449) — 奠基性的方法论文
- [ColQwen family on Hugging Face](https://huggingface.co/vidore) — 可直接投产的 checkpoint
- [M3DocRAG (Adobe)](https://arxiv.org/abs/2411.04952) — 多页多模态 RAG 基线
- [Vespa multi-vector tutorial](https://docs.vespa.ai/en/colpali.html) — 参考服务栈
- [Qdrant multi-vector support](https://qdrant.tech/documentation/concepts/vectors/#multivectors) — 备选索引
- [AstraDB multi-vector](https://docs.datastax.com/en/astra-db-serverless/databases/vector-search.html) — 备选托管索引
- [Nougat OCR](https://github.com/facebookresearch/nougat) — 支持公式的 OCR 兜底
