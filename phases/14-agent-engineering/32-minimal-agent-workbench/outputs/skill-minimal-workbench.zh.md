---
name: minimal-workbench
description: 为任何仓库铺下三文件的最小可行智能体工作台——简短的 AGENTS.md 路由器、持久的 agent_state.json，以及按项目当前 backlog 定制的 JSON task_board.json。
version: 1.0.0
phase: 14
lesson: 32
tags: [workbench, agents-md, state, task-board, scaffold]
---

给定一个仓库路径和一份简短 backlog，搭建最小可行智能体工作台。

产出：

1. `AGENTS.md` 不超过 80 行。它必须路由到：状态文件、任务板、更深的规则文档（哪怕为空）、验证命令。此文件中不得有散文式教程。
2. `agent_state.json`，带这些键：`active_task_id`、`touched_files`、`assumptions`、`blockers`、`next_action`。所有可选字段默认为空数组或空字符串，对数组永远不用 `null`。
3. `task_board.json`，作为任务的 JSON 数组。每个任务有 `id`、`goal`、`owner`（`builder` | `reviewer` | `human`）、`acceptance`（字符串列表），以及 `status`（`todo` | `in_progress` | `done` | `blocked`）。
4. `docs/agent-rules.md` 占位文件，每个面放一个 H2，供后面的课填充。

硬性拒绝：

- 超过 80 行或少于 10 行的 `AGENTS.md`。太长智能体会跳过它；太短它承载不了任何路由。
- 引用聊天历史而非仓库的状态文件。仓库是记录的系统。
- 没有 `acceptance` 的任务板。没有验收标准的任务会变成「看起来不错」的橡皮图章。
- `owner` 是 `agent` 或 `model` 的任务。owner 是角色，不是实体。

拒绝规则：

- 如果仓库没有验证命令，拒绝写 `AGENTS.md`，直到提供一个或打一个桩。指向一个缺失门的路由器比没有路由器还糟。
- 如果 backlog 有超过 12 个未完成任务，拒绝并要求用户拆分。超过一屏的板会漂移成规划剧场。
- 如果项目在被追踪的文件里携带了秘密，拒绝写状态文件，并先把秘密泄露作为阻塞性发现提出来。

输出结构：

```
<repo>/
├── AGENTS.md
├── agent_state.json
├── task_board.json
└── docs/
    └── agent-rules.md
```

结尾附「下一步读什么」，指向：

- 第 33 课，把规则占位文件变成可执行约束。
- 第 34 课，了解持久 state schema。
- 第 36 课，了解每个任务的 scope contract。