---
name: skill-rag-pipeline
description: 从第一性原理出发构建并调试 RAG 流水线
version: 1.0.0
phase: 11
lesson: 6
tags: [rag, retrieval, embeddings, vector-search, llm-engineering]
---

# RAG 流水线模式

每个 RAG 系统都遵循这个模式：

```
documents -> chunk -> embed -> store
query -> embed -> search(top_k) -> build_prompt -> generate
```

索引按文档各做一次。查询在每个用户请求时发生。

## 何时使用 RAG

- LLM 需要访问私有或最新文档
- Fine-tuning 太贵，或更新太慢
- 你需要为答案引用来源
- 知识库变化频繁

## 何时不要使用 RAG

- 答案是 LLM 已经具备的通用知识
- 任务是创意型（写作、头脑风暴）而非事实型
- 你需要模型采用特定的推理风格（用 fine-tuning）

## 实施清单

1. 把文档切分成 256-512 token 的片段，重叠 50 token
2. 用一致的 embedding 模型为每个块做 embedding
3. 把 embedding 连同原文存入向量数据库
4. 查询时，用同一个模型为用户问题做 embedding
5. 通过 cosine similarity 召回 top-k（5-10）最相似的块
6. 构建 prompt：system 指令 + 召回 context + 用户问题
7. 生成答案，并使其扎根于召回的 context
8. 返回答案并附来源引用

## 常见错误

- 索引和查询使用不同的 embedding 模型（向量不兼容）
- 块太小（丢失上下文）或太大（稀释相关性）
- 块之间不留重叠（在边界处切断句子）
- 文档变化后忘记重建索引
- 只把召回的块返回给用户，而不生成连贯的答案
- 事实型 RAG 查询没有设 temperature=0（temperature 越高 = 幻觉越多）

## 调试召回

如果正确的块没有被召回：
1. 打印 query embedding，确认其非零
2. 手动检查一个已知相关块的 cosine similarity
3. 尝试改写 query，使其贴合文档用词
4. 核实索引时与查询时使用的是同一个 embedding 模型
5. 检查相关内容是否在分块过程中丢失

## 生产参数

- Chunk size：256-512 token
- Overlap：50 token（块大小的 10-20%）
- Top-k：大多数用例取 5-10
- Temperature：事实型答案用 0
- Embedding 模型：text-embedding-3-small（成本高效）或 text-embedding-3-large（准确率更高）
