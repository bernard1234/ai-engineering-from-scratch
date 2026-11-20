---
name: llm-security-plan
description: 产出一份 LLM 安全计划，涵盖 secrets vault、带一致性 tokenization 的 PII 脱敏、网络 egress 允许列表、审计日志保留与 zero-trust 姿态。
version: 1.0.0
phase: 17
lesson: 25
tags: [security, vault, hashicorp, aws-secrets-manager, pii, presidio, egress, audit-log, zero-trust, ci-cd-supply-chain]
---

给定监管范围（SOC 2、HIPAA、GDPR）、当前凭据状态与网络/egress 姿态，产出一份安全计划。

产出：

1. Vault 迁移。挑选 vault（HashiCorp、AWS Secrets Manager、Azure Key Vault、GCP Secret Manager）。Gateway 模式：apps → gateway → 运行时访问 vault。弃用硬编码 env 与配置文件里的凭据。
2. Secret 扫描。每次 commit 都启用 TruffleHog / GitGuardian / Gitleaks。检测到就阻止 PR。
3. 轮换策略。≤ 90 天。尽可能自动化。为 CI/CD 凭据单独轮换（更短 —— 建议 30d）。
4. PII 脱敏。实体识别（Presidio + regex）。一致性 tokenization（同值 → 同占位符）以保留语义。
5. Egress 允许列表。把 LLM 供应商域名、vector DB、vault 端点加入白名单。DNS 允许列表解析器。
6. 审计日志。仅追加、不可变。必需字段：用户、租户、prompt/响应 hash、token、成本、guardrail 触发。按框架保留（SOC 2 1y / HIPAA 6y）。
7. CI/CD 卫生。OIDC 身份联邦（不用静态云密钥）。把 CI/CD 凭据范围收窄。引用 2026 年 Vercel 供应链事件作为动机。

硬性拒绝：
- 配置文件里的静态密钥。拒绝。
- 在审计日志里存原始 prompt。拒绝 —— 只存 hash，除非监管框架明确另有要求。
- 允许 egress 到 `*` 或“互联网”。拒绝 —— 用白名单。

拒绝规则：
- 如果没有客户可接受的 vault（气隙要求），拒绝常规方案，改为设计一个带轮换的基于文件的降级方案。明确说明它安全性较低。
- 如果以“延迟”为由拒绝 PII 脱敏，拒绝 —— 延迟通常 <20 ms，而监管风险远大于此。
- 如果要求对 vault root token 采用 >90 天的轮换，拒绝 —— 它会成为入侵向量。

输出：一页纸的计划，包含 vault、扫描、轮换、脱敏、egress、审计日志、CI/CD 姿态。结尾用单一指标收尾：每月 secret 扫描命中数；目标为零。
