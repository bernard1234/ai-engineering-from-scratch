# Agent 状态机——Graph、Node 与 Checkpoint

> 手写出来的 ReAct 循环就是一个 `while True`。把同一个循环写成显式 graph，它就变成了一个你可以 checkpoint、interrupt、branch 和 time-travel 的东西。agent 没有变，变的是它外面的 harness。

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 11 · 09 (Function Calling), Phase 11 · 14 (Model Context Protocol)
**Time:** ~75 分钟
## 问题场景

你上线了一个 function calling agent。它跑了三轮都没问题，然后出事了：模型调用的某个 tool 返回了 500，用户中途改了主意，或者 agent 决定不经人工签字就退掉一笔订单。`while True:` 循环没有任何钩子。你没法暂停它，没法回退，也没法分叉出“如果模型当时选了另一个 tool 会怎样”。一旦把它带出 demo 环境交付，agent 就变成一个黑盒——要么成了，要么没成，中间过程一概不可见。

一旦看清这一点，下一步就很明显。agent 本来就是一个状态机——system prompt 加上消息历史、加上待执行的 tool 调用、加上下一个动作。把这个状态机显式化：用 node 表示“模型在思考”“tool 在运行”“人工在审批”，用 edge 表示它们之间的条件转移。图一旦显式，harness 就白得四样东西：checkpointing（在步骤之间保存状态）、interrupts（暂停等待人工）、streaming（流式输出 token 和中间事件）以及 time-travel（回退到先前状态并尝试另一条分支）。

这个抽象的参考实现是 LangGraph。它不是 LangChain 意义上的 agent 框架（“给你一个 AgentExecutor，祝你好运”）。它是一个 graph runtime：state 是一等公民，持久化是一等公民，interrupt 也是一等公民。agent 循环变成了你画出来的东西，而不是你手写的东西。

## 核心概念

![LangGraph StateGraph：node、edge 与 checkpointer](../assets/langgraph-stategraph.svg)

一个 `StateGraph` 由三部分组成。

1. **State。** 一个类型化的 dict（TypedDict 或 Pydantic model），在 graph 中流动。每个 node 接收完整的 state，返回一个局部更新，LangGraph 会按字段用 *reducer* 合并它——应当累积的 list 用 `operator.add`，默认是覆盖。
2. **Nodes。** Python 函数 `state -> partial_state`。每一个都是一个离散步骤：“调用模型”“运行 tools”“总结”。
3. **Edges。** node 之间的转移。静态 edge 只去一个地方。条件 edge 接受一个路由函数 `state -> next_node_name`，这样 graph 就能根据模型输出分支。

你编译这个 graph。compile 会绑定拓扑、挂上一个 checkpointer（可选，但对生产至关重要），并返回一个 runnable。你用一个初始 state 和一个 `thread_id` 来调用它。每一步执行都会持久化一个以 `(thread_id, checkpoint_id)` 为键的 checkpoint。

### 四项超能力

**Checkpointing。** 每一次 node 转移都会把新 state 写入一个 store（测试用内存，生产用 Postgres/Redis/SQLite）。用同一个 `thread_id` 再次调用 graph 即可恢复。graph 从它暂停的地方继续。

**Interrupts。** 给一个 node 标记 `interrupt_before=["human_review"]`，执行就会在该 node 运行之前停下。state 会被持久化。你的 API 答复用户“等待审批”。之后对同一个 `thread_id` 发来带 `Command(resume=...)` 的请求即可恢复执行。

**Streaming。** `graph.stream(state, mode="updates")` 会在状态变化发生时产出 state 增量。`mode="messages"` 流式输出模型 node 内部的 LLM token。`mode="values"` 产出完整快照。在 UI 里呈现什么，由你挑选。

**Time-travel。** `graph.get_state_history(thread_id)` 返回完整的 checkpoint 日志。把任意一个先前的 `checkpoint_id` 传给 `graph.invoke`，你就从那个点分叉。这对调试（“如果模型当时选了 tool B 会怎样？”）和重放生产 trace 的回归测试都很有用。

### reducer 才是关键

每个 state 字段都有一个 reducer。多数默认值就够了——新值覆盖旧值。但消息 list 需要 `operator.add`，这样新消息是追加而不是替换。并行的 edge 会通过 reducer 合并各自的更新。如果两个 node 都更新 `messages`，而你忘了 `Annotated[list, add_messages]`，第二个会静默胜出，你会丢掉这一轮的一半内容。reducer 是库里唯一微妙的地方；把它搞对，其余部分自然组合起来。

### 四节点 ReAct 图

一个生产级 ReAct agent 就是四个 node 加两条 edge：

1. `agent` — 用当前消息历史调用 LLM。返回 assistant 消息（其中可能包含 tool_calls）。
2. `tools` — 执行最后一条 assistant 消息里的所有 tool_calls，把 tool 结果作为 tool 消息追加进去。
3. 从 `agent` 出发的一条条件 edge：如果最后一条消息带 tool_calls，路由到 `tools`，否则路由到 `END`。
4. 从 `tools` 回到 `agent` 的一条静态 edge。

就是这样。你用大约 40 行代码得到了完整的 ReAct 循环（Thought → Action → Observation → Thought → …），外加 checkpointing、interrupts 和 streaming。

### StateGraph vs Send（fanout）

`Send(node_name, state)` 让一个 node 派发并行子图。例如：agent 决定同时查询三个 retriever。每个 `Send` 都会衍生一次目标 node 的并行执行；它们的输出通过 state reducer 合并。这就是 LangGraph 在不引入线程原语的情况下表达 orchestrator-workers 模式的方式。

### 子图

一个已编译的 graph 可以作为另一个 graph 的 node。外层 graph 看到的是一个单独的 node；内层 graph 拥有自己的 state 和自己的 checkpoint。团队就是这样构建 supervisor-worker agent 的：supervisor graph 把用户意图路由到按领域划分的 worker 子图。

```figure
l5-state-graph-ledger
```

## Build It

### 第 1 步：state 与 nodes

```python
from typing import Annotated, TypedDict
from langchain_core.messages import AnyMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

def agent_node(state: State) -> dict:
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

def should_continue(state: State) -> str:
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else END

tool_node = ToolNode(tools=[search_web, read_file])

graph = StateGraph(State)
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
graph.add_edge("tools", "agent")

app = graph.compile(checkpointer=MemorySaver())
```

`add_messages` 就是让消息 list 累积而不是覆盖的那个 reducer。忘了它是最常见的 LangGraph bug。

### 第 2 步：用一个 thread 运行

```python
config = {"configurable": {"thread_id": "user-42"}}
for event in app.stream(
    {"messages": [HumanMessage("find the Anthropic headquarters address")]},
    config,
    stream_mode="updates",
):
    print(event)
```

每个更新都是一个 dict `{node_name: state_delta}`。你的前端可以把这些流式推给 UI，让用户看到“agent 在思考……正在调用 search_web……拿到结果……正在作答”。

### 第 3 步：加入 human-in-the-loop interrupt

标记一个 node，让执行在它运行之前暂停。

```python
app = graph.compile(
    checkpointer=MemorySaver(),
    interrupt_before=["tools"],  # pause before every tool call
)

state = app.invoke({"messages": [HumanMessage("delete the production database")]}, config)
# state["__interrupt__"] is set. Inspect proposed tool calls.
# If approved:
from langgraph.types import Command
app.invoke(Command(resume=True), config)
# If denied: write a rejection message and resume
app.update_state(config, {"messages": [AIMessage("Blocked by human reviewer.")]})
```

state、checkpoint 和 thread 在整个 interrupt 期间都会持久化。除了执行期间，没有任何东西留在内存里。

### 第 4 步：用 time-travel 调试

```python
history = list(app.get_state_history(config))
for snapshot in history:
    print(snapshot.values["messages"][-1].content[:80], snapshot.config)

# Fork from a prior checkpoint
target = history[3].config  # three steps back
for event in app.stream(None, target, stream_mode="values"):
    pass  # replay from that point forward
```

把 `None` 作为 input 传入，会从给定的 checkpoint 开始重放；传入一个值，会先把它作为更新追加到该 checkpoint 的 state 上再继续。这样你就能复现一次糟糕的 agent 运行，而无需重跑整段对话。

### 第 5 步：为生产环境换掉 checkpointer

```python
from langgraph.checkpoint.postgres import PostgresSaver

with PostgresSaver.from_conn_string("postgresql://...") as checkpointer:
    checkpointer.setup()
    app = graph.compile(checkpointer=checkpointer)
```

SQLite、Redis 和 Postgres 都已随包提供。`MemorySaver` 只用于测试。任何需要跨重启持久化的东西都要用真正的 store。

## 技能

> 你把 agent 构建成 graph，而不是 `while True` 循环。

在用 LangGraph 之前，先花 60 秒做一次设计：

1. **给 node 命名。** 每一个离散决策或带副作用的动作都是一个 node。“agent 思考”“tool 运行”“审批人批准”“响应流式输出”。如果你列不出它们，说明任务还不是 agent 形态。
2. **声明 state。** 用最小化的 TypedDict，每个 list 字段都配一个 reducer。不要把一切都塞进 `messages`；把任务特有的字段（工作中的 `plan`、`budget` 计数器、`retrieved_docs` list）提到顶层。
3. **画出 edge。** 除非下一步取决于模型输出，否则用静态 edge。每条条件 edge 都需要一个带具名分支的路由函数。
4. **一开始就选好 checkpointer。** 测试用 `MemorySaver`，其他一切用 Postgres/Redis/SQLite。没有 checkpointer 就不要上线——没有 checkpointer 就没有 resume、没有 interrupt、没有 time-travel。
5. **在 tool 运行之前决定 interrupt，而不是之后。** 审批放在进入有副作用 node 的那条 edge 上，这样你可以在造成损害之前取消；校验放在模型输出的那条 edge 上，这样你可以廉价地拒掉错误调用。
6. **默认 stream。** UI 用 `mode="updates"`，模型 node 内部的 token 级 streaming 用 `mode="messages"`，eval 期间的全量快照用 `mode="values"`。

拒绝上线一个没有 checkpointer 的 LangGraph agent。拒绝上线一个在副作用*之后*才 interrupt 的 agent。拒绝上线一个 `messages` 字段没有以 `add_messages` 作 reducer 的 agent。

## Exercises

1. **简单。** 用上面那个四节点 ReAct graph，配一个计算器 tool 和一个 web 搜索 tool。验证 `list(app.get_state_history(config))` 对一段两轮对话返回至少四个 checkpoint。
2. **中等。** 加一个在 `agent` 之前运行的 `planner` node，把结构化的 `plan: list[str]` 写进 state。让 `agent` 把 plan 里的步骤标记为完成。如果 `plan` 在 checkpoint 恢复后丢失（reducer 写错了），让测试失败。
3. **困难。** 构建一个 supervisor graph，用 `Send` 在三个子图（`researcher`、`writer`、`reviewer`）之间路由。每个子图有自己的 state 和 checkpointer。在外层 graph 上加 `interrupt_before=["writer"]`，让人类可以审批研究简报。确认从先前 checkpoint 的 time-travel 只会重跑分叉出去的那条分支。

## Key Terms

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| StateGraph | "那个 LangGraph 图" | 在 compile 之前，你往其中添加 node 和 edge 的构建器对象。 |
| Reducer | "字段怎么合并" | 当某个 node 为该字段返回更新时应用的函数 `(old, new) -> merged`；默认是覆盖，`add_messages` 是追加。 |
| Thread | "一个对话 ID" | 一个 `thread_id` 字符串，用来限定一次会话的所有 checkpoint。 |
| Checkpoint | "一个暂停的状态" | 在一个 node 转移之后持久化的完整 graph state 快照，以 `(thread_id, checkpoint_id)` 为键。 |
| Interrupt | "暂停等人工" | `interrupt_before` / `interrupt_after` 在 node 边界停止执行；用 `Command(resume=...)` 恢复。 |
| Time-travel | "从先前的步骤分叉" | `graph.invoke(None, config_with_old_checkpoint_id)` 从那个 checkpoint 开始向前重放。 |
| Send | "并行子图派发" | 一个 node 可以返回的构造器，用来衍生目标 node 的 N 次并行执行。 |
| Subgraph | "一个作为 node 的已编译 graph" | 作为另一个 graph 中 node 使用的已编译 StateGraph；保留自己的 state 作用域。 |

## Further Reading

- [LangGraph documentation](https://langchain-ai.github.io/langgraph/) —— StateGraph、reducer、checkpointer 和 interrupt 的权威参考。
- [LangGraph concepts: state, reducers, checkpointers](https://langchain-ai.github.io/langgraph/concepts/low_level/) —— 本课采用的心智模型，直接来自官方文档。
- [LangGraph Persistence and Checkpoints](https://langchain-ai.github.io/langgraph/concepts/persistence/) —— 关于 Postgres/SQLite/Redis store、checkpoint 命名空间和 thread ID 的细节。
- [LangGraph Human-in-the-loop](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/) —— `interrupt_before`、`interrupt_after`、`Command(resume=...)` 以及编辑 state 的模式。
- [Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models" (ICLR 2023)](https://arxiv.org/abs/2210.03629) —— 每个 LangGraph agent 都在实现的模式；读它了解推理轨迹的依据。
- [Anthropic — Building effective agents (Dec 2024)](https://www.anthropic.com/research/building-effective-agents) —— 应该偏好哪些 graph 形状（chain、router、orchestrator-workers、evaluator-optimizer），以及何时偏好。
- Phase 11 · 09（Function Calling）—— 每个 LangGraph agent node 都在复用的 tool 调用原语。
- Phase 11 · 14（Model Context Protocol）—— 通过 MCP adapter 接入 LangGraph `ToolNode` 的外部 tool 发现。
- Phase 11 · 17（Agent 框架取舍）—— 何时选 LangGraph 而不是 CrewAI、AutoGen 或 Agno。
