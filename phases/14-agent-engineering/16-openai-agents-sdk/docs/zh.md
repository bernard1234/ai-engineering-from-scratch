# OpenAI Agents SDK：Handoff、Guardrail、Tracing

> OpenAI Agents SDK 是构建在 Responses API 之上的轻量多智能体框架。五个原语：Agent、Handoff、Guardrail、Session、Tracing。Handoff 是名为 `transfer_to_<agent>` 的工具。Guardrail 在输入或输出上触发。Tracing 默认开启。

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 01 (Agent Loop), Phase 14 · 06 (Tool Use)
**Time:** ~75 minutes

## 学习目标

- 说出 OpenAI Agents SDK 的五个原语。
- 解释 handoff：为什么它们被建模为工具、模型看到什么名字形状、上下文如何转移。
- 区分 input guardrail、output guardrail 与 tool guardrail；解释 `run_in_parallel` vs 阻塞模式。
- 用标准库实现一个带 handoff + guardrail + span 风格 tracing 的运行时。

## 问题

无法干净委派的智能体最终把所有东西塞进一个 prompt。没有 guardrail 的智能体会泄露 PII、产出违反策略的输出，或者无限循环。OpenAI 的 SDK 把让多智能体工作变得可控的三个原语固化了。

## 概念

### 五个原语

1. **Agent。** LLM + instructions + tools + handoffs。
2. **Handoff。** 委派给另一个智能体。以名为 `transfer_to_<agent_name>` 的工具呈现给模型。
3. **Guardrail。** 对输入（仅第一个智能体）、输出（仅最后一个智能体）或工具调用（每个函数工具）的校验。
4. **Session。** 跨轮次的自动对话历史。
5. **Tracing。** 针对 LLM 生成、工具调用、handoff、guardrail 的内置 span。

### Handoff 作为工具

模型在它的工具列表里看到 `transfer_to_billing_agent`。调用它就会让运行时：

1. 复制对话上下文（或通过 `nest_handoff_history` beta 折叠它）。
2. 用目标智能体的 instructions 初始化它。
3. 用目标智能体继续这次运行。

这就是被产品化的 supervisor 模式（第 13 课 / 第 28 课）。

### Guardrails

三种口味：

- **Input guardrails。** 跑在第一个智能体的输入上。在任何 LLM 调用之前拒绝不安全或超范围的请求。
- **Output guardrails。** 跑在最后一个智能体的输出上。抓住 PII 泄露、策略违规、畸形响应。
- **Tool guardrails。** 每个函数工具跑一次。校验参数、检查权限、审计执行。

模式：

- **Parallel**（默认）。guardrail LLM 与主 LLM 并排跑。尾部延迟更低。如果被触发，主 LLM 的工作被丢弃（token 浪费）。
- **Blocking**（`run_in_parallel=False`）。guardrail LLM 先跑。如果被触发，主调用不浪费任何 token。

触发器抛出 `InputGuardrailTripwireTriggered` / `OutputGuardrailTripwireTriggered`。

### Tracing

默认开启。每一次 LLM 生成、工具调用、handoff 和 guardrail 都发出一个 span。`OPENAI_AGENTS_DISABLE_TRACING=1` 退出。`add_trace_processor(processor)` 把 span 扇出到你自己的后端，与 OpenAI 的并存。

### Sessions

`Session` 把对话历史存在一个后端（SQLite、Redis、自定义）里。`Runner.run(agent, input, session=session)` 自动加载并追加。

### 这个模式在哪里会出问题

- **Handoff 漂移。** Agent A 交接给 Agent B，B 又交接回 A。加一个跳数计数器。
- **Guardrail 绕过。** Tool guardrail 只在函数工具上触发；内置工具（文件读取器、网页抓取）需要单独的策略。
- **过度 tracing。** span 里的敏感内容。配 OTel GenAI 内容捕获规则（第 23 课）——外部存储，按 ID 引用。

```figure
ae-agent-handoff
```

## Build It

`code/main.py` 用标准库实现 SDK 的形态：

- `Agent`、`FunctionTool`、`Handoff`（作为带转移语义的函数工具）。
- `Runner`，带输入/输出/工具 guardrail、handoff 派发和跳数计数器。
- 一个简单的 span 发射器，展示 trace 形状。
- 一个 triage 智能体，根据用户查询交接给 billing 或 support；guardrail 在其中一个输入上触发。

运行它：

```
python3 code/main.py
```

trace 展示两次成功的 handoff、一次输入 guardrail 触发，以及一棵镜像真实 SDK 所发内容的 span 树。

## Use It

- **OpenAI Agents SDK** 用于 OpenAI 优先产品。
- **Claude Agent SDK**（第 17 课）用于 Claude 优先产品。
- **LangGraph**（第 13 课）当你想要显式状态和持久恢复时。
- **自定义** 当你需要精确控制（语音、多提供商、联邦部署）时。

## Ship It

`outputs/skill-agents-sdk-scaffold.md` 脚手架出一个 Agents SDK 应用，带 triage 智能体、handoff、输入/输出/工具 guardrail、session store 和一个 trace processor。

## 练习

1. 加一个 handoff 跳数计数器：N 次转移后拒绝。追踪这个行为。
2. 把 `nest_handoff_history` 作为一个选项实现——在转移前把先前消息折叠成一份摘要。
3. 写一个阻塞式 output guardrail。对比会触发它的 prompt 与通过的 prompt 的延迟。
4. 把 `add_trace_processor` 接到一个 JSON 记录器。每个 span 发出什么形状？
5. 读 SDK 文档。把你的标准库玩具移植到 `openai-agents-python`。你哪里建模错了？

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| Agent | 「LLM + instructions」 | SDK 中的 Agent 类型；拥有工具和 handoff |
| Handoff | 「转移」 | 模型调用来委派给另一个智能体的工具 |
| Guardrail | 「策略检查」 | 对输入 / 输出 / 工具调用的校验 |
| Tripwire | 「guardrail 触发」 | guardrail 拒绝时抛出的异常 |
| Session | 「历史存储」 | 运行之间持久化的对话记忆 |
| Tracing | 「Span」 | 对 LLM + 工具 + handoff + guardrail 的内置可观测性 |
| Blocking guardrail | 「顺序检查」 | guardrail 先跑；触发时不浪费 token |
| Parallel guardrail | 「并发检查」 | guardrail 并排跑；延迟更低，触发时浪费 token |

## 延伸阅读

- [OpenAI Agents SDK docs](https://openai.github.io/openai-agents-python/) —— 原语、handoff、guardrail、tracing
- [Claude Agent SDK overview](https://platform.claude.com/docs/en/agent-sdk/overview) —— Claude 风味的对应物
- [Anthropic，Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) —— 到底什么时候才该用 handoff
- [OpenTelemetry GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) —— Agents SDK span 所映射到的标准