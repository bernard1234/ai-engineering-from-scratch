---
name: a2a-integrator
description: 设计两个 agent 之间的 A2A 集成 —— Agent Card、task schema、auth、流式或轮询。
version: 1.0.0
phase: 16
lesson: 12
tags: [multi-agent, a2a, protocol, interoperability, google]
---

给定两个需要互操作的 agent 系统，产出 A2A 集成方案：Agent Card 内容、task schema、auth、transport 模式。

产出：

1. **Agent Card。** name、version、skills、endpoints、支持的模态（text、structured、image、audio、video）、protocol_version、auth 声明。
2. **每个 skill 的 task schema。** 输入 JSON schema + artifact JSON schema。要写清楚 —— 客户端会做校验。
3. **认证选择。** bearer token（OAuth2 或不透明）、mTLS，或签名请求。结合威胁模型（公网、VPC、混合）给出理由。
4. **Transport 模式。** 轮询、SSE 流式，还是 webhook 回调。长时间运行或进度密集的任务用流式；短任务用轮询。
5. **限流。** 按 client 与按 task 的限制。防止滥用。
6. **幂等性。** 处理重复 `POST /tasks` 请求的策略（client 侧 task-key、server 侧去重）。
7. **失败处理。** `failed` 之外的 task 状态（可重试与致命）、死信策略、错误 artifact schema。
8. **MCP 与 A2A 的分工。** 如果远端 agent 内部使用 MCP，注明哪些 tool 对外暴露、哪些保留在内部。

硬性拒绝：

- 未声明协议版本的 Agent Card。
- 在用例需要结构化时却用自由文本的 task schema。
- 公网部署上的 Auth=none。

拒绝规则：

- 如果两个 agent 运行在同一进程内，拒绝 A2A，推荐直接进行 Python/JS 调用。A2A 用于跨系统边界。
- 如果延迟要求是亚 100ms 往返，拒绝 A2A，推荐带共享 schema 的直接 RPC。
- 如果远端 agent 没有声明 Agent Card，拒绝集成，建议先发布一张。

输出：一份一页纸的集成简报。结尾把 Agent Card JSON 原样贴出，工程团队可以直接放进 `/.well-known/agent.json`。
