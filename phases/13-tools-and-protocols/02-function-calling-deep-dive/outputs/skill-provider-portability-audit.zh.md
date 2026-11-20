---
name: provider-portability-audit
description: 审查针对某一家 provider 的 function-calling 集成，找出移植到另外两家时会出问题的点。
version: 1.0.0
phase: 13
lesson: 02
tags: [function-calling, openai, anthropic, gemini, portability]
---

给定在某一 provider（OpenAI、Anthropic 或 Gemini）上的 function-calling 集成，产出一份可移植性审计，列出同一套逻辑在另外两家 provider 上交付时会出现的每一处字段改名、行为差异与硬性限制冲突。

产出：

1. 声明差异。对集成中的每个工具，给出迁移到另外两家 provider 各自所需的包裹方式 / 字段改名 / schema 转换。标记目标 provider 不支持的 JSON Schema 构造（Gemini：OpenAPI 3.0 子集；OpenAI strict：不支持 `$ref`，不支持模棱两可的 `oneOf`）。
2. 响应差异。记录工具调用在各家 provider 响应形态中的位置（`tool_calls[]`、`content[]` 块、`parts[]` 条目），以及由谁负责解析 `arguments`（OpenAI 上是字符串，Anthropic 与 Gemini 上是对象）。
3. `tool_choice` 差异。把集成当前的选择设置（auto / forbid / force / required）映射到目标 provider 的形态；标记缺失的模式。
4. 限制冲突。报告工具数量（128 / 64 / 64）、schema 深度（5 / 10 / 实际上无上限）以及每个参数的长度上限。对任何超出目标 provider 限制的集成给出 block 级严重程度。
5. strict 模式映射。说明 strict 语义在目标上是否得以保留。OpenAI 的 `strict: true` 在 Anthropic 上没有完全等价的对应；Gemini 的 `responseSchema` 近似，但位于请求级别。

硬性拒绝：
- 任何在非 OpenAI 目标上假定 `arguments` 是字符串的集成。会静默产生错误结果。
- 任何在移植到 Anthropic 或 Gemini 时工具数量超过 64 且没有路由器的集成。
- 任何在目标为 OpenAI strict 模式时，schema 中使用 `$ref` 的集成。

拒绝规则：
- 如果被要求移植一个依赖某 provider 特有、且无对应物功能的集成（例如 OpenAI Responses API 的有状态轮次、Anthropic 的 computer-use 块），拒绝并说明哪项功能在目标上没有等价物。
- 如果被要求选出赢家，拒绝。选择取决于宿主的 strict 模式需求、成本结构与并行调用需求。

输出：一份单页审计，含逐工具差异表、限制表，以及针对每个目标 provider 的最终“移植裁决”（ship / needs-router / blocked-by-feature）。结尾用一句话点出杠杆最高的迁移改动。
