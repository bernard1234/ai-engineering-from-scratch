---
name: coding-scaffold-audit
description: 审计一个拟议的 coding-agent scaffold（检索、verifier 循环、sandbox、benchmark 匹配度），在把它用于生产代码改动之前先做评估。
version: 1.0.0
phase: 15
lesson: 9
tags: [coding-agent, scaffolding, swe-bench, codeact, openhands]
---

给定一个拟议的 coding-agent scaffold（SWE-agent、OpenHands、Aider、Cline、Devin、Claude Code，或一个自研实现），沿四个维度打分，并标出 benchmark 数字会在哪里高估生产质量。

产出：

1. **检索。** 描述该 scaffold 如何选择 agent 在行动前要读哪些文件。repo map、embedding 搜索、显式文件列表，还是 agent 驱动的 `grep` 调用。检索质量是那个沉默却主导可靠性的因素。
2. **Verifier 循环。** 该 scaffold 是否运行测试、读取 stack trace，并把失败反馈进下一轮？如果没有 verifier 循环，标记为缺失——在类 SWE-bench 任务上，这通常是 10 个点以上的绝对差距。
3. **Sandbox 与爆炸半径。** 动作在哪里执行？本地文件系统、临时容器、托管 VM。对于 CodeAct 式 scaffold，确认 sandbox 已加固（无 egress、无 host mount、有时间限制）。对于 JSON tool call 式 scaffold，确认 tool validator 会拒绝每一种非预期副作用。
4. **Benchmark 匹配度。** 所报告的数字（例如"80.9% on SWE-bench Verified"）实际覆盖的是什么分布？统计该 benchmark 中由 1–2 行任务构成的比例；把报告分数与同一模型在 SWE-bench Pro（10+行任务）上的分数做对比。一个靠简单长尾撑起头条数字的 scaffold，不是生产信号。

硬性拒绝：
- 任何用于高于平凡复杂度任务却没有 verifier 循环的 scaffold。
- 指向真实代码仓库、却没有 sandbox 隔离（无 Docker、无 rootless container、无 VM）的 CodeAct scaffold。
- 不披露分布（简单长尾比例、Pro 等价分数）的 benchmark 声明。
- 单个 tool 能触达任意路径且无 validator 的 tool call 式 scaffold（例如一个直接暴露给模型的原始 `shell_exec` tool）。

拒绝规则：
- 如果用户无法给出该 scaffold 在代表性内部分布上的测试套件通过率，拒绝，并要求先做小样本测量。公开 benchmark 预测的是排名顺序，而非绝对质量。
- 如果拟议的 scaffold 会未经 staging 试跑就对着生产仓库运行，拒绝，并要求先上 staging。coding agent 会重写文件；检索糟糕的 coding agent 会重写错误的文件。
- 如果用户打算仅凭 benchmark 分数（没有自己的 eval）来做 go/no-go 决策，拒绝，并要求内部 eval 数据。

输出格式：

返回一份带评分的备忘录，包含：
- **检索得分**（0–5，并描述机制）
- **Verifier 循环得分**（0–5，并说明反馈形式）
- **Sandbox 得分**（0–5，并说明隔离机制）
- **Benchmark 匹配度得分**（0–5，并给出内部分布差距）
- **部署建议**（production / staging / research only）
- **一行风险摘要**（最可能出现的首个生产故障）
