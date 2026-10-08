---
name: workbench-audit
description: 审计一个仓库的七个智能体工作台面，并在任何智能体工作开始前报告哪些缺失、部分缺失或健康。
version: 1.0.0
phase: 14
lesson: 31
tags: [workbench, audit, reliability, agent-engineering]
---

给定一个仓库路径和将要在其中运行的智能体产品，审计七个工作台面并产出一份就绪报告。

七个面：

1. Instructions：智能体首先读取的根文件（例如 `AGENTS.md`），简短，并把智能体路由到更深层的规则。
2. State：一个持久的、机器可读的文件，记录任务、已改动的文件、阻塞项、下一步动作。
3. Scope：每个任务一份契约，列出允许的文件、禁止的文件、验收标准、回滚计划。
4. Feedback：一个运行器，捕获 command、stdout、stderr、exit code，并把结果回馈进循环。
5. Verification：一个门，运行测试、lint、类型检查、冒烟运行，并确认验收标准。
6. Review：用不同角色的第二遍检查，构建者不能给自己的作业打分。
7. Handoff：一个工件，总结改了什么、为什么、还剩下什么，以及下一步最佳动作。

产出：

- 每个面一个分数：0 缺失、1 部分、2 健康。把每个分数绑定到一个你观察到的文件或流程。
- 按杠杆排序的三个优先级：哪个缺失面如果先补上，能消除最多的失败模式。
- 一份 `workbench_audit.json` 机器可读报告，加一份 `workbench_audit.md` 人类可读摘要。
- 针对最弱面的一个起步补丁：把分数从 0 推到 1 的最小文件改动。

硬性拒绝：

- 没有文件路径或流程引用的「健康」分数。没有证据的审计会腐坏。
- 一个合并的「agent config」面。合并面会在任务坏掉时掩盖究竟是哪个面失败了。
- 因为测试慢就跳过 verification。如果 verification 不在工作台上，构建者就是在给自己的作业打分。

拒绝规则：

- 如果仓库根本没有测试命令，拒绝 verification 分数，并把它作为阻塞性发现提出来。
- 如果仓库没有版本控制历史，拒绝 handoff 分数，并把它作为阻塞性发现提出来。
- 如果智能体产品以 root 运行或有不受限的文件访问，拒绝 scope 分数，直到定义好沙箱或写入清单。

输出结构：

```
workbench-audit/
├── workbench_audit.json
├── workbench_audit.md
├── patches/
│   └── <weakest-surface>.patch
└── README.md
```

结尾附「下一步读什么」，指向：

- 第 32 课，了解最小仓库布局。
- 第 33 课，深入了解 instructions 面。
- 第 38 课，了解验证门。
