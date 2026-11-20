---
name: skill-embedding-patterns
description: embedding、向量检索与相似度计算的生产级模式
version: 1.0.0
phase: 11
lesson: 4
tags: [embeddings, vectors, similarity, search, chunking, quantization]
---

# Embedding 模式

每个 embedding 工作流都遵循这份契约：

```
text -> embed(text) -> vector (float array)
similarity(vector_a, vector_b) -> score (float)
```

embedding 模型和相似度度量是唯一真正重要的两个决策。其余都是管道工程。

## 何时使用 embedding

- 跨文档的语义搜索（找含义，而不是找关键词）
- 相似条目的聚类（工单、商品评论、bug 报告）
- 基于最近邻的分类（用与标注示例的相似度给新条目打标签）
- 推荐系统（找出与用户喜欢的条目相似的条目）
- 去重（用相似度阈值找出近似重复内容）

## 何时不要使用 embedding

- 精确关键词匹配（用全文搜索）
- 结构化查询（用 SQL、过滤器）
- 人工标注更快的极小数据集（少于 100 条）
- 可解释性比准确率更重要的任务（embedding 是不透明的）

## 模型选择

根据你的约束来选：

- **需要 API、追求性价比**：OpenAI text-embedding-3-small（1536d，$0.02/1M tokens）
- **需要最高准确率**：Voyage-3（1024d，$0.06/1M tokens，MTEB 最高）
- **需要本地/私有**：BGE-M3（1024d，免费，多语言，建议用 GPU）
- **需要快速的本地原型**：all-MiniLM-L6-v2（384d，免费，可在 CPU 上运行）
- **需要多语言**：Cohere embed-v3（1024d）或 BGE-M3（两者多语言都强）

规则：绝不要在索引和查询之间混用不同的 embedding 模型。不同模型的向量处在互不兼容的空间里。

## Chunking 规则

1. 目标每块 256-512 token，重叠 50 token
2. 能避免就绝不要在句子中间切分
3. 每块都附带 metadata（源文件、章节标题、位置）
4. 对结构化文档（Markdown、HTML），先按标题边界切分
5. 通过搜索已知答案并检查召回结果来测试分块质量

## 相似度度量选择

- **Cosine similarity**：默认选择，能处理变长文本，已归一化
- **Dot product**：当向量已做单位归一化时使用（OpenAI 模型就是），略快
- **Euclidean distance**：用于聚类，当绝对位置有意义时

向量归一化后，三者给出的排序完全相同。只有在向量未归一化时，选择才有影响。

## 存储优化

三级压缩，可叠加：

1. **Matryoshka 截断**：降低维度（1536 -> 256，节省 6 倍，准确率损失 3-5%）
2. **Float16 quantization**：每个维度的存储减半（节省 2 倍，准确率损失 <1%）
3. **Binary quantization**：每维 1 bit（节省 32 倍，准确率损失 5-10%，需配合重打分）

生产模式：先对全量语料做二值检索，再用 float32 向量对前 1000 名重新打分。

## Retrieve-then-rerank

两阶段流水线，追求最佳准确率：

1. Bi-encoder 召回前 100 个候选（快，使用预计算的 embedding）
2. Cross-encoder 重排到前 10（慢，逐个处理 query-doc 对）

在精确率指标上，这比单阶段检索高 10-15%。当准确率比延迟更重要时使用。

## 常见错误

- 索引和查询使用不同的 embedding 模型
- 对整篇文档做 embedding 而不是分块（embedding 变成所有内容的平均）
- 做 cosine similarity 之前不归一化向量（多数模型会预归一化，但要核实）
- 忽略块间重叠（在边界处被切开的句子会丢失上下文）
- 只存向量不存原文（检索时两者都需要）
- 模型更换后不重新 embedding（旧向量不兼容）
- 只按准确率选维度（存储和延迟随维度线性增长）

## 调试 embedding

如果检索结果很差：

1. 确认 query embedding 非零（空输入或纯空白输入会产生零向量）
2. 手动检查一个已知相关文档的相似度分数
3. 尝试改写 query，使其贴合文档用词
4. 检查分块边界，确保相关内容没有被切散到多个块里
5. 对比不同度量（cosine、dot、euclidean）下的 top-k 结果，以发现归一化问题
6. 用一个必然匹配的 query（从文档里复制一句话）测试，确认流水线本身能工作

## 生产参数

- Chunk size：256-512 token
- Chunk overlap：50 token（块大小的 10-20%）
- Top-k 召回：直接使用取 5-10，用于 rerank 取 50-100
- 相似度阈值：cosine 用 0.7 以上（低于此值的结果通常不相关）
- 批量 embedding：每次 API 调用处理 100-500 条文本以提升吞吐
- 索引重建：模型更换或文档大幅更新时重新 embedding
