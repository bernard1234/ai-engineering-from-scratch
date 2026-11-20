---
name: skill-advanced-rag
description: 用 hybrid search、rerank 和 evaluation 构建生产级 RAG
version: 1.0.0
phase: 11
lesson: 7
tags: [rag, hybrid-search, bm25, reranking, hyde, evaluation]
---

# Advanced RAG 模式

基础 RAG：embed query -> vector search -> top-k -> generate。
Advanced RAG：embed query + BM25 -> fuse ranks -> rerank -> top-k -> generate。

```
query -> [vector search (top-50)] -+-> RRF fusion -> reranker (top-5) -> prompt -> LLM
                                   |
query -> [BM25 search (top-50)]  --+
```

## 何时从基础 RAG 升级

- 检索质量跌破 70% Recall@5
- 用户反馈答案错误或无关
- 语料库增长到 100K chunks 以上
- query 使用的词汇与文档不同
- 多跳（multi-hop）问题持续失败

## 实施清单

1. 在向量索引之外再加上 BM25 索引
2. 并行执行两种检索（各取 top-50）
3. 用 Reciprocal Rank Fusion（k=60）合并
4. 用 cross-encoder 对候选结果 rerank
5. 取 top-5 放进最终 prompt
6. 在测试集上加上 faithfulness evaluation

## 技术选型指南

- **Hybrid search**：生产环境始终使用。在 query 时没有额外成本。
- **Reranking**：当 Recall@50 好但 Recall@5 差时使用。增加 50-200ms 延迟。
- **HyDE**：当 query 模糊，或与文档使用的词汇不同时使用。增加一次 LLM 调用。
- **Parent-child chunks**：当小 chunk 缺少上下文、而大 chunk 稀释相关性时使用。
- **Metadata filtering**：当语料有清晰的类别（日期、来源类型、部门）时使用。
- **Query decomposition**：用于需要从多篇文档取信息的多跳问题。

## 常见错误

- BM25 和向量检索使用不同的 chunk 集合（它们必须检索同一个语料库）
- rerank 用的候选池太小（top-10 太少；用 top-50）
- 对每个 query 都加 HyDE（只有当词汇不匹配才是瓶颈时它才有帮助）
- 不评估改动（每种技术前后都要测 Recall@k）
- 在测出失败点之前就把流水线过度设计

## Evaluation 工作流

1. 创建 50+ 个带有已知答案 chunk 的测试问题
2. 对每种检索方法测量 Recall@5 和 Recall@10
3. 对检索成功的 query，测量生成答案的 faithfulness
4. 随着语料库增长，每周跟踪指标
5. 在添加更多技术之前，先逐个排查失败案例
