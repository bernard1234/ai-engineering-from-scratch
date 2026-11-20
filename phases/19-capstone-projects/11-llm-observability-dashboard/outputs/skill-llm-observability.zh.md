---
name: llm-observability
description: 构建一个自托管的 LLM 可观测性仪表盘，摄取 OpenTelemetry GenAI span、运行 eval，并在五分钟内捕获注入的回归。
version: 1.0.0
phase: 19
lesson: 11
tags: [capstone, observability, otel, langfuse, phoenix, evals, drift, clickhouse]
---

给定至少六个 SDK 家族（OpenAI、Anthropic、Google GenAI、LangChain、LlamaIndex、vLLM）的生产 LLM 流量，部署一套自托管可观测性平面，摄取 OTLP GenAI-semconv span、运行 eval、检测漂移并告警。

构建计划：

1. 带 OTLP HTTP receiver 的 OpenTelemetry Collector，尾采样处理器（保留 100% 错误、10% 成功、100% 高毒性/PII），导出器指向 ClickHouse + S3。
2. 镜像 GenAI semconv 的 ClickHouse span schema：gen_ai.system、gen_ai.request.model、usage.input/output_tokens、latency_ms、user_id、app_id，外加用于 prompt/completion 的 JSON 字段袋。
3. 用于 app、用户、会话、标注队列的 Postgres 元数据存储。
4. 在每个 SDK 家族的客户端应用上启用 OpenLLMetry 自动埋点；验证规范 span 正确落地。
5. DeepEval + RAGAS + Phoenix 评估器包，在采样后的 trace 上调度；为 PII 与 off-policy 定制 LLM-judge。
6. 对池化后的 prompt embedding 做每周 PSI / KL 漂移检测；告警阈值 0.2。
7. 用于 eval 分数聚合与延迟分位数的 Prometheus exporter；Alertmanager 推送至 Slack（warning）+ PagerDuty（critical）。
8. Next.js 15 App Router 仪表盘：总览、trace 搜索 + 瀑布图、eval 趋势、漂移图、告警。
9. 回归探针：注入一种响应模式，使其 1% 的概率泄露伪造 SSN；测量 MTTR（告警触发时间）。

评估标准：

| 权重 | 标准 | 衡量方式 |
|:-:|---|---|
| 25 | Trace schema 覆盖率 | 产出规范 GenAI span 的 SDK 家族数量（目标 6+） |
| 20 | Eval 正确性 | DeepEval / RAGAS 分数对比人工标注集 |
| 20 | 仪表盘 UX | 注入回归下的 MTTR（目标 5 分钟内） |
| 20 | 成本 / 规模 | 持续 1k span/秒 摄取且无积压 |
| 15 | 告警 + 漂移检测 | Prometheus/Alertmanager 链路端到端跑通 |

硬性否决：

- 发明 OpenTelemetry GenAI semconv 中不存在的属性名的 span schema。
- 丢弃错误的尾采样策略（一个众所周知的 anti-pattern）。
- 不采样即按摄取速率运行的 eval（成本不可接受）。
- 只展示「latency」而没有 p50/p95/p99 区分的仪表盘。

拒绝规则：

- 在没有 PII 脱敏策略的情况下拒绝持久化 prompt 或 completion。
- 在没有逐 SDK 规范 span 回归测试的情况下拒绝声称「多 SDK 支持」。
- 在没有基线窗口的情况下拒绝交付漂移检测；零样本漂移毫无用处。

输出：一个仓库，包含 collector 配置、ClickHouse schema、Next.js 15 仪表盘、eval 任务、漂移检测器、告警链路、带标注回归的 10k-trace 演示数据集，以及一份书面说明，记录注入 PII 回归的 MTTR，并列出在迭代中降低 MTTR 的前三项仪表盘 UX 改进。
