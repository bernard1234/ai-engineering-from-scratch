# OpenTelemetry GenAI 语义约定

> OpenTelemetry 的 GenAI SIG（2024 年 4 月启动）定义了 agent 遥测的标准 schema。span 名称、属性和内容捕获规则在厂商之间收敛，使得 agent trace 在 Datadog、Grafana、Jaeger 和 Honeycomb 中含义一致。

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 13 (LangGraph), Phase 14 · 24 (Observability Platforms)
**Time:** ~60 minutes

## 学习目标

- 说出 GenAI span 类别：model/client、agent、tool。
- 区分 `invoke_agent` 的 CLIENT 与 INTERNAL span，以及各自适用时机。
- 列出顶层 GenAI 属性：provider name、request model、data-source ID。
- 解释内容捕获契约：opt-in、`OTEL_SEMCONV_STABILITY_OPT_IN`、外部引用推荐。

## 问题

每个厂商都发明自己的 span 名称。运维团队最终要为每个框架构建各自的仪表盘。OpenTelemetry 的 GenAI SIG 通过定义一个全生态共同遵循的标准来解决这个问题。

## 概念

### Span 类别

1. **Model / client spans。** 覆盖原始 LLM 调用。由提供商 SDK（Anthropic、OpenAI、Bedrock）和框架模型适配器发射。
2. **Agent spans。** `create_agent`（agent 构造时）和 `invoke_agent`（运行时）。
3. **Tool spans。** 每次工具调用一个；通过父子关系连接到 agent span。

### Agent span 命名

- Span 名：若有命名则为 `invoke_agent {gen_ai.agent.name}`；否则回退到 `invoke_agent`。
- Span kind：
  - **CLIENT** —— 用于远程 agent 服务（OpenAI Assistants API、Bedrock Agents）。
  - **INTERNAL** —— 用于进程内 agent 框架（LangChain、CrewAI、本地 ReAct）。

### 关键属性

- `gen_ai.provider.name` —— `anthropic`、`openai`、`aws.bedrock`、`google.vertex`。
- `gen_ai.request.model` —— 模型 ID。
- `gen_ai.response.model` —— 实际解析到的模型（因路由可能与请求不同）。
- `gen_ai.agent.name` —— agent 标识符。
- `gen_ai.operation.name` —— `chat`、`completion`、`invoke_agent`、`tool_call`。
- `gen_ai.data_source.id` —— 用于 RAG：查询了哪个语料库或存储。

针对 Anthropic、Azure AI Inference、AWS Bedrock、OpenAI 有特定技术的约定。

### 内容捕获

默认规则：instrumentation 默认**不应**捕获输入/输出。通过以下方式 opt-in 捕获：

- `gen_ai.system_instructions`
- `gen_ai.input.messages`
- `gen_ai.output.messages`

推荐的生产模式：把内容存储在外部（S3、你的日志存储），在 span 上记录引用（指针 ID，而非正文）。这是第 27 课的内容投毒防御接入可观测性。

### 稳定性

截至 2026 年 3 月，大多数约定仍处于实验状态。用以下方式 opt-in 稳定预览：

```
OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental
```

Datadog v1.37+ 把 GenAI 属性原生映射进它的 LLM Observability schema。其他后端（Grafana、Honeycomb、Jaeger）支持原始属性。

### 这个模式在哪里会出错

- **在 span 中捕获完整 prompt。** PII、密钥、客户数据出现在运维可读的 trace 里。存到外部。
- **没有 `gen_ai.provider.name`。** 缺少归属时多提供商仪表盘会失效。
- **没有父链接的 span。** 孤立的 tool span。始终传播 context。
- **没有设置稳定性 opt-in。** 后端升级时你的属性可能被重命名。

```figure
ae-genai-span-tree
```

## Build It

`code/main.py` 实现一个符合 GenAI 约定的标准库 span 发射器：

- 带 GenAI 属性 schema 的 `Span`。
- 带 `start_span`、嵌套 context 的 `Tracer`。
- 一次脚本化 agent 运行，发射：`create_agent`、`invoke_agent`（INTERNAL）、逐工具的 span、LLM 调用的 `chat` span。
- 一个内容捕获模式，把 prompt 存到外部并在 span 上记录 ID。

运行它：

```
python3 code/main.py
```

输出：带所有必需 GenAI 属性的 span 树，以及展示 opt-in 内容引用的「外部存储」。

## Use It

- **Datadog LLM Observability**（v1.37+）原生映射属性。
- **Langfuse / Phoenix / Opik**（第 24 课）—— 自动 instrument 生态。
- **Jaeger / Honeycomb / Grafana Tempo** —— 原始 OTel trace；基于 GenAI 属性构建仪表盘。
- **自托管** —— 运行带 GenAI processor 的 OTel Collector。

## Ship It

`outputs/skill-otel-genai.md` 把 OTel GenAI span 接入现有 agent，带内容捕获默认值和外部引用存储。

## 练习

1. 用 `invoke_agent`（INTERNAL）+ 逐工具 span 给第 01 课的 ReAct 循环加 instrument。发送到一个 Jaeger 实例。
2. 增加「仅引用」模式的内容捕获：prompt 存入 SQLite，span 属性只携带行 ID。
3. 阅读 `gen_ai.data_source.id` 的规范。把它接入第 09 课的 Mem0 搜索。
4. 设置 `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`，并验证 collector 没有重命名你的属性。
5. 构建一个仪表盘：仅凭 GenAI 属性得出「哪些工具错误与哪些模型相关」。

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| GenAI SIG | 「OpenTelemetry GenAI 小组」 | 定义 schema 的 OTel 工作组 |
| invoke_agent | 「agent span」 | 表示一次 agent 运行的 span 名 |
| CLIENT span | 「远程调用」 | 调用远程 agent 服务的 span |
| INTERNAL span | 「进程内」 | 进程内 agent 运行的 span |
| gen_ai.provider.name | 「提供商」 | anthropic / openai / aws.bedrock / google.vertex |
| gen_ai.data_source.id | 「RAG 源」 | 一次检索命中了哪个语料库/存储 |
| Content capture | 「prompt 日志」 | opt-in 捕获消息；生产中存外部 |
| Stability opt-in | 「预览模式」 | 固定实验约定的环境变量 |

## 延伸阅读

- [OpenTelemetry GenAI 语义约定](https://opentelemetry.io/docs/specs/semconv/gen-ai/) —— 规范
- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) —— 默认 GenAI span
- [AutoGen v0.4（Microsoft Research）](https://www.microsoft.com/en-us/research/articles/autogen-v0-4-reimagining-the-foundation-of-agentic-ai-for-scale-extensibility-and-robustness/) —— 内置 OTel span
- [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview) —— W3C trace context 传播
