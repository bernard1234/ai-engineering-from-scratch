---
name: observability-stack
description: 给定技术栈、规模、预算与许可证立场，挑选一套 LLM observability 技术栈（开发平台 + 网关 + 可选的规模化层），并定义 OpenTelemetry GenAI 属性集。
version: 1.0.0
phase: 17
lesson: 13
tags: [observability, langfuse, langsmith, phoenix, arize, helicone, opik, opentelemetry, genai-conventions]
---

给定技术栈（LangChain / DSPy / 原生 SDK）、规模（traces/天）、预算、许可证立场（只要 MIT vs 商业授权可以）、以及自托管要求，产出 observability 方案。

产出：

1. 开发平台选择。Langfuse（OSS）、LangSmith（LangChain 优先的商业产品）、Opik（Comet OSS），或不选。用技术栈与许可证给出理由。
2. 网关/遥测选择。Helicone（代理 + 网关）、SigNoz（全栈 APM）、OpenLLMetry（纯 OTel）。如果已经在用 AI 网关（第 17 阶段 · 19），说明集成方式。
3. 规模化/数据湖层。可选；Arize AX 或裸 Iceberg 用于长期分析，Phoenix 用于 RAG 漂移。
4. OTel GenAI 约定。规定最小属性集：`gen_ai.system`、`gen_ai.request.model`、`gen_ai.usage.input_tokens`、`gen_ai.usage.output_tokens`、`gen_ai.request.temperature`、`gen_ai.response.finish_reasons`，外加组织专属字段（tenant_id、user_id、task）。
5. 采样策略。100% errors、100% 高成本（>$0.10/call）、N% 成功采样率。原始数据保留窗口（14d / 30d / 90d）。聚合指标保留更久。
6. 告警。五个必须配告警的指标：error rate、P99 TTFT、cost/request、prompt-cache 命中率、refusal rate。

硬性拒绝：
- 在框架专属 SDK 内部插桩且没有 OTel 兜底。拒绝——这是框架锁定。
- 非受监管负载下，以 Datadog 级定价保留 100% traces、每月超过 $500。拒绝——建议采样。
- 忽视 OpenTelemetry GenAI 约定。拒绝——2026 年的互操作需要它们。

拒绝规则：
- 如果 traces/天 > 500 万，且团队坚持 Datadog 全量保留，在没有成本预测的情况下拒绝。
- 如果团队只要 MIT，却选了 LangSmith，拒绝——Langfuse 才是 MIT 的对等物。
- 如果团队没有 AI 网关，却选 Helicone 同时当网关和 observability，接受——该代理可兼作网关，上限约 500 RPS（网关规模化在第 17 阶段 · 19 覆盖）。

输出：一页方案，写明开发平台、网关、规模化层（如有）、OTel 属性集、采样规则、五个告警。最后给出一个标志技术栈漂移的单一指标：过去 7 天内携带完整 OTel GenAI 属性的 LLM 调用占比。
