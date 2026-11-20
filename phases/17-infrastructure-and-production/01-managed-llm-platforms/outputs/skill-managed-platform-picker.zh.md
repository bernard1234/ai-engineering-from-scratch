---
name: managed-platform-picker
description: 给定负载、SLA 与合规要求，选出一个托管 LLM 平台（Bedrock、Azure OpenAI、Vertex AI）并为冗余再选一个，然后产出一份 FinOps 埋点计划。
version: 1.0.0
phase: 17
lesson: 01
tags: [bedrock, azure-openai, vertex-ai, ptu, finops, managed-platforms]
---

给定一份负载画像（所需模型、每月 token 量、P50/P99 的 TTFT SLA、合规约束、现有云足迹），产出一个平台推荐。

产出：

1. 主平台。点名平台、它覆盖的具体模型，并说明按利用率该用 on-demand 还是 Provisioned Throughput Units（PTU）/ Provisioned Throughput。引用盈亏平衡的算法（PTU 约在 40-60% 持续利用率时打平）。
2. 次平台。点名双供应商最低要求下的后备平台。论证这一配对——冗余必须覆盖模型重叠（Bedrock 上的 Claude 加 Azure OpenAI 上的 GPT 是常见组合）以及区域重叠。
3. FinOps 埋点。明确第一天就要开启什么：Bedrock Application Inference Profiles、作为成本对象的 Azure 作用域加 PTU 预留、Vertex 每团队一个 project 加 BigQuery Billing Export。点名归因维度——按用户、按任务、按租户。
4. SLA 检查。把目标的 TTFT P99 与公开 benchmark 对比（Azure OpenAI PTU ≈ 50 ms P50；Bedrock on-demand ≈ 75 ms P50）。若 SLA 比 on-demand 能提供的更紧，就要求 PTU。
5. 合规检查。按需核验 BAA、SOC 2 Type II、HIPAA、EU 数据驻留。注意三者都满足基线，但保留策略与 abuse monitoring 的 opt-out 各有不同。
6. 迁移路径。点名团队本周就能做的一个可逆步骤（例如通过抽象了供应商的 AI gateway 部署；给归因 header 埋点）和一个更长期的步骤（承诺 PTU；跨区域 failover）。

硬性拒绝：
- 推荐单一平台却不点名后备平台。拒绝，并坚持双供应商最低要求。
- 在没有利用率估计的情况下选 PTU。拒绝，并索取持续利用率数据。
- 在归因被列为需求时忽略 Bedrock Application Inference Profiles——它们是最干净的原生面。

拒绝规则：
- 若负载要求 Claude、Gemini、GPT 全部作为 P0，就要点明三平台的现实（gateway 之后的 Bedrock + Vertex + Azure OpenAI），而不是假装一个平台能服务全部三者。
- 若 SLA 是 TTFT P99 < 100 ms 而预期预算撑不起 PTU，拒绝承诺该 SLA——解释 on-demand 的方差上限。
- 若客户要求“用最便宜的供应商”，拒绝——价格是多维的（token 单价 + 专属容量 + 归因开销 + 锁定成本）。

输出：一份单页决策，包含主平台、次平台、PTU 与 on-demand 的取舍、埋点清单、SLA/合规核验，以及两个迁移步骤。结尾给出一个能捕捉计划漂移的单一指标（持续利用率、PTU 浪费或归因覆盖率）。
