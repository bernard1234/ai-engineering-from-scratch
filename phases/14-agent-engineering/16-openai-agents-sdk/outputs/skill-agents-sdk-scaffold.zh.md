---
name: agents-sdk-scaffold
description: 搭建一个 OpenAI Agents SDK 应用，包含 triage 智能体、handoff、输入/输出/工具 guardrail、session 存储以及 trace 处理器。
version: 1.0.0
phase: 14
lesson: 16
tags: [openai, agents-sdk, handoffs, guardrails, tracing, session]
---

给定一个产品领域及一组专家智能体，搭建一个 OpenAI Agents SDK 应用。

产出：

1. 每个专家一个 `Agent`，外加一个只有 handoff（没有领域工具）的 `triage` 智能体。
2. 每个领域工具一个 `FunctionTool`，带类型化输入 schema、清晰的 description（告诉模型何时使用它）以及执行沙箱。
3. 从 triage 到每个专家的 `Handoff`。核对工具名遵循 `transfer_to_<agent>` 约定。
4. 针对 PII、策略、范围的 `InputGuardrail`。默认使用 parallel 模式，除非 guardrail LLM 相对于主模型较大——那就用 blocking。
5. 针对长度、PII、策略的 `OutputGuardrail`。对安全关键输出，在生产上始终 blocking。
6. 在接触网络或文件系统的函数工具上设置 per-tool guardrail。
7. `Session` 存储（默认 SQLite；生产用 Redis）。
8. 在 OpenAI 的 trace UI 之外，用 `add_trace_processor` 把 span 接入你的后端。

硬拒绝：

- 带领域工具的 Triage 智能体。Triage 只做 handoff；混入工具会稀释路由器的决策。
- 会改写输入/输出的 Guardrail。Guardrail 是批准或拒绝——它们不重写。
- 静默的 handoff 循环。要求一个跳数计数器（默认最大 3）。

拒绝规则：

- 如果用户想要“不要 guardrail，只要快速推进”，对任何面向付费用户或 PII 的产品都拒绝。
- 如果产品只有 2 个专家，建议用 `Agents` 加一个直接分类器（第 12 课）来做 routing，而不是 triage+handoff——token 成本更低。
- 如果生产上禁用了 tracing，拒绝上架。没有 trace，多步骤故障无法调试。

输出：`agents.py`、`tools.py`、`guardrails.py`、`app.py`、`README.md`，含 triage 智能体理由、guardrail 模式、trace 处理器及 session 后端。结尾的“接下来读什么”指向第 23 课（OTel GenAI）、第 24 课（观测后端），或第 17 课（Claude Agent SDK 的对应实现）。