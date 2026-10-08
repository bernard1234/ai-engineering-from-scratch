---
name: tool-registry
description: 构建一个生产工具目录与注册表，带 JSON Schema 校验、并行调度和可观测性。
version: 1.0.0
phase: 14
lesson: 06
tags: [function-calling, tools, schema, validation, bfcl, parallel-tools]
---

给定任务领域，产出一个 agent 能在 BFCL V4 各轴（agentic、multi-turn、live、non-live、hallucination）上可靠使用的工具目录。

产出：

1. 工具定义。每个工具：`name`（snake_case）、`description`（告诉模型何时使用、何时不用）、带类型化属性的 JSON Schema 输入、必填字段、适用的 enums、数值的 minimum/maximum、每个工具的超时、每个工具的沙箱策略（fs surface、network、memory cap）。
2. 描述质量检查。用「这能否告诉模型何时在其它工具中选择该工具？」来检查每个描述。如果两个工具的描述重叠，拒绝并重写。
3. 并行调度计划。对每个现实任务，识别哪些工具调用相互独立（可并行）以及哪些必须串行。产出一个预期的调度图。
4. 校验策略。Enum 检查、类型强制规则（例如「接受 int-as-string，拒绝 float-as-string」）、必填字段强制。每次失败返回结构化 observation 字符串，绝不抛给循环。
5. 可观测性。每个工具发出一个 OpenTelemetry GenAI `tool_call` span，属性含 `gen_ai.tool.name`、`gen_ai.tool.call.id`、`gen_ai.tool.call.arguments`、`gen_ai.tool.call.result`（当内容策略要求时用引用而非内联）。

硬拒绝：

- 通用 shell/命令执行工具。拒绝并拆成具体动词（`git_status`、`fs_read`、`npm_test`）。
- 当参数是闭集值时缺失 enums。Enum 校验是抓漂移最便宜的办法。
- 两个不同工具用同一个描述。模型无法可靠地在它们之间选择。
- 只给出工具名的 `description`（「两数相加」）。要包含何时在替代方案中选择它。
- 没有超时。每个工具调用都必须有上限。

拒绝规则：

- 如果单个 agent 的工具列表超过 30 个，拒绝并建议子 agent 委派（Lesson 17）。
- 如果任何工具在没有确认门的情况下执行破坏性动作，拒绝并指向 Lesson 09（权限、沙箱）。
- 如果任务是 computer use（点击、输入、截图），拒绝并指向 Lesson 21——那是带视觉动作的独立工具形态。

输出：一个可粘贴进 Anthropic / OpenAI / Gemini SDK 调用的 JSON 工具目录、一个调度图、一份校验策略文档，以及一个注册表应通过的 BFCL 风格迷你 eval。

结尾加「what to read next」指针：Lesson 09（沙箱）、Lesson 23（OTel GenAI spans）或 Lesson 30（eval-driven）。