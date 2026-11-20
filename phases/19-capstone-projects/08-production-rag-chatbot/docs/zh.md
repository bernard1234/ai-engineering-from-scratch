# Capstone 08 — 面向受监管垂直行业的生产级 RAG Chatbot

> Harvey、Glean、Mendable 和 LlamaCloud 在 2026 年都跑同一套生产形态。用 docling 或 Unstructured 摄取，视觉内容用 ColPali。混合搜索。用 bge-reranker-v2-gemma 重排序。用 Claude Sonnet 4.7 并以 60-80% 命中率的 prompt caching 做合成。用 Llama Guard 4 与 NeMo Guardrails 防护。用 Langfuse 与 Phoenix 观测。用 RAGAS 在 200 题 golden set 上评分。在一个受监管领域（法律、临床、保险）中构建一个，本 capstone 就是要通过 golden set、红队和漂移看板。

**Type:** Capstone
**Languages:** Python（流水线 + API）、TypeScript（聊天 UI）
**Prerequisites:** 第 5 阶段（NLP）、第 7 阶段（transformers）、第 11 阶段（LLM engineering）、第 12 阶段（multimodal）、第 17 阶段（infrastructure）、第 18 阶段（safety）
**Phases exercised:** P5 · P7 · P11 · P12 · P17 · P18
**Time:** 30 小时

## 问题场景

受监管领域的 RAG（法律合同、临床试验方案、保险保单）是 2026 年出货最多的生产形态，因为 ROI 显而易见、利害关系具体。Harvey（Allen & Overy）为法律构建了它。Mendable 交付开发者文档版本。Glean 覆盖企业搜索。模式是：高保真摄取、混合检索加重排序、带引用强制与 prompt caching 的合成、多层安全防护，以及持续漂移监控。

难的部分不是模型，而是管辖感知的合规（HIPAA、GDPR、SOC2）、引用级别的可审计性、成本控制（命中率高时 prompt caching 带来 60-90% 折扣）、经 RAGAS faithfulness 的幻觉检测，以及源文档更新而索引没跟上时的漂移检测。本 capstone 要求你在一个 200 题 golden set 上交出全部这些，并配一套红队测试。

## 核心概念

流水线有两侧。**摄取**：docling 或 Unstructured 解析结构化文档；ColPali 处理视觉丰富的文档；chunk 获得摘要、标签和基于角色的访问标签。向量进入 pgvector + pgvectorscale（5000 万向量以下）或 Qdrant Cloud；稀疏 BM25 并行运行。**对话**：LangGraph 处理记忆与多轮；每个查询跑混合检索，用 bge-reranker-v2-gemma-2b 重排序，用 Claude Sonnet 4.7（prompt 缓存）合成，输出经 Llama Guard 4 与 NeMo Guardrails，并发出一个以引用为锚的响应。

评估栈有四层。**Golden set**（200 条带引用的标注 Q/A）衡量正确性。**红队**（越狱、PII 提取尝试、域外问题）衡量安全性。**RAGAS** 每轮自动衡量 faithfulness / answer relevance / context precision。**漂移看板**（Arize Phoenix）每周监视检索质量与幻觉分数。

Prompt caching 是成本杠杆。Claude 4.5+ 与 GPT-5+ 支持缓存 system prompt + 检索到的 context。在 60-80% 命中率下，单次查询成本下降 3-5 倍。流水线必须为稳定的前缀（system prompt + 重排序后的 context 放在最前）而设计，以取得高缓存命中率。

## 架构

```
documents (contracts, protocols, policies)
      |
      v
docling / Unstructured parse + ColPali for visuals
      |
      v
chunks + summaries + role-labels + jurisdiction tags
      |
      v
pgvector + pgvectorscale  +  BM25 (Tantivy)
      |
query + role + jurisdiction
      |
      v
LangGraph conversational agent
   +--- retrieve (hybrid)
   +--- filter by role + jurisdiction
   +--- rerank (bge-reranker-v2-gemma-2b or Voyage rerank-2)
   +--- synthesize (Claude Sonnet 4.7, prompt cached)
   +--- guard (Llama Guard 4 + NeMo Guardrails + Presidio output PII scrub)
   +--- cite + return
      |
      v
eval:
  RAGAS faithfulness / answer_relevance / context_precision (online)
  Langfuse annotation queue (sampled)
  Arize Phoenix drift (weekly)
  red team suite (pre-release)
```

## 技术栈

- 摄取：Unstructured.io 或 docling 处理结构化文档；ColPali 处理视觉丰富的 PDF
- 向量库：5000 万向量以下用 pgvector + pgvectorscale；否则 Qdrant Cloud
- 稀疏：带字段权重的 Tantivy BM25
- 编排：LlamaIndex Workflows（摄取）+ LangGraph（对话）
- 重排序器：自托管 bge-reranker-v2-gemma-2b 或托管 Voyage rerank-2
- LLM：带 prompt caching 的 Claude Sonnet 4.7；兜底自托管 Llama 3.3 70B
- 评估：RAGAS 0.2 在线，DeepEval 做幻觉与越狱套件
- 可观测性：自托管 Langfuse 带标注队列；Arize Phoenix 做漂移
- 防护：Llama Guard 4 输入/输出分类器、NeMo Guardrails v0.12 策略、Presidio PII 擦除
- 合规：chunk 上的基于角色的访问标签；GDPR/HIPAA 的管辖标签

```figure
canary-rollout
```

## Build It

1. **摄取。** 用 Unstructured 或 docling 解析你的语料（认真构建的话 1000-10000 份文档）。对扫描件 / 视觉密集页面，走 ColPali。产出带摘要、角色标签、管辖标签的 chunk。

2. **索引。** 稠密 embedding（Voyage-3 或 Nomic-embed-v2）进 pgvector + pgvectorscale。经 Tantivy 的 BM25 侧索引。角色与管辖过滤作为 payload。

3. **混合检索。** 先按 role+jurisdiction 过滤；然后并行稠密 + BM25；用 reciprocal rank fusion 合并；前 20 进重排序器；前 5 进合成。

4. **带 prompt caching 的合成。** system prompt + 静态策略放在缓存头；重排序后的 context 作为缓存扩展；用户问题作为未缓存后缀。稳态目标 60-80% 缓存命中率。

5. **防护。** 输入上跑 Llama Guard 4；NeMo Guardrails 的 rail 拦截域外问题或策略禁止的话题；Presidio 擦除输出中意外的 PII；引用强制做后置过滤。

6. **Golden set。** 200 条由领域专家标注的 Q/A 对，含（answer, citations）。按精确引用匹配、答案正确性、faithfulness（RAGAS）给 agent 打分。

7. **红队。** 50 条对抗 prompt：越狱（PAIR、TAP）、PII 外泄尝试、域外、跨管辖泄漏。按通过/失败与严重度打分。

8. **漂移看板。** Arize Phoenix 每周跟踪检索质量（nDCG、引用 faithfulness）。下降 5% 即告警。

9. **成本报告。** Langfuse：prompt caching 命中率、每查询 token 数、按阶段拆分的 $/查询。

## Use It

```
$ chat --role=analyst --jurisdiction=GDPR
> what is the data-retention obligation for EU user profiles under our contract?
[retrieve]  hybrid top-20 filtered to GDPR + analyst-role
[rerank]    top-5 kept
[synth]     claude-sonnet-4.7, cache hit 74%, 0.8s
answer:
  The contract (Section 12.4, Master Services Agreement dated 2024-03-11)
  obligates EU user profile deletion within 30 days of termination per GDPR
  Article 17. The DPA amendment (DPA-v2.1, Section 5) extends this to 14 days
  for "restricted" category data.
  citations: [MSA-2024-03-11 s12.4, DPA-v2.1 s5]
```

## Ship It

`outputs/skill-production-rag.md` 描述了交付物。一个受监管领域 chatbot，带合规标签部署，通过评分表，并配有实时漂移监控。

| 权重 | 标准 | 如何衡量 |
|:-:|---|---|
| 25 | RAGAS faithfulness + answer relevance | 在 golden set（200 条 Q/A）上的在线分数 |
| 20 | 引用正确性 | 带可验证来源锚点的答案比例 |
| 20 | 防护覆盖率 | Llama Guard 4 通过率 + 越狱套件结果 |
| 20 | 成本 / 延迟工程 | Prompt cache 命中率、p95 延迟、$/查询 |
| 15 | 漂移监控看板 | Phoenix 实时看板，带每周检索质量趋势 |
| **100** | | |

## Exercises

1. 在另一个管辖下构建第二份语料切片（例如 GDPR 之外再加 HIPAA）。在 20 题跨管辖探针上演示 role+jurisdiction 过滤阻止跨泄漏。

2. 在一周的生产流量上测量 prompt cache 命中率。找出哪些查询破坏了缓存前缀。重构。

3. 加带 10k token 摘要缓冲的多轮记忆。测量 faithfulness 是否随对话增长而下降。

4. 把 Claude Sonnet 4.7 换成自托管 Llama 3.3 70B。测量 $/查询与 faithfulness 差值。

5. 加一个“不确定”模式：若前序重排序分数低于阈值，agent 说“我没有可信的引用”而不是作答。测量虚假自信的降低。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Prompt caching | “缓存 system + context” | Claude/OpenAI 特性：命中的缓存前缀 token 打 60-90% 折扣 |
| RAGAS | “RAG 评估器” | 自动给 faithfulness、answer relevance、context precision 打分 |
| Golden set | “标注评估集” | 200+ 条专家标注的带引用 Q/A；地面真值 |
| Jurisdiction tag | “合规标签” | 挂在 chunk 上的 GDPR/HIPAA/SOC2 范围；由检索过滤器执行 |
| Citation faithfulness | “有据答案率” | 由可检索来源片段支撑的论断比例 |
| Drift | “检索质量衰减” | nDCG 或引用分数的每周变化；告警阈值 5% |
| Red team | “对抗评估” | 发布前的越狱、PII 提取、域外探针 |

## Further Reading

- [Harvey AI](https://www.harvey.ai) — 参考法律生产栈
- [Glean 企业搜索](https://www.glean.com) — 企业规模 RAG 参考
- [Mendable 文档](https://mendable.ai) — 开发者文档 RAG 参考
- [LlamaCloud Parse + Index](https://docs.cloud.llamaindex.ai/llamaparse/getting_started) — 托管摄取
- [Anthropic prompt caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) — 成本杠杆参考
- [RAGAS 0.2 文档](https://docs.ragas.io/) — 权威 RAG 评估框架
- [Arize Phoenix](https://github.com/Arize-ai/phoenix) — 参考漂移可观测性
- [Llama Guard 4](https://www.llama.com/docs/model-cards-and-prompt-formats/llama-guard-4/) — 2026 安全分类器
- [NeMo Guardrails v0.12](https://docs.nvidia.com/nemo-guardrails/) — 策略 rail 框架
