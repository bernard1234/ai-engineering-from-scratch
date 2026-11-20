# Capstone 02 — RAG over Codebase（跨 repo 语义搜索）

> 2026 年，每一家认真做工程的组织都跑着一个理解语义而不只是字符串的内部代码搜索。Sourcegraph Amp、Cursor 的 codebase answers、Augment 的企业图谱、Aider 的 repomap、Pinterest 的内部 MCP——同一个形状。摄入许多 repo，用 tree-sitter 解析，对函数级和类级的 chunk 做 embedding，混合检索，重排，带引用作答。这个 capstone 要你构建一个能处理 10 个 repo 共 2M 行代码、并且在每次 git push 后都经得起增量重建索引的系统。

**Type:** Capstone
**Languages:** Python（ingestion）、TypeScript（API + UI）
**Prerequisites:** 第 5 阶段（NLP foundations）、第 7 阶段（transformers）、第 11 阶段（LLM engineering）、第 13 阶段（tools）、第 17 阶段（infrastructure）
**Phases exercised:** P5 · P7 · P11 · P13 · P17
**Time:** 30 小时

## 问题场景

到 2026 年，每个前沿编码 agent 都自带一层 codebase 检索，因为单靠 context 窗口解决不了跨 repo 的问题。Claude 的 1M token context 有帮助，但并没有消除对排序检索的需求。对原始 chunk 做朴素的余弦搜索，会在生成代码、monorepo 重复代码以及很少被 import 的长尾符号上污染结果。生产级答案是混合（dense + BM25）检索，作用于 AST 感知的 chunk，加一个重排器，并由符号引用图支撑。

你是通过索引一个真实的仓库群——而不是一个教程 repo——并测量 MRR@10、引用忠实度和增量新鲜度来学会它的。失败模式是基础设施层面的：一个 10 万文件的 monorepo，一次改动半个文件的 push，一个需要跨四个 repo 才能正确回答的查询。

## 核心概念

一条 AST 感知的摄入流水线用 tree-sitter 解析每个文件，抽取函数节点和类节点，并在节点边界而不是固定 token 窗口处切 chunk。每个 chunk 得到三种表示：dense embedding（Voyage-code-3 或 nomic-embed-code）、稀疏 BM25 词项，以及一句简短的自然语言摘要。摘要增加了第三种可检索模态——用户问“X 的授权是怎么做的”，而摘要里提到了“authz”，即使代码里只有 `check_permission`。

检索是混合式的。一个查询同时触发 dense 和 BM25 搜索，合并 top-k，把并集交给 cross-encoder 重排器（Cohere rerank-3 或 bge-reranker-v2-gemma-2b）。重排后的列表交给长上下文综合器（Claude Sonnet 4.7 配 prompt caching，或自托管的 Llama 3.3 70B），并要求每条论断都按文件和行范围给出引用。没有引用的答案会被后置过滤器拒绝。

增量新鲜度是那个基础设施难题。git push 触发一次 diff：哪些文件变了，哪些符号变了。只有受影响的 chunk 重新 embed。受影响的跨文件符号边（imports、方法调用）被重新计算。索引保持一致，而无需每次提交都重新处理 2M 行。

## 架构

```
git push --> webhook --> ingest worker (LlamaIndex Workflow)
                           |
                           v
             tree-sitter parse + AST chunk
                           |
            +--------------+----------------+
            v              v                v
          dense        BM25 index       summary (LLM)
        (Voyage / bge)  (Tantivy)        (Haiku 4.5)
            |              |                |
            +------> Qdrant / pgvector <----+
                            |
                            v
                      symbol graph (Neo4j / kuzu)
                            |
  query --> LangGraph agent (retrieve -> rerank -> synth)
                            |
                            v
                 Claude Sonnet 4.7 1M context
                            |
                            v
                 answer + file:line citations
```

## 技术栈

- 解析：tree-sitter，覆盖 17 种语言语法（Python、TS、Rust、Go、Java、C++ 等）
- Dense embedding：Voyage-code-3（托管）或 nomic-embed-code-v1.5（自托管），bge-code-v1 作为兜底
- 稀疏索引：Tantivy（Rust）配 BM25F，按符号名与函数体做字段加权
- 向量库：Qdrant 1.12 配混合检索，或对 5000 万向量以下的团队用 pgvector + pgvectorscale
- Chunk 摘要模型：Claude Haiku 4.5 或 Gemini 2.5 Flash，走 prompt caching
- 重排器：Cohere rerank-3 或自托管的 bge-reranker-v2-gemma-2b
- 编排：摄入用 LlamaIndex Workflows，查询 agent 用 LangGraph
- 综合器：Claude Sonnet 4.7（1M context）配 prompt caching
- 符号图：Neo4j（托管）或 kuzu（嵌入式）存 import 与调用边
- 可观测性：每个检索 + 综合步骤一个 Langfuse span

```figure
ce-hybrid-retrieval
```

## Build It

1. **摄入遍历器。** 在每个 push hook 上遍历 git 历史。收集变更文件。对每个文件用 tree-sitter 解析，抽取函数节点和类节点及其完整源码跨度。产出 chunk 记录 `{repo, path, start_line, end_line, symbol, body}`。

2. **Chunk 摘要器。** 把 chunk 批量送进 Haiku 4.5 调用，系统前言走 prompt caching。提示词：“用一句话总结这个函数，点明它的公开契约和副作用。”摘要与 chunk 一同存放。

3. **Embedding 池。** 两条并行队列：dense（Voyage-code-3，批大小 128）与 summary（同一模型，但作用于摘要字符串）。把向量写入 Qdrant，payload 为 `{repo, path, start_line, end_line, symbol, kind}`。

4. **BM25 索引。** 字段加权的 Tantivy 索引：符号名权重 4，符号体权重 1，摘要权重 2。这既支持“找名为 X 的函数”，也支持“找做 X 这件事的函数”。

5. **符号图。** 对每个 chunk 记录边：imports（本文件用到 repo Z 的符号 Y）、calls（本函数调用类 C 的方法 M）、继承。存入 kuzu。查询时用来跨 repo 边界扩展检索。

6. **查询 agent。** 三节点的 LangGraph。`retrieve` 并行触发 dense 与 BM25，按 (repo, path, symbol) 去重。`rerank` 对 top-50 跑 cross-encoder，保留 top-10。`synth` 带着重排后的 chunk 调用 Claude Sonnet 4.7，缓存系统提示词，强制要求 file:line 引用。

7. **引用强制。** 解析模型输出；任何没有 `(repo/path:start-end)` 锚点的论断都会被标记为需重新询问或直接丢弃。只把带引用的答案返回给用户。

8. **增量重建索引。** 每次 webhook 时计算符号级 diff。只重新 embed 文本变化的 chunk。为 import 变化的 chunk 重算符号边。目标：在 2M LOC 的仓库群上，50 个文件的 push 在 60 秒内完成重建索引。

9. **Eval。** 标注 100 个跨 repo 问题及其黄金 file:line 答案。测量 MRR@10、nDCG@10、引用忠实度（带可验证锚点的论断比例）以及 p50/p99 延迟。

## Use It

```
$ code-rag ask "how is S3 multipart abort wired into our retry budget?"
[retrieve]  12 chunks dense + 7 chunks bm25, 16 unique after dedup
[rerank]    top-5 kept (cohere rerank-3)
[synth]     claude-sonnet-4.7, cache hit rate 68%, 2.1s
answer:
  Multipart aborts are triggered by `AbortMultipartOnFail` in
  services/uploader/retry.go:122-148, which decrements the per-bucket
  retry budget defined in config/budgets.yaml:34-51 ...
  citations: [services/uploader/retry.go:122-148, config/budgets.yaml:34-51,
              libs/s3client/multipart.ts:44-61]
```

## Ship It

交付物 skill 为 `outputs/skill-codebase-rag.md`。给定一个 repo 语料库，它搭起摄入流水线、混合索引和查询 agent，并为任何跨 repo 问题返回带引用的答案。评分标准：

| Weight | Criterion | How it is measured |
|:-:|---|---|
| 25 | 检索质量 | 100 题留出集上的 MRR@10 与 nDCG@10 |
| 20 | 引用忠实度 | 带可验证 file:line 锚点的答案论断比例 |
| 20 | 延迟与规模 | 在索引语料规模下 10k QPS 时的 p95 查询延迟 |
| 20 | 增量索引正确性 | 50 文件 commit 从 git push 到可搜索的耗时 |
| 15 | UX 与答案格式 | 引用可点击性、片段预览、追问入口 |
| **100** | | |

## Exercises

1. 把 Voyage-code-3 换成自托管的 nomic-embed-code。测量 MRR@10 差额。报告在开启重排后差距是否缩小。

2. 往语料里注入 20% 生成代码（LLM 产出的样板代码）并重新评测。观察检索被污染的情况。在 payload 里加一个 “generated” 标记，并对这些命中降权。

3. 在你的语料规模下 benchmark Qdrant 混合检索 vs pgvector + pgvectorscale。报告批大小为 1 时的 p99。

4. 加一个基于采样的漂移检查：每周重跑 100 题评测。MRR@10 下降 > 5% 时告警。

5. 扩展到跨语言符号解析：一个 Python 函数通过 gRPC 调用 Go 服务。用符号图把它们连起来。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| AST-aware chunking | “按函数切分” | 在 tree-sitter 节点边界而非固定 token 窗口处切代码 |
| Hybrid search | “dense + sparse” | 并行跑 BM25 与向量搜索，合并 top-k，再重排 |
| Cross-encoder rerank | “二阶段排序” | 把每个 (query, candidate) 对一起打分的模型，比余弦更准 |
| Prompt caching | “缓存系统提示词” | 2026 年 Claude / OpenAI 的能力，对重复的前缀 token 计费最高减免 90% |
| Symbol graph | “代码图” | 跨文件、跨 repo 的 imports、calls、继承边 |
| Citation faithfulness | “有据答案率” | 用户可通过点击锚点并阅读被引用跨度来验证的论断比例 |
| Incremental re-index | “push 到可搜索的时间” | 从 git push 到变更符号可被查询的挂钟时间 |

## Further Reading

- [Sourcegraph Amp](https://ampcode.com) — 生产级跨 repo 代码智能
- [Sourcegraph Cody RAG architecture](https://sourcegraph.com/blog/how-cody-understands-your-codebase) — 这个 capstone 的参考深度文章
- [Aider repo-map](https://aider.chat/docs/repomap.html) — tree-sitter 排序的 repo 视图
- [Augment Code enterprise graph](https://www.augmentcode.com) — 商业化的符号图 RAG
- [Qdrant hybrid search docs](https://qdrant.tech/documentation/concepts/hybrid-queries/) — 参考实现
- [Voyage AI code embeddings](https://docs.voyageai.com/docs/embeddings) — Voyage-code-3 细节
- [Cohere rerank-3](https://docs.cohere.com/reference/rerank) — cross-encoder 参考
- [Pinterest MCP internal search](https://medium.com/pinterest-engineering) — 内部平台参考
