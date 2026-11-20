---
name: doc-qa
description: 在 1 万页规模上构建视觉优先的多模态文档问答系统，采用 late-interaction 检索和证据区域引用。
version: 1.0.0
phase: 19
lesson: 04
tags: [capstone, multimodal, rag, colpali, colqwen, late-interaction, pdf]
---

给定一个 PDF 语料（10-K、科学论文、扫描件），构建一条流水线：用 ColPali 式 late interaction 把页面当作图像索引，并用页级证据区域回答问题。

构建计划：

1. 用 PyMuPDF 在 180 DPI 下把每页 PDF 渲染成 1536x2048 的 PNG。
2. 用 ColQwen2.5-v0.2 或 ColQwen3-omni 为每页做 embedding。把多向量 patch embedding 存入 Vespa、Qdrant multi-vector 或 AstraDB。
3. 应用 DocPruner 式的 50% patch 剪枝。验证在 ViDoRe v3 上精度下降保持在 0.5% 以下。
4. 查询时：对 query token 做 embedding；对每页的 patch 计算 MaxSim；排出 top-k。
5. 用 Qwen3-VL-30B 或 Gemini 2.5 Pro 综合，传入查询加 top-5 页面图像。要求给出 `(doc_id, page, region)` 锚点引用。
6. 对公式或表格密集的页面，运行 Nougat 或 dots.ocr 作为可选文本通道，与图像一同传入。
7. 构建一个 Next.js 15 viewer，把证据区域以 bounding box 的形式叠加到源页面上。
8. 在 ViDoRe v3 和 M3DocVQA 上评测。产出“内容类别 × 方法”矩阵，对比视觉优先与先 OCR 再转文本在纯文本、表格、图表、手写和公式上的表现。

Assessment rubric:

| Weight | Criterion | Measurement |
|:-:|---|---|
| 25 | ViDoRe v3 / M3DocVQA 准确率 | 在匹配页面上对比先 OCR 转文本基线的 benchmark |
| 20 | 证据区域定位 | 被引用区域中包含答案跨度的比例 |
| 20 | 存储与延迟工程 | DocPruner 压缩、索引 p95、2s 内的答案 p95 |
| 20 | 多页推理 | 手工标注的 100 题多页集合上的准确率 |
| 15 | 溯源查看 UX | 叠加保真度、对比工具、逐页浏览器 |

Hard rejects:

- 把 OCR 文本塞进单向量 embedding，却当作“视觉优先”推销的 OCR 优先流水线。
- 任何丢弃 patch 级 bounding box、因而无法渲染证据叠加层的系统。
- 未记录 DocPruner 设置就报告的存储数字。

Refusal rules:

- 拒绝在没有专门脱敏策略的情况下索引扫描版法律合同。ColQwen 的 embedding 会泄露内容。
- 拒绝针对用户未披露的语料提供服务。受监管领域必须留有审计轨迹。
- 拒绝在未对同一语料运行两条流水线的情况下与先 OCR 再转文本做对比。

Output：一个 repo，包含摄入流水线、Vespa（或 Qdrant multi-vector）配置、100 题多页评测集、viewer UI，以及一篇带“内容类别 x 方法”矩阵、并具体建议 2026 年哪些内容类别仍更适合先 OCR 再转文本的说明。
