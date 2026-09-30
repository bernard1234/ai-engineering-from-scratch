---
name: hybrid-planner
description: 构建一个混合规划器——ChatHTN 用于可证明可靠的计划，AlphaEvolve 用于带机器可校验评估器的代码搜索——并为问题挑对的那一个。
version: 1.0.0
phase: 14
lesson: 11
tags: [planning, htn, chathtn, alphaevolve, evolutionary-search]
---

给定一个问题类别（受策略约束的工作流 vs 代码优化 vs 开放式任务），挑一个规划器并产出正确的脚手架。

决策：

1. 这个问题有硬前提 / 策略 / 调度约束吗？-> HTN（ChatHTN）。
2. 这个问题有确定性的、机器可校验的适应度函数吗？-> 进化（AlphaEvolve）。
3. 两者都没有？-> 改为用 ReAct（第 01 课）或 ReWOO（第 02 课）。

对 HTN，产出：

1. `Operator` 类型，带 `preconditions`、`effects_add`、`effects_remove`。
2. `Method` 类型，带 `task`、`preconditions`、`subtasks`。
3. 一个先试方法、回退到 LLM 分解、并缓存成功 LLM 分解的规划器。
4. 一个校验步骤，拒绝引用未知算子或方法的 LLM 分解。

对进化，产出：

1. 一个候选程序的种子种群。
2. 一个返回标量适应度的确定性评估器。
3. 一个变异算子（LLM 驱动或基于规则）。
4. 一个带早停的选择循环（保留 top-k、变异、重复）。

硬拒绝：

- LLM 输出未经算子 schema 校验就直接应用的 ChatHTN。可靠性主张会失败。
- 评估器调用 LLM 裁判的 AlphaEvolve。适应度必须确定性；LLM 裁判引入的随机噪声是循环无法恢复的。
- 对开放式任务（「写一篇博客」）用两者任一。没有评估器、没有前提条件 -> 用 ReAct。

拒绝规则：

- 如果领域没有清晰的算子 schema，拒绝 ChatHTN。建议 ReWOO 或普通 ReAct。
- 如果领域没有机器可校验的适应度，拒绝 AlphaEvolve。建议 Self-Refine（第 05 课）。
- 如果用户想要「规划器 + LLM 做最终拍板」，拒绝。符号正确性与 LLM 探索之间的切分是承重的。

输出：`operators.py`、`methods.py`、`planner.py`（HTN）或 `evaluator.py`、`mutator.py`、`loop.py`（进化），加一个带决策理由的 `README.md`。结尾加「接下来读什么」，如果辩论式验证适合这个问题就指向第 25 课，如果任务归根结底是 ReWOO 形状的就指向第 02 课。