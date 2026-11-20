---
name: durable-execution-review
description: 审查一次拟议的长时间运行 agent 部署是否具备正确的 durable execution 形态（activity、确定性、checkpoint 后端、人工输入状态、恢复时 HITL）。
version: 1.0.0
phase: 15
lesson: 12
tags: [durable-execution, workflows, checkpointing, temporal, langgraph, agents-sdk]
---

给定一次拟议的长时间运行 agent 部署（Temporal + OpenAI Agents SDK、带 PostgreSQL checkpointer 的 LangGraph、Microsoft Agent Framework、Claude Code Routines、Cloudflare Durable Objects，或自研等价物），对照 durable execution 模式审计该设计。

产出：

1. **Activity 清单。** 列出每一个 activity（LLM 调用、工具调用、HTTP 请求、文件写入）。对每一个，确认它被包裹为带 retry 策略、超时和 idempotency key 的 activity。activity 封装之外的裸 LLM 调用是一个可靠性漏洞。
2. **Workflow 确定性。** 找出 workflow 代码内部的每一处非确定性读取（墙钟、随机、外部状态）。每一处都必须注册为一个副作用 activity，使 replay 返回相同的值。隐藏的非确定性是 replay 漂移最常见的成因。
3. **Checkpoint 后端。** 指明后端（PostgreSQL、SQLite、Redis、Durable Objects）。确认它能在部署后存活。SQLite 仅限开发。Redis 需要配置 AOF 或 snapshot。Cloudflare Durable Objects 是透明的，但需要唯一键的纪律。
4. **人工输入状态。** 确认 HITL 的暂停是一等 workflow 状态，而不是轮询循环。workflow 应阻塞在一个外部信号上（批准队列、webhook、`interrupt()` 原语），该信号在批准到达时精确恢复。
5. **恢复时 HITL 策略。** 对于崩溃后的任何恢复，说明在执行下一个 activity 之前是否需要重新 HITL。否则，durable execution 加上崩溃前已授予的批准，可能在 context 已改变时重新触发一个已批准的动作。这对长程任务至关重要。

硬性拒绝：
- 在 Agent SDK 用法中，LLM 调用未被包裹为 activity。
- 无法在部署后存活的 checkpoint 后端。
- workflow 内嵌墙钟或随机值而未做 activity 包裹。
- 把人工输入建模为轮询循环而非信号。
- 长程运行（超过一小时）没有恢复时 HITL 策略。
- 运行没有在持久化之上叠加预算 kill switch（第 13 课）。

拒绝规则：
- 如果用户提议一个对副作用 activity 没有显式 idempotency 的 durable workflow，拒绝，并要求先给出 idempotency key。否则重试会双重执行。
- 如果用户无法展示一次 replay 测试（运行 workflow、中途崩溃、replay、断言没有重复副作用），拒绝，并要求在生产前完成该测试。
- 如果用户提议一次 24 小时无人值守运行且没有 HITL checkpoint，拒绝。35 分钟退化（第 12 课注释）使得即便持久化正确，这也是一个可靠性问题。

输出格式：

返回一份设计审查备忘录，包含：
- **Activity 表格**（activity、retry 策略、超时、idempotency key）
- **确定性审计**（非确定性读取及其处理方式）
- **Checkpoint 后端**（名称、是否能在部署后存活、replay 测试状态）
- **HITL 状态形状**（一等状态 / 轮询 / 缺失）
- **恢复时 HITL 策略**（明确说明，附理由）
- **就绪度**（生产 / 预发 / 仅研究）
