---
name: permission-mode-picker
description: 在开始一次运行之前，把一项 Claude Code 任务匹配到正确的 permission mode、预算上限与所需隔离。
version: 1.0.0
phase: 15
lesson: 10
tags: [claude-code, permission-modes, auto-mode, budgets, isolation]
---

给定一个拟议的 Claude Code 任务，选定 permission mode、设定预算，并明确在允许 agent 开始之前所需的最低隔离级别。

产出：

1. **任务画像。** 用一句话说明该任务做什么，再用一句话说明一旦出错时的爆炸半径。
2. **模式建议。** 以下之一：`plan`、`default`、`acceptEdits`、`auto`、`dontAsk`、`bypassPermissions`。用一句话结合爆炸半径给出理由。
3. **预算数字。** `max_turns`、`max_budget_usd` 以及任何按 tool 上限的具体取值。对于超过一小时的无人值守运行，要指定一个美元上限，等于或低于你为一个无法回滚的人为错误愿意付出的代价。
4. **隔离要求。** 文件系统范围（仅项目目录、scratch 目录、临时容器）。网络策略（无 egress、仅 allowlist、完全放开）。凭证面（无、受限 token、宽泛 token）。对于 `bypassPermissions` 或 `dontAsk`，运行必须位于一个未挂载任何生产凭证的临时容器内。
5. **轨迹审计计划。** 运行结束后，人将如何审查该轨迹？对 `auto`、`dontAsk` 以及任何超过 30 分钟时程的运行都必须执行。

硬性拒绝：
- 对着一个有未提交改动的 repo 使用 `bypassPermissions`。
- 没有预算上限的 `auto`。
- 环境中带有宽泛凭证（AWS、GCP、带 repo scope 的 GitHub PAT）却使用任何高于 `acceptEdits` 的模式。
- 超过一小时且未安排轨迹审计的无人值守运行。
- 声称仅凭 Auto Mode 的 classifier 就足以应对一个全新的任务分布。

拒绝规则：
- 如果用户说不出一次失败的爆炸半径，拒绝，并要求在开始前给出一句明确的最坏情况陈述。
- 如果用户在一个可触达生产数据库凭证的工作区里请求 `auto`，拒绝，并要求先提供受限凭证或临时容器。
- 如果拟议的预算上限超过了用户在一次糟糕运行中愿意承受的损失，拒绝，并要求更低的限额。

输出格式：

返回一张一页的运行卡片，包含：
- **任务摘要**（一句话）
- **爆炸半径**（一句话，最坏情况）
- **模式**（明确写出）
- **预算**（`max_turns`、`max_budget_usd`、按 tool 上限）
- **隔离**（文件系统范围、网络策略、凭证面）
- **审计计划**（谁审查轨迹、何时审查、依据什么评分准则）
