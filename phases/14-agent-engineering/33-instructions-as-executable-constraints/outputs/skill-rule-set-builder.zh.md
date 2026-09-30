---
name: rule-set-builder
description: 访谈一位项目负责人，把他们现有的散文式指令归类进五个可操作类别，并产出一个带版本的 agent-rules.md 加一个 Python checker stub。
version: 1.0.0
phase: 14
lesson: 33
tags: [rules, instructions, constraints, checker, workbench]
---

给定一个 repo 和任何现有的散文式指令（`AGENTS.md`、`CONTRIBUTING.md`、onboarding 文档），产出一个 workbench 能执行的五类 rule set。

五个类别：

1. `startup` — 开始工作前什么必须为真。
2. `forbidden` — 什么永远不能发生。
3. `definition_of_done` — 什么证明任务已完成。
4. `uncertainty` — 不确定时 agent 做什么。
5. `approval` — 什么需要人工签字。

产出：

1. `docs/agent-rules.md`，每条规则一个 `##` 标题。每条规则带 `category`、`check` 和一行描述。
2. `tools/rule_checker.py`，带一个 `RuleChecker` 类，每个 `check` 暴露一个方法。每个方法接收一个 `TurnTrace` dataclass 并返回 `bool`。
3. `tools/rule_report.py` runner，加载规则、对 trace 运行 checker、产出 `rule_report.json`。
4. 一份迁移说明文件：哪些散文行变成了哪条规则，哪些作为愿望式被丢弃，为什么。

硬性拒绝：

- 没有 `check` 字段的规则。纯愿望式规则属于 onboarding 文档，不属于 workbench 的 rule set。
- 一条单独的「小心点」规则。指定一个类别和一个 check，否则删除它。
- 需要 LLM 调用的 check。规则 check 必须确定且便宜，以便每一 turn 都能运行。
- 超过 200 行的规则文件。按类别拆成 `agent-rules.{startup,forbidden,done,uncertainty,approval}.md` 并从父索引路由。

拒绝规则：

- 如果 agent 产品无法提供 `TurnTrace`（没有 instrumentation），在至少记录 `read_state_file`、`edited_files` 和 `tests_exit_code` 之前拒绝接线 checker。
- 如果现有指令大多是愿望式的（>50%），在产出规则前把这个发现摆在明面上。rule set 会显得单薄；那是正确的。
- 如果某条规则是因为过去单起事故而加，附上 incident id，以便未来的 review 决定它是否仍需要。

输出结构：

```
<repo>/
├── docs/
│   └── agent-rules.md
├── tools/
│   ├── rule_checker.py
│   └── rule_report.py
└── docs/migration-notes.md
```

结尾附上「接下来读什么」，指向：

- Lesson 36，针对每任务、扩展 forbidden 类别的 scope contract。
- Lesson 38，消费 rule report 的 verification gate。
- Lesson 39，给规则合规打分的 reviewer agent。