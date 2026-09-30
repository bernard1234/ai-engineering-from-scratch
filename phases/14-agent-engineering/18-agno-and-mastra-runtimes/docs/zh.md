# 生产级 Agent 运行时——快速实例化与类型化工作流

> 生产级 agent 运行时优化的是原型框架所忽略的东西：实例化成本、类型化的工作流界面，以及一个可直接部署的后端。2026 年的搭配：Agno（Python）主打微秒级 agent 实例化和无状态 FastAPI 后端。Mastra 则在 Vercel AI SDK 的基座上提供 agents、tools、workflows、统一的模型路由和组合式存储。

**Type:** Learn
**Languages:** Python, TypeScript
**Prerequisites:** Phase 14 · 01 (Agent Loop), Phase 14 · 13 (LangGraph)
**Time:** ~45 minutes

## 学习目标

- 识别 Agno 的性能目标，以及它们在何时真正重要。
- 说出 Mastra 的三大原语——Agents、Tools、Workflows——以及它支持的服务器适配器。
- 解释为什么无状态的、以 session 为作用域的 FastAPI 后端是推荐的 Agno 生产路径。
- 针对给定技术栈（Python 优先 vs TypeScript 优先）选择 Agno 或 Mastra。

## 问题

LangGraph、AutoGen、CrewAI 都属于框架偏重的类型。只想「在我的运行时里快速得到 agent 循环」的团队会选择 Agno（Python）或 Mastra（TypeScript）。两者都舍弃了一部分由框架持有的原语，换来了原生速度和与周边技术栈更紧密的契合。

## 概念

### Agno

- Python 运行时，前身为 Phi-data。
- 「没有图、链，也没有绕来绕去的模式——只有纯 Python。」
- 其文档给出的性能目标：约 2μs 的 agent 实例化、每个 agent 约 3.75 KiB 内存、约 23 个模型提供商。
- 生产路径：无状态的、以 session 为作用域的 FastAPI 后端。每个请求启动一个全新的 agent；session 状态存放在数据库里。
- 原生多模态（文本、图像、音频、视频、文件）以及 agentic RAG。

当你每秒要创建数千个短生命周期的 agent（聊天汇聚、评测流水线）时，这些速度目标才有意义。当一个 agent 要运行 10 分钟时，它们就没那么重要了。

### Mastra

- TypeScript，构建在 Vercel AI SDK 之上。
- 三大原语：**Agents**、**Tools**（Zod 类型化）、**Workflows**。
- 统一模型路由——截至 2026 年 3 月，跨 94 个提供商的 3300+ 个模型。
- 组合式存储：memory、workflows、observability 可分别落到不同后端；规模化时可观测性推荐 ClickHouse。
- Apache 2.0 许可证，其中 `ee/` 目录采用源码可得的商业许可证。
- 服务器适配器支持 Express、Hono、Fastify、Koa；对 Next.js 和 Astro 有一等集成。
- 附带 Mastra Studio（localhost:4111）用于调试。
- 在 1.0（2026 年 1 月）时已有 22k+ GitHub stars、每周 300k+ npm 下载量。

### 定位

两者都不是要成为 LangGraph。它们的竞争点在于：

- **语言契合度。** Agno 面向 Python 优先的团队；Mastra 面向 TypeScript 优先的团队。
- **运行时人体工学。** Agno = 接近零开销；Mastra = 与 Vercel 生态集成。
- **可观测性。** 两者都集成 Langfuse/Phoenix/Opik（第 24 课），但 Mastra Studio 是官方自有的。

### 何时选择哪一个

- **Agno** —— Python 后端、大量短生命周期 agent、强性能需求、FastAPI 团队。
- **Mastra** —— TypeScript 后端、Next.js / Vercel 部署、统一的多提供商模型路由、Zod 类型化 tools。
- **LangGraph**（第 13 课）——当持久化状态和显式的图推理比原生速度更重要时。
- **OpenAI / Claude Agent SDK** —— 当你想要提供商产品化的形态时（第 16–17 课）。

### 这个模式在哪里会出错

- **为性能而性能。** 当工作负载是每个请求一次慢速 agent 调用时，因为「2μs」听起来不错而选择 Agno。此时开销并不是瓶颈。
- **生态锁定。** Mastra 的 Vercel 风格集成在 Vercel 上是加分项，在别处却是减分项。
- **商业许可证的混淆。** Mastra 的 `ee/` 目录是源码可得的，并非 Apache 2.0。如果你打算 fork，请阅读许可证。

```figure
wb-runtime-spawn
```

## Build It

本课主要是比较性的——单一代码产物无法同时公平呈现两个框架。参见 `code/main.py` 中的并排玩具实现：一个极简的「运行 agent、流式输出、持久化 session」流程，实现了两次（一次 Agno 风格，一次 Mastra 风格）。

运行它：

```
python3 code/main.py
```

两条结构不同但功能等价的 trace。

## Use It

- **Agno** —— 需要速度和 FastAPI 形态的 Python 后端。
- **Mastra** —— 拥有众多提供商和工作流原语的 TypeScript 后端。
- 两者都提供官方自有的可观测性钩子。两者都集成 Langfuse。

## Ship It

`outputs/skill-runtime-picker.md` 根据技术栈、延迟预算和运营形态，在 Agno、Mastra、LangGraph 或某个提供商 SDK 之间做选择。

## 练习

1. 阅读 Agno 的文档。把标准库版 ReAct 循环（第 01 课）移植到 Agno。哪些东西消失了？哪些保留了下来？
2. 阅读 Mastra 的文档。把同一个循环移植到 Mastra。在工具类型化上有什么变化（Zod vs 无类型）？
3. 基准测试：测量你技术栈上的 agent 实例化延迟。Agno 的 2μs 对你的工作负载重要吗？
4. 设计一次迁移：如果你一直在 Python 上运行 CrewAI，迁移到 Agno 会破坏什么？
5. 阅读 Mastra 的 `ee/` 许可证条款。哪些限制会影响一个开源 fork？

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| Agno | 「快速的 Python agents」 | 无状态、以 session 为作用域的 agent 运行时 |
| Mastra | 「Vercel AI SDK 上的 TypeScript agents」 | Agents + Tools + Workflows + Model Router |
| Unified Model Router | 「多提供商访问」 | 跨 94 个提供商访问 3300+ 模型的单一客户端 |
| Composite storage | 「多后端」 | memory/workflows/observability 各自落到不同的存储 |
| Mastra Studio | 「本地调试器」 | 用于内省 agents 的 localhost:4111 UI |
| Source-available | 「不是开源」 | 许可证允许阅读源码但限制商业使用 |

## 延伸阅读

- [Agno Agent Framework 文档](https://www.agno.com/agent-framework) —— 性能目标、FastAPI 集成
- [Mastra 文档](https://mastra.ai/docs) —— 原语、服务器适配器、Model Router
- [LangGraph 概览](https://docs.langchain.com/oss/python/langgraph/overview) —— 有状态图替代方案
- [Comet Opik](https://www.comet.com/site/products/opik/) —— Mastra 集成所引用的可观测性对比
