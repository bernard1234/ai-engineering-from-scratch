# 并行 / 群体 / 网络化架构

> 与 supervisor 相对照：没有中心决策者。agent 读取共享的事件总线，异步地领取工作，把结果写回去。LangGraph 明确支持“Swarm Architecture”（群体架构），用于去中心化的动态环境。Matrix（arXiv:2511.21686）把控制流与数据流都表示为经由分布式队列传递的序列化消息，从而消除 orchestrator 瓶颈。取舍是明确的：用确定性和可追踪性换可扩展性。群体适合包含许多相互独立子问题的任务；它不适合需要单一连贯计划的任务。

**Type:** Learn + Build
**Languages:** Python (stdlib, `threading`, `queue`)
**Prerequisites:** 第 16 阶段，第 05 课（Supervisor Pattern）、第 04 课（Primitive Model）
**Time:** ~75 分钟

## 问题场景

Supervisor 能扩展到少数几个工作者。那几百个呢？supervisor 本身就成了瓶颈：关于谁做什么的每一个决策都汇聚到一个 agent 上。一个慢的计划步骤就会拖住整个系统。

群体架构把设计反过来。不再由一个中心规划者派发工作，而是工作者从共享队列里领取工作。“协调”被固化进事件总线的语义里。没有 orchestrator；系统会一直扩展，直到队列成为瓶颈。

## 核心概念

### 结构形态

```
                ┌──── shared queue ────┐
                │                      │
       ┌────────┼────────┐  ◄──────┬───┘
       ▼        ▼        ▼         │
     Worker  Worker  Worker   Worker
      A       B       C        D
       │        │        │         │
       └────────┴────────┴─────────┘
                 │
                 ▼
            results pool
```

没有 orchestrator。每个工作者重复：领取任务、处理、写入结果（并可选地入队后续任务）。

### 群体适合什么

- **大量相互独立的任务。** 抓取、转换、分类。任务之间不相互依赖。
- **时长变化的工作。** 如果有些任务耗时 100ms、另一些耗时 10s，群体能自动均衡负载——快的工作者领取下一个任务。supervisor 则必须预先估计时长。
- **吞吐优先于确定性。** 你关心的是总完成时间，而不是严格的顺序。

### 群体在哪儿会失效

- **有顺序的工作流。** 如果第 3 步需要第 2 步的输出，群体就有第 3 步在第 2 步完成前就触发的风险。
- **需要全局计划的任务。** 复杂的研究问题受益于一个规划者。一群研究者产出的是彼此独立的事实，而不是一份连贯的报告。
- **调试。** 没有中心日志、异步执行，复现一个 bug 的代价很高。

### Matrix（arXiv:2511.21686）

Matrix 是 2025 年的论文，把群体推到它的自然结论：控制流和数据流都是分布式队列上的序列化消息。没有中心协调者。容错来自消息的持久性。可扩展性是消息 broker 的问题，而不是系统的问题。

贡献：一种编程模型，其中多智能体协调是“这个 agent 订阅哪个消息主题？”，而不是“supervisor 下一个选哪个 agent？”这使系统看起来像一个 pub/sub 事件网格。

### 图框架中的群体

LangGraph 2025 年的文档明确把“Swarm Architecture”描述为多智能体模式之一：agent 是节点，但边构成一张带环的有向图，任何节点都可以从池中被激活。工作者按条件从可用工作中领取，而不是由 supervisor 分配。

### 失效模式：饥饿与热点

如果所有工作者都去领最快能拿到的任务，长时间任务就永远轮不到，直到只剩下它们。这是经典的队列饥饿。

缓解措施：
- 带显式老化（aging）的优先队列（随等待时间提高优先级）。
- 工作者专业化：某些工作者只接“长”任务。
- 背压：限制进入队列的快任务数量。

### 基于内容的路由这一环

群体与基于内容的路由（第 22 课）天然配对。不要一个通用队列，而是每种消息类型一个队列。专门的工作者只订阅自己的类型。这是能扩展到数千个 agent 的消息总线架构的基础。

```figure
sw-work-stealing
```

## Build It

`code/main.py` 实现一个由 4 个工作线程组成的群体，它们从一个共享的 `queue.Queue` 中领取。任务时长各不相同（有的快，有的慢）。演示对比：

- **顺序基线：** 一个工作者串行处理所有任务。
- **固定分配：** 每个任务预先分配给某个特定工作者（supervisor 风格）。
- **群体：** 工作者从共享队列领取。

群体能自动均衡负载；固定分配在其被分配到的任务很慢时，会让快的工作者闲着。

运行：

```
python3 code/main.py
```

输出显示每个工作者的任务数（群体分配不均但最优）以及挂钟时间。

## Use It

`outputs/skill-swarm-fit.md` 评估一个任务应当用群体还是 supervisor。输入：任务独立性、时长方差、顺序要求、可调试性需求。

## Ship It

检查清单：

- **带老化的优先队列。** 防止长任务饥饿。
- **工作者幂等。** 如果工作者中途崩溃，一个任务可能被领取不止一次。工作者必须幂等。
- **持久化队列。** 生产环境用 Kafka、Redis Streams 或数据库支撑的队列。`queue.Queue` 仅在内存中。
- **按任务可观测。** 每个任务都有 trace ID；每个工作者都用它记录开始/结束。
- **背压。** 如果队列增长速度超过工作者排空速度，就放慢生产者。

## Exercises

1. 运行 `code/main.py`。在时长可变的工作负载上，群体比顺序式快多少？比固定分配快多少？
2. 增加一个优先队列变体（用 `queue.PriorityQueue`）。按任务的 “importance” 字段分配优先级。观察低优先级任务在持续负载下是否会饿死。
3. 实现一个热点检测器：当任何工作者处理的任务数超过最慢工作者的 3 倍时记录日志。这说明了任务时长分布的什么情况？
4. 阅读 Matrix 论文（arXiv:2511.21686）的摘要和第 3 节。找出 Matrix 接受的一个具体取舍（可扩展性收益）和放弃的一个（可追踪性、确定性）。
5. 把群体演示改成使用一个 `queue.Queue` 存放 (task_type, payload) 元组，工作者只订阅特定类型。当任务异构时，什么样的路由规则才合理？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Swarm architecture | “去中心化的 agent” | 工作者从共享队列领取；没有中心 orchestrator。 |
| Event bus | “agent 订阅主题” | 按类型或内容把任务路由给工作者的消息 broker。 |
| Starvation | “任务永远不跑” | 低优先级任务永远领不到，因为更高优先级的工作持续到来。 |
| Hot-spotting | “一个工作者被淹了” | 负载不均，一个工作者拿到大部分任务。 |
| Back-pressure | “让生产者慢下来” | 当队列变满时向上游发出停止生产信号的机制。 |
| Idempotent worker | “重跑也安全” | 同一任务处理两次产生相同结果。因为工作者可能中途崩溃，所以必须有此性质。 |
| Durable queue | “能扛住崩溃” | 由磁盘或复制存储支撑的队列；工作者崩溃时任务不丢失。 |
| Matrix framework | “全消息传递的群体” | 数据流和控制流都是分布式队列上的序列化消息。 |

## Further Reading

- [LangGraph workflows and agents — Swarm Architecture](https://docs.langchain.com/oss/python/langgraph/workflows-agents) — 明确支持群体架构
- [Matrix — A Decentralized Framework for Multi-Agent Systems](https://arxiv.org/abs/2511.21686) — 全消息传递的群体
- [Anthropic engineering — why supervisor not swarm in Research](https://www.anthropic.com/engineering/multi-agent-research-system) — 某个具体生产系统为何明确选择 supervisor 而非群体
- [AutoGen v0.4 actor-model docs](https://microsoft.github.io/autogen/stable/) — 事件驱动的 actor 重写版，比 v0.2 的 GroupChat 更接近群体
