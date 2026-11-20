# OpenTelemetry GenAI —— 端到端追踪 tool 调用

> 一个 agent 调用了五个 tool、三个 MCP server 和两个子 agent。你需要一条贯穿全部的 trace。OpenTelemetry GenAI semantic conventions（v1.37 及以上的稳定属性）是 2026 年的标准，Datadog、Langfuse、Arize Phoenix、OpenLLMetry 和 AgentOps 都原生支持。本课点出必需的属性，梳理 span 层级（agent → LLM → tool），并交付一个可以接入任何 OTel exporter 的 stdlib span emitter。

**Type:** Build
**Languages:** Python（stdlib，OTel span emitter）
**Prerequisites:** 第 13 阶段，第 07 课（MCP server）、第 13 阶段，第 08 课（MCP client）
**Time:** ~75 分钟

## Learning Objectives

- 说出 LLM span 与 tool 执行 span 所必需的 OTel GenAI 属性。
- 构建覆盖 agent 循环、LLM 调用、tool 调用和 MCP client dispatch 的 trace 层级。
- 决定哪些内容要采集（opt-in），哪些要脱敏（默认行为）。
- 在不改写 tool 代码的情况下，把 span 发送到本地 collector（Jaeger、Langfuse）。

## 问题场景

2026 年 2 月的一次调试：用户报告“我的 agent 有时要 30 秒才响应，有时只要 3 秒”。没有 trace。日志显示了 LLM 调用，但没有 tool dispatch，没有 MCP server 往返，也没有子 agent。你只能猜。最终你发现：某个 MCP server 偶尔在冷启动时挂起。

没有端到端追踪，你根本无法定位这个问题。OTel GenAI 解决了它。

这些约定在 2025-2026 年由 OpenTelemetry semantic-conventions 小组确定。它们定义了稳定的属性名，使 Datadog、Langfuse、Phoenix、OpenLLMetry 和 AgentOps 都能解析相同的 span。插桩一次，发往任意后端。

## 核心概念

### Span 层级

```
agent.invoke_agent  (top, INTERNAL span)
 ├── llm.chat       (CLIENT span)
 ├── tool.execute   (INTERNAL)
 │    └── mcp.call  (CLIENT span)
 ├── llm.chat       (CLIENT span)
 └── subagent.invoke (INTERNAL)
```

整体嵌套在一个 trace id 之下。span id 连接父子关系。

### 必需属性

按照 2025-2026 年的 semconv：

- `gen_ai.operation.name` —— `"chat"`、`"text_completion"`、`"embeddings"`、`"execute_tool"`、`"invoke_agent"`。
- `gen_ai.provider.name` —— `"openai"`、`"anthropic"`、`"google"`、`"azure_openai"`。
- `gen_ai.request.model` —— 请求的模型字符串（例如 `"gpt-4o-2024-08-06"`）。
- `gen_ai.response.model` —— 实际提供服务的模型。
- `gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens`。
- `gen_ai.response.id` —— 用于关联的 provider 响应 id。

tool span 使用：

- `gen_ai.tool.name` —— tool 标识符。
- `gen_ai.tool.call.id` —— 具体的调用 id。
- `gen_ai.tool.description` —— tool 描述（可选）。

agent span 使用：

- `gen_ai.agent.name` / `gen_ai.agent.id` / `gen_ai.agent.description`。

### Span 类型

- 跨进程边界的调用使用 `SpanKind.CLIENT`（LLM provider、MCP server）。
- agent 自身的循环步骤与 tool 执行使用 `SpanKind.INTERNAL`。

### Opt-in 的内容采集

默认情况下，span 携带指标和计时——不携带 prompt 或 completion。大载荷和 PII 默认关闭。设置 `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` 以及特定的内容采集环境变量，才能包含内容。在生产环境启用前请仔细评估。

### Span 上的事件

token 级事件可以作为 span event 添加：

- `gen_ai.content.prompt` —— 输入消息。
- `gen_ai.content.completion` —— 输出消息。
- `gen_ai.content.tool_call` —— 按记录形式保存的 tool 调用。

事件在一个 span 内按时间排序，便于细致回放。

### Exporter

OTel span 可导出到：

- **Jaeger / Tempo。** 开源，可本地部署。
- **Langfuse。** 面向 LLM 可观测性；可视化 token 用量。
- **Arize Phoenix。** 评测与追踪结合在一起。
- **Datadog。** 商业产品；原生解析 `gen_ai.*` 属性。
- **Honeycomb。** 列式导向；便于查询。

它们都说 OTLP，也就是线格式。你的代码无需关心。

### 跨 MCP 的传播

当 MCP client 调用 server 时，把 W3C traceparent header 注入请求。Streamable HTTP 支持标准 header。Stdio 原生不携带 HTTP header；规范 2026 年的路线图讨论了在 JSON-RPC 调用上添加 `_meta.traceparent` 字段。

在该功能发布之前：手动把 traceparent 放进每个请求的 `_meta` 中。server 记录 trace id。

### 指标

除 span 之外，GenAI semconv 还定义了指标：

- `gen_ai.client.token.usage` —— histogram。
- `gen_ai.client.operation.duration` —— histogram。
- `gen_ai.tool.execution.duration` —— histogram。

它们用于不需要逐次调用细节的仪表板。

### AgentOps 层

AgentOps（2024 年成立）专注于 GenAI 可观测性。它包装流行框架（LangGraph、Pydantic AI、CrewAI），自动发出 OTel span。如果你的技术栈使用受支持的框架，它会很有用；否则使用手动插桩。

```figure
t3-span-waterfall
```

## Use It

`code/main.py` 向 stdout 发出 OTel 形态的 span（类似 OTLP-JSON 格式），对应一个调用 LLM、dispatch 两个 tool 并完成一次 MCP 往返的 agent。没有真实的 exporter——本课聚焦 span 形态与属性集。把输出粘贴到兼容 OTLP 的查看器，或者直接阅读它。

值得关注的点：

- trace id 在所有 span 之间共享。
- 父子关系通过 `parentSpanId` 编码。
- 必需的 `gen_ai.*` 属性都已填充。
- 内容采集默认关闭；有一个场景通过环境变量开启它。

## Ship It

本课产出 `outputs/skill-otel-genai-instrumentation.md`。给定一个 agent 代码库，该 skill 产出插桩方案：在哪里添加 span、填充哪些属性，以及以哪些 exporter 为目标。

## Exercises

1. 运行 `code/main.py`。数一数 span 的数量，并指出哪些是 CLIENT，哪些是 INTERNAL。

2. 开启内容采集（环境变量），确认出现 `gen_ai.content.prompt` 和 `gen_ai.content.completion` 事件。注意这对 PII 的影响。

3. 添加 tool 执行指标 `gen_ai.tool.execution.duration`，并在每次调用时作为 histogram 样本发出。

4. 把父 agent span 的 traceparent 传播到 MCP 请求的 `_meta.traceparent` 字段。验证 MCP server 会看到相同的 trace id。

5. 阅读 OTel GenAI semconv 规范。找出 semconv 中列出、但本课代码并未发出的一个属性，把它加上。

## Key Terms

| 术语 | 常见说法 | 实际含义 |
|------|----------------|------------------------|
| OTel | “OpenTelemetry” | 用于 trace、metric、log 的开放标准 |
| GenAI semconv | “GenAI 语义约定” | LLM / tool / agent span 的稳定属性名 |
| `gen_ai.*` | “属性命名空间” | 所有 GenAI 属性共享此前缀 |
| Span | “计时操作” | 带开始、结束和属性的工作单元 |
| Trace | “跨 span 的祖先关系” | 共享同一 trace id 的 span 树 |
| SpanKind | “CLIENT / SERVER / INTERNAL” | 关于 span 方向的提示 |
| OTLP | “OpenTelemetry Line Protocol” | exporter 使用的线格式 |
| Opt-in content | “prompt / completion 采集” | 默认关闭；通过环境变量启用 |
| traceparent | “W3C 头” | 跨服务传播 trace 上下文 |
| Exporter | “后端专用的发送组件” | 把 span 发往 Jaeger / Datadog 等的组件 |

## Further Reading

- [OpenTelemetry — GenAI semconv](https://opentelemetry.io/docs/specs/semconv/gen-ai/) —— GenAI span、metric 和 event 的规范约定
- [OpenTelemetry — GenAI spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/) —— LLM 与 tool 执行 span 的属性列表
- [OpenTelemetry — GenAI agent spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/) —— agent 级的 `invoke_agent` span
- [open-telemetry/semantic-conventions — GenAI spans](https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/gen-ai-spans.md) —— 托管在 GitHub 上的权威来源
- [Datadog — LLM OTel semantic convention](https://www.datadoghq.com/blog/llm-otel-semantic-convention/) —— 生产集成演练
