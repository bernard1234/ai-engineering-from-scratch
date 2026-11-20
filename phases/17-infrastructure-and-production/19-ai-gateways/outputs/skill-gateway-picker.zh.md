---
name: gateway-picker
description: 给定规模、延迟预算、合规要求、运维姿态与价格容忍度，选择一款 AI gateway（LiteLLM、Portkey、Kong AI、Cloudflare/Vercel）。
version: 1.0.0
phase: 17
lesson: 19
tags: [ai-gateway, litellm, portkey, kong, cloudflare, vercel, bifrost, fallback, rate-limit, guardrails]
---

给定 RPS（当前与未来 12 个月预测）、延迟预算、合规（是否必须 self-host）、guardrails 需求（PII redaction、jailbreak detection、audit）以及价格容忍度，产出一份 gateway 推荐。

产出：

1. **主 gateway。** 指明工具名称。用 RPS 上限、开销和特性契合度来论证。
2. **fallback 链。** 三个 provider 按顺序；OpenAI → Anthropic → self-hosted 是标准配方。计算预期可用性。
3. **rate-limit 策略。** >500 RPS 推荐 sliding-window；否则 token-bucket 可接受。按租户分层。
4. **Guardrails。** 若需要 PII/jailbreak，选 Portkey；若需要规模 + guardrails，选 Kong；LiteLLM 仅限 dev 层。
5. **observability 交接。** 指向第 17 阶段 · 13 的选择；确认 OTel GenAI 约定能贯通。
6. **迁移。** 若从应用层集成迁移，分阶段推进（gateway 上 1% canary，成功后再扩大）。

硬性拒绝：
- LiteLLM 用于 >2000 RPS。拒绝——Kong benchmark 显示会出现级联故障；先迁移。
- Portkey 用于 TTFT P99 < 100 ms 的 SLA。拒绝——30 ms 开销吃掉太多预算。
- Cloudflare AI Gateway 用于受监管的 on-prem 客户。拒绝——仅托管；无法 self-host。

拒绝规则：
- 如果规模不确定性很大（当前 100 RPS，计划 6 个月内到 2K+），在承诺使用 LiteLLM 前必须提供迁移计划。
- 如果合规要求 SOC 2 Type II，而所选 gateway 是纯 OSS、没有托管 SLA，要求客户自有的 SOC 2 认证。
- 如果团队没有 Kubernetes 却选择 self-host Kong，拒绝——建议改用托管 Kong 或 Portkey managed。

输出：一页纸的决策，包含 gateway、fallback 链、rate-limit 策略、guardrail 姿态、observability 流向、迁移计划。最后给出一个指标：过去一小时的 gateway 延迟 P99；越界即告警。
