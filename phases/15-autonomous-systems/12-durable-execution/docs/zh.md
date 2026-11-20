# 长时间运行的后台 agent：durable execution

> 生产环境中的长程 agent 不会跑在 `while True` 里。每一次 LLM 调用都变成一个 activity，带 checkpoint、retry 和 replay。Temporal 与 OpenAI Agents SDK 的集成于 2026 年 3 月正式可用。Claude Code Routines（Anthropic）无需持久的本地进程即可按计划运行 Claude Code 调用。会话在等待人工输入时暂停，能在部署后存活，并以 `thread_id` 为键从最新 checkpoint 恢复。在这些新的人体工学之下，是一个老模式——workflow 编排——外加一个新输入：把 LLM 调用视为非确定性 activity，在恢复时必须以确定性的方式 replay。

**Type:** Learn
**Languages:** Python（stdlib，最小化的 durable execution 状态机）
**Prerequisites:** 第 15 阶段，第 10 课（Permission modes）、第 15 阶段，第 01 课（Long-horizon agents）
**Time:** ~60 分钟

## 问题场景

设想一个运行四小时的 agent。它调用三次工具，两次向用户提问，并发出四十次 LLM 调用。中途，它所在的主机重启了。会发生什么？

- 在天真的 `while True` 循环里：一切都丢失了。运行从头重启。三次工具调用（带真实副作用）再次执行。用户被再次询问他们已经批准过的事情。四十次 LLM 调用被重新计费。
- 使用 durable execution：运行从最近的 checkpoint 恢复。已完成的 activity 不会重新执行；其结果从持久日志中 replay。用户不必重新批准已经批准过的事情。已经发出的 LLM 调用不会重新计费。

这正是 workflow 引擎已经提供了十年的模式（Temporal、Cadence、Uber 的 Cherami）。新之处在于，LLM 调用如今成了一种 activity——非确定性、昂贵、带副作用——而它们能干净地套进这个模式。

本课贯穿始终的主题：长程可靠性会衰减（METR 观察到“35 分钟退化”——成功率随任务跨度大致呈二次方下降）。durable execution 让你能运行超出可靠性曲线所支持的时长；如果设计正确，这是一种新的安全失败方式，如果设计错误，则是不安全的。

## 核心概念

### Activity、workflow 与 replay

- **Workflow**：确定性的编排代码。定义 activity 的顺序、分支、等待。必须是确定性的，这样它才能从事件日志 replay，而不会出现意外的分歧。
- **Activity**：一个非确定性、可能失败的工作单元。LLM 调用、工具调用、文件写入、HTTP 请求。每个 activity 都会记录其输入以及（完成后）其输出。
- **事件日志**：持久化的后备存储。每个 activity 的开始、完成、失败、重试，以及每个 workflow 决策都会被记录。
- **Replay**：恢复时，workflow 代码从头重新运行；每个已完成的 activity 返回其记录的结果而不重新执行。只有尚未完成的 activity 才真正运行。

这与 React 基于虚拟 DOM 重新渲染、或 Git 从 commit 重建工作树是同一个形状。编排器中的确定性，正是让持久化变得廉价的原因。

### 为什么 LLM 调用契合这个模式

LLM 调用是：
- 非确定性的（temperature > 0；即便是 temperature 0 也会随模型版本漂移）。
- 昂贵的（金钱和延迟）。
- 可能失败的（限流、超时）。
- 带副作用的（如果它们调用工具）。

这恰恰就是 activity 的画像。把每次 LLM 调用包裹成 activity，就能给你带指数退避的重试、跨重启的 checkpoint，以及用于调试的可 replay 的 trace。

### 以 `thread_id` 为键的 checkpoint

LangGraph、Microsoft Agent Framework、Cloudflare Durable Objects 和 Claude Code Routines 都收敛到相同的 API 形状：一个 `thread_id`（或等价物）标识会话；每次状态转换都持久化到某个后端（默认 PostgreSQL，开发用 SQLite，缓存用 Redis）；恢复时读取最新的 checkpoint。

后端的选择很重要：

- **PostgreSQL**：持久、可查询、能在部署后存活。LangGraph 的默认选择。
- **SQLite**：仅限本地开发；跨主机会丢数据。
- **Redis**：快但易失，除非配置了 AOF/snapshot。
- **Cloudflare Durable Objects**：透明分布式；由唯一键划定范围；可存活数小时到数周。

### 把人工输入当作一等状态

propose-then-commit（第 15 课）需要一个持久的“等待人工”状态。workflow 暂停，外部队列持有待处理请求，一次批准正好从那个点恢复。没有持久化，这只是尽力而为；有了它，一夜之间到达的批准会让 workflow 在早上继续。

### 35 分钟退化

METR 观察到，被测的每类 agent 在连续运行约 35 分钟后都会出现可靠性衰减。任务时长翻倍，失败率大致变为四倍。durable execution 并不能修复这一点；它只是让你运行超出可靠性曲线所支持的时长。安全的做法是把持久化与以下两者结合：在重新进入时需要重新 HITL 的 checkpoint，以及无论墙钟时间如何都对总算力设上限的预算 kill switch（第 13 课）。

### 什么时候 durable execution 是错误答案

- 几分钟以内、没有人工输入的运行。开销 > 收益。
- 严格只读的信息检索。
- 正确性要求在一个 context window 内端到端完成的任务（某些推理任务；某些一次性生成）。

```figure
memory-consolidation
```

## Use It

`code/main.py` 用 stdlib Python 实现了一个最小化的 durable execution 引擎。它支持：

- `@activity` 装饰器，把输入和输出记录到 JSON 事件日志。
- 一个把 activity 串联起来的 workflow 函数。
- 一个 `run_or_replay(workflow, event_log)` 函数，replay 已完成的 activity 而不重新执行它们。

驱动程序模拟一个三 activity 的 workflow，中途崩溃，并展示 (a) 天真的重试重新执行一切，对比 (b) replay 只运行缺失的那个 activity。

## Ship It

`outputs/skill-durable-execution-review.md` 审查一次拟议的长时间运行 agent 部署是否具备正确的 durable execution 形态：activity、确定性、checkpoint 后端、人工输入状态，以及恢复时 HITL 策略。

## Exercises

1. 运行 `code/main.py`。观察天真的重试与 replay 之间 activity 执行次数的差异。改变崩溃点，展示 replay 次数随之变化。

2. 把玩具引擎改造为显式使用 `thread_id`。模拟两个共享该引擎的并发会话，确认它们的事件日志不会冲突。

3. 取玩具引擎中的一个 activity。引入一处非确定性（workflow 决策内部的墙钟时间戳）。演示 replay 时的分歧。解释真实引擎如何处理这一点（副作用注册、`Workflow.now()` API）。

4. 阅读 LangChain 的“Runtime behind production deep agents”文章。列出该 runtime 持久化的每一个状态，并说出每个状态覆盖哪种失败模式。

5. 为一个 6 小时的自主编码任务设计 checkpoint 策略。你在哪里 checkpoint？崩溃后恢复是什么样子？什么需要重新 HITL？

## Key Terms

| 术语 | 人们的说法 | 实际含义 |
|---|---|---|
| Workflow | “agent 的脚本” | 确定性的编排代码；可从事件日志 replay |
| Activity | “一个步骤” | 非确定性的单元（LLM 调用、工具调用）；前后都会记录 |
| Event log | “后备存储” | 对每次状态转换的持久记录 |
| Replay | “恢复” | 重跑 workflow；已完成的 activity 返回记录结果而不重新执行 |
| Checkpoint | “存档点” | 以 thread_id 为键的持久化状态；恢复时最新者胜出 |
| thread_id | “会话键” | 划定持久状态范围的标识符 |
| 35-minute degradation | “可靠性衰减” | METR：成功率随任务跨度大致呈二次方下降 |
| Non-determinism | “replay 时的漂移” | 墙钟、随机、LLM 输出；必须注册为副作用 |

## Further Reading

- [Anthropic — Claude Code Agent SDK: agent loop](https://code.claude.com/docs/en/agent-sdk/agent-loop) — 预算、轮数与恢复语义。
- [Microsoft — Agent Framework: human-in-the-loop and checkpointing](https://learn.microsoft.com/en-us/agent-framework/workflows/human-in-the-loop) — RequestInfoEvent 形状。
- [LangChain — The Runtime Behind Production Deep Agents](https://www.langchain.com/conceptual-guides/runtime-behind-production-deep-agents) — 具体的 runtime 要求。
- [OpenAI Agents SDK + Temporal integration（Trigger.dev 公告）](https://trigger.dev) — LLM 调用的 activity 形状。
- [Anthropic — Measuring agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) — 35 分钟退化的引用来源。
