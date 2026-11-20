# Prompt Caching 与 Semantic Caching 的经济学

> **定价快照日期 2026-04。** 下文中的数字结论反映的是本课发布时抓取的厂商价目表；在向下游引用前，请对照链接文档核实。

> 缓存发生在两层。L2（provider 级）prompt/前缀缓存在重复前缀上复用 attention KV——Anthropic 的 prompt-caching 文档宣称在长 prompt 上最多可降低 90% 成本、85% latency；对 Claude 3.5 Sonnet，cache 读取为 $0.30/M，而全新输入为 $3.00/M，5 分钟 TTL，1 小时 TTL 选项需支付 2 倍的写入溢价（docs.anthropic.com，2026-04）。OpenAI prompt caching 对 ≥1024 tokens 的 prompt 自动生效，缓存输入相对全新输入约便宜 90%（platform.openai.com，2026-04）；各模型的精确缓存费率取决于实时价目表。L1（应用级）semantic caching 在 embedding 相似度命中时完全跳过 LLM。厂商所说的“95% 准确率”指的是匹配正确性，而非命中率——已报告的生产命中率从 10%（开放式聊天）到 70%（结构化 FAQ）不等；两家厂商都没有发布官方基线，因此把这些视为社区遥测而非保证。生产中的坑：并行化会杀死缓存（在第一次 cache 写入前发出的 N 个并行请求可能让花费膨胀数倍），而前缀里的动态内容会彻底阻止缓存命中。ProjectDiscovery 报告称，通过把动态文本移出可缓存前缀，命中率从 7% 提升到 74%（2025-11）。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级双层缓存模拟器)
**Prerequisites:** 第 17 阶段，第 04 课（Serving Engine Internals），第 06 课（SGLang RadixAttention）
**Time:** ~60 分钟

## Learning Objectives

- 区分 L2 prompt/前缀缓存（在 provider 侧复用 KV）与 L1 semantic caching（相似 prompt 上绕过 LLM）。
- 解释 Anthropic 的 `cache_control` 显式标记，以及两种 TTL 选项（5 分钟 vs 1 小时）及其价格乘数。
- 给定命中率、prompt/response 组合与 token 价格，计算预期每月节省。
- 指出让账单膨胀 5-10 倍的并行化反模式，以及让命中率崩塌的动态内容反模式。

## 问题场景

你给 RAG 服务加上 prompt caching。账单纹丝不动。你测命中率，是 7%。你的 prompt 看起来是静态的，其实不是——system prompt 里包含格式化到分钟的当前日期、一个请求 ID，以及为多样性而随机重排的示例。每个请求都写入一条新 cache 条目，读取为零。

另一边，你的 agent 对每个用户问题跑十个并行 tool 调用。十个全都在第一次 cache 写入完成之前抵达 provider。十次写入，零次读取。你的账单是“带缓存”本该有的成本的 5-10 倍。

缓存是一种协议，不是一个开关。两层，两种不同的失败模式。

## 核心概念

### L2——provider 级 prompt/前缀缓存

Provider 为可缓存前缀存储 attention KV，并在下一次匹配该前缀的请求上复用它。你支付一次写入成本，读取几乎免费。

**Anthropic（Claude 3.5 / 3.7 / 4 系列）**：在请求中使用显式的 `cache_control` 标记。你标注哪些块可缓存。TTL：5 分钟（写入成本为基准的 1.25 倍）或 1 小时（写入成本为基准的 2 倍）。Cache 读取：Claude 3.5 Sonnet 上为 $0.30/M，而全新输入为 $3.00/M——便宜 10 倍（docs.anthropic.com，截至 2026-04）。各模型费率不同（Opus/Haiku 另行公布）；务必对照实时定价页。

**OpenAI**：对 ≥1024 tokens 的 prompt 自动缓存（platform.openai.com，2026-04）。没有显式开关。在当前 gpt-4o/gpt-5 价目表上，缓存输入比全新输入便宜约 10 倍。文档与发布说明都没有公布官方命中率基线；在精心设计 prompt 的情况下，社区报告集中在 30–60%。监控 `usage.cached_tokens` 以测量你自己的数据。

**Google（Gemini）**：通过显式 API 进行 context caching；1M-token context 意味着缓存回报更高。

**自托管（vLLM、SGLang）**：第 17 阶段 · 06 涵盖了 RadixAttention——同样的模式，跑在你自己的算力上。

### L1——应用级 semantic caching

在真正调用 LLM 之前，先对 prompt 做哈希、做 embedding，并查找一条相似的缓存请求（余弦相似度高于阈值，通常 0.95+）。命中就返回缓存响应。未命中则调用 LLM 并缓存结果。

开源：Redis Vector Similarity、GPTCache、Qdrant。商业：Portkey Cache、Helicone Cache。

厂商的准确率宣称指的是返回的缓存响应在语义上合适的频率——而非你命中的频率。生产命中率：

- 开放式聊天：10-15%。
- 结构化 FAQ / 客服：40-70%。
- 代码问题：20-30%（细微变体会杀死命中）。
- 语音 agent 重复 prompt：50-80%（语音归一化到固定集合）。

### 并行化反模式

你的 agent 并行发起 10 个 tool 调用。10 个都带同样的 4K-token system prompt。Anthropic 的 cache 写入是按请求的；第一次 cache 写入在 provider 看到 prompt 后约 300 ms 完成。第 2-10 个请求落在同一毫秒窗口内，每个都遭遇 cache miss。你付了 10 次写入溢价、0 次读取折扣。

修复：批量 + 先串行——先单独发请求 1，等 1 的 cache 填充后再发 2-10。这给第一次 tool 调用增加 300 ms，却省下 5-10 倍的账单。

### 动态内容反模式

你的 system prompt 长这样：

```
You are a helpful assistant. The current time is 14:32:17.
User ID: abc123. Today is Tuesday...
```

每个请求都是唯一的。每个请求都写入。零命中。

修复：把所有真正静态的内容移到可缓存前缀；把动态内容追加到 cache 边界之后：

```
[cacheable]
You are a helpful assistant. [rules, examples, instructions]
[/cacheable]
[dynamic, not cached]
Current time: 14:32:17. User: abc123.
```

ProjectDiscovery 用这种方式把 cache 命中率从 7% 提升到 74%，并公开了剖析。

### 批量 + 缓存叠加用于过夜负载

Batch API（第 17 阶段 · 15）以 24 小时周转给到 50% 折扣。再叠加缓存输入，就能在此之上再拿约 10 倍。过夜分类、标注与报告生成类负载通过叠加可以降到同步未缓存成本的约 10%。

### 你该记住的数字

定价点抓取于 2026-04，来自所链接的厂商文档，每几个月就会漂移——依赖之前请重新核对。

- Anthropic 缓存读取：Claude 3.5 Sonnet 上 $0.30/M，比全新输入便宜约 10 倍（docs.anthropic.com）。
- Anthropic cache 写入溢价：1.25 倍（5 分钟 TTL）或 2 倍（1 小时 TTL）。
- OpenAI 自动缓存：适用于 ≥1024 tokens 的 prompt；在当前价目表上，缓存输入约按全新输入的 10% 计价（platform.openai.com）。
- Semantic cache 命中率（社区报告）：开放聊天约 10%；结构化 FAQ 最高约 70%。并非厂商文档化的基线。
- ProjectDiscovery：通过把动态内容移出前缀，命中率从 7% → 74%（项目博客，2025-11）。
- 并行化反模式：当 N 个并行请求错过第一次 cache 写入时，常见报告是账单膨胀 5–10 倍。

```figure
semantic-cache-hit
```

## Use It

`code/main.py` 在混合负载上模拟 L1 + L2 缓存。报告命中率、账单，并展示并行化惩罚。

## Ship It

本课产出 `outputs/skill-cache-auditor.md`。给定 prompt 模板与流量，审计可缓存性并给出重构建议。

## Exercises

1. 运行 `code/main.py`。切换并行化开关。账单变化多少？
2. 你的 system prompt 里有一个日期。把它移出去。展示前后命中率的计算。
3. 给定你的请求到达率，计算 1 小时 TTL（2 倍写入）vs 5 分钟 TTL（1.25 倍写入）的盈亏平衡点。
4. Semantic cache 在 0.95 阈值下命中 20%。在 0.85 下命中 50%，但你会看到不正确的缓存响应。选择正确的阈值并给出理由。
5. 你对每个用户问题批量跑 10 个并行子查询。在不增加端到端 latency 的前提下重写为对缓存友好的形式。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| L2 prompt cache | “前缀缓存” | Provider 为重复前缀存储 KV |
| `cache_control` | “Anthropic 缓存标记” | 显式标注可缓存块的属性 |
| Cache write premium | “写入税” | 首次从 miss 转为 cache 的额外成本（1.25 倍或 2 倍） |
| L1 semantic cache | “embedding 缓存” | 调用 LLM 前在应用层做哈希与 embedding |
| GPTCache | “LLM 缓存库” | 流行的 OSS L1 缓存库 |
| Cache hit rate | “命中数 / 总数” | 由缓存服务的请求占比 |
| Parallelization anti-pattern | “N 次写入陷阱” | N 个并行请求各 miss 缓存 N 次 |
| Dynamic content trap | “prompt 里带时间戳的陷阱” | 前缀里的动态字节会杀死命中率 |
| RadixAttention | “副本内缓存” | SGLang 的前缀缓存实现 |

## Further Reading

- [Anthropic Prompt Caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) ——官方的 `cache_control` 语义与 TTL。
- [OpenAI Prompt Caching](https://platform.openai.com/docs/guides/prompt-caching) ——自动缓存行为与适用条件。
- [TianPan — Semantic Caching for LLMs Production](https://tianpan.co/blog/2026-04-10-semantic-caching-llm-production)
- [ProjectDiscovery — Cut LLM Costs 59% With Prompt Caching](https://projectdiscovery.io/blog/how-we-cut-llm-cost-with-prompt-caching)
- [DigitalOcean / Anthropic — Prompt Caching](https://www.digitalocean.com/blog/prompt-caching-with-digital-ocean)
