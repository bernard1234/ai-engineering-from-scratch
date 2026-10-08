---
name: memory-blocks
description: 生成一个 Letta 形状的三层记忆系统（core blocks、recall、archival），带一个处于关键路径之外的 sleep-time 整合 agent。
version: 1.0.0
phase: 14
lesson: 08
tags: [memory, letta, blocks, sleep-time, consolidation]
---

给定目标运行时、主模型和一个（可能更强的）sleep-time 模型，产出一个带显式 block 类型和异步整合的三层记忆系统。

产出：

1. `Block` 类型，含 `label`、`value`、`limit`、`description`、`version`、`history`。每次写入递增版本并记录旧值。暴露 `near_limit(threshold=0.8)`。
2. 一个 `BlockStore`，至少含三个默认 blocks：`human`（关于用户的事实）、`persona`（agent 自我概念）、`task`（当前范围）。允许用户自定义 blocks。
3. 一个 `Recall` 存储——按会话分页的轮次日志。每轮自动写入。尾部在达到上限时驱逐但仍可检索。
4. 一个 `Archival` 存储——至少两个后端（vector、KV）。插入返回记录 id。矛盾时失效而非删除。
5. 一个 `PrimaryAgent`，处理轮次且只发出原始写入。关键路径上不摘要。
6. 一个 `SleepTimeAgent`，在轮次之间运行：摘要超过阈值的 blocks、失效矛盾的 archival 记录、把 `learned_context` 写进共享 blocks。

硬拒绝：

- 任何在面向用户的轮次期间同步运行、且不是直接查找的记忆操作。摘要、整合、失效属于 sleep-time 遍历。
- 矛盾时删除 archival 记录。失效能让历史保持可审计。
- 在没有审查步骤的情况下写 Persona 或 Safety block。这些 blocks 全局塑造行为；静默写入掩盖 bug。

拒绝规则：

- 如果运行时无法跨会话持久化 blocks，拒绝发布一个被描述为「记忆」的产品。降级该声明。
- 如果 sleep-time agent 没有轨迹输出，拒绝。静默整合是调试的死区。
- 如果用户要求「不失效，始终信任最新写入」，在任何历史声明重要的领域（合规、医疗、法律）拒绝。

输出：每个组件一个文件，外加一份命名默认 blocks、sleep-time 节奏和矛盾解决策略的 `README.md`。结尾「what to read next」：如果 agent 需要对记忆做 graph 推理，指向 Lesson 09；如果产品需要记忆操作上的 OTel spans，指向 Lesson 23。