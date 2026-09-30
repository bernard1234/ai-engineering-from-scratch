# 生产运行时：Queue、Event、Cron

> 生产智能体运行在六种运行时形态上：request-response、streaming、durable execution、基于队列的后台、event-driven、scheduled。先选形态，再选框架。可观测性在每一种形态下都是承重的。

**Type:** Learn
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 13 (LangGraph), Phase 14 · 22 (Voice)
**Time:** ~60 minutes

## 学习目标

- 说出六种生产运行时形态，并把每种匹配到一个框架 / 产品模式。
- 解释为什么 durable execution（LangGraph）对长时程任务很重要。
- 描述 event-driven 运行时，以及何时 Claude Managed Agents 合适。
- 解释多步智能体的「可观测性即承重」这一主张。

## 问题

生产智能体以 Jupyter notebook 不会暴露的方式失败：第 37 步的网络超时、语音通话中途用户挂断、机器重启时 cron 作业死掉、后台 worker 内存耗尽。运行时形态决定了哪些失败是可存活（survivable）的。

## 概念

### Request-response

- 同步 HTTP。用户等待完成。
- 只对短任务（<30s）可行。
- 技术栈：Agno（Python + FastAPI）、Mastra（TypeScript + Express/Hono/Fastify/Koa）。
- 可观测性：标准 HTTP 访问日志 + OTel spans。

### Streaming

- SSE 或 WebSocket 用于渐进式输出。
- LiveKit 把它扩展到语音/视频的 WebRTC（第 22 课）。
- 技术栈：任何带 streaming 支持的框架 + 一个处理 SSE/WS 的前端。
- 可观测性：逐 chunk 计时、首 token 延迟、尾部延迟。

### Durable execution

- 每一步之后状态被 checkpoint；失败时自动恢复。
- AutoGen v0.4 actor 模型把失败隔离到单个智能体（第 14 课）。
- LangGraph 的核心差异化能力（第 13 课）。
- 当步数未知且恢复成本高时必不可少。

### Queue-based / background

- 作业进入队列，worker 取走，结果通过 webhook 或 pub/sub 流回。
- 对长时程智能体必不可少（据 Anthropic 的 computer use 公告，每个任务几十到几百步）。
- 技术栈：Celery（Python）、BullMQ（Node）、SQS + Lambda（AWS）、自定义。
- 可观测性：队列深度、逐作业延迟分布、DLQ 大小。

### Event-driven

- 智能体订阅触发器：新邮件、PR 被打开、cron 触发。
- Claude Managed Agents 开箱即用地覆盖这一点（第 17 课）。
- CrewAI Flows（第 15 课）把事件驱动的确定性工作流结构化。
- 可观测性：触发源、事件到启动的延迟、智能体延迟。

### Scheduled

- 周期运行的 cron 形态智能体。
- 与 durable execution 结合，让一次失败的夜间运行在下一个 tick 恢复。
- 技术栈：Kubernetes CronJob + 一个 durable 框架；托管（Render cron、Vercel cron）。

### 2026 年的部署模式

- **CrewAI Flows** 用于事件驱动生产。
- **Agno** 无状态 FastAPI 用于 Python 微服务。
- **Mastra** 服务端适配器（Express、Hono、Fastify、Koa）用于嵌入。
- **Pipecat Cloud / LiveKit Cloud** 用于托管语音（第 22 课）。
- **Claude Managed Agents** 用于托管的长时程异步。

### 可观测性是承重的

没有 OpenTelemetry GenAI spans（第 23 课）加一个 Langfuse/Phoenix/Opik 后端（第 24 课），你就无法调试一个在第 40 步失败的多步智能体。对生产而言这并非可选项。它是「我们调试得很快」与「我们带着更多日志从头重放」之间的区别。

### 生产运行时在哪里会失败

- **选错形态。** 为一个 5 分钟任务选 request-response。用户挂起；worker 堆积；重试叠加。
- **没有 DLQ。** 队列 worker 没有 dead-letter。失败的作业凭空消失。
- **不透明的后台工作。** 后台智能体运行而不导出 trace。失败在用户上报之前不可见。
- **跳过 durable state。** 任何超过 30 秒且你承受不起重启的运行都需要 durable execution。

```figure
wb-runtime-shapes
```

## Build It

`code/main.py` 是一个标准库多形态演示：

- Request-response 端点（普通函数）。
- Streaming 处理器（生成器）。
- 带 DLQ 的队列 worker。
- 事件触发注册表。
- Cron 形态调度器。

运行它：

```bash
python3 code/main.py
```

输出：五条轨迹，展示每种形态在同一任务上的行为。相同的智能体逻辑，不同的外层壳。第六种形态（durable execution）有意放在第 13 课用 LangGraph checkpointing 覆盖。

## Use It

- **Request-response** 用于对话式 UX。
- **Streaming** 用于渐进式响应。
- **Durable** 用于长时程任务。
- **Queue** 用于批处理 / 异步 / 长时运行。
- **Event** 用于智能体响应性。
- **Cron** 用于日常维护（记忆整合、评估、成本报告）。

## Ship It

`outputs/skill-runtime-shape.md` 为任务挑选运行时形态，并接好可观测性要求。

## 练习

1. 把你第 01 课的 ReAct 循环移植到你的技术栈中的全部六种形态。哪种形态适合哪个产品面？
2. 给基于队列的演示加一个 DLQ。模拟 10% 的作业失败；暴露 DLQ 大小。
3. 写一个 cron 触发的评估智能体，每晚对当天 top 20 条轨迹运行。
4. 实现带背压的 streaming：如果客户端很慢，就暂停智能体。这与轮次预算如何相互作用？
5. 阅读 Claude Managed Agents 文档。什么时候你会把一个自托管的长时程智能体迁到托管？

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| Request-response | 「同步」 | 用户等待；只适合短任务 |
| Streaming | 「SSE / WS」 | 渐进式输出；更好的 UX；延迟按 chunk 可观测 |
| Durable execution | 「从失败中恢复」 | 被 checkpoint 的状态；在最后一步重启 |
| Queue-based | 「后台作业」 | 生产者 / worker 池 / DLQ |
| Event-driven | 「基于触发」 | 智能体对外部事件做出反应 |
| DLQ | 「Dead-letter queue」 | 失败作业的停车场 |
| Claude Managed Agents | 「托管 harness」 | Anthropic 托管的带缓存 + 压缩的长时程异步 |

## 延伸阅读

- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)——durable execution 细节
- [Claude Managed Agents overview](https://platform.claude.com/docs/en/managed-agents/overview)——托管的长时程异步
- [Anthropic，Introducing computer use](https://www.anthropic.com/news/3-5-models-and-computer-use)——「每个任务几十到几百步」
- [AutoGen v0.4（Microsoft Research）](https://www.microsoft.com/en-us/research/articles/autogen-v0-4-reimagining-the-foundation-of-agentic-ai-for-scale-extensibility-and-robustness/)——actor 模型故障隔离