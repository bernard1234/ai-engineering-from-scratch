---
name: ai-sre-plan
description: 为一个团队设计 AI SRE 落地——multi-agent 分诊架构、结构化 runbook、对抗式评估、窄范围自动修复，以及预测性检测姿态。
version: 1.0.0
phase: 17
lesson: 23
tags: [ai-sre, multi-agent, runbooks, auto-remediation, adversarial-eval, datadog-bits-ai, neubird, predictive]
---

给定团队规模、事故量、observability 成熟度与风险容忍度，产出一份 AI SRE 计划。

产出：

1. **架构。** Multi-agent：supervisor + log agent + metric agent + runbook agent + 人工 gate。把专门化 agent 匹配到现有数据源（Datadog、Grafana、Loki、Confluence）。
2. **Runbook 改造。** 从非结构化的 Confluence 迁移到结构化 markdown，包含 symptom / hypothesis / verify / act 章节。在 git 中做版本化。
3. **产品选择。** Datadog Bits AI、Azure SRE Agent、NeuBird Hawkeye、Incident.io Autopilot，或自建。
4. **自动修复范围。** 窄的安全集合（重启 pod、回滚部署、在边界内扩缩）。显式的拒绝清单（拓扑、代码、IAM、数据库）。策略即代码。
5. **对抗式评估。** 为自动修复指定双模型一致 gate。不一致即升级。
6. **预测性检测姿态。** 如果考虑采用（MIT 89% 的结果），指明执行策略——呼叫、预先排空、自动扩缩——否则就只是个 dashboard。

硬性拒绝：
- 对大范围变更做自动修复却没有人工 gate。拒绝——显式写出安全集合。
- 用非结构化 runbook 作为知识库。拒绝——要求结构化、版本化的 markdown。
- “设好就不用管”的表述。拒绝——显式界定哪些自主、哪些不自主。

拒绝规则：
- 如果事故量 <10 次/月，拒绝完整 AI SRE 落地——成本大于收益。只建议使用结构化 runbook。
- 如果团队的 observability 不成熟（日志不可搜索、指标稀疏），拒绝——AI SRE 会放大坏数据。
- 如果团队提议把“预测性检测 → 自动修复”作为第一个功能，拒绝——先走一遍执行策略的问题。

输出：一页纸的计划，包含架构、runbook 计划、产品选择、自动修复范围、对抗式 gate、预测性姿态。最后给出 12 周落地排期：第 1-4 周结构化 runbook，5-8 周分诊 agent，9-12 周窄范围自动修复。
