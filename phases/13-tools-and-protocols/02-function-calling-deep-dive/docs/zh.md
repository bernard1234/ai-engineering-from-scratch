# Function Calling 深入剖析 —— OpenAI、Anthropic、Gemini

> 三家 frontier provider 在 2024 年收敛到同一个工具调用循环，随后又在其他所有方面分道扬镳。OpenAI 使用 `tools` 与 `tool_calls`。Anthropic 使用 `tool_use` 与 `tool_result` 块。Gemini 使用 `functionDeclarations` 与唯一 id 关联。本节并排比对这三者，使在某一家 provider 上交付的代码在移植时不会崩掉。

**Type:** Build
**Languages:** Python（标准库，schema 转换器）
**Prerequisites:** 第 13 阶段，第 01 课（工具接口）
**Time:** ~75 分钟

## Learning Objectives

- 说明 OpenAI、Anthropic、Gemini 三者 function-calling 载荷在形态上的三处差异（declaration、call、result）。
- 把一份工具声明转换到三家 provider 的格式，并预判 strict 模式约束会在哪里不同。
- 在各家 provider 中使用 `tool_choice`，强制、禁止或自动选择工具调用。
- 了解每家 provider 的硬性限制（工具数量、schema 深度、参数长度）以及超限时各自抛出的错误特征。

## 问题场景

function-calling 请求的形态随 provider 而异。三个来自 2026 年生产技术栈的具体例子：

**OpenAI Chat Completions / Responses API。** 你传入 `tools: [{type: "function", function: {name, description, parameters, strict}}]`。模型的响应包含 `choices[0].message.tool_calls: [{id, type: "function", function: {name, arguments}}]`，其中 `arguments` 是一个你必须解析的 JSON 字符串。strict 模式（`strict: true`）通过 constrained decoding 强制 schema 合规。

**Anthropic Messages API。** 你传入 `tools: [{name, description, input_schema}]`。响应以 `content: [{type: "text"}, {type: "tool_use", id, name, input}]` 形式返回。`input` 已经解析好（是对象，不是字符串）。你以一条新的 `user` 消息回复，其中包含 `{type: "tool_result", tool_use_id, content}` 块。

**Google Gemini API。** 你传入 `tools: [{functionDeclarations: [{name, description, parameters}]}]`（嵌套在 `functionDeclarations` 下）。响应以 `candidates[0].content.parts: [{functionCall: {name, args, id}}]` 形式到达，其中 `id` 在 Gemini 3 及以上版本中唯一，用于并行调用的关联。你以 `{functionResponse: {name, id, response}}` 回复。

相同的循环。不同的字段名、不同的嵌套、字符串与对象的不同约定、不同的关联机制。一个在 OpenAI 上写了天气 agent 的团队，移植到 Anthropic 要付两天的对接成本，再到 Gemini 又要一天，全花在管道上。

本节构建一个转换器，把三种格式统一成一份规范的 tool declaration，并在边缘处路由。第 13 阶段，第 17 课 把同一模式推广为 LLM gateway。

## 核心概念

### 共同结构

每家 provider 都需要五样东西：

1. **工具清单。** 每个工具的名称、描述与输入 schema。
2. **工具选择。** 强制某个工具、禁止工具，或让模型自行决定。
3. **调用产出。** 指明工具与参数的结构化输出。
4. **调用 id。** 把响应关联到正确的调用（并行时很重要）。
5. **结果注入。** 一条把结果与调用关联回的消息或块。

### 逐字段的形态差异

| 方面 | OpenAI | Anthropic | Gemini |
|--------|--------|-----------|--------|
| 声明外层 | `{type: "function", function: {...}}` | `{name, description, input_schema}` | `{functionDeclarations: [{...}]}` |
| schema 字段 | `parameters` | `input_schema` | `parameters` |
| 响应容器 | assistant 消息上的 `tool_calls[]` | 类型为 `tool_use` 的 `content[]` | 类型为 `functionCall` 的 `parts[]` |
| 参数类型 | 字符串化的 JSON | 已解析的对象 | 已解析的对象 |
| id 格式 | `call_...`（OpenAI 生成） | `toolu_...`（Anthropic） | UUID（Gemini 3+） |
| 结果块 | 角色 `tool`、`tool_call_id` | 带 `tool_result`、`tool_use_id` 的 `user` | 带匹配 `id` 的 `functionResponse` |
| 强制某工具 | `tool_choice: {type: "function", function: {name}}` | `tool_choice: {type: "tool", name}` | `tool_config: {function_calling_config: {mode: "ANY"}}` |
| 禁止工具 | `tool_choice: "none"` | `tool_choice: {type: "none"}` | `mode: "NONE"` |
| strict schema | `strict: true` | schema 即 schema（始终强制） | 请求级的 `responseSchema` |

### 你实际会撞上的限制

- **OpenAI。** 每个请求 128 个工具。schema 深度 5。参数字符串 <= 8192 字节。strict 模式不允许 `$ref`，不允许有重叠的 `oneOf`/`anyOf`/`allOf`，且每个属性都必须列在 `required` 中。
- **Anthropic。** 每个请求 64 个工具。schema 深度实际无上限，但实践限制为 10。没有 strict 模式开关；schema 是一份契约，模型通常会遵守。
- **Gemini。** 每个请求 64 个 function。schema 类型是 OpenAPI 3.0 子集（与 JSON Schema 2020-12 略有差异）。自 Gemini 3 起并行调用带唯一 id。

### `tool_choice` 行为

所有人都支持三种模式，只是叫法不同。

- **Auto。** 模型自行选择工具或文本。默认。
- **Required / Any。** 模型必须至少调用一个工具。
- **None。** 模型不得调用工具。

外加每家 provider 各自独有的一种模式：

- **OpenAI。** 按名称强制某个工具。
- **Anthropic。** 按名称强制某个工具；`disable_parallel_tool_use` 标志区分单次与多次。
- **Gemini。** `mode: "VALIDATED"` 让每个响应都经由 schema 校验器，无论模型意图如何。

### 并行调用

OpenAI 的 `parallel_tool_calls: true`（默认）会在一条 assistant 消息中产出多个调用。你把它们全部执行，再用一条批量的 tool 角色消息回复，每个 `tool_call_id` 对应一条。Anthropic 历史上只做单次调用；`disable_parallel_tool_use: false`（自 Claude 3.5 起默认）启用多次。Gemini 2 允许并行调用，但不给稳定 id；Gemini 3 加入 UUID，使乱序返回的响应能干净地关联。

### 流式

三者都支持流式工具调用。线路格式不同：

- **OpenAI。** `tool_calls[i].function.arguments` 的增量块逐步到达。你累积到 `finish_reason: "tool_calls"` 为止。
- **Anthropic。** block-start / block-delta / block-stop 事件。`input_json_delta` 块携带部分参数。
- **Gemini。** `streamFunctionCallArguments`（Gemini 3 新增）产出的块带有 `functionCallId`，使多个并行调用可以交错。

第 13 阶段，第 03 课 深入讲解并行 + 流式的重组。本节聚焦声明与单次调用的形态。

### 错误与修复

非法参数错误的呈现方式也不一样。

- **OpenAI（非 strict）。** 模型返回 `arguments: "{bad json}"`，你的 JSON 解析失败，你注入一条错误消息并重新调用。
- **OpenAI（strict）。** 校验在解码过程中进行；非法 JSON 不可能出现，但可能出现 `refusal`。
- **Anthropic。** `input` 可能包含意外字段；schema 只是建议性的。请在自己服务端校验。
- **Gemini。** OpenAPI 3.0 的怪癖：对象字段上的 `enum` 会被静默忽略；请自行校验。

### 转换器模式

你代码中的一份规范 tool declaration 大致长这样（形态由你选择）：

```python
Tool(
    name="get_weather",
    description="Use when ...",
    input_schema={"type": "object", "properties": {...}, "required": [...]},
    strict=True,
)
```

三个小函数把它转换成三家 provider 的形态。`code/main.py` 中的测试框架正是这样做的，然后让一个假的工具调用在每家 provider 的响应形态间往返。无需网络——本节讲的是形态，不是 HTTP。

生产团队会把这一转换器封装进 `AbstractToolset`（Pydantic AI）、`UniversalToolNode`（LangGraph）或 `BaseTool`（LlamaIndex）。第 13 阶段，第 17 课 交付一个 gateway，在任意一家之上暴露 OpenAI 形态的 API。

```figure
function-call-args
```

## Use It

`code/main.py` 定义一个规范的 `Tool` dataclass，以及三个转换器，分别产出 OpenAI、Anthropic、Gemini 的声明 JSON。然后它把三种形态中各一份手工构造的 provider 响应解析回同一个规范调用对象，证明底层语义完全相同。运行它，并排比对三份声明。

值得关注的点：

- 三个声明块只在外部包裹和字段名上不同。
- 三个响应块的不同在于调用所在的位置（顶层 `tool_calls`、`content[]` 块、`parts[]` 条目）。
- 一个 `canonical_call()` 函数从三种响应形态中提取 `{id, name, args}`。

## Ship It

本节产出 `outputs/skill-provider-portability-audit.md`。给定针对某一家 provider 的 function-calling 集成，该 skill 产出一份可移植性审计：它依赖了哪些 provider 限制、哪些字段需要改名，以及移植到另外两家时各自会坏在哪里。

## Exercises

1. 运行 `code/main.py`，验证三份 provider 声明 JSON 序列化的都是同一个底层 `Tool` 对象。修改规范工具以添加一个 enum 参数，确认只有 Gemini 转换器需要处理 OpenAPI 那个怪癖。

2. 为每家 provider 添加一个 `ListToolsResponse` 解析器，提取模型在 `list_tools` 或发现调用之后返回的工具清单。OpenAI 原生没有对应物；记下这一不对称。

3. 实现 `tool_choice` 转换：把规范的 `ToolChoice(mode="force", tool_name="x")` 映射到三家 provider 的形态。再映射 `mode="any"` 与 `mode="none"`。对照本节的差异表。

4. 从三家 provider 中挑一家，从头到尾读它的 function-calling 指南。找出它的 schema 规范中另外两家不支持的一个字段。候选：OpenAI 的 `strict`、Anthropic 的 `disable_parallel_tool_use`、Gemini 的 `function_calling_config.allowed_function_names`。

5. 写一个测试向量：一个参数违反已声明 schema 的工具调用。把它送进每家 provider 的校验器（第 01 节的标准库实现可作代理），记录触发了哪些错误。记录你会为严格性在生产中选择哪一家 provider。

## Key Terms

| 术语 | 常见说法 | 实际含义 |
|------|----------------|------------------------|
| Function calling | “工具使用” | provider 层面用于结构化工具调用产出的 API |
| Tool declaration | “工具规格” | 名称 + 描述 + JSON Schema 输入载荷 |
| `tool_choice` | “强制 / 禁止” | auto / required / none / 指定名称等模式 |
| Strict mode | “schema 强制” | OpenAI 的标志，约束解码以匹配 schema |
| `tool_use` block | “Anthropic 的调用形态” | 带 id、name、input 的内联内容块 |
| `functionCall` part | “Gemini 的调用形态” | 一个包含 name、args、id 的 `parts[]` 条目 |
| Arguments-as-string | “字符串化 JSON” | OpenAI 以 JSON 字符串而非对象返回参数 |
| Parallel tool calls | “一轮内扇出” | 一条 assistant 消息中的多个工具调用 |
| Refusal | “模型拒绝” | 仅 strict 模式下的拒绝块，替代调用 |
| OpenAPI 3.0 subset | “Gemini 的 schema 怪癖” | Gemini 使用一种类 JSON Schema、带细微差异的方言 |

## Further Reading

- [OpenAI — Function calling guide](https://platform.openai.com/docs/guides/function-calling) — 权威参考，含 strict 模式与并行调用
- [Anthropic — Tool use overview](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview) — `tool_use` 与 `tool_result` 块的语义
- [Google — Gemini function calling](https://ai.google.dev/gemini-api/docs/function-calling) — 并行调用、唯一 id 与 OpenAPI 子集
- [Vertex AI — Function calling reference](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling) — Gemini 的企业级接口面
- [OpenAI — Structured outputs](https://platform.openai.com/docs/guides/structured-outputs) — strict 模式 schema 强制的细节
