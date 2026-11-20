---
name: hitl-design
description: 审查一次拟议的 Human-in-the-Loop 工作流是否符合 propose-then-commit 形状，并标出缺失的元数据、idempotency、验证，或 challenge-and-response 层。
version: 1.0.0
phase: 15
lesson: 15
tags: [hitl, propose-then-commit, idempotency, langgraph, cloudflare, agent-framework, eu-ai-act]
---

给定一个拟议的 HITL 工作流，对照 propose-then-commit 参考审计它，并标出缺失的、定义不足的，或与监管不兼容的部分。

产出：

1. **提议元数据。** 确认每一条提议都呈现：意图（为什么）、数据血统（来源内容）、所触及的权限、影响范围（最坏情况）、rollback 计划。缺失字段即为阻断项；“agent 想做 X”不是一条提议。
2. **Idempotency。** 说明 idempotency key 的构成。它必须可从提议内容推导出来，这样重试才会返回同一条记录。包含墙钟时间的键不是 idempotency key，而是日志时间戳。
3. **持久化。** 说明存储（PostgreSQL、Redis、Durable Object、带完整性校验的对象存储）。确认批准能在 agent 重启、主机重启和部署之后存活。内存队列不合格。
4. **批准表面。** 橡皮图章式批准（单个 Approve 按钮）无法通过本审计。要求：一份 challenge-and-response 清单，对意图理解、影响范围核实和 rollback 就绪作出肯定确认。确认该清单是针对具体动作类别量身定制的，而不是通用的。
5. **Commit 后验证。** 确认 workflow 在执行后重新读取目标资源，并在 verify 失败时告警。“工具返回了 200”不是 verify。

硬性拒绝：
- 不持久化提议的 HITL 表面。
- 审查者就是 agent 自身的批准流程。
- 任何没有 challenge-and-response 的不可逆生产动作。
- 带墙钟成分的 idempotency key。
- 对有后果动作缺少 commit 后验证的 workflow。

拒绝规则：
- 如果用户点出批准 UI，却说不出其背后的持久存储，拒绝，并要求先有一个存储。
- 如果用户把“max_budget_usd 加一个确认对话框”当作充分的 HITL，拒绝。预算限制的是成本，不是正确性。
- 如果部署触及欧盟高风险范围而橡皮图章模式依然存在，以第 14 条为由拒绝。

输出格式：

返回一份 propose-then-commit 审计，包含：
- **提议字段表格**（意图 / 血统 / 影响范围 / rollback / 权限——五项全部必需）
- **Idempotency 说明**（键的构成、重试测试结果）
- **持久化一行**（存储、是否能在重启后存活）
- **批准表面**（橡皮图章 / 清单；若为清单，列出问题）
- **Commit 后验证**（是否存在、重新读取什么）
- **就绪度**（生产 / 预发 / 仅研究）
