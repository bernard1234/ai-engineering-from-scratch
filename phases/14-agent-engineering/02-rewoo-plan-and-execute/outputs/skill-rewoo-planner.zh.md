---
name: rewoo-planner
description: 从用户请求和工具目录生成一个经过校验的 ReWOO 计划 DAG。
version: 1.0.0
phase: 14
lesson: 02
tags: [rewoo, plan-and-execute, planning, dag, distillation]
---

给定一个用户请求和一个工具目录（名称、输入 schema、描述），产出一个 ReWOO 计划：一个由步骤组成的 DAG，带工具调用和证据引用（`#E1`、`#E2`、...）。在交给执行器之前校验计划。

产出：

1. 一个计划 DAG。每个节点有 id（`E1`、`E2`、...）、工具名、参数字典（字符串可以包含 `#E<k>` 引用），以及可选的 `parallel_group` 标签。
2. 校验输出。通过拓扑排序做无环检查；引用解析检查（每个 `#E<k>` 都有一个前置的生产者）；工具存在性检查（每个工具名都在目录中）；参数 schema 检查（每个参数都匹配工具的输入 schema）。
3. 并行性提示。对每一个拓扑层，列出可以并发执行的节点。
4. planner/solver 分工建议。如果计划少于 3 步，推荐改用 ReAct。如果计划需要无界循环（每一步都重新规划），推荐带 replanner 的 Plan-and-Execute。如果计划超过 30 步或面向网页/移动端，推荐带合成计划数据的 Plan-and-Act。

硬性拒绝：

- 带环的计划。ReWOO 假定是 DAG；环是 ReAct 或 LATS 的事。
- 引用了在拓扑序中尚不存在的 `#E<k>` 的计划。指出具体是哪条边失败。
- 调用目录外工具的计划。不要为了凑一个计划而编造工具。
- 引用参数类型与工具 schema 不匹配的计划（例如 `#E1` 替换出字符串，但工具期望 int）。

拒绝规则：

- 若任务是开放式探索（需要未知工具、未知步骤），拒绝并推荐 ReAct 或 LATS（第 4 课）。
- 若工具目录含有破坏性工具却没有门禁审批工具，拒绝并指向第 9 课（权限、沙箱）。

输出：一个结构化计划（JSON 或 YAML）、一份校验报告、一张并行性映射，以及一个指向执行器（ReWOO Worker）、replanner（Plan-and-Execute）或更大轨迹采样循环（Plan-and-Act）的后续动作。

结尾附「接下来读什么」说明：若该任务类别此前已被尝试过，指向第 3 课（Reflexion）；若计划能受益于搜索，指向第 4 课（LATS）。