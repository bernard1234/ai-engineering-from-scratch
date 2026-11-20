---
name: codebase-rag
description: 构建一个跨 repo 的语义搜索系统，具备 AST 感知切块、混合检索、增量重建索引和带引用的答案。
version: 1.0.0
phase: 19
lesson: 02
tags: [capstone, rag, code-search, tree-sitter, qdrant, bm25, hybrid-retrieval]
---

给定 10 个以上、总计至少 2M 行代码的 repo，构建一条摄入流水线、一个混合索引，以及一个带引用强制的查询 agent，用可验证的 file:line 锚点回答跨 repo 的问题。

构建计划：

1. 用 tree-sitter 解析每个文件。在函数和类节点边界处切块。存储 `{repo, path, start_line, end_line, symbol, body}`。
2. 用 Claude Haiku 4.5 或 Gemini 2.5 Flash 为每个 chunk 生成摘要，系统提示词走 prompt caching。把一句话摘要与 chunk 放在一起存放。
3. 索引到三种结构：Qdrant（dense，Voyage-code-3 或 nomic-embed-code）、Tantivy（带字段权重的 BM25）和 kuzu（imports、calls、继承的符号图边）。
4. 构建三节点的 LangGraph 查询 agent：retrieve（dense 并行 BM25）、rerank（Cohere rerank-3 或 bge-reranker-v2-gemma-2b）、synth（Claude Sonnet 4.7 配 prompt caching，并强制 file:line 引用）。
5. 后置过滤：拒绝任何缺少可验证 `(repo/path:start-end)` 锚点的论断；重新询问或丢弃。
6. 接一个 git push webhook，计算符号级 diff，只重新 embed 变化的 chunk。目标：2M LOC 的仓库群中，50 文件的 commit 在 60s 内可搜索。
7. 用 100 题留出集评测。报告 MRR@10、nDCG@10、引用忠实度和延迟分位数。
8. 跑一个每周漂移任务，重新执行评测，并在 MRR@10 下降 > 5% 时告警。

Assessment rubric:

| Weight | Criterion | Measurement |
|:-:|---|---|
| 25 | 检索质量 | 100 题留出集上的 MRR@10 与 nDCG@10 |
| 20 | 引用忠实度 | 带可验证 file:line 锚点的答案论断比例 |
| 20 | 延迟与规模 | 在索引语料规模下 10k QPS 时的 p95 查询延迟 |
| 20 | 增量索引正确性 | 50 文件 commit 从 git push 到可搜索的耗时 |
| 15 | UX 与答案格式 | 引用可点击性、片段预览、追问入口 |

Hard rejects:

- 用固定大小 token 切块代替 AST 感知切块。这会污染生成代码占比高的语料。
- 只有余弦检索，既无 BM25 也无重排。已知在精确符号名查询上会失败。
- 答案缺少强制性的 file:line 引用。
- 每次 git push 都全量重新 embed；必须是增量的。

Refusal rules:

- 拒绝在未读许可证的情况下索引 repo。有些许可证禁止在第三方向量库中做 embedding。
- 拒绝回答声称引用了索引从未见过的文件的查询；返回前始终核实锚点。
- 拒绝在 p95 超过 4s 时给出答案；改为返回部分结果加一个跟进句柄。

Output：一个 repo，包含摄入流水线、LangGraph 查询 agent、100 题标注评测集、一个 Langfuse 仪表盘链接，以及一篇写明你修复的三种检索失败模式（生成代码污染、长尾符号召回、跨 repo 符号解析）和对应精确改动的说明。
