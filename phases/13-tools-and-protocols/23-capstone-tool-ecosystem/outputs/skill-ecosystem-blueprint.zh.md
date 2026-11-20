---
name: ecosystem-blueprint
description: 给定产品需求，产出一份完整的 Phase 13 生态架构；点名 primitives、安全态势、遥测和打包方式。
version: "1.0.0"
phase: "13"
lesson: "23"
tags: [mcp, capstone, ecosystem, architecture, a2a, otel]
---

给定一个产品需求（研究、摘要、自动化，或任何 agent 驱动的工作流），产出一份完整架构。

产出：

1. MCP 表面。定义 `server/discover`、每请求协议元数据、tools、resources、prompts 和缓存策略。点名任何 `ui://` Apps。
2. 扩展。如果工作是异步的，声明 `io.modelcontextprotocol/tasks`，并设计 `tasks/get`、`tasks/update` 和 `tasks/cancel`。初始 handle 保持在 `resultType: task`，把轮询结果设为 `resultType: complete`，不要使用 `tasks/result` 或 `tasks/list`。
3. 安全态势。OAuth 2.1 scope 集合、网关 RBAC 矩阵、固定哈希 manifest、Rule of Two 审计。
4. A2A 协作。识别任何 sub-agent 调用。定义它们的 Agent Cards。
5. 遥测。OTel GenAI span 层级。Exporter 与后端的选择。
6. 打包。AGENTS.md、SKILL.md，以及部署表面（Docker Compose、K8s）。
7. 映射到 Phase 13 课程。每个设计选择可以追溯到哪一课。

硬性拒绝：

- 任何在单轮中同时组合不可信输入、敏感数据与有后果操作的架构（Rule of Two）。
- 任何在 MCP 和 A2A 各跳之间缺少 trace 传播的架构。
- 任何在 LLM 层没有至少一个 fallback provider 的架构。
- 任何依赖 `initialize`、`Mcp-Session-Id`、`tasks/result` 或 `tasks/list` 的当前 MCP 设计。

拒绝规则：

- 如果该产品需求用直接 LLM 调用就能更好地满足，拒绝搭建完整生态。
- 如果团队缺乏运营网关的能力，推荐托管网关，并记录信任的转移。
- 如果架构涉及支付，要求一个单独审查过的支付授权协议，并明确签署。

输出：一页蓝图，包含 primitives、安全态势、A2A 跳、遥测计划、打包和课程映射。最后用一句话指出该部署中最棘手的单一运维风险。
