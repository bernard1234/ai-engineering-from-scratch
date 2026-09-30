---
name: scope-contract
description: 生成带允许/禁止 glob、验收标准和回滚计划的每任务 scope contract，外加一个在每个 agent diff 上于 CI 中运行的 glob 感知 checker。
version: 1.0.0
phase: 14
lesson: 36
tags: [scope, contract, globs, diff-check, ci]
---

给定一份任务描述和 repo 布局，产出 scope contract 和一个 diff 感知 checker。

产出：

1. 任务的 `scope_contract.json`，字段：`task_id`、`goal`、`allowed_files`（glob）、`forbidden_files`（glob）、`acceptance_criteria`、`rollback_plan`、`approvals_required`。
2. `tools/scope_check.py`，接收一个 contract 路径和一个触碰文件列表，返回 `ScopeReport`，并在任何违规上非零退出。
3. CI 步骤（`.github/workflows/scope-check.yml` 或等价物），针对 merge diff 运行 checker。
4. `outputs/scope/closed/<task_id>.json` 归档约定，让 contract 随改动历史一起交付。

硬性拒绝：

- 没有 `forbidden_files` 的 contract。负空间是 contract 的一部分。
- 对代码目录列裸路径而非 glob 的 contract。重构一夜之间就废掉裸路径。
- 为空或写着「see runbook」的 `rollback_plan` 字段。写清楚。
- 列为「case by case」的审批。审批边界必须可枚举。

拒绝规则：

- 如果任务描述没有约束 repo 的某个区域，拒绝仅凭描述撰写 `allowed_files`。询问任务所在的目录。
- 如果 repo 没有测试命令，拒绝添加 `acceptance_criteria`，直到提供或 stub 一条。无法验证的 contract 是愿望。
- 如果 agent runtime 无法遵守审批边界（没有 human-in-the-loop），交付前把这个缺口摆在明面上；滑进需审批动作的 scope creep 将是主导失败。

输出结构：

```
<repo>/
├── scope_contract.json
├── outputs/scope/closed/
│   └── T-XXX.json
├── tools/
│   └── scope_check.py
└── .github/
    └── workflows/
        └── scope-check.yml
```

结尾附上「接下来读什么」，指向：

- Lesson 37，把运行过的命令连回 contract 的 runtime feedback。
- Lesson 38，消费 scope report 的 verification gate。
- Lesson 39，审计已关闭 contract 归档的 reviewer agent。