---
name: state-graph
description: 构建一个 LangGraph 形状的状态机，带类型化状态、条件边、逐节点检查点化和持久恢复。
version: 1.0.0
phase: 14
lesson: 13
tags: [langgraph, state-machine, durable, checkpointing, human-in-the-loop]
---

给定一个目标运行时、一个状态形状、一组节点函数和一个 checkpointer 后端，产出一个有状态智能体图。

产出：

1. 一个类型化的 `State`（dict 或 Pydantic）。记录每个字段。节点读状态；它们返回更新。
2. 一个 `StateGraph`，带 `add_node`、`add_edge`、`add_conditional_edges`、`set_entry`，以及 `START`/`END` 哨兵。
3. 一个 `Checkpointer` 接口，带 `save(session_id, node, state)` 和 `load_latest(session_id)`。默认 SQLite；允许 Postgres/Redis/自定义。
4. 一个 `Runner`，遍历图、每个节点后序列化状态、为 human-in-the-loop 捕获 `PausedAtNode`，并支持 `resume_from` 加可选的 `state_override`。
5. 三个拓扑辅助器：supervisor（中心路由）、swarm（共享工具交接）、hierarchical（子图）。

硬拒绝：

- 没有显式随机种子或墙上时钟捕获的非确定性节点。恢复假定给定输入状态下节点输出是可复现的。
- 只保存「摘要」状态的 checkpointer。序列化完整状态，否则恢复会断。
- 每条边都是条件边的图。优先线性链加偶尔的分支。

拒绝规则：

- 如果用户要求没有持久化的状态图，拒绝。重点就在于持久恢复；如果你不需要恢复，用第 12 课的工作流模式。
- 如果用户要求「只在成功时检查点」，拒绝。失败同样需要状态——那才是调试开始的地方。
- 如果图超过约 30 个节点，拒绝扁平布局并要求嵌套子图。扁平的 30 节点图无法评审。

输出：`state.py`、`graph.py`、`checkpointer.py`、`runner.py`、解释状态 schema、checkpointer 选择和恢复语义的 `README.md`。结尾加「接下来读什么」：actor 模型替代指向第 14 课，handoff/guardrail 层指向第 16 课，图步骤上的 OTel span 指向第 23 课。