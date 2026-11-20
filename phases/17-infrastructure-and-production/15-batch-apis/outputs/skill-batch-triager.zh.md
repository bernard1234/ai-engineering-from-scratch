---
name: batch-triager
description: 把 LLM 负载分流到 interactive / semi-interactive / batch 三条车道，计算叠加折扣（batch + cache）的节省，并标出分流错误的负载。
version: 1.0.0
phase: 17
lesson: 15
tags: [batch-api, openai-batch, anthropic-batches, vertex-batch, triage, cost]
---

给定一个负载（名称、用户对 latency 的期望、流量规模、共享 prompt 结构），产出分流 + 成本方案。

产出：

1. 车道。Interactive（受 TTFT 约束、同步）、semi-interactive（能接受数分钟、异步队列）或 batch（早上之前即可、batch API）。用具体的用户期望给出理由。
2. 当前成本。按当前配置（同步、无缓存等）计算每月成本。
3. 目标成本。计算建议配置（batch + cache 或 sync + cache）下的成本。以当前成本的百分比表示。
4. 迁移方案。针对具体 provider 的步骤（选与负载所用模型匹配的那一个，而不是两个都写）：
   - OpenAI：迁移到 `/v1/batches`。符合条件（≥1024 tokens）的 prompt 会自动启用 prompt caching——无需设置 `cache_control`。可选地传 `prompt_cache_key` 以获得更精细的归因。
   - Anthropic：迁移到 Message Batches。cache 复用需要在可缓存的 prompt 片段上显式标注 `cache_control` 块（例如 `{"type": "ephemeral"}`）；batch 折扣可与缓存读取定价叠加。
   - 两者通用：埋点一个成功/失败 webhook，并为错过周转窗口的 batch 准备一条溢出到同步的车道。
5. 风险。如果 batch 周转在 P99 达到 20 小时怎么办？写明下游系统的行为（邮件投递、队列溢出到同步）。
6. 可观测项。能捕捉分流错误的指标：batch 任务完成 latency P95；若 > 12 小时则告警。

硬性拒绝：
- 用户只需“早上之前”的 latency，却把过夜 pipeline 以同步模式跑、不带 batch。拒绝——指出约 90% 的浪费支出。
- 对任何用户期望低于 15 分钟的东西承诺 batch。拒绝——batch SLA 是 24h。
- 在带共享 system prompt 的 batch 负载上忽视 prompt caching。拒绝——叠加折扣正是重点。

拒绝规则：
- 如果负载对外宣传为“实时”，但真实用户期望是数分钟，在建议 batch 前要求明确确认。
- 如果负载的目标 provider 在 batch 中不支持 prompt caching（例如任何没有 KV 前缀复用的自定义或自托管栈），说明只有 batch 折扣适用，并在没有叠加节省的情况下重新计算。OpenAI 的 batch 缓存是自动的；Anthropic 的 batch 缓存需要显式 `cache_control` 块。
- 如果负载有严格的 latency SLA（例如 P99 < 60s），直接拒绝 batch——它属于别的车道。

输出：一页分流，包含车道、当前成本、目标成本、迁移步骤、风险、可观测项。最后给出节奏：随着产品面变化，每季度重新分流所有负载。
