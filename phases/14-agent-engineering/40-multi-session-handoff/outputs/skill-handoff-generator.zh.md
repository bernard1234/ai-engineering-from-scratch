---
name: handoff-generator
description: 从 workbench 产物生成会话结束时的 handoff packet，同时产出人类可读的 Markdown 和机器可读的 JSON，对应七个标准字段。
version: 1.0.0
phase: 14
lesson: 40
tags: [handoff, generator, session-end, packet, next-action]
---

给定一个 workbench（state、verdict、review、feedback 日志、diff），产出一个接入 agent runtime 的会话结束 handoff generator。

产出：

1. `tools/generate_handoff.py`，暴露 `generate_handoff(snapshot) -> (markdown, payload)`。
2. `outputs/handoff/<session_id>/handoff.md` 和 `handoff.json`。
3. `handoff.schema.json`，覆盖七个必填字段以及 feedback 尾部格式。
4. 会话结束钩子脚本，运行 generator，并在任何字段缺失时拒绝关闭会话。
5. `docs/handoff.md`，列出七个字段、它们的来源以及裁剪策略。

硬性拒绝：

- 一份没有 `next_action` 的 handoff。伪装成 handoff 的状态报告会毒害下一个会话。
- 一个手写摘要的 generator。agent 的职责是把 workbench 留在可生成的状态。
- 一份与 JSON 不一致的 markdown packet。JSON 是源；markdown 是 JSON 的渲染。
- 一条超过 30 条的 feedback 尾部。完整日志在版本控制里；packet 必须保持小巧。

拒绝规则：

- 如果缺少 verification 报告，拒绝生成 packet。一份没有 verdict 的 handoff 只是一厢情愿。
- 如果缺少 review 报告且预期应有真人 reviewer，拒绝并先要求通过 review。
- 如果 diff 摘要为空但会话运行超过 5 分钟，在生成前把这个异常摆出来；怀疑是卡住的会话，而不是真的没做事。

输出结构：

```
<repo>/
├── outputs/handoff/<session_id>/
│   ├── handoff.md
│   └── handoff.json
├── tools/generate_handoff.py
├── handoff.schema.json
└── docs/handoff.md
```

以「接下来读什么」结尾，指向：

- 第 41 课，在一个真实风格的示例应用上做端到端练习。
- 第 42 课，把 generator 打包进 capstone 的 workbench pack。
- 第 29 课（Production Runtimes），把会话结束接入 queue、event 和 cron 触发器。