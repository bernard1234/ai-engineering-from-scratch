---
name: eval-suite
description: 构建一个三层评估套件（静态 benchmark、自定义离线、在线生产），带 evaluator-optimizer 循环和 CI 门禁。
version: 1.0.0
phase: 14
lesson: 30
tags: [evaluation, ci, regression, benchmarks, llm-judge]
---

给定一个智能体产品，构建一个接入 CI 的三层评估套件。

产出：

1. **静态 benchmark 层**——至少一个相关 benchmark（代码用 SWE-bench Verified、工具使用用 BFCL V4、网页用 WebArena、桌面用 OSWorld、通用能力用 GAIA）。始终同时报告 +-审计后的分数。
2. **自定义离线层**——至少一个在领域特定维度（事实性、语气、scope、拒绝质量）上打分的 LLM-judge 评分标准。至少一个在智能体运行后探测实际状态的基于执行的用例。至少一个带 gold 路径的基于轨迹的用例。
3. **在线评估层**——会话回放、guardrail 触发的告警、通过 OTel GenAI spans（第 23 课）的逐步成本/延迟追踪。
4. **Evaluator-optimizer 运行器**——把智能体包进提议 / 判定 / 优化，带轮次上限。
5. **CI 门禁**——在相比基线 >=5% 回归时让构建失败。随时间追踪基线。
6. **用例映射**——Phase 14 各课中的每一条 guardrail 和每一条学到的规则都至少有一个用例。

硬性拒绝：

- 没有基线的评估套件。没有参照物你就无法检测回归。
- 在事实性任务上没有外部依据的 LLM-judge。CRITIC 模式（第 05 课）是必须的。
- 没有固定种子或快照状态的脆弱用例。误报会侵蚀团队对评估的信任。

拒绝规则：

- 如果用户想要「只有 happy path」，拒绝。每一种失败模式（第 26 课）都应该有一个用例。
- 如果用户想要「不要 CI 门禁」，对面向付费用户的产品拒绝。否则评估漂移是不可见的。
- 如果用户想要「全是 LLM-judge」，在事实性和合规任务上拒绝。那里需要基于执行或程序化的评估器。

输出：`cases/benchmarks/`、`cases/custom/`、`cases/online/`、`runner.py`、`ci_gate.py`、`README.md`，说明评分标准、基线，以及 Phase 14 映射表。结尾附「下一步读什么」，指向第 24 课（observability）、第 26 课（failure modes），或第 23 课（OTel）以了解底层基础。