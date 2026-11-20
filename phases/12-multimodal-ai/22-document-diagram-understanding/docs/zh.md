# 文档与图表理解

> 文档不是照片。一份 PDF、科学论文、发票或手写表单带有版式、表格、图表、脚注、页眉以及纯图像理解无法捕捉的语义结构。前 VLM 时代的栈是一条流水线：Tesseract OCR + LayoutLMv3 + 表格抽取启发式。VLM 浪潮用免 OCR 的模型取代了它——Donut（2022）、Nougat（2023）、DocLLM（2023）——直接输出结构化标记。到 2026 年，前沿做法就是 “把页面图像以 2576px 原生分辨率喂给 Claude Opus 4.7”，结构化标记输出免费得到。本课梳理文档 AI 的三个时代脉络。

**Type:** Build
**Languages:** Python（stdlib，版式感知的文档解析骨架）
**Prerequisites:** Phase 12 · 05（LLaVA）、Phase 5（NLP）
**Time:** ~180 分钟

## Learning Objectives

- 解释文档 AI 的三个时代：OCR 流水线、免 OCR、VLM 原生。
- 描述 LayoutLMv3 的三路输入：文本、版式（bbox）、图像 patch，以及统一掩码。
- 比较 Donut（免 OCR，图像 → 标记）、Nougat（科学论文 → LaTeX）、DocLLM（版式感知生成）、PaliGemma 2（VLM 原生）。
- 为新任务（发票、科学论文、手写表单、中文票据）挑选文档模型。

## 问题场景

“理解这份 PDF” 比看起来难得多。信息存在于：

- 文本内容（90% 的信号）。
- 版式（页眉、脚注、侧边栏、双栏排版）。
- 表格（行、列、合并单元格）。
- 图表与示意图。
- 手写批注。
- 字体与排版（标题 vs 正文）。

裸 OCR 只能输出文本，其余全部丢失。一个关心发票的系统需要知道 “Total: $1,245” 来自右下角，而不是某条脚注。

## 核心概念

### 时代 1 —— OCR 流水线（2021 年前）

经典技术栈：

1. PDF → 每页转成图像。
2. Tesseract（或商用 OCR）抽取文本，并给出每个词的边界框。
3. 版式分析器识别区块（页眉、表格、段落）。
4. 表格结构识别器解析表格。
5. 领域规则 + 正则抽取字段。

对干净的印刷文本有效。遇到手写、倾斜扫描、复杂表格、非拉丁文字就会失效。每一种失败模式都需要一条自定义异常处理路径。

### TrOCR（2021）

TrOCR（Li 等，arXiv:2109.10282）用 transformer 编码器-解码器取代了 Tesseract 经典的 CNN-CTC，训练数据是合成 + 真实文本图像。在手写和多语言文本上取得明显优势。它仍然是一条流水线（检测器 → TrOCR → 版式），但 OCR 这一步大幅改善。

### 时代 2 —— 免 OCR（2022-2023）

第一批免 OCR 模型的主张是：彻底跳过检测，把图像像素直接映射到结构化输出。

Donut（Kim 等，arXiv:2111.15664）：
- 编码器-解码器 transformer，编码器为 Swin-B。
- 输出可以是表单理解用的 JSON、摘要用的 markdown，或任意任务专用 schema。
- 没有 OCR、没有版式、没有检测。

Nougat（Blecher 等，arXiv:2308.13418）：
- 专门在科学论文上训练。
- 输出为 LaTeX / markdown。
- 能处理公式、多栏版式、图表。
- 几乎每个 arXiv 解析器都会调用的模型。

这些都是专才，不是通才。Donut 处理科学论文会失败；Nougat 处理发票会失败。

### LayoutLMv3（2022）

另一条路线。LayoutLMv3（Huang 等，arXiv:2204.08387）保留 OCR，但加入版式理解：

- 三路输入：OCR 文本 token、每个 token 的 2D 边界框、图像 patch。
- 在三种模态上做掩码训练目标（掩码文本、掩码 patch、掩码版式）。
- 下游任务：分类、实体抽取、表格 QA。

LayoutLMv3 是 OCR 基文档理解的顶峰。在表单和发票上很强。需要上游 OCR。在标准化文档 benchmark 上取得了 VLM 之前的最佳精度。

### DocLLM（2023）

DocLLM（Wang 等，arXiv:2401.00908）是 LayoutLM 的生成式兄弟。以版式 token 为条件生成自由形式的答案。在文档 QA 上更好；但依然依赖 OCR 输入。

### 时代 3 —— VLM 原生（2024+）

2024 年的 VLM 已经好到可以完全取代流水线。把整页高清图像喂给 VLM，提问，得到答案。

- LLaVA-NeXT 的 336 tile AnyRes 可处理小尺寸文档。
- Qwen2.5-VL 的动态分辨率原生支持 2048+ 像素。
- Claude Opus 4.7 支持 2576px 文档。
- PaliGemma 2（2025 年 4 月）专门针对文档 + 手写训练。

VLM 原生与 OCR 流水线之间的差距迅速收窄。到 2026 年，VLM 原生在以下方面胜出：

- 场景文本（手写 + 印刷混合、多语种混排）。
- 含合并单元格的复杂表格。
- 嵌入正文的数学公式。
- 带文字标注的图。

OCR 流水线仍在以下方面胜出：

- 每页时延敏感的超大规模纯扫描负载。
- 流水线可靠性（确定性失败 vs VLM 幻觉）。
- 要求 OCR 输出可审计的受监管环境。

### Claude 4.7 / GPT-5 前沿

在 2576 像素原生输入下，前沿 VLM 的文档理解精度接近人类。2026 年初的 benchmark 数字：

- DocVQA：Claude 4.7 ~95.1，PaliGemma 2 ~88.4，Nougat ~77.3，流水线式 LayoutLMv3 ~83。
- ChartQA：Claude 4.7 ~92.2，GPT-4V ~78。
- VisualMRC：Claude 4.7 ~94。

闭源模型的领先主要来自分辨率和基础 LLM 的规模。7B 的开源模型落后几个点，但正在追上。

### 数学公式与 LaTeX 输出

科学论文的公式需要精确的 LaTeX 输出。Nougat 正是为此训练的。用 LaTeX 目标训练过的 VLM（Qwen2.5-VL-Math、Nougat 衍生模型）能产出可用的 LaTeX。若没有显式的 LaTeX 训练，VLM 产出的是可读但不精确的转写。

2026 年的科学论文流水线：先用 Nougat 处理 PDF，再用 VLM 处理棘手的页面。

### 手写内容

这仍是最难的子任务。印刷 + 手写混合场景（医生笔记、填好的表单）中，OCR 流水线在成本上仍优于 VLM。纯手写的 VLM 正在进步（Claude 4.7、PaliGemma 2）。

### 2026 年方案

对于一个新的文档 AI 项目：

- 大规模纯印刷发票：LayoutLMv3 + 规则，成本高效。
- 混合文档（科学 + 手写 + 表单）：VLM 原生（PaliGemma 2 或 Qwen2.5-VL）。
- 完整 arXiv 摄取：Nougat 处理数学，VLM 处理图表。
- 受监管场景：OCR 流水线 + VLM 校验器交叉核对。

```figure
mm-doc-layout
```

## Use It

`code/main.py`：

- 一个玩具版版式感知 tokenizer：给定 (text, bbox) 对，产出 LayoutLMv3 风格的输入。
- 一个 Donut 风格的任务 schema 生成器：面向表单的 JSON 模板。
- 比较 OCR 流水线、Donut、Nougat 与 VLM 原生每页的 token 预算。

## Ship It

本课产出 `outputs/skill-document-ai-stack-picker.md`。给定一个文档 AI 项目（领域、规模、质量、监管），在 OCR 流水线、免 OCR 专才与 VLM 原生之间做选择。

## Exercises

1. 你的项目每天处理 1000 万张发票。哪种技术栈能在不损失精度的前提下把每页成本降到最低？

2. 为什么 LayoutLMv3 在表单 QA 上优于纯 CLIP 的 VLM，却在场景文本上表现更差？bbox 输入流放弃了什么？

3. Nougat 生成 LaTeX。给出一个 VLM 原生输出在 LaTeX 保真度上胜过 Nougat 的测试用例，以及一个 Nougat 胜出的用例。

4. 阅读 PaliGemma 2 论文（Google，2024）。与 PaliGemma 1 相比，提升文档精度的关键训练数据新增是什么？

5. 设计一个监管安全的混合方案：OCR 流水线为主，VLM 作为二级交叉核对。如何消解两者不一致？

## Key Terms

| 术语 | 常见说法 | 实际含义 |
|------|-----------------|------------------------|
| OCR pipeline | “Tesseract 风格” | 分阶段栈：检测 -> OCR -> 版式 -> 规则；确定性、脆弱 |
| OCR-free | “Donut 风格” | 跳过显式 OCR 的图像到输出 transformer；单模型 |
| Layout-aware | “LayoutLM” | 输入包含每个 token 的 bbox 坐标；跨模态统一掩码 |
| VLM-native | “前沿 VLM” | 把页面图像直接以高分辨率喂给 Claude/GPT/Qwen VLM；无流水线 |
| DocVQA | “文档 benchmark” | 文档 VQA 标准评测；引用最多的分数 |
| Markup output | “LaTeX / MD” | 用结构化输出格式替代自由文本；便于下游自动化 |

## Further Reading

- [Li 等 —— TrOCR（arXiv:2109.10282）](https://arxiv.org/abs/2109.10282)
- [Blecher 等 —— Nougat（arXiv:2308.13418）](https://arxiv.org/abs/2308.13418)
- [Huang 等 —— LayoutLMv3（arXiv:2204.08387）](https://arxiv.org/abs/2204.08387)
- [Kim 等 —— Donut（arXiv:2111.15664）](https://arxiv.org/abs/2111.15664)
- [Wang 等 —— DocLLM（arXiv:2401.00908）](https://arxiv.org/abs/2401.00908)
