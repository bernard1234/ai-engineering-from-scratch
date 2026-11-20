---
name: multi-agent-team
description: 构建一支由 architect、并行 coders、reviewer 与 tester 组成的多智能体软件团队；在 SWE-bench Pro 上评测，并产出一份交接失败复盘。
version: 1.0.0
phase: 19
lesson: 10
tags: [capstone, multi-agent, swe-bench, langgraph, a2a, worktree, roles]
---

给定一个 GitHub issue URL 与一个并行度，部署一支多智能体软件团队，产出一个可合并的 PR。在 50 个 SWE-bench Pro issue 上评测，并发布一张交接失败直方图。

构建计划：

1. 任务板：file-backed（或 Redis）的 JSONL 存储，承载类型化消息。消息种类：plan_request、subtask、diff_ready、review_needed、review_feedback、approved、test_needed、test_passed、test_failed、replan_needed。
2. Architect（Opus 4.7）：读取 issue、撰写方案，并发出一个带显式接口（涉及的文件、公开函数、测试影响）的子任务 DAG。
3. N 个 coders（Sonnet 4.7）：各自领取一个子任务，拉起一个新的 `git worktree add` + Daytona sandbox，独立实现。
4. 合并协调器：三方合并；仅当文件级重叠时才使用 LLM 介入的冲突解决。
5. Reviewer（GPT-5.4）：阅读合并后的 diff；不能批准自己撰写的 diff；发出 approved 或路由回相关 coder 的 review_feedback。
6. Tester（Gemini 2.5 Pro）：在干净的 sandbox 中运行测试套件；发出带产物的 test_passed 或 test_failed。
7. 交接记账：每条跨角色消息都变成一个 Langfuse span，记录 payload 大小与模型。计算 token amplification = total_tokens / single_agent_baseline_tokens。
8. 注入一个明显的 bug 探针（10% 的运行），以测量 reviewer 的误批率。
9. 在 50 个 SWE-bench Pro issue 上运行；发布 pass@1、wall-clock 相对单 Agent 基线、按角色的 token 拆分、交接失败直方图。

评估标准：

| 权重 | 标准 | 衡量方式 |
|:-:|---|---|
| 25 | SWE-bench Pro pass@1 | 50 个 issue 子集上的 pass@1 |
| 20 | 并行加速 | wall-clock 相对单 Agent 基线 |
| 20 | 评审质量 | 注入缺陷探针上的误批率 |
| 20 | token 效率 | 每个已解决 issue 的总 token 相对单 Agent |
| 15 | 协调工程 | 合并冲突解决、交接失败直方图 |

硬性否决：

- reviewer 可以批准自己撰写或自己提出的 diff。这是硬约束。
- 报告里没有对齐的单 Agent 基线运行。多 Agent 必须在*按美元算*上取胜，而不只是 pass@1。
- 任务板上的消息是自由格式字符串，而不是类型化的 A2A 消息。
- 合并协调器默默丢弃冲突的 diff，而不是路由回去重新规划。

拒绝规则：

- 拒绝在没有按角色预算上限（token + 美元）的情况下运行。
- 拒绝为 tester 尚未在干净 sandbox 中验证过的 PR 开单。
- 拒绝单次运行中把 coder 扩展到 8 个以上。超过这个数，协调开销就会占主导。

输出：一个仓库，包含任务板 + 角色 worker、50 个 issue 的 SWE-bench Pro 运行日志、一次对齐的单 Agent 基线运行、带角色标记 span 与按角色 token 拆分的 Langfuse 仪表盘、一份注入 bug 探针报告，以及一份复盘——点名最常断掉的三个交接，以及各自因哪项消息 schema 或 prompt 改动而减少。
