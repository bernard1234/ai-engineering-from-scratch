---
name: rollout-runbook
description: 为新 LLM 模型或 prompt 模板设计 shadow → canary → A/B → 100% 的发布计划，包含五道 canary gate、感知噪声地板的阈值，以及数秒级的回滚路径。
version: 1.0.0
phase: 17
lesson: 20
tags: [rollout, canary, shadow, progressive-delivery, feature-flags, argo-rollouts, flagger, kserve]
---

给定一项候选变更（新模型、新 prompt 模板、新 router 策略）、基线生产指标与风险容忍度，产出一份发布 runbook。

产出：

1. **Shadow 计划。** 时长（24-72 小时）。记录的指标：输出、token 数、latency、refusal、error。告警条件：成本变化 >20%、输出长度变化 >30%、任何 schema 违规。
2. **Canary 推进。** 阶段（1% → 10% → 25% → 50% → 75% → 100%）。每阶段时长（30 分钟到 24 小时，视流量而定；确保每阶段有足够数据达到统计置信）。
3. **五道 gate。** 明确 latency P99、cost/request、error/refusal、output-length P99、点踩率的具体阈值。设在噪声地板之上（预期有 15% 的不可消除波动）。
4. **工具。** 指明发布控制器（Argo Rollouts、Flagger、KServe）以及用于即时回滚的 feature flag 系统。
5. **回滚路径。** 记录三个动作：翻转 flag → 还原固定 digest → 验证。目标时间：端到端 60 秒以内。
6. **是否跳过 A/B？** 给出理由。改进型变体可跳过 A/B；本质不同的变更（新行为、新成本曲线）需要 A/B。

硬性拒绝：
- 跳过 shadow mode。拒绝——成本飙升和长度回归会从离线 eval 中溜过去。
- 阈值比 15% 波动更紧。拒绝——误报会中止合法的发布。
- 回滚需要重新部署。拒绝——那不是回滚，是一份损失报告。

拒绝规则：
- 如果变更是安全关键的（例如 PII 处理变更），要求额外显式 gate：在 shadow 样本中零 PII 泄漏后才能开始 canary。
- 如果流量低于 100 请求/小时，要求延长 canary 阶段——否则 gate 噪声会淹没信号。
- 如果团队无法为五道 canary gate 提供基线指标，拒绝发布——基线是前提条件。

输出：一页纸的 runbook，包含 shadow、canary、gate、工具、回滚、A/B 姿态。最后要求一次回滚演练：首次真实部署前先演练一遍回滚。
