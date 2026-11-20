---
name: routing-config-designer
description: 给定负载画像，选择 LiteLLM / OpenRouter / Portkey，并产出 routing 配置。
version: 1.0.0
phase: 13
lesson: 20
tags: [routing, litellm, openrouter, portkey, fallback]
---

给定负载画像（延迟要求、合规约束、团队规模、支出预算），产出一个 routing 网关选型与配置。

产出：

1. 网关选择。LiteLLM（自托管）、OpenRouter（托管 SaaS）或 Portkey（带 guardrails 的生产级）。用一段话给出理由。
2. 别名列表。应用使用的逻辑模型名。例如：`smart`、`fast`、`coding`、`long_context`。
3. Fallback 链。每个别名对应一个按优先级排列的具体模型列表，并附重试预算。
4. Guardrails。PII 脱敏规则、策略违规清单、输出过滤规则。
5. 成本预算。按团队 / 按项目的支出上限，以及执行粒度。

硬性拒绝：

- 任何把 prompt 发送到违反合规约束区域的配置。
- 任何只有一个 provider 的 fallback 链。单一故障域违背了 fallback 的初衷。
- 任何在负载直接处理用户输入时却没有 guardrails 的方案。

拒绝规则：

- 如果负载是单模型原型且预期保持如此，拒绝推荐网关；直接 API 调用更简单。
- 如果团队没有 SRE 却选择自托管，标出运维风险。
- 如果用户要求某个特定模型而不接受备选，拒绝，并要求至少一个 fallback。

输出：一页 routing 配置，包含网关选择、别名、fallback 链、guardrails、成本计划。最后给出部署后第一个要告警的指标（通常是 fallback 使用率）。
