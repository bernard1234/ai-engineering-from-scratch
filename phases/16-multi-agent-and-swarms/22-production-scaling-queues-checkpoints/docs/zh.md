# 生产级扩展 —— Queue、Checkpoint、持久性

> 要把 multi-agent 系统扩展到数千个并发运行，需要 **持久执行**（durable execution）—— 工作 queue 加 checkpoint，使得任何 worker 在崩溃后都能恢复任何一次运行，前提是 lease 处理、幂等的副作用、确定性重放都已就位。LangGraph 的 runtime 是参考范例：它在每个 super-step 之后写入一个以 `thread_id` 为键的 checkpoint（默认用 Postgres）；worker 崩溃会释放 lease，另一个 worker 接着恢复。agent 可以无限期休眠等待人类输入。**MegaAgent**（arXiv:2408.09955）运行每个 agent 的生产者-消费者 queue，含三种状态（Idle / Processing / Response）和两层协调（组内 chat + 组间 admin chat）。**Fiber/async** 在 LLM 流式场景下胜过线程逐任务：线程 99% 的时间都在空等 token，而 fiber 在 I/O 上协作式让出。反方观点：Ashpreet Bedi 的“Scaling Agentic Software”主张 **只用 FastAPI + Postgres**，直到负载证明不行为止 —— 简单架构能走得出乎意料地远。本课构建持久 checkpoint 日志、带状态转换的每 agent 工作 queue、async 与线程的对比演示，并落地务实的“从简单开始”规则。

**Type:** Learn + Build
**Languages:** Python (stdlib, `asyncio`, `sqlite3`)
**Prerequisites:** 第 16 阶段，第 09 课（Parallel Swarm Networks）、第 13 课（Shared Memory）
**Time:** ~75 分钟

## 问题场景

一个原型 multi-agent 系统在一台笔记本上、三个 agent 跑在内存事件循环里，运转良好。你要把它搬到生产环境：

- agent 有时会运行数小时（长篇研究、human-in-the-loop 等待）。
- worker 进程会崩溃。重启会丢失状态。
- 峰值负载是平均值的 10 倍；你需要水平扩展。
- 用户按 agent 运行次数付费；计费需要 exactly-once 语义。

内存事件循环这些都做不到。你需要在其下放一个持久执行层。2026 年的标准选项有：

1. 带 checkpoint 的工作流引擎（Temporal、LangGraph runtime）。
2. 带状态存储的消息 queue（Postgres + SQS/RabbitMQ）。
3. Actor 模型框架（MegaAgent 的每 agent 生产者-消费者）。
4. 手写的 FastAPI + Postgres（Bedi 的论点）。

本课把每一种都搭一个缩影。

## 核心概念

### 持久执行，这个模式

持久执行引擎在每个“步骤”（用 LangGraph 的说法是 super-step）之后持久化完整的程序状态。崩溃时：

```
worker crashes mid-step
  -> lease timeout
  -> another worker picks up the thread_id
  -> resumes from last checkpoint
  -> no duplicate side effects
```

要让它奏效，需要：

- **可序列化状态。** 所有 agent 状态都必须可持久化。带活跃数据库连接的函数闭包无法存活。
- **确定性恢复。** 给定相同的状态和相同的输入，agent 产出相同的动作（或在 LLM 调用上退回到外部确定性 oracle）。
- **幂等副作用。** 外部调用（tool call、支付）必须幂等，或使用去重键。

LangGraph 在每个 super-step 后写入 checkpoint；Temporal 在每个 activity 后写入；Restate 使用事件溯源的 journal。三者实现的都是同一个模式。

### 每步一个 checkpoint 的 runtime

LangGraph 的 runtime 是现成的范例：每个 agent 有一个 `thread_id`；状态是一个带类型的 dict；每个 super-step 向 checkpoints 表写一行。恢复时，runtime 从最后一个 checkpoint 重放，而不是从头开始。agent 可以 `interrupt()` 等待人类输入；runtime 会持久化并释放该 worker。输入到达时，任何 worker 都能恢复。

这是 2026 年 4 月的参考生产设计。

### MegaAgent 的每 agent queue

arXiv:2408.09955 描述了一个规模实验：单集群中数千个并发 agent。架构：

```
agent i:
  state ∈ {Idle, Processing, Response}
  in_queue   <- messages addressed to agent i
  out_queue  -> replies + side effects

coordinators:
  intra-group chat  (agents in the same group)
  inter-group admin chat  (high-level routing)
```

两层协调让组内会话保持稠密、组间保持稀疏 —— 这正是让成本在数千个 agent 中保持线性的模式。

### Async 与线程逐任务之争

LLM 调用是 I/O 密集型的。一个等待下一个 token 的线程有 99% 的时间处于空闲。每个线程约占 1MB 内存；10,000 个并发调用仅栈就要 10GB。

Fiber（Python `asyncio`、Go goroutine、Rust `tokio`）在 I/O 上协作式让出。同样的 10,000 个调用可以轻松装进一个进程。在 LLM-agent 的规模下，async 不是优化 —— 它就是架构。

例外：CPU 密集的后处理（embedding、tokenizer 技巧）仍然需要线程或进程。把你的 I/O 层与 CPU 层分开。

### Bedi 的反方观点

“Scaling Agentic Software”（Ashpreet Bedi，2026）认为，大多数团队在测量负载之前就过度设计了。务实的默认做法：

- FastAPI + Postgres。
- 每次 agent 运行是一行记录；用乐观并发就地更新状态。
- 通过 `pg_notify` 或一个简单的 Celery worker 跑后台任务。
- 重试策略放在应用代码里。

对于约 100 个以下、任务规模可控的并发 agent 运行，这往往就够了。等到你测量到它失败时再升级。

规则是：当你遇到简单架构解决不了的具体问题时，再采用持久执行框架。过早采用会把时间烧在并无回报的仪式上。

### Exactly-once 语义

对于付费的 agent 运行，你需要“有效 exactly-once”（at-least-once 投递 + 幂等消费者）。工程手法有：

- **每次运行一个去重键。** 在每次副作用调用中都带上它。
- **Outbox 模式。** 副作用先写入一张表，再由单独的进程执行它们。两步都幂等。
- **补偿事务。** 当副作用成功、但其跟踪写入失败时，安排一次补偿。

这些都是数据库工程模式，并非 LLM 专属。LLM 带来的额外负担只是 LLM 调用很慢；其余都是标准的分布式系统问题。

### Rainbow 部署

Anthropic 的 multi-agent 研究系统使用“rainbow 部署”：多个版本的 agent runtime 并发运行，使长时间运行的 agent 不必在每次代码部署时被杀死。把新版本以 canary 方式放到一部分流量上；等旧版本上的 agent 跑完后停用旧版本。

这对长时运行的有状态系统是标准做法；2026 年的变通在于 agent 可以存活数小时，因此部署周期必须迁就这一点。

### 标准生产检查清单

- 持久状态（checkpoint、快照，或 outbox + 可重放日志）。
- 幂等副作用。
- 面向 LLM 调用的 async I/O 层。
- 带去重的 at-least-once 投递。
- 有状态工作负载的 rainbow/canary 部署。
- 可观测性：每 agent 轨迹、super-step 审计、重试计数器。

```figure
sw-checkpoint-replay
```

## Build It

`code/main.py` 实现了：

- `CheckpointStore` —— 基于 SQLite、以 thread-id 为键的 checkpoint 日志。每个 super-step 追加一行。
- `run_with_checkpoint(agent, thread_id)` —— 模拟运行中途崩溃；第二个 worker 从最后一个 checkpoint 恢复。
- `AgentQueue` —— 每 agent 的 Idle / Processing / Response 状态机，带一个小型工作 queue。
- `demo_async_vs_threads()` —— 分别通过 asyncio 和线程运行 500 个并发的模拟“LLM 调用”；报告真实耗时和峰值内存（近似值）。

运行：

```
python3 code/main.py
```

预期输出：模拟崩溃后 checkpoint 恢复成功；async 版本在 1 秒内处理 500 个并发调用；线程版本要花好几秒，且每个并发单元的内存占用高几个数量级。

## Use It

`outputs/skill-scaling-advisor.md` 就持久执行的选择给出建议：FastAPI + Postgres、LangGraph runtime、Temporal，或自研。依据负载、状态保留需求和部署频率来校准。

## Ship It

标准的生产加固措施：

- **从简单开始（Bedi 规则）。** FastAPI + Postgres，直到你测量到它失败。
- **优化之前先全面埋点。** 每次运行的延迟直方图、每步耗时、重试次数、故障分类。
- **副作用采用 outbox 模式。** 尤其是支付和外部 API 调用。
- **Rainbow 部署。** 部署期间绝不要杀掉进行中的 agent 运行。
- **当你遇到具体问题时**，再采用持久执行引擎（Temporal / LangGraph / Restate）：长达数小时的 human-in-the-loop 等待、跨区域协调、复杂的重试/补偿策略。
- **I/O 层用 async。** 线程只用于 CPU 密集的后处理。

## Exercises

1. 运行 `code/main.py`。确认 checkpoint 恢复有效；测量 async 与线程的并发差异。
2. 实现一张 **outbox** 表：每个 tool call 先写入 outbox，再由单独的 goroutine/任务执行。通过把 tool call 跑两次来验证幂等性。
3. 模拟一次 **rainbow 部署**：两个并发的 runtime 版本；把一半的新 thread_id 路由到每个版本；确认旧版本上进行中的线程不会被中断。
4. 阅读 LangGraph 的 runtime 文档（下方有链接）。找出 runtime 的哪些特性在手写的 FastAPI + Postgres 版本中最难复刻。这是采用它的理由，还是可以推迟？
5. 阅读 MegaAgent（arXiv:2408.09955）第 3 节。两层协调（组内 + 组间 admin chat）是显式的。勾画你会如何把它映射成带两个 queue 族的消息 queue。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Durable execution | “持久化程序状态” | 引擎在每个 super-step 后写入状态；崩溃恢复是确定性的。 |
| Super-step | “事务边界” | checkpoint 之间的工作单元。LangGraph 的术语。 |
| thread_id | “agent 运行标识符” | 绑定 checkpoint 与恢复逻辑的键。 |
| Idempotency | “可安全重试” | 重复执行副作用与执行一次产生相同结果。 |
| Outbox pattern | “解耦副作用” | 把意图写入一张表；由单独的 executor 执行并标记完成。 |
| At-least-once delivery | “可能有重复” | 消息 queue 的语义；去重键让消费者达到有效一次。 |
| Rainbow deploy | “版本重叠” | 长时间运行工作负载期间多个 runtime 版本并发。 |
| Async fiber | “协作式让出” | 用户态并发；在 I/O 密集负载下相比线程更便宜。 |
| Checkpoint | “状态快照” | super-step 边界的序列化状态；恢复的关键。 |

## Further Reading

- [LangChain — The runtime behind production deep agents](https://www.langchain.com/conceptual-guides/runtime-behind-production-deep-agents) —— LangGraph runtime 的设计
- [MegaAgent](https://arxiv.org/abs/2408.09955) —— 每 agent 生产者-消费者 queue；数千并发 agent 下的两层协调
- [Matrix](https://arxiv.org/abs/2511.21686) —— 以消息 queue 作为协调基底的去中心化框架
- [Temporal docs](https://docs.temporal.io/) —— 持久执行的标准工作流引擎
- [Anthropic — Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) —— 包括 rainbow 部署在内的生产经验
