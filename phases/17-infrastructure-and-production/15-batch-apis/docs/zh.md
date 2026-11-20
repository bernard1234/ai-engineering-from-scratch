# Batch API——作为行业标准的 50% 折扣

> 每一家主流 provider 都提供异步 batch API，50% 折扣、约 24 小时周转。OpenAI、Anthropic、Google，以及大多数推理平台（Fireworks batch 档、Together batch）都实现了同样的模式。把 batch 与 prompt caching 叠加，过夜 pipeline 就能降到同步未缓存成本的约 10%。规则极其简单：只要不是交互式，就该走 batch。内容生成 pipeline、文档分类、数据抽取、报告生成、批量标注、目录打标——任何能容忍 24 小时 latency 的负载，在迁到 batch 之前都是留在桌上的钱。2026 年的生产模式是把每个新的 LLM 负载分流到三条车道：交互式（同步 + 缓存）、半交互式（异步队列 + 兜底）、batch（过夜，叠加缓存输入）。那些假装交互式、却能容忍数分钟 latency 的负载浪费最多。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级 batch-vs-sync 成本模拟器)
**Prerequisites:** 第 17 阶段，第 14 课（Prompt & Semantic Caching）
**Time:** ~45 分钟

## Learning Objectives

- 指出三大 provider 的 batch API（OpenAI、Anthropic、Google）以及共同的 50% 折扣 + 24h 周转保证。
- 为过夜分类负载计算 batch + cached-input 叠加的成本，并与同步未缓存基线对比。
- 把负载分流为 interactive / semi-interactive / batch，并说明车道选择的理由。
- 指出两个陷阱：半交互（用户期望比 24h 更快）与输出 schema 漂移（batch 文件格式因 provider 而异）。

## 问题场景

你的团队上线了一条夜间报告生成 pipeline。5 万份文档，逐一摘要，对摘要聚类，起草一份高管简报。以同步方式运行要 4 小时、每晚 $2,000。你听说了 batch API。

Batch 给你 50% 折扣。你还对 system prompt 启用 prompt caching（在全部 5 万次调用间共享）。叠加后，账单降到每晚 $180——约为基线的 9%。同一条 pipeline，三处配置改动。

Batch 是 LLM 成本工具箱里最便宜、却没人拉的那根杠杆。原因主要是组织性的：团队以为这是“实时”，可 SLA 其实是“早上之前”。本课讲的是别把 90% 的账单留在桌上。

## 核心概念

### 三种 batch API

**OpenAI Batch API**：JSONL 文件上传，内含一系列请求。承诺 24 小时周转（实践中通常约 2-8 小时）。输入与输出 token 均享 50% 折扣。`/v1/batches` 端点。符合缓存条件的输入还能在此基础上享受缓存输入定价。

**Anthropic Message Batches**：JSONL 上传。24 小时周转。50% 折扣。支持 `cache_control`——cache 写入是显式的，读取在批内自动发生。

**Google Vertex AI Batch Prediction**：BigQuery 或 GCS 输入。Gemini 同样 50% 折扣。与 Vertex pipeline 集成。

### 语义：异步，而非缓慢

Batch 的含义是“我承诺 24 小时内返回”——而不是“这要花 24 小时”。典型 P50 是 2-6 小时。Provider 在 GPU 库存未被充分利用的低峰窗口调度你的批。

### 与缓存叠加

一次 5 万份文档的摘要，共用同一个 4K-token system prompt：

- 同步未缓存：50000 ×（$input × 4000 + $output × 200），按全价。
- 同步缓存：system prompt 在首次写入后缓存；其余 49999 次拿到便宜 10 倍的输入。
- Batch 缓存：上述所有再加上读取与写入各 50% 折扣。

叠加效果：batch + cache = 同步未缓存账单的约 10%。任何过夜运行、且有共享 system prompt 的负载都该用它。

### 负载分流

**Interactive**——用户等待响应。TTFT 重要。同步调用 + prompt caching。不能走 batch。

**Semi-interactive**——用户提交任务，几分钟后回来看。异步队列，batch 不可用时兜底到同步。想想中等规模的 RAG 索引。

**Batch**——用户期望“早上之前”或“下一小时”拿到结果。内容 pipeline、规模化分类、离线分析。永远走 batch，永远叠加缓存。

常见错误：因为 pipeline 是生产环境，就把一切都归为交互式。生产不是 latency 规格——SLA 才是。

### 半交互陷阱

有些功能看起来是交互式的，却能容忍 5-10 分钟。例如：一份带“刷新”按钮的夜间客户健康报告。用户点刷新，等 10 分钟没问题。团队却把它做成了同步。50 个并发刷新，成本是批量处理并通过邮件送达的 10 倍。

要问的问题是：“24 小时对这个用户意味着什么？”如果答案是“他们不会察觉”，就走 batch。

### 输出 schema 陷阱

Batch 文件格式因 provider 而异：

- OpenAI：JSONL，每行一个请求。
- Anthropic：JSONL，每行一条 message；响应格式内嵌。
- Vertex：BigQuery 表或带 TFRecord 的 GCS 前缀。

写一个跨 provider 的“统一 batch 客户端”，意味着每个 provider 都要有适配代码。宣称支持多 provider batch 的网关（Portkey、LiteLLM 的部分档位）也只是对原始格式做了薄封装。

### 你该记住的数字

- 各 provider 的 batch 折扣：输入 + 输出一律 50%。
- 周转 SLA：保证 24 小时，典型 P50 为 2-6 小时。
- 叠加 batch + 缓存输入：约为同步未缓存成本的 10%。
- 负载分流规则：如果能接受 24h latency，就永远走 batch。

```figure
batch-lane-triage
```

## Use It

`code/main.py` 为一个 5 万份文档的负载，计算 sync、sync+cache、batch、batch+cache 各方案的成本。以 $ 和百分比报告节省。

## Ship It

本课产出 `outputs/skill-batch-triager.md`。给定负载特征，分流为 interactive/semi/batch，并估算节省。

## Exercises

1. 运行 `code/main.py`。对于一个 10 万份文档、3K-token system prompt、500-token 输出的 pipeline，计算全叠加（batch + cache）相对同步基线的节省。
2. 从你熟悉的一个真实产品里挑三个功能。把每个分流到 interactive/semi/batch。
3. 一个用户抱怨他的报告花了 3 小时。这是 batch 分流错误，还是合理的交互式？写出判定标准。
4. 你的 batch API 返回 SLA 是 24h，但 P99 是 20 小时。你如何向用户传达这一点——下游系统在边界情况下的行为是什么？
5. 计算盈亏平衡点：共享前缀达到多长时，batch + cache 比在你自有预留 GPU 上过夜运行更便宜？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Batch API | “异步折扣” | 50% 折扣，24h 周转 |
| JSONL | “batch 格式” | 每行一个 JSON 请求；OpenAI/Anthropic 标准 |
| Message Batches | “Anthropic 的 batch” | Anthropic 的 batch API 产品名 |
| Batch prediction | “Vertex batch” | Vertex AI 的 batch API 产品 |
| Turnaround SLA | “24h 承诺” | 保证值，而非典型值；典型值为 2-6h |
| Workload triage | “交互性决策” | interactive / semi / batch 的路由决策 |
| Output schema | “响应格式” | 各 provider 的 JSONL 布局；不可移植 |
| Stacked discount | “batch + cache” | 两者都适用时约为未缓存同步账单的 10% |

## Further Reading

- [OpenAI Batch API](https://platform.openai.com/docs/guides/batch) ——JSONL 格式与 `/v1/batches` 语义。
- [Anthropic Message Batches](https://docs.anthropic.com/en/docs/build-with-claude/batch-processing) ——batch 格式与 `cache_control` 的交互。
- [Vertex AI Batch Prediction](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/batch-prediction-gemini) ——Gemini batch 语义。
- [Finout — OpenAI vs Anthropic API Pricing 2026](https://www.finout.io/blog/openai-vs-anthropic-api-pricing-comparison)
- [Zen Van Riel — LLM API Cost Comparison 2026](https://zenvanriel.com/ai-engineer-blog/llm-api-cost-comparison-2026/)
