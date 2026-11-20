# 工具接口 —— 为什么 Agent 需要结构化 I/O

> 语言模型产出 token，程序执行动作。二者之间的鸿沟就是工具接口：一份让模型请求某个动作、由宿主机代为执行的契约。2026 年的每一套技术栈——OpenAI、Anthropic、Gemini 上的 function calling，MCP 的 `tools/call`，A2A 的 task parts——都是同一个四步循环的不同编码方式。本节为这个循环命名，并给出运行它所需的最小机制。

**Type:** Learn
**Languages:** Python（标准库，不使用 LLM）
**Prerequisites:** 第 11 阶段（LLM completion API）
**Time:** ~45 分钟

## Learning Objectives

- 解释为什么一个只能生成文本的 LLM 无法独自对真实世界采取动作。
- 画出四步工具调用循环（描述 → 决策 → 执行 → 观察），并说明每一步由谁负责。
- 把工具描述写成三个部分：名称、JSON Schema 输入、确定性执行函数。
- 区分纯工具与有副作用的工具，并说明这种划分为何对安全很重要。

## 问题场景

LLM 输出的是下一个 token 上的概率分布，这就是它全部的输出面。如果你问一个聊天模型“班加罗尔现在天气如何”，它能写出一句看起来合理的话，但它无法真的去连接天气 API。那句话也许碰巧正确，也可能已经是三天前的旧信息。

弥合这一鸿沟正是工具接口存在的目的。宿主机程序——你的 agent 运行时、Claude Desktop、ChatGPT、Cursor，或某个自定义脚本——向模型通告一份可调用工具的清单。当模型判断需要执行某个动作时，它会产出一个结构化载荷，指明工具名称及其参数。宿主解析该载荷，真正执行工具，再把结果回传。循环持续进行，直到模型判断不再需要调用工具为止。

这份契约的第一版于 2023 年 6 月以 OpenAI 的 “functions” 参数形式发布。Anthropic 随后在 Claude 2.1 中以 `tool_use` 块跟进。几个月后 Gemini 加入了 `functionDeclarations`。如今每个 provider 暴露的都是同一形态：输入一份 JSON Schema 类型的工具清单，输出一个 JSON 载荷形式的工具调用。Model Context Protocol（2024 年 11 月）把这份契约推广开来，使一个工具注册表可以服务所有模型。A2A（2026 年 4 月，v1.0）为 agent 之间的委派叠加了同样的原语。

四步循环是贯穿上述所有方案的不变量。Phase 13 余下的内容都是对它的展开。

## 核心概念

### 第 1 步：描述

宿主机用三个字段声明每个工具。

- **Name。** 一个稳定的、机器可读的标识符。用 `get_weather`，而不是 “weather thing”。
- **Description。** 一段自然语言的简要说明。“当用户询问某个特定城市的当前天气状况时使用。不要用于历史数据。”
- **Input schema。** 一个 JSON Schema 对象（draft 2020-12），描述该工具的参数。

模型收到这份清单。现代 provider 会用各自的模板把这些声明序列化进 system prompt，因此作为调用方的你只需处理结构化形式。

### 第 2 步：决策

给定用户的消息和可用工具，模型会选择三种行为之一。

1. **直接回答**：以文本作答，不调用工具。
2. **调用一个或多个工具。** 产出结构化的调用对象。在 `parallel_tool_calls: true` 下（OpenAI 与 Gemini 默认开启，Anthropic 需显式开启），模型可以在一轮中产出多个调用。
3. **拒绝。** strict 模式下的 structured output 可以产出一个带类型的 `refusal` 块，而不是一次调用。

工具调用载荷有三个稳定字段：调用 `id`、工具 `name`，以及 JSON 形式的 `arguments` 对象。id 的存在是为了让宿主机能把稍后的结果对应到具体的那次调用；当并行调用的返回顺序被打乱时，这一点尤其重要。

### 第 3 步：执行

宿主机收到调用，依照已声明的 schema 校验参数，然后运行执行器。参数非法意味着模型幻觉出了字段或用错了类型——这在弱模型上是非常常见的失败模式。面对非法参数，生产级宿主通常有三种做法：快速失败并把错误反馈给模型；用带约束的解析器修复 JSON；或者带着校验错误信息重试模型。

执行器本身是普通代码。Python、TypeScript、一条 shell 命令、一次数据库查询。它产生一个结果，通常是字符串，但也可以是任意 JSON 值或结构化内容块（MCP 中的文本、图像或资源引用）。结果必须可序列化。

### 第 4 步：观察

宿主机把工具结果追加进对话（作为一条带匹配 `id` 的 `tool` 角色消息），然后重新调用模型。此时模型在上下文中已拥有工具输出，可以给出最终答案，或请求更多调用。这一过程持续进行，直到模型不再产出调用，或宿主机触达迭代次数的安全上限。

### 信任划分

从安全角度看，工具分两类。

- **Pure（纯）。** 只读、确定性、无副作用。`get_weather`、`search_docs`、`get_current_time`。可以放心地试探性调用。
- **Consequential（有后果）。** 会改变状态、花钱、触碰用户数据。`send_email`、`delete_file`、`execute_trade`。必须加闸门。

Meta 在 2026 年为 agent 安全提出的 “Rule of Two” 认为：单轮之中最多只能组合以下三者中的两项——不可信输入、敏感数据、有后果的动作。工具接口正是你落实这条规则的场所——通过拒绝调用、要求用户确认或提升权限范围。完整的安全章节见 第 13 阶段，第 15 课，agent 级别的权限策略见 Phase 14 · 09。

### 循环发生在哪里

| 场景 | 谁负责描述 | 谁负责决策 | 谁负责执行 |
|---------|---------------|-------------|--------------|
| 单轮 function calling（OpenAI/Anthropic/Gemini） | 应用开发者 | LLM | 应用开发者 |
| MCP | MCP server | 经由 MCP client 的 LLM | MCP server |
| A2A | Agent Card 发布方 | 调用方 agent | 被调用 agent |
| Web 浏览器（function-calling agent） | 浏览器扩展 / WebMCP | LLM | 浏览器运行时 |

处处都是同样的四步。列名会变，结构不变。

### 为什么不干脆让模型直接输出 JSON？

“让模型用 JSON 回复” 是 function calling 之前的老做法。在 frontier 模型上它大约有 5% 到 15% 的失败率，在更小的模型上则高得多。失败形态包括缺失花括号、多余逗号、幻觉字段和类型错误。于是你还需要一个 JSON 修复步骤、一次重试，或一个受约束的解码器。

原生 function calling 更好的原因有三。第一，provider 在精确的调用形态上对模型做了端到端训练，因此在 strict 模式下合法 JSON 率可升到 98% 到 99%。第二，调用载荷位于自己的协议槽位中，而不是混在自由文本里——因此工具调用永远不会泄漏进用户可见的回复。第三，provider 用 constrained decoding 强制 schema 合规（OpenAI 的 strict 模式、Anthropic 的 `tool_use`、Gemini 的 `responseSchema`）。输出保证通过校验。

第 13 阶段，第 02 课 并列走查三家 provider 的 API。第 13 阶段，第 04 课 深入 structured output。

### 熔断

当模型不再产出调用，或宿主机触达最大轮数时，循环终止。生产级宿主把它设在 5 到 20 轮之间。超过这个范围，你几乎肯定陷入了模型无法自行退出的循环。Claude Code 默认 20 轮，OpenAI Assistants 为 10，Cursor 的 agent 模式为 25。

另一种做法——不设上限的循环——每半年就会以 “agent 一夜之间花了 400 美元 API 费用” 的事后复盘形式出现。没有上限就别上线。

Phase 14 · 12 深入讨论错误恢复与自愈；Phase 17 讨论生产环境的速率限制。

### Phase 13 接下来走向何处

- 第 02 到 05 节打磨 provider 层面的工具调用接口。
- 第 06 到 14 节把该循环推广为 MCP。
- 第 15 到 18 节防御恶意服务器、对抗性用户，以及未认证的远程认证攻击面。
- 第 19 到 22 节把这一模式延伸到 agent 之间的协作、可观测性、路由与打包。
- 第 23 节用所有这些原语交付一套完整的生态。

余下每一节都是对这个四步循环的展开。请把它当作不变量记在心中。

```figure
tp-tool-loop
```

## Use It

`code/main.py` 在不使用 LLM 的情况下运行四步循环。一个假的 “decider” 函数通过对用户消息做模式匹配来模拟模型；而执行器、schema 校验器和观察步骤的测试框架都是真实的。运行它可以看到完整的请求/响应编排过程与可打印的中间状态，随后你可以在后续课程中把假 decider 换成任意真实的 provider。

值得关注的点：

- 工具注册表为每个工具保存三个字段：名称、描述、schema，以及一个执行器引用。
- 校验器是一个极简的 JSON Schema 子集（types、required、enum、min/max），只用标准库写成。第 13 阶段，第 04 课 提供了更完整的实现。
- 循环把迭代次数限制在五次。生产级 agent 恰恰需要这种熔断。

## Ship It

本节产出 `outputs/skill-tool-interface-reviewer.md`。给定一份工具定义草稿（名称 + 描述 + schema + 执行器概要），该 skill 会从循环契合度出发对它进行审查：名称是否机器稳定，描述是否是一份完整的使用说明，schema 是否正确使用 JSON Schema 2020-12，以及 pure 与 consequential 的分类是否明确。

## Exercises

1. 在 `code/main.py` 中新增第四个工具 `get_stock_price(ticker)`。把它的描述写成 “当用户按股票代码询问当前股价时使用。不要用于历史价格或市场综述。” 运行测试框架，确认假 decider 会把提到股票代码的查询路由到新工具。

2. 破坏 schema 校验器。传入一个 `arguments` 对象缺少必填字段的调用，确认宿主在执行前拒绝它。再传入一个带有额外未知字段的调用。做出判断：宿主应当拒绝还是忽略？用安全方面的论据为你的选择辩护。

3. 把测试框架中的每个工具归类为 pure 或 consequential。为需要的注册表条目加上 `consequential: true` 标记，并修改循环，使得每当选中一个 consequential 工具时打印一行 “would confirm with user”。这正是每个生产级宿主都需要的确认闸门的形态。

4. 在纸上画出四步循环，并用你最喜欢的客户端（Claude Desktop、Cursor、ChatGPT 或自定义技术栈）填上上面的 provider 列表格。与 第 13 阶段，第 06 课 中 MCP 专用的变体相互对照。

5. 从头到尾读一遍 OpenAI 的 function-calling 指南。找出那个存在于请求中、却不在本节所述四步循环里的字段。解释它增加了什么，以及为什么它只是便利而非必需。

## Key Terms

| 术语 | 常见说法 | 实际含义 |
|------|----------------|------------------------|
| Tool | “模型能调用的一样东西” | 名称 + JSON Schema 类型输入 + 执行器函数三者的组合 |
| Function calling | “原生工具使用” | provider 层面的 API 支持，用结构化工具调用来替代散文式输出 |
| Tool call | “模型的行动请求” | 由模型产出的、包含 `id`、`name`、`arguments` 的 JSON 载荷 |
| Tool result | “工具返回的东西” | 执行器的输出，包装为带匹配 id 的 `tool` 角色消息 |
| Parallel tool calls | “一次多个调用” | 单个模型轮次中的多个调用对象，彼此独立、可按 id 排序 |
| Strict mode | “保证 JSON” | 强制模型输出通过已声明 schema 校验的 constrained decoding |
| Pure tool | “只读工具” | 无副作用；可安全重复运行 |
| Consequential tool | “动作工具” | 改变外部状态；需要闸门、审计或用户确认 |
| Four-step loop | “工具调用周期” | describe → decide → execute → observe |
| Host | “Agent 运行时” | 持有工具注册表、调用模型并运行执行器的程序 |

## Further Reading

- [OpenAI — Function calling guide](https://platform.openai.com/docs/guides/function-calling) — OpenAI 风格工具声明与调用形态的权威参考
- [Anthropic — Tool use overview](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview) — Claude 的 `tool_use` / `tool_result` 块格式
- [Google — Gemini function calling](https://ai.google.dev/gemini-api/docs/function-calling) — Gemini 中的 `functionDeclarations` 与并行调用语义
- [Model Context Protocol — Specification 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28) — 工具接口当前的无状态、provider 无关的推广形态
- [JSON Schema — 2020-12 release notes](https://json-schema.org/draft/2020-12/release-notes) — 每个现代工具 API 都在使用的 schema 方言
