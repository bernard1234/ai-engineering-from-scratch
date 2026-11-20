# 并行工具调用与工具流式输出

> 三次独立的天气查询若串行执行，就是三次往返。并行执行，总耗时便塌缩到最慢的那一次调用。如今每个 frontier provider 都能在单轮中产出多个工具调用。收益是真实的，管道却是微妙的。本节把两半都走一遍：并行扇出，以及流式参数的重组，重点在 id 关联这个陷阱。

**Type:** Build
**Languages:** Python（标准库，线程池 + 流式测试框架）
**Prerequisites:** 第 13 阶段，第 02 课（function calling 深入剖析）
**Time:** ~75 分钟

## Learning Objectives

- 解释 `parallel_tool_calls: true` 为何存在，以及何时应禁用它。
- 在并行扇出期间，把流式参数的块关联到正确的 tool-call id。
- 把零散的 `arguments` 字符串重组为完整 JSON，且不提前解析。
- 运行一个三城市天气基准，展示串行与并行的时延差异。

## 问题场景

没有并行调用时，回答“班加罗尔、东京和苏黎世的天气如何”的 agent 会这样做：

```
user -> LLM
LLM -> call get_weather(Bengaluru)
host -> run executor, reply with result
LLM -> call get_weather(Tokyo)
host -> run executor, reply with result
LLM -> call get_weather(Zurich)
host -> run executor, reply with result
LLM -> final text answer
```

三次 LLM 往返，每次还要叠加执行器的时延。大约是理想墙钟时间的 4 倍。

有了并行调用：

```
user -> LLM
LLM -> call get_weather(Bengaluru); call get_weather(Tokyo); call get_weather(Zurich)
host -> run all three executors concurrently, reply with three results
LLM -> final text answer
```

一次 LLM 往返。执行器耗时是三者中的最大值，而不是总和。OpenAI、Anthropic、Gemini 上的生产基准显示，扇出类负载的墙钟时间可减少 60% 到 70%。

代价是关联复杂度。当三个调用乱序完成时，你的结果必须携带匹配的 `tool_call_id`，模型才能把它们对上。当结果以流式到达时，你必须在执行前把零散的参数片段拼成完整 JSON。Gemini 3 加入唯一 id，部分原因就是解决一个真实问题：对同一工具的两次并行调用原本无法区分。

## 核心概念

### 启用并行

- **OpenAI。** `parallel_tool_calls: true` 默认开启。设为 `false` 可强制串行。
- **Anthropic。** 通过 `disable_parallel_tool_use: false` 实现并行（Claude 3.5 及以后默认）。设为 `true` 则串行。
- **Gemini。** 始终具备并行能力；`tool_config.function_calling_config.mode = "AUTO"` 让模型自行决定。

当工具之间存在顺序依赖（先 `create_file` 再 `write_file`）、一次调用的输出会成为另一次调用的输入，或限流器扛不住扇出时，应禁用并行。

### id 关联

模型产出的每个调用都有一个 `id`。宿主返回的每个结果都必须带上同一个 id。否则结果就是歧义的。

- **OpenAI。** 每条 tool 角色消息上的 `tool_call_id`。
- **Anthropic。** 每个 `tool_result` 块上的 `tool_use_id`。
- **Gemini。** 每个 `functionResponse` 上的 `id`（Gemini 3 及以上；Gemini 2 按名称匹配，遇到同名并行调用就失效了）。

### 并发执行调用

宿主把每个调用交给各自的线程、协程或远程 worker 执行。最简单的测试框架用线程池；生产环境用 asyncio 配合 `asyncio.gather`，或结构化并发。完成的顺序不可预测——id 才是标识符。

一个常见 bug：按调用清单的顺序而非完成顺序回复结果。这通常也能跑通，因为模型只关心 `tool_call_id`，但一旦某个结果被丢弃或重复，乱序提交会让调试更难。优先按完成顺序回复，并显式带上 id。

### 流式工具调用

当模型以流式输出时，`arguments` 分片到达。三个并行调用的三股块流在线路上交错。你需要为每个 id 各配一个累加器。

按 provider 的形态：

- **OpenAI。** 每个块是 `choices[0].delta.tool_calls[i].function.arguments`（部分字符串）。块中携带 `index`（在调用清单中的位置）。你按 index 累积，在 `id` 首次出现时读取它，并在 `finish_reason = "tool_calls"` 时解析 JSON。
- **Anthropic。** 流事件先是 `message_start`，然后每个类型为 `tool_use` 的块对应一个 `content_block_start`（含 id、name 与空 input）。`content_block_delta` 事件携带 `input_json_delta` 块。`content_block_stop` 关闭每个块。
- **Gemini。** `streamFunctionCallArguments`（Gemini 3 及以上）产出的块带有 `functionCallId`，使调用能干净交错。在 Gemini 3 之前，流式一次性返回一个完整调用。

### 部分 JSON 与提前解析陷阱

在 `arguments` 完整之前你无法解析它。像 `{"city": "Beng` 这样的部分 JSON 并不合法，解析会抛异常。正确的判定信号是 provider 的调用结束标志：OpenAI 的 `finish_reason = "tool_calls"`、Anthropic 的 `content_block_stop`，或 Gemini 的流结束事件。只有到那时才尝试 `json.loads`。更稳健的做法是使用增量 JSON 解析器，在结构完成时逐个产出事件；OpenAI 的流式指南推荐这种方式，用于实现实时显示“思考中”指示器的体验。数花括号并不是可靠完整性判定（引号字符串或转义内容中的括号会造成误判），只能当作非正式的调试启发式使用。

### 乱序完成

```
call_A: fast API, returns first
call_B: slow API, returns second
call_C: median API, returns third
```

宿主的回复仍必须引用这些 id：

```
[{role: "tool", tool_call_id: "call_A", content: ...},
 {role: "tool", tool_call_id: "call_B", content: ...},
 {role: "tool", tool_call_id: "call_C", content: ...}]
```

在 OpenAI 或 Anthropic 上，回复中的顺序对正确性没有影响。只要 id 匹配，Gemini 接受任意顺序。

### 基准：串行 vs 并行

`code/main.py` 中的测试框架模拟三个执行器，时延分别为 400、600、800 毫秒。串行运行总耗时 1800 毫秒。并行运行则是 max(400, 600, 800) = 800 毫秒。这个差距是常量而非比例，因此工具越多，节省越多。

现实中的注意事项：并行调用会给下游 API 带来压力。对限流服务做 10 路扇出必然失败。第 13 阶段，第 17 课 讨论 gateway 层的背压；重试语义计划在未来的 phase 中讲解。

### 流式扇出的墙钟时间

如果模型本身在流式输出，你可以在某个调用的参数一完成时就立即开始执行，而不必等到所有调用都定稿。这是 OpenAI 有文档记录、但并非所有 SDK 都暴露的优化。本节中的测试框架就做到了：一旦模拟流产出完整的参数对象，宿主立刻启动该调用。

```figure
tp-parallel-fanout
```

## Use It

`code/main.py` 分两半。前半部分用 `concurrent.futures.ThreadPoolExecutor` 分别以串行和并行方式运行三个模拟天气调用，并打印墙钟时间。后半部分回放一段假的流式响应——三个并行调用的 `arguments` 块交错在同一条流上——并用 `StreamAccumulator` 按 id 重组。没有 LLM，没有网络，只有重组逻辑。

值得关注的点：

- 串行计时器停在 1.8 秒。在相同的假时延下，并行计时器停在 0.8 秒。
- 累加器通过按 id 缓冲来处理乱序到达的块，并且只在每个调用的 JSON 完整时才解析。
- 执行器在某个 id 的参数定稿的那一刻就启动，而不是等所有流结束。

## Ship It

本节产出 `outputs/skill-parallel-call-safety-check.md`。给定一个工具注册表，该 skill 审查哪些工具可以安全并行、哪些存在顺序依赖、哪些会压垮下游限流——并返回一份带逐工具 `parallel_safe` 标记的修订注册表。

## Exercises

1. 运行 `code/main.py` 并调整模拟时延。确认并行与串行的比例大致为 `max/sum`（由于线程调度、序列化与测试框架开销，真实运行会略微偏离理想值）。时延分布达到什么程度时并行就不再值得？

2. 扩展累加器以处理“调用在流处理中途被取消”的情况：丢弃其缓冲区并发出 `cancelled` 事件。哪家 provider 明确记录了这一情况？查看 Anthropic 的 `content_block_stop` 语义与 OpenAI 的 `finish_reason: "length"` 行为。

3. 把线程池换成 `asyncio.gather`。对两者做基准。由于上下文切换开销更低，异步应该会有小幅优势，但前提是执行器确实在做真实 I/O。

4. 挑两个不应并行的工具（例如先 `create_file` 再 `write_file`）。在注册表中加入 `ordering_dependency` 图，并据此对并行扇出设闸。这是依赖感知调度的最小机制，未来某个 agent 工程 phase 会将其形式化。

5. 阅读 OpenAI 的并行 function calling 章节与 Anthropic 的 `disable_parallel_tool_use` 文档。找出 Anthropic 建议禁用并行的那一类现实工具。（提示：对同一资源的有后果变更。）

## Key Terms

| 术语 | 常见说法 | 实际含义 |
|------|----------------|------------------------|
| Parallel tool calls | “一轮内扇出” | 模型在单条 assistant 消息中产出多个工具调用 |
| `parallel_tool_calls` | “OpenAI 的开关” | 启用或禁用多次调用产出 |
| `disable_parallel_tool_use` | “Anthropic 的反向开关” | 退出标志；默认为并行启用 |
| Tool call id | “关联句柄” | 结果消息必须回显的每次调用标识符 |
| Accumulator | “流缓冲” | 针对部分 `arguments` 块的按 id 字符串缓冲 |
| Out-of-order completion | “最快者先到” | 并行调用以不可预测的顺序完成；id 是胶水 |
| Dependency graph | “顺序约束” | 输出会流入其他工具输入的工具；不可并行 |
| Parse-early trap | “JSON.parse 炸了” | 试图解析尚不完整的 `arguments` 字符串 |
| `streamFunctionCallArguments` | “Gemini 3 特性” | 每次调用带唯一 id 的流式参数块 |
| Completion-order reply | “别等全部” | 结果一到就按 id 回复 |

## Further Reading

- [OpenAI — Parallel function calling](https://platform.openai.com/docs/guides/function-calling#parallel-function-calling) — 默认行为与退出开关
- [Anthropic — Parallel tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/parallel-tool-use) — `disable_parallel_tool_use` 与结果批量提交
- [Google — Gemini function calling parallel section](https://ai.google.dev/gemini-api/docs/function-calling) — 自 Gemini 3 起按 id 关联的并行调用
- [OpenAI — Streaming responses with tools](https://platform.openai.com/docs/api-reference/responses-streaming) — OpenAI 流的参数分块重组
- [Anthropic — Streaming messages](https://docs.anthropic.com/en/api/messages-streaming) — 带 `input_json_delta` 的 `content_block_delta`
