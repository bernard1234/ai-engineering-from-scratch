---
name: verification-gate
description: 生成一个确定性的 verification gate，把 scope、rule 和 feedback artifact 合并成每任务一份的 verification_report.json，外加没有绿色判定就拒绝合并的 CI 接线。
version: 1.0.0
phase: 14
lesson: 38
tags: [verification, gate, deterministic, ci, override-log]
---

给定项目的验收标准和现有 workbench artifact，产出 verification gate 和覆盖审计日志。

产出：

1. `tools/verify_agent.py`，暴露 `verify(task_id, artifacts) -> VerdictReport`。纯函数、确定性、无 LLM 调用。
2. 作为唯一真相源判定的 `outputs/verification/<task_id>.json`。
3. `tools/override.py`，把签名覆盖条目追加到 `outputs/verification/overrides.jsonl`（必须含 reason、user id、timestamp、finding code）。
4. 在 `passed: false` 上失败并内联展示 report 的 CI workflow。
5. `docs/verification.md`，列出每项检查、其严重度、其来源 artifact 和覆盖政策。

硬性拒绝：

- 调用 LLM 的检查。gate 是确定性管道；LLM 判断属于 reviewer。
- agent 无需签名条目就能走的覆盖路径。覆盖仅限人类。
- 省略其消费的 artifact 路径的 verification report。report 必须可审计。
- workflow 能静默降级的 block 级 finding。严重度在写时固定，而非读时。

拒绝规则：

- 如果项目没有验收命令，在它存在前拒绝交付 gate。一个什么都证明不了的 gate 是作秀。
- 如果 rule report 不存在，拒绝跳过规则检查；fail closed。
- 如果 feedback log 不存在，拒绝跳过验收检查；缺失日志本身就是 block。
- 如果覆盖条目不进版本控制，拒绝接线覆盖路径；脱记录的覆盖会击败 gate。

输出结构：

```
<repo>/
├── tools/
│   ├── verify_agent.py
│   └── override.py
├── outputs/verification/
│   ├── overrides.jsonl
│   └── <task_id>.json
├── docs/verification.md
└── .github/workflows/verify.yml
```

结尾附上「接下来读什么」，指向：

- Lesson 39，在绿色判定之后接手的 reviewer agent。
- Lesson 40，把判定放进 packet 的 handoff generator。
- Lesson 41，对真实风格样例应用跑 gate。