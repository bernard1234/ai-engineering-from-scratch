# 有状态图编排——持久化执行与检查点

> 智能体是一个状态机；节点是函数；边是转移；状态在每个节点之后被检查点化。在任何失败处从最后一个成功检查点恢复。LangGraph 是 2026 年这种底层有状态编排模型的参考。

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 01 (Agent Loop), Phase 14 · 12 (Workflow Patterns)
**Time:** ~75 minutes

## 学习目标

- 描述 LangGraph 的核心模型：带类型化状态、函数节点、条件边和节点后检查点的状态机。
- 说出文档强调的四种能力：durable execution、streaming、human-in-the-loop、comprehensive memory。
- 解释 LangGraph 支持的三种编排拓扑：supervisor、peer-to-peer（swarm）、hierarchical（嵌套子图）。
- 用标准库实现一个带类型化状态、条件边和检查点/恢复循环的状态图。

## 问题

智能体和工作流共有一个问题：当一个 40 步的运行在第 38 步失败时，你想从第 38 步恢复，而不是从头再来。二等的状态模型会让运维人员围绕一个假定每次都是全新运行的库去拼重试。

LangGraph 的设计回答：状态是一等公民的类型化对象，变更显式，检查点在每个节点之后持久化。恢复只是一个 `load_state(session_id)` 调用。

## 概念

### 图

一个图由以下定义：

- **状态类型。** 一个类型化字典（或 Pydantic 模型），每个节点读它、改它。
- **节点。** 纯函数 `(state) -> state_update`。更新在返回后合并进状态。
- **边。** 节点之间的条件转移或直接转移。
- **入口与出口。** `START` 和 `END` 哨兵节点标记边界。

示例：一个带 `classify`、`refund`、`bug`、`sales`、`done` 节点的智能体——一个作为图的 routing 工作流。

### 持久化执行

每个节点返回后，运行时序列化状态并把它写入一个 checkpointer（SQLite、Postgres、Redis、自定义）。在第 N 步失败时，运行时可以 `resume(session_id)` 并从第 N+1 步以精确状态继续。

LangGraph 文档明确强调了这很要紧的生产用户：Klarna、Uber、J.P. Morgan。主张不在于图的形状；而在于「图的形状加上检查点化让恢复变得廉价」。

### Streaming

每个节点都可以产出部分输出。图把逐节点增量事件流给调用方，让 UI 随图运行而更新。

### Human-in-the-loop

在节点之间检查和修改状态。实现方式：在关键节点前暂停，把状态呈现给人类，接受修改，恢复。checkpointer 让这变得容易，因为状态已经序列化好了。

### Memory

短期（一次运行内——状态里的对话历史）和长期（跨运行——通过 checkpointer 加一个独立的长期存储持久化）。LangGraph 通过工具与外部记忆系统（Mem0、自定义）集成。

### 三种拓扑

1. **Supervisor。** 中心路由 LLM 派发给专家 subagent。`langgraph-supervisor` 里的 `create_supervisor()`（不过 LangChain 团队在 2026 年推荐直接通过工具调用来做这件事，以获得更多上下文控制）。
2. **Swarm / peer-to-peer。** 智能体通过共享的工具表面直接交接。没有中心路由。
3. **Hierarchical。** 管理 sub-supervisor 的 supervisor，以嵌套子图实现。

### 这个模式在哪里会出问题

- **检查点太小。** 只检查点对话轮次，会让工具状态和记忆写入不可恢复。完整状态必须序列化。
- **非确定性节点。** 恢复假定节点输入产生同样的状态更新。随机种子、墙上时钟、外部 API 都必须被捕获。
- **条件边过度使用。** 每一条边都是条件边的图，是一台无法推理的状态机。优先线性链加偶尔的分支。

```figure
langgraph-state
```

## Build It

`code/main.py` 实现了一个标准库有状态图：

- `State` —— 一个类型化字典，带 `messages`、`step`、`route`、`output`、`human_approval`。
- `Node` —— 一个接收状态并返回更新字典的可调用对象。
- `StateGraph` —— 节点 + 边 + 条件边 + run + resume。
- `SQLiteCheckpointer`（内存假实现）—— 在每个节点后序列化状态；`load(session_id)` 恢复。
- 一个演示图：classify -> branch(refund / bug / sales) -> human gate -> send。

运行它：

```
python3 code/main.py
```

trace 展示第一次运行在 human gate 处失败、持久化、然后 resume 产出最终输出。

## Use It

- **LangGraph** —— 参考实现，生产就绪。用 `create_react_agent`、`create_supervisor`，或自建图。
- **AutoGen v0.4**（第 14 课）—— 高并发场景的 actor 模型替代。
- **Claude Agent SDK**（第 17 课）—— 带内置 session store 的托管 harness。
- **自定义** —— 当你需要对状态形状或 checkpointer 后端做精确控制时。

## Ship It

`outputs/skill-state-graph.md` 在任意目标运行时中生成一个 LangGraph 形状的状态图，接好检查点化与恢复。

## 练习

1. 当分类置信度低于阈值时，加一条从 `classify` 到 `end` 的条件边。在人类手动设置 `route` 后恢复运行。
2. 把 SQLite 风格假实现换成真正的 SQLite checkpointer。度量每步序列化开销。
3. 实现并行边：两个节点并发运行，用自定义 reducer 合并。不可变状态在这里换来了什么？
4. 读 `langgraph-supervisor` 参考。把玩具移植到 `create_supervisor`。对比 trace 的形状。
5. 加 streaming：每个节点在运行时产出部分状态。打印到达的增量。

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| State graph | 「智能体即状态机」 | 类型化状态 + 节点 + 边 + reducer |
| Checkpointer | 「持久化后端」 | 每个节点后序列化状态；使恢复成为可能 |
| Reducer | 「状态合并器」 | 把当前状态与节点更新组合起来的函数 |
| Conditional edge | 「分支」 | 由状态函数选择的边 |
| Subgraph | 「嵌套图」 | 在另一个图内部当作节点使用的图 |
| Durable execution | 「从失败恢复」 | 以精确状态在最后一个成功节点处重启 |
| Supervisor | 「路由 LLM」 | 专家 subagent 的中心派发器 |
| Swarm | 「P2P 智能体」 | 智能体通过共享工具交接；没有中心路由 |

## 延伸阅读

- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) —— 参考文档
- [langgraph-supervisor reference](https://reference.langchain.com/python/langgraph/supervisor/) —— supervisor 模式 API
- [AutoGen v0.4，Microsoft Research](https://www.microsoft.com/en-us/research/articles/autogen-v0-4-reimagining-the-foundation-of-agentic-ai-for-scale-extensibility-and-robustness/) —— actor 模型替代
- [Claude Agent SDK overview](https://platform.claude.com/docs/en/agent-sdk/overview) —— session store 与 subagents