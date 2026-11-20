---
name: document-ai-stack-picker
description: 根据领域、规模和监管需求，在 OCR 流水线、免 OCR 专才与 VLM 原生之间为文档 AI 项目做选择。
version: 1.0.0
phase: 12
lesson: 22
tags: [document-ai, ocr, donut, nougat, paligemma, vlm-native]
---

给定一个文档 AI 项目（领域：发票 / 科学论文 / 表单 / 混合；规模：每天的页数；质量门槛；监管需求），挑选技术栈并产出参考配置。

产出：

1. 技术栈选择。时代 1（OCR 流水线 + LayoutLMv3）、时代 2（Donut / Nougat 免 OCR）、时代 3（VLM 原生）或混合方案。
2. 每页成本估算。所选技术栈下的 token 数与延迟。
3. 精度预期。DocVQA + ChartQA + 领域专用 benchmark。
4. 手写策略。成本不敏感时用 VLM 原生；规模化时用专用 TrOCR + 路由。
5. 数学 / LaTeX 输出。科学论文用 Nougat；其他用 VLM。
6. 监管兜底。带交叉核对审计日志的混合方案。

硬性拒绝：
- 在未做成本分析的情况下，为每天 >100 万页的场景提议 VLM 原生。每页 2576px 的 token 成本不可忽视。
- 为受监管流程推荐没有审计路径的单模型方案。
- 声称 Nougat 能处理扫描发票。它不能——它是科学论文专才。

拒绝规则：
- 如果规模每天 >1000 万页，拒绝时代 3，推荐时代 1，并把时代 3 用作抽样校验器。
- 如果领域以手写为主，拒绝 OCR 流水线，推荐 VLM 原生 + 手写专才（TrOCR）。
- 如果公式要求 LaTeX 保真度，必须在链路中保留 Nougat。

输出：一页纸方案，包含技术栈、成本、精度、手写、数学、监管。末尾列出 arXiv 2308.13418（Nougat）、2204.08387（LayoutLMv3）、2111.15664（Donut）。
