---
name: rollback-rehearsal
description: 为一个拟议的长时程自主工作流设计回滚演练测试，并审计 checkpoint 后端在审计轨迹持久化方面的表现。
version: 1.0.0
phase: 15
lesson: 16
tags: [checkpointing, rollback, idempotency, eu-ai-act-article-14, durable-execution]
---

给定一个拟议的长时程自主工作流，设计一个回滚演练测试，证明 idempotency + precondition + verify + rollback 这套栈确实能端到端工作，并审计 checkpoint 后端是否达到监管可用的程度。

产出：

1. **演练脚本。** 一个具体测试：(a) 启动工作流，(b) 在提交中途让它崩溃，(c) 恢复，(d) 断言动作恰好触发一次，(e) 注入一次校验失败，(f) 断言回滚触发且状态被恢复。任何生产工作流在通过这个测试至少一次之前都不应上线。
2. **idempotency 审计。** 确认 idempotency key 由提案内容推导而来（第 15 课），且提交逻辑使用显式的执行状态（`pending` -> `executing` -> `committed`/`failed`）。在副作用之前按 idempotency key 预留/加锁，并仅在副作用通过校验之后才标记 `committed`。
3. **前置条件清单。** 列出工作流在提交时必须重新检查的每一个前置条件。检查时与使用时的时间差（time-of-check vs time-of-use）是最常见的生产 bug；前置条件必须在提交时求值，而不是在提案时。
4. **校验清单。** 对每一个有后果的动作，指出用来确认副作用确实发生的那次具体读取。“返回 200”不可接受。
5. **回滚清单。** 对每一个有后果的动作，把回滚归类为 in-band、compensating transaction 或 out-of-band 告警。No-op rollback（“这个我们撤不回来”）必须在提案中明确写出（第 15 课的元数据）。

硬性拒绝：
- 没有演练过回滚的工作流。
- 部署时会丢数据的 checkpoint 后端。
- 状态在动作执行之后才写入、而非之前的提交路径。
- 只检查工具调用返回码的“已校验”状态。
- 只在提案时运行、不在提交时运行的前置条件检查。

拒绝规则：
- 如果用户尚未在 staging 中至少跑过一次演练脚本，拒绝其生产上线。
- 如果用户拿不出 checkpoint 存储的 schema，拒绝，并要求先提供 schema 文档。监管者要的是可查询的状态。
- 如果工作流依赖内存中的 checkpoint（没有持久化），拒绝。

输出格式：

返回一份演练计划，包含：
- **测试脚本纲要**（带断言的步骤）
- **idempotency 表**（key 组成、状态写入顺序）
- **前置条件表**（检查项、求值时机、后果）
- **校验表**（动作、确认所用的读取）
- **回滚表**（动作、类型、目标状态）
- **后端证明**（存储、能否存活部署 y/n、是否可查询 y/n）
- **就绪度**（生产 / staging / 仅研究）
