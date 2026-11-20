# Supervisor / Orchestrator-Worker 模式

> 一个 lead agent 负责计划与委派；专门化的 worker 在并行的 context 中执行并回报。这正是 Anthropic Research 系统背后的模式（Claude Opus 4 作为 lead，Sonnet 4 作为 subagent），在内部 research eval 上相对单 agent Opus 4 测得 +90.2%。Anthropic 的工程博文指出，BrowseComp 上 80% 的方差仅由 token 用量就能解释——multi-agent 之所以胜出，很大程度上是因为每个 subagent 都获得一个全新的 context window。本课从 primitive 出发构建 supervisor 模式，并涵盖 2026 年来自生产部署的工程经验。

**Type:** Learn + Build
**Languages:** Python (stdlib, `threading`)
**Prerequisites:** 第 16 阶段，第 04 课（Primitive Model）
**Time:** ~75 分钟

## 问题场景

研究是单 agent 系统会失败的典型任务。你问“2023 到 2026 年间 multi-agent 系统发生了什么变化？”单 agent 顺序读五篇论文，用它们的文本填满一半 context，然后必须把它们放在一起推理。读到第五篇时它已经忘了第一篇。它无法并行。

supervisor 模式解决了这个问题：一个 lead agent 规划搜索，把每个子问题委派给一个 worker，然后综合。每个 worker 为一个狭窄的问题获得自己的 200k-token 窗口。lead 从不看原始论文——只看 worker 的摘要。

Anthropic 的生产 Research 系统报告，在内部 research eval 上相对单个 Opus 4 提升 +90.2%。同一篇博文指出，BrowseComp 80% 的方差仅由 *token 用量* 解释。每个 subagent 拥有全新 context 是主要机制。

## 核心概念

### 模式

```
                 ┌──────────────┐
                 │   Lead       │  plans, decomposes,
                 │  (Opus 4)    │  synthesizes
                 └──┬────┬───┬──┘
                    │    │   │
            ┌───────┘    │   └───────┐
            ▼            ▼           ▼
      ┌─────────┐  ┌─────────┐  ┌─────────┐
      │ Worker1 │  │ Worker2 │  │ Worker3 │
      │(Sonnet) │  │(Sonnet) │  │(Sonnet) │
      └─────────┘  └─────────┘  └─────────┘
         fresh       fresh        fresh
         context     context      context
```

lead 从不读原始材料。worker 们在 lead 综合之前从不看彼此的工作。每个箭头都是一次携带狭窄产物的 handoff。

### 为什么它能赢

三个机制：

1. **每个 subagent 拥有全新 context。** 探索“FIPA-ACL 遗产”的 worker 不会携带 lead 花在规划上的 40k tokens。它为一个问题获得 200k 窗口。
2. **通过 prompt 实现专门化。** lead 的 prompt 是“分解并综合”，不是“研究”。每个 worker 的 prompt 都很窄：“找出 X 中发生了什么变化。”聚焦的 prompt 产出聚焦的结果。
3. **并行。** worker 并发运行。墙钟时间大致是 `max(worker_times) + plan + synthesis`，而不是 `sum(worker_times)`。

### 工程经验（Anthropic 2025）

Anthropic 的博文列出了几条在 2026 年仍然适用的生产经验：

- **按查询复杂度匹配投入。** 简单查询：一个 agent，3-10 次 tool call。复杂查询：10+ 个 agent。必须由 lead 来估计，而不是调用方。
- **先宽后窄。** 先分解为宽泛的子问题，如果答案值得深挖，再为每个子问题派生更多 worker。
- **Rainbow 部署。** agent 是长时间运行且有状态的。传统的蓝绿部署行不通。Anthropic 使用 rainbow：新版本逐步放量，同时旧版本排空。
- **token 用量占主导。** multi-agent 的 tokens 约为单 agent 的 15 倍。只有任务价值足以证明成本时才运行它。

### 转向图原生

LangGraph 最初提供了 `langgraph-supervisor` 库，带一个高层 `create_supervisor` 辅助函数。2025 年，LangChain 把推荐做法改为直接通过 tool call 实现 supervisor 模式，因为 tool call 能更好地控制*supervisor 看到什么*（context engineering）。该库仍然可用；文档现在推荐 tool call 形式。

### 失败模式

- **lead 编造计划。** 如果 lead 生成的子问题并未分解真正的问题，worker 就会在错误的目标上做精确的研究。
- **worker 过度探索。** 如果没有明确的范围边界，worker 会漂移出被分配的子问题，污染综合步骤。
- **综合冲突。** 两个 worker 返回矛盾的事实。lead 必须要么重新询问（增加一轮），要么显式标注分歧。静默地选择一边是最糟糕的失败：用户永远不知道曾经发生过分歧。

### 何时 supervisor 是错的

- **顺序任务。** 如果第 2 步确实需要第 1 步的输出，并行毫无收益。用 pipeline（CrewAI Sequential、LangGraph 线性图）。
- **简单查询。** 单 agent 处理得更快更便宜。在派生 worker 之前先用 lead 的“按复杂度匹配投入”检查。
- **严格的确定性。** supervisor 使用 LLM 选择的委派。当审计/重放比适应性更重要时，静态图更好。

```figure
supervisor-hierarchy
```

## Build It

`code/main.py` 用 `threading` 实现一个带三个并行 worker 的 supervisor。lead 把查询分解为子问题，worker 并发处理每个子问题，lead 进行综合。没有真实 LLM——worker 是脚本化的，模拟抓取并总结。

关键结构：

- `Lead.plan(query)` 把查询拆成 3 个子问题。
- `Worker.run(sub_q)` 返回一个假摘要（在生产中可以是任何使用工具的 agent）。
- `Lead.run(query)` 在线程中启动 worker，join，然后综合。

运行：

```
python3 code/main.py
```

输出展示计划、带起止时间戳的并行 worker 追踪，以及最终综合。你能看到墙钟时间的收益：三个 0.3 秒的 worker 在约 0.35 秒内跑完，而不是 0.9 秒。

## Use It

`outputs/skill-supervisor-designer.md` 接收用户查询并产出 supervisor 模式设计：lead 的 system prompt、worker 角色、子问题分解规则，以及综合模板。在构建新的研究型 agent 系统之前使用它。

## Ship It

部署 supervisor 模式前的检查清单：

- **模型配对。** lead 使用推理级模型（Opus 级、`o3` 级）。worker 使用更快、更便宜的模型（Sonnet、`o4-mini`）。
- **worker 超时。** 任何运行时长超过中位数 2 倍的 worker 都会被杀掉；lead 要么以更窄的范围重新派生，要么不带它继续。
- **每个 worker 的 token 上限。** 硬限制（比如预期综合输入的 10 倍）防止失控的 worker 烧穿预算。
- **可观测性。** 追踪 lead 的计划、每个 worker 的 tool call 以及综合过程。这是一切事后调试的基础。
- **Rainbow 发布。** 有状态的长运行 agent 需要渐进式版本切换，而不是热替换。

## Exercises

1. 运行 `code/main.py`，然后把 lead 改成派生 5 个 worker 而不是 3 个。观察墙钟时间的变化。在这个演示中，worker 数量达到多少时，派生开销会超过并行节省？
2. 实现 worker 超时：杀掉任何运行超过 0.5 秒的 worker，让 lead 对其余结果进行综合。你需要什么可观测性才能知道某个 worker 被砍掉了？
3. 为 lead 的综合增加一步冲突检测：如果两个 worker 返回矛盾的答案，lead 标注分歧而不是选择其中一个。如何在不调用 LLM 的情况下检测矛盾？
4. 阅读 Anthropic 的 Research 系统工程博文。列出这个玩具演示要在生产运行所需的三个实践。
5. 对比 LangGraph 的 `create_supervisor`（遗留）与新的 tool call 推荐做法。哪一个让你更好地控制 supervisor 看到的内容？为什么 Anthropic 明确只把子答案、而不是原始 worker context 传入综合？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Supervisor | “lead agent” | 一个负责计划、委派和综合的 orchestrator agent。它不亲自做工作。 |
| Worker | “subagent” | 由 supervisor 以狭窄范围调用的聚焦 agent，拥有自己的 context window。 |
| Orchestrator-worker | “supervisor 模式” | 同一件事，不同名字。2026 年的文献两种都用。 |
| Fresh context | “干净的窗口” | worker 的 context 从其 system prompt 和被分配的问题开始，而不是 lead 的历史。 |
| Rainbow deployment | “渐进式发布” | 长运行的有状态 agent 需要按版本排空并替换，而不是蓝绿部署。 |
| Token dominance | “context 就是那个变量” | 据 Anthropic，research eval 80% 的方差来自总共使用的 tokens，而非模型选择。 |
| Scale effort | “让 agent 数量匹配复杂度” | lead 估计查询难度，相应地派生 1 个或 10+ 个 worker。 |
| Synthesis conflict | “worker 意见不一致” | 两个 worker 返回矛盾的事实；lead 必须暴露分歧，而不是静默选择一边。 |

## Further Reading

- [Anthropic engineering — How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)——supervisor 模式的生产参考
- [LangGraph workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents)——tool call 式 supervisor 现在是推荐形式
- [LangGraph supervisor reference](https://reference.langchain.com/python/langgraph-supervisor)——遗留辅助库，2026 年生产中仍在使用
- [OpenAI cookbook — Orchestrating Agents: Routines and Handoffs](https://developers.openai.com/cookbook/examples/orchestrating_agents)——基于 handoff 的 supervisor 变体
