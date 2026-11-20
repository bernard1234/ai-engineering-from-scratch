# 多模态 RAG 与跨模态检索

> vision-native 文档 RAG 只是一个切片。生产环境的多模态 RAG 范围更广 —— 在文本、图像、音频和视频之间做检索，以支撑诸如旅行规划（"帮我找一家安静、有自然光的素食早午餐"）、医疗分诊（"这张照片加这些记录对应什么伤情"）、电商（"和我这张自拍相似、属于我尺码的穿搭"）以及现场服务（"结合这个发动机声音和零件照片做诊断"）这类工作流。2025 年的三篇综述 —— Abootorabi 等、Mei 等、Zhao 等 —— 把子问题条理化：cross-modal retrieval、retrieval fusion、generation grounding、multimodal evaluation。本课解读这些综述，并设计一条生产级流水线。

**Type:** Build
**Languages:** Python（stdlib，带 fusion 的跨模态 retriever + grounded 生成器）
**Prerequisites:** Phase 12 · 23（ColPali）、Phase 11（RAG 基础）
**Time:** ~180 分钟

## Learning Objectives

- 设计 cross-modal retrieval：text → image、image → text、audio → video 等。
- 比较三种 fusion 策略：score fusion、attention-based fusion、MoE fusion。
- 解释 generation grounding：当来源混杂多种模态时，"引用你的来源"具体长什么样。
- 说出 2025 年三篇权威的多模态 RAG 综述及其子问题分类体系。

## 问题场景

单模态 RAG 已是成熟的模式：对 query 做 embedding、对 chunk 做 embedding、检索、塞进 LLM。而多模态 RAG 需要：

1. 多个检索头（每种模态的 embedding 都要落在兼容的空间里）。
2. 跨模态的检索结果融合。
3. 能跨模态引用来源的 generation grounding。
4. 覆盖跨模态信号的评测指标。

2025 年的几篇综述最终都收敛到同一套分类体系。

## 核心概念

### 跨模态检索

给定模态 A 的 query，检索模态 B 的文档。有三种模式：

1. 共享 embedding 空间。CLIP 和 CLAP 把 text + image / text + audio 的 embedding 映射到共享空间。跨模态余弦相似度可以直接使用。仅限于 CLIP 训练过的模态对。

2. 逐模态编码器 + 翻译层。文本编码器 + 图像编码器 + 一个小型 translator 模块在两个空间之间做映射。Gupta 等的 Sen2Sen 以及 2024 年的其他设计。灵活，但增加了复杂度。

3. 用 VLM 作编码器。用 VLM 的 hidden states 作为检索表示。VLM 支持的任何模态都能用。质量更高，成本也更高。

选择：text+image 用 CLIP / SigLIP 2；text+audio 用 CLAP；要达到前沿质量的跨模态效果，用 VLM hidden states。

### 融合策略

你检索到 10 条结果：5 张图片、3 段文本、2 段音频。怎么合并？

Score fusion（最便宜）。每种模态有自己的 retriever，各自返回分数。先在模态内做归一化，再求和。简单，通常奏效。

Attention-based fusion。把所有检索项拼接起来，让一个小型 attention 网络为其分配权重。需要训练。

MoE fusion。门控网络把请求路由到模态专属的 expert。不同 query 类型路由方式不同 —— 视觉类问题会给图像更高权重。

生产环境默认做法：score fusion，并对 query 的主导模态略作偏置。如果 A/B 在你的领域上显示出明显收益，再升级到 MoE。

### 生成接地

LLM 应当标注每一条论断是由哪个检索项支撑的。对于多模态：

- 文本来源：标准引用 `[1]`。
- 图片来源：`[img 3]` 并附简短 caption。
- 音频：`[audio 2 at 0:34]`。

用 grounding-aware 数据训练生成器：训练目标中的每条论断都标注来源索引。推理时模型便会自然地输出引用。

### 2025 年的综述

Abootorabi 等（arXiv:2502.08826，"Ask in Any Modality"）：多模态 RAG 的分类体系。覆盖 retrieval、fusion、generation。覆盖面最广。

Mei 等（arXiv:2504.08748，"A Survey of Multimodal RAG"）：聚焦子任务 benchmark 与失败模式。对评测设计很有用。

Zhao 等（arXiv:2503.18016）：以视觉为核心的综述。在 ColPali 系列工作上尤为扎实。

三篇合读，可以掌握截至 2025 年春季的最新进展。其中大部分子问题仍处于开放状态。

### MuRAG —— 奠基性论文

MuRAG（Chen 等，2022）是第一个多模态 RAG。它从多模态 KB 中检索图像 + 文本，再生成答案。在 VLM 浪潮之前就展示了可行性。现代系统（REACT、VisRAG、M3DocRAG）都建立在它之上。

### 一个生产级旅行规划示例

Query："帮我找一家安静、有自然光的素食早午餐。"

流水线：

1. 拆解 query。"安静" → 音频 / 评论关键词；"素食早午餐" → 菜单项；"自然光" → 图像特征。
2. 按模态分别检索：
   - 对评论做文本检索："素食早午餐、安静氛围"。
   - 对餐厅照片做图像检索："自然光、通透"。
   - 对环境音片段做音频检索："低分贝、无音乐"。
3. 融合分数。每家餐厅得到一个综合分。
4. top-k 餐厅 → 携带全部证据的 VLM 生成器 → 带引用的答案。

这已经远超 text-RAG。每种模态都补充了纯文本会漏掉的信号。

### Agentic 多模态 RAG

多跳：如果第一轮检索没有得到高置信度的答案，LLM 会改写查询并再次检索。Phase 14 的 agentic RAG 模式在这里同样适用。例如：

- 检索初始 top-10 → LLM 判断"噪音太多，过滤 <40 dB" → 重新检索。
- 检索图像 → LLM 发现其中一张有菜单 → 检索菜单文本 → 作答。

这增加了复杂度，但能处理单次检索搞不定的 query。

### 评测

跨模态评测仍不成熟。常用替代指标：

- 逐模态的 Recall@k。
- 融合后的 top-k 准确率。
- 人工判定的端到端满意度。
- 任务级指标（完成的预订数、成交的购买数）。

目前没有覆盖所有模态的标准 benchmark。多数论文在领域特定任务上评测。

```figure
contrastive-matrix
```

## Use It

`code/main.py`：

- 三个 mock retriever（text、image、audio），运行在同一个餐厅语料上。
- score fusion，用可配置权重合并各模态分数。
- 一个生成器桩，输出带引用的最终答案。
- 一个简单的 agentic 循环，在置信度低时改写 query。

## Ship It

本课产出 `outputs/skill-multimodal-rag-designer.md`。给定一份含多模态查询流的产品规格，它负责设计 retriever、fusion、生成器与评测方案。

## Exercises

1. 设计一个医疗分诊的多模态 RAG：query = 伤情照片 + 文本症状。各模态从什么 KB 检索？

2. Score fusion 就是一个简单的加权求和。它存在哪种失败模式，而 MoE fusion 能避免？

3. 阅读 Abootorabi 等的分类体系（第 3 节）。三个经典子问题是什么，它们如何映射到你选定的产品？

4. 为旅行规划多模态 RAG 设计一份评测规格。哪些指标覆盖图像召回、音频召回和综合正确性？

5. Agentic 多跳 RAG 每多一轮往返就要付出延迟代价。在什么样的 query 难度下，准确率收益才值得这点延迟？

## Key Terms

| 术语 | 常被说成 | 实际含义 |
|------|-----------------|------------------------|
| Cross-modal retrieval | "用一种模态查询，检索另一种" | 文本 query 检索图像；图像 query 检索文本；需要共享空间或翻译层 |
| Score fusion | "分数合并" | 各模态检索分数的加权求和；最简单的 fusion |
| MoE fusion | "模态路由 expert" | 门控网络为每个 query 决定该信任哪个模态的分数 |
| Grounded generation | "引用你的来源" | 答案中的每条论断都标注来源索引 |
| MuRAG | "第一个多模态 RAG" | 2022 年确立多模态 RAG 模式的论文 |
| Agentic multi-hop | "改写后重试" | 首轮置信度低时，LLM 重新查询 retriever |

## Further Reading

- [Abootorabi 等 —— Ask in Any Modality（arXiv:2502.08826）](https://arxiv.org/abs/2502.08826)
- [Mei 等 —— A Survey of Multimodal RAG（arXiv:2504.08748）](https://arxiv.org/abs/2504.08748)
- [Zhao 等 —— Vision RAG Survey（arXiv:2503.18016）](https://arxiv.org/abs/2503.18016)
- [Chen 等 —— MuRAG（arXiv:2210.02928）](https://arxiv.org/abs/2210.02928)
- [Liu 等 —— REACT（arXiv:2301.10382）](https://arxiv.org/abs/2301.10382)
