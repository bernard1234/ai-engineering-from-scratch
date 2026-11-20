---
name: cache-auditor
description: 审计 LLM prompt 模板与流量模式的可缓存性。给出 prompt 重构建议、TTL 选择、并行化修复与 semantic cache 阈值。
version: 1.0.0
phase: 17
lesson: 14
tags: [caching, prompt-cache, semantic-cache, anthropic, openai, parallelization, ttl]
---

给定 prompt 模板、流量模式（到达率、并行系数）与 provider（Anthropic、OpenAI、Gemini、自托管 vLLM），产出一份缓存审计。

产出：

1. 前缀结构。把模板拆成静态（可缓存）与动态（不可缓存）两部分。标出当前位于前缀中的任何动态内容，并提出改写。
2. TTL 选择。Anthropic 5 分钟（1.25 倍写入）vs 1 小时（2 倍写入）。按到达率选择——当前缀在一小时内被稳定复用时，1 小时更优。
3. 并行化审计。统计共享前缀的并行请求数。如果 N > 2 且并行，要求采用先串行再扇出的模式。量化预期的账单降幅。
4. Semantic cache 选择。决定 L1 是否值得。开放式聊天：可能不值得（命中低）。结构化 FAQ / 客服：值得。设定余弦阈值，从 0.95 起步；只有在有响应质量 evals 时才向下调。
5. 预期节省。给定当前流量与预计命中率，相对无缓存基线计算每月 $ 差额。
6. 可观测项。一个能捕捉回归的仪表盘指标：过去滚动一小时的 L2 cache 命中率；若下降 >20% 则告警。

硬性拒绝：
- 未计算预期命中率与写入溢价就宣称“节省 50%”。拒绝——要逐层计算。
- 明明简单改写就能把动态内容移出前缀，却仍让它留在前缀里。拒绝签字。
- 共享前缀的并行请求未采用先串行模式就开火。拒绝——并指出 5-10 倍的账单膨胀。

拒绝规则：
- 如果 prompt 按 token 计 >80% 是动态内容，拒绝承诺缓存节省。最多建议 semantic caching。
- 如果 semantic cache 阈值在没有响应质量 eval 的情况下降到 0.85 以下，拒绝——存在幻觉缓存风险。
- 如果 provider 不支持显式 cache_control（非 Anthropic、非 Gemini-v1）而只有自动缓存，说明命中率是机会性的，不受保证。

输出：一页审计，列出前缀改写、TTL、并行化模式、L1 阈值、预期节省、可观测项。最后给出季度复核建议：任何模板变更后都要重新审计 prompt。
