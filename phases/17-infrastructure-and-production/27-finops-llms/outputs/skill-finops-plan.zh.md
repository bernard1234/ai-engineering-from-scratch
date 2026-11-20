---
name: finops-plan
description: 设计一套 LLM FinOps 计划 —— 归因 schema（user/task/tenant + 四个 token 层）、三层执行阶梯，以及单位指标（每个已解决 / 产物的成本）。
version: 1.0.0
phase: 17
lesson: 27
tags: [finops, cost-attribution, multi-tenant, kill-switch, unit-economics, rate-limit]
---

给定产品面、租户分层、月度支出与当前归因状态，产出一份 FinOps 计划。

产出：

1. 归因 schema。在调用点打上 `user_id`、`task_id`、`route`、`tenant_id`。四个 token 层计数（prompt / tool / memory / response）。优先采用 telemetry-joiner 模式。
2. 单位指标。定义产品结果指标 —— 每工单成本、每产物成本、每 agent 任务成本、每会话成本。绑定到计费模型。
3. 执行阶梯。按租户限流（峰值的 2-3 倍）、日消费上限（合同的 1.5-3 倍）、z-score > 4 触发 kill switch。
4. 看板。前 5 个视图：今日按租户支出、按任务的结果成本、按用户分布、cache 命中率影响、模型路由拆分。
5. 叠加优化审计。检查 cache（Phase 17 · 14）、batch（Phase 17 · 15）、路由（Phase 17 · 16）、gateway（Phase 17 · 19）是否都已启用。标出缺失的杠杆。
6. 评审节奏。每周：最大支出者 + 异常。每月：按租户的 unit economics。每季度：把工作负载重新分诊为交互式/半交互/batch。

硬性拒绝：
- 在调用点没有归因就交付。拒绝 —— 事后打标签会丢失约 10-30% 的支出。
- 单桶计费。拒绝 —— 要求四个 token 层拆分。
- 没有 z-score 依据的 kill switch。拒绝 —— 在启用前要求基线统计。

拒绝规则：
- 如果产品租户数 < 10，拒绝完整的多租户执行 —— 先要求基本的按租户归因。
- 如果每结果成本未定义，拒绝看板 —— 先选定一个单位指标。
- 如果任一单一租户占总支出 > 40%，要求在计划交付前做专门的 unit-economics 评审。

输出：一页纸的计划，包含归因 schema、单位指标、执行阶梯、看板、叠加优化审计、评审节奏。结尾用单一告警收尾：日支出 vs 预测；当偏差 > 20% 时呼叫。
