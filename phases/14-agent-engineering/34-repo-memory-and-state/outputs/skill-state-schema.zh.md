---
name: state-schema
description: 为 agent state 和 task board 生成项目专属的 JSON Schema、一个带原子写入的 Python StateManager，以及一个让 schema 升级无法破坏 workbench 的迁移脚手架。
version: 1.0.0
phase: 14
lesson: 34
tags: [state, schema, json-schema, atomic-writes, migrations]
---

给定一个 repo 和运行在其中的 agent 产品，为 workbench 产出 schema 优先的 state 文件。

产出：

1. `schemas/agent_state.schema.json`，覆盖必需 key、允许的 status 值、数组与 null 的纪律，以及一个 `schema_version` 整数。
2. `schemas/task_board.schema.json`，覆盖 task id 模式、允许的 owner、允许的 status 以及验收数组。
3. `tools/state_manager.py`，暴露 `load`、`commit`、`update`，采用 temp-and-rename 原子写入。
4. `tools/migrate_state.py` 脚手架，用于下一次 schema 升级；文件来自未知版本时大声失败。
5. 以 `schema_version: 1` 和全新 backlog 播种的 `agent_state.json` 和 `task_board.json`。

硬性拒绝：

- 没有 `schema_version` 字段的 schema。迁移不是可选项。
- 在期望数组处允许 `null`。`null` 是伪装成数据的写入期 bug。
- 使用普通 `open(path, "w")` 的写入者。只用原子写入；部分文件会破坏真相源。
- 在 state 里存 token、原始聊天记录或 PII。state 只放与 repo 相关的事实。

拒绝规则：

- 如果 repo 没有版本控制，拒绝交付 state 文件。原子写入加 git diff 才是持久性的故事。
- 如果项目没有至少一条验收命令来验证 `done` 转移，拒绝 `status: done` 这个枚举值。没有验收检查就加 `done` 是作秀。
- 如果项目打算在没有锁策略的情况下跨进程共享 state，交付前把这个发现摆在明面上；原子 rename 必要但不充分。

输出结构：

```
<repo>/
├── agent_state.json
├── task_board.json
├── schemas/
│   ├── agent_state.schema.json
│   └── task_board.schema.json
└── tools/
    ├── state_manager.py
    └── migrate_state.py
```

结尾附上「接下来读什么」，指向：

- Lesson 35，启动时调用 manager 的 initialization script。
- Lesson 38，读取 state 来给完成度打分的 verification gate。
- Lesson 40，消费同一 schema 的 handoff generator。