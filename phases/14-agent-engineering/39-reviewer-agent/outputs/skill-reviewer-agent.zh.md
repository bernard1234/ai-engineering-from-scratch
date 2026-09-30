---
name: reviewer-agent
description: 搭建一个 reviewer agent 角色，带五维 rubric，读取 builder 的产物、生成结构化的 review report，并让人类审查从写好的页面开始，而非从空白开始。
version: 1.0.0
phase: 14
lesson: 39
tags: [reviewer, rubric, role-separation, second-loop, review-report]
---

给定一个已经在产出 workbench artifact 的 builder agent，搭建一个读取它们并写结构化 report 的 reviewer。

产出：

1. `agents/reviewer.md`，含 reviewer 的 system prompt：只读访问、五维 rubric、每个分数必须引用对应 artifact 路径。
2. `tools/reviewer.py`，从 workbench 加载 `ReviewerInputs` 并对每个维度运行 LLM scorer。
3. `outputs/review/<task_id>.json`，作为规范的 review report 路径。
4. `docs/reviewer-rubric.md`，列出五个维度、每个维度回答的问题，以及 0-1-2 分的锚点描述。
5. CI 步骤，每当 builder 任务收尾时，把 review report 作为 PR 评论发布。

硬性拒绝：

- 对 diff 有写权限的 reviewer。builder 与 reviewer 之间的差距就是全部信号；把它塌缩掉会毁掉可靠性。
- 没有每个分数锚点描述的 rubric。「0 到 2 打分」而没有锚点，会塌缩成凭感觉。
- 省略引用的 review report。每个分数必须指向一个文件或 trace 条目。
- 与 builder 共用 system prompt。同一模型没问题；同一 prompt 不行。

拒绝规则：

- 如果 builder 没有产出 verification report，拒绝运行 reviewer。在值得请裁判之前，acceptance 必须先通过。
- 如果项目已收尾的任务少于三个，拒绝声称 rubric 已校准。把最初的 report 保存为 calibration set。
- 如果要求 reviewer 在最低 confidence 以下打分，拒绝并把不确定的维度上报给人类。

输出结构：

```
<repo>/
├── agents/reviewer.md
├── tools/reviewer.py
├── outputs/review/
│   └── <task_id>.json
├── docs/reviewer-rubric.md
└── .github/workflows/review.yml
```

结尾附上「接下来读什么」，指向：

- Lesson 40，了解合并 verification + review 的 handoff packet。
- Lesson 41，了解端到端演练 builder/reviewer 分离的真实风格任务。
- Lesson 05（Self-Refine 和 CRITIC），了解本课所改进的单 agent 自审基线。
