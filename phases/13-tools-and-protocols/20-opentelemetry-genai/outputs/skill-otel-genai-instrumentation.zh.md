---
name: otel-genai-instrumentation
description: 为 agent 代码库产出端到端发出 OTel GenAI span 的插桩方案。
version: 1.0.0
phase: 13
lesson: 19
tags: [otel, observability, gen-ai, tracing]
---

给定一个 agent 代码库（LLM 调用、tool dispatch、MCP client、子 agent），产出 OTel GenAI 插桩方案。

产出：

1. Span 层级。根 span `agent.invoke_agent`（INTERNAL）及其子 span：`llm.chat`（CLIENT）、`tool.execute`（INTERNAL）、`mcp.call`（CLIENT）、`subagent.invoke`（INTERNAL）。
2. 每个 span 的属性清单。`gen_ai.operation.name`、`gen_ai.provider.name`、`gen_ai.request.model`、`gen_ai.response.model`、`gen_ai.usage.*`、`gen_ai.tool.name`、`gen_ai.agent.name`。
3. 传播规则。在每次远程调用上注入 W3C traceparent；对 MCP stdio 先以 `_meta.traceparent` 作为过渡字段。
4. 内容采集策略。默认关闭；说明由哪个环境变量启用；点明 PII 风险。
5. Exporter 选择。Jaeger / Tempo / Langfuse / Phoenix / Datadog / Honeycomb；以 OTLP 作为线格式。

硬性拒绝：
- 任何缺少跨 MCP 或子 agent 边界 trace 传播的方案。
- 任何默认开启内容采集的方案。会泄漏 prompt 和 PII。
- 任何发出缺少 `gen_ai.` 或明确厂商前缀的任意自定义属性的方案。

拒绝规则：
- 如果代码库使用的框架自带 OTel 自动插桩（Pydantic AI、LangGraph、AgentOps），优先推荐该框架的 hook。
- 如果 exporter 后端是本地部署，而团队没有 SRE 支持，推荐托管后端。
- 如果用户要求为调试生产而采集内容，在没有类型化的同意策略和 PII 脱敏流水线之前拒绝。

输出：一份单页方案，包含 span 层级、每个 span 的属性清单、传播规则、内容采集策略和 exporter 选择。结尾给出最应设置告警的指标（通常是 p95 `gen_ai.client.operation.duration`）。
