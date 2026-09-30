---
name: web-desktop-harness
description: 构建一个 WebArena/OSWorld 风格的 harness，带基于执行的评测与轨迹效率指标。
version: 1.0.0
phase: 14
lesson: 20
tags: [webarena, osworld, harness, trajectory-efficiency]
---

给定一个目标应用（网页或桌面）和一列带黄金轨迹的任务，构建一个评测 harness。

产出：

1. 任务定义：`(tid, description, gold_steps, success_predicate, state_reset)`。
2. 运行器：运行 agent、捕获每个动作、记录步数 + 耗时 + 成功状态。
3. 轨迹效率指标：`agent_steps / gold_steps`。按任务和汇总分别报告。
4. 任务之间的状态重置——绝不在被其他任务污染过的状态上运行下一个任务。
5. 失败模式分类器：对每次失败，标注它是 grounding 失误（错误元素）还是规划失误（错误动作）。

硬性拒绝：

- 任务之间没有状态重置。跨任务污染会使所有分数失效。
- 只报告成功率。轨迹效率是 2026 年的标准。
- 只有截图、没有 DOM 对等的 harness。有些 agent 同时使用 DOM+vision；除非刻意约束界面，否则两者都给。

拒绝规则：

- 如果任务没有黄金轨迹，拒绝。没有它们就无法衡量效率。
- 如果应用没有固定到特定版本，拒绝。漂移会使跨运行比较失效。
- 如果 agent 有破坏性工具（删除、发布），要求使用应用的沙箱副本。

输出：`tasks.py`、`runner.py`、`failure_classifier.py`、`report.py`、`README.md`，说明重置策略、黄金轨迹来源，以及 grounding-vs-planning 的切分。结尾以「接下来读什么」指向第 21 课（computer use 模型）或第 30 课（评测驱动的开发）。
