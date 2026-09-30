---
name: benchmark-harness
description: 为代码库构建一个 SWE-bench 风格的 harness，带 FAIL_TO_PASS / PASS_TO_PASS 门槛、污染检查与步数指标。
version: 1.0.0
phase: 14
lesson: 19
tags: [swe-bench, gaia, agentbench, harness, evaluation]
---

给定一个代码库和一列（bug、修复）对，构建一个以真实单元测试为门槛、并记录运营指标的基准 harness。

产出：

1. 每个任务的定义：`(tid, description, state_before, fail_to_pass_tests, pass_to_pass_tests, solution)`。
2. 一个运行器，应用 agent 的补丁、在沙箱中运行仓库测试套件，并记录：FTP 通过数、PTP 通过数、步数、token、墙钟时间、成本。
3. 一个污染检查：把 issue 文本与产出的补丁做模式匹配；重叠 >=30% 时标记。
4. 一个报告器，把每个任务和汇总分数以 JSON 输出，外加 P50/P75/P95 的步数和成本。
5. 一个 CI 任务，在每次 PR 上运行 harness，并在回归 >=5% 时失败。

硬性拒绝：

- 只报告单一汇总数字的 harness。要求每个任务的结果 + 分布。
- 没有沙箱就运行测试的 harness。agent 提供的补丁是不可信代码。
- 没有 PASS_TO_PASS 门槛的 harness。破坏其他测试的补丁会让产品悄然回归。

拒绝规则：

- 如果用户只要求「FAIL_TO_PASS 分数」，拒绝。加上 PASS_TO_PASS；破坏现有测试比漏掉修复更严重的回归。
- 如果测试没有固定到特定 commit，拒绝。测试的漂移会让跨运行分数无法比较。
- 如果任务与训练期间见过的 issue 文本重叠，明确标记。

输出：`tasks.py`、`harness.py`、`contamination.py`、`report.py`、`README.md`，说明沙箱、门槛和污染策略。结尾以「接下来读什么」指向第 30 课，即在 harness 之上做评测驱动的开发。
