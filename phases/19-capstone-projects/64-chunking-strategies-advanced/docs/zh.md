# Chunking 策略对比

> chunking 决定了你的检索器究竟能捞回什么。边界切错了，再强的 embedding 模型、再好的 reranker、再聪明的 LLM 都救不回来。

**Type:** Build
**Languages:** Python
**Prerequisites:** 第 11 阶段第 04 课（embeddings）、第 06 课（RAG）、第 07 课（advanced RAG）；第 19 阶段 Track B 基础（第 20 至 29 课）
**Time:** ~90 分钟

## Learning Objectives
- 从零实现五种 chunking 策略：固定窗口、句子、递归切分、语义聚类，以及结构化 markdown 标题。
- 在一个带 gold 标注答案 span 的 fixture 语料上测量 recall@k，并解释为何某种策略在散文上获胜、另一种策略在技术文档上获胜。
- 读懂 chunk 长度分布，识别每种策略注入的失效模式：孤立句子、从符号中间切开、只有标题的 chunk、语义漂移。
- 不跑基准，仅凭三个属性为新语料挑出默认策略：文档类型、平均段落长度，以及格式是否带有显式结构。

## 问题场景

每条 RAG pipeline 都始于把源文档切成足够小（能塞进 embedding 模型）又足够大（每片都承载一个自足的想法）的片段。切在哪里的选择不是超参数。它是检索器可能返回内容的上界。

一个问“预算中止阈值长什么样”的查询，只有当承载该中止阈值的 chunk 可达时才能成功。如果固定窗口切分器把阈值数值与周围上下文切开，embedding 就会移到另一个簇，BM25 分数下降，reranker 看到噪声，LLM 生成的答案就是错的。2024 年的论文 “LongRAG: Enhancing Retrieval-Augmented Generation with Long-context LLMs” 测到，仅凭 chunking 选择就带来 35 个百分点的检索 recall 绝对波动。2025 年关于上下文 chunk 标题的后续工作缩小了差距，但没有闭合它。

本课并排构建五种策略，在一个带 gold 标注答案 span 的 fixture 语料上运行它们，让你自己读 recall 数字。

## 核心概念

```mermaid
flowchart LR
  Doc[Source Document] --> S1[Fixed Window]
  Doc --> S2[Sentence]
  Doc --> S3[Recursive Split]
  Doc --> S4[Semantic Cluster]
  Doc --> S5[Structural Markdown]
  S1 --> Chunks1[Chunks]
  S2 --> Chunks2[Chunks]
  S3 --> Chunks3[Chunks]
  S4 --> Chunks4[Chunks]
  S5 --> Chunks5[Chunks]
  Chunks1 --> Index[Embedding Index]
  Chunks2 --> Index
  Chunks3 --> Index
  Chunks4 --> Index
  Chunks5 --> Index
  Index --> Eval[Recall@k vs Gold Spans]
```

### 固定窗口

暴力基线。每 N 个字符切一刀。可选地重叠，使在位置 N 被切断的句子完整出现在从位置 N - overlap 开始的 chunk 里。快、确定性强、边界很糟。把它当对照，而不是默认。

### 句子

用正则或简单状态机在句子边界处切分。把一句或多句打包进一个 chunk，直到达到目标字符预算。不再从词中间切。仍会从段落中间、小节中间切。许多早期 RAG pipeline 的默认，也是没有其他结构可依的散文的合理选择。

### 递归切分

2023 年前后库流行起来的层级策略。先尝试用最强的分隔符切（双换行、段落），不行就退到下一个（单换行），再退到句子，最后退到字符。当 chunk 符合预算时递归终止。对结构不一致的文档很强，因为它逐区域自适应。

### 语义聚类

为每个句子做 embedding。把共享主题质心的连续句子聚成一簇。每当与质心的运行相似度跌破阈值就切一刀。边界反映的是含义，不是字符。构建较慢且依赖 embedding 模型，但对在段落内部切换主题的文档有韧性。

### 结构化 markdown 标题

对带有显式结构的文档（markdown、reStructuredText、RFC 风格编号小节），在标题边界处切分。每个 chunk 由标题及其下方的全部内容组成，直到同级或更高级的下一个标题。每个主题的 chunk 最小，但只有语料格式良好时才可用。

### recall@k 如何度量边界选择

一条 gold 标注查询带着答案 span 在源文档中的精确字符偏移。切分之后，你问：检索器返回的前 k 个 chunk 中有任何一个与 gold span 重叠吗？有，则该查询的 recall@k 为 1；没有则为 0。在整个查询集上取平均。对每种策略跑同样的评测，差距就告诉你哪种边界策略能在你的语料上活下来。

```figure
ci-chunk-boundaries
```

## Build It

`code/main.py` 实现了：

- `fixed_window(text, size, overlap)` —— 基线。
- `sentence_chunks(text, target)` —— 简单句子打包器。
- `recursive_split(text, separators, target)` —— 层级递归。
- `semantic_chunks(text, similarity_threshold)` —— 在确定性 mock embedding 之上做基于质心的聚类。
- `structural_markdown(text)` —— 标题感知的切分器。
- `mock_embed(text, dim)` —— 基于哈希的 embedding，使循环可离线运行。
- `DenseIndex` —— 与第 19 阶段 Track B 混合检索课使用的相同形状。
- `eval_recall(strategy, corpus, queries, k)` —— 比较循环。
- 一个 `main()`，在 fixture 语料上运行每一种策略并打印 recall@k 表。

运行它：

```bash
python3 code/main.py
```

输出是一张小表，每行一个策略，每列一个 k。在结构化 fixture 上句子切分落败。在 markdown fixture 上结构化 markdown 获胜。在混合 fixture 上递归切分守住阵地，因为递归会自适应。在没有任何有用结构线索的散文 fixture 上，语义聚类获胜。

## 表格掩盖不了的失效模式

**孤立句子。** 句子打包产生的 chunk 可能漏掉主题句。于是 embedding 指向了错误的簇。

**从符号中间切开。** 在代码或 YAML 内部使用固定窗口，会把一个标识符切成两半。两半都 embed 成噪声。

**只有标题的 chunk。** 结构化 markdown 会产生只含 `## Title` 的 chunk。把它们过滤掉，或把下一个 chunk 的第一段挂上去。

**语义漂移。** 当语料主题统一时，语义聚类会切得太少。一个 5000 字符的 chunk 把许多具体答案塞进一个弥散的 embedding。把语义聚类与硬性字符上限结合。

**过期的 embedding。** 语义聚类会用到 embedding 模型。如果你换了模型，chunk 也会跟着变。把 chunk 模型与检索模型分开固定，或者一起重建索引。

## 不跑基准也能选出默认策略

三个属性决定新语料的默认 chunker。

| 属性 | 取值 | 默认选择 |
|----------|-------|---------|
| 文档类型 | 无结构的散文 | Recursive split，目标 800 |
| 文档类型 | Markdown / RFC / API 文档 | Structural markdown |
| 文档类型 | 代码 | AST 感知（超出本课范围；见第 19 阶段第 02 课） |
| 段落长度 | 长、单一主题 | Sentence，目标 500 |
| 段落长度 | 短、主题混杂 | Semantic，阈值 0.6 |

拿不准时，就选递归切分。它是最强的单策略基线。

## Use It

生产模式：

- 在交付新 pipeline 之前先跑 eval；不要盲信你所用库的默认策略。
- 每当更换 embedding 模型或语料组合，就重跑 eval；胜者是随语料而变的。
- 把策略名持久化到每个 chunk 的元数据里，以便日后归因回退。

## Ship It

第 69 课的 Track F 端到端 RAG 系统把这里选出的 chunker 用作第一阶段。第 68 课的 eval harness 读取的 recall@k 形状，与本课 `eval_recall` 返回的形状相同。挑出在你的语料上获胜的策略，把它向前传递。

## Exercises

1. 加入第六种策略：用 `tiktoken` 而非字符计数做 token 窗口。在同一个 fixture 上与固定窗口比较。
2. 向散文 fixture 中注入 30% 比例的代码块。重跑表格。解释为何除结构化 markdown 外每一种策略的 recall 都下降。
3. 把确定性 embedding 换成你项目真实 provider 的 embedding。测量语义聚类 recall 的差值。报告策略之间的差距是扩大还是缩小。
4. 为每个 chunk 增加一个 `summary` 字段：一句话的质心描述。把 summary 追加到 chunk 正文后重跑 eval。测量 recall 的提升。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Recall@k | “我们拿到正确的 chunk 了吗？” | 前 k 个 chunk 中任一个与 gold 答案 span 重叠的查询所占比例 |
| Chunk overlap | “滑动窗口” | 把上一个 chunk 的最后 N 个字符重新包含进下一个 chunk |
| Structural splitter | “标题感知的 chunk” | 在 H1/H2/H3 边界处切分；标题文本属于该 chunk 的一部分 |
| Semantic chunker | “主题感知的 chunk” | 对句子做 embedding，按质心相似度聚类，在漂移处切分 |
| Centroid drift | “主题跳变” | 运行均值与下一个句子之间的余弦相似度跌破阈值 |

## Further Reading

- [LongRAG: Enhancing Retrieval-Augmented Generation with Long-context LLMs (arXiv 2406.15319)](https://arxiv.org/abs/2406.15319)
- [Anthropic, Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval)
- [LlamaIndex, Chunking strategies for production RAG](https://docs.llamaindex.ai/en/stable/optimizing/production_rag/)
- 第 11 阶段第 06 课 —— RAG 基础
- 第 11 阶段第 07 课 —— advanced RAG
- 第 19 阶段第 65 课 —— 对这里产出的 chunk 排序的混合检索
- 第 19 阶段第 68 课 —— 在生产中为策略选择打分的 eval harness
