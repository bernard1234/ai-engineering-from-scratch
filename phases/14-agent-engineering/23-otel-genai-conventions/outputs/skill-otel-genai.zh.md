---
name: otel-genai
description: 用 OpenTelemetry GenAI 语义约定给 agent 加 instrument —— invoke_agent、chat、tool_call span，带正确属性与 opt-in 内容捕获。
version: 1.0.0
phase: 14
lesson: 23
tags: [opentelemetry, genai, observability, tracing, semantic-conventions]
---

给定一个 agent 运行时，接入 OTel GenAI 语义约定。

产出：

1. 每次 agent 运行一个 `invoke_agent` span。远程 agent 服务用 CLIENT kind，进程内用 INTERNAL。名称：`invoke_agent {gen_ai.agent.name}`。
2. 每次 LLM 调用一个 `chat` span，带 `gen_ai.operation.name=chat`、`gen_ai.provider.name`、`gen_ai.request.model`、`gen_ai.response.model`。
3. 每次工具调用一个 `tool_call` span，带 `gen_ai.tool.name`，适用时带 `gen_ai.data_source.id`（RAG 语料库 / 记忆存储）。
4. Opt-in 内容捕获：默认关闭；开启时把输入/输出存到外部，并在 span 上记录 `*.reference_id`。
5. Context 传播：使用 W3C trace context 头，让多进程运行（Claude Agent SDK CLI 子进程）缝合成一条 trace。

硬性拒绝：

- 默认内联捕获完整 prompt/输出。PII 和密钥泄露风险；也违反规范。
- 缺少 `gen_ai.provider.name`。多提供商仪表盘会失效。
- 孤立的 tool span。始终通过活动 context 设置父子关系。

拒绝规则：

- 如果运行时无法跨进程边界传播 context，拒绝。多进程 trace 缝合对 Claude Agent SDK + CLI 用户是必需的。
- 如果产品有监管约束（HIPAA、GDPR），拒绝内联内容捕获。仅用带访问控制的外部存储。
- 如果后端没有设置 `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`，警告：collector 升级时属性名可能改变。

输出：`tracer.py`、`attributes.py`、`content_store.py`、`README.md`，说明 span 结构、稳定性 opt-in 与内容捕获策略。结尾以「接下来读什么」指向第 24 课（后端：Langfuse、Phoenix、Opik）或第 17 课的 Claude Agent SDK trace-context 传播。
