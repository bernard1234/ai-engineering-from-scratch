---
name: production-rag
description: 部署一个受监管领域的 RAG chatbot，带角色 + 管辖过滤、prompt caching、防护和实时漂移监控。
version: 1.0.0
phase: 19
lesson: 08
tags: [capstone, rag, chatbot, regulated, llama-guard, nemo-guardrails, ragas, langfuse]
---

给定一个受监管领域语料（法律合同、临床试验方案、保险保单或类似），部署一个 chatbot，用可验证引用作答、遵守角色与管辖访问策略，并接受漂移监控。

构建计划：

1. 用 docling 或 Unstructured 解析语料；把视觉密集文档路由到 ColPali。产出带角色与管辖标签的 chunk。
2. 稠密索引（Voyage-3 或 Nomic-embed-v2）进 pgvector + pgvectorscale；稀疏 BM25 经 Tantivy。
3. 接好 LangGraph 对话 agent：检索（按 role + jurisdiction 过滤，稠密+BM25 混合，reciprocal rank fusion）、重排序（bge-reranker-v2-gemma-2b 或 Voyage rerank-2）、合成（带 prompt caching 的 Claude Sonnet 4.7）。
4. 用稳定前缀组装 prompt：system 前言 -> 策略块 -> 重排序后的 context -> 用户查询。目标 60-80% prompt cache 命中率。
5. 防护：输入与输出上跑 Llama Guard 4，NeMo Guardrails v0.12 rails 处理域外与策略禁止问题，Presidio 擦除输出 PII，引用强制做后置过滤。
6. 构建 200 题专家标注、含（answer, citations）的 golden set。按精确引用匹配、答案正确性、RAGAS faithfulness 打分。
7. 构建 50 条 prompt 的红队（PAIR、TAP、PII 提取、域外、跨管辖探针）。
8. Arize Phoenix 漂移看板每周跟踪检索 nDCG 与引用 faithfulness；下降 5% 即告警。
9. Langfuse 成本报告：prompt cache 命中率、每查询 token 数、按阶段的 $/查询。

评估评分表：

| 权重 | 标准 | 衡量方式 |
|:-:|---|---|
| 25 | RAGAS faithfulness + answer relevance | 在 200 题 golden set 上的在线分数 |
| 20 | 引用正确性 | 带可验证来源锚点的答案比例 |
| 20 | 防护覆盖率 | Llama Guard 4 通过率 + 越狱套件结果 |
| 20 | 成本 / 延迟工程 | Prompt cache 命中率、p95 延迟、$/查询 |
| 15 | 漂移监控看板 | 实时 Phoenix 看板，带每周检索质量趋势 |

硬性驳回：

- 任何泄漏跨管辖数据的 chatbot。role+jurisdiction 过滤必须在检索之前执行，而不是之后。
- 破坏缓存前缀的合成 prompt（在 system 与 context 之间重排策略）。这会毁掉缓存经济学。
- 没有记录红队运行的防护配置。
- 没有引用的答案；没有可验证锚点的引用。

拒绝规则：

- 拒绝在受监管领域中部署而每个 chunk 上没有管辖标签。
- 拒绝在专家标注的 golden set 问题上训练检索。污染会摧毁评估可信度。
- 拒绝在 README 中没有明确的 SOC2/HIPAA/GDPR 适用性矩阵时声称“合规”。

产出：一个仓库，包含摄取流水线、LangGraph 对话 agent、200 题 golden set、50 条 prompt 红队、Phoenix 漂移看板、Langfuse 成本看板，以及一份说明你观察到的前三个引用断裂模式以及每个对应的检索或 prompt 修复的总结。
