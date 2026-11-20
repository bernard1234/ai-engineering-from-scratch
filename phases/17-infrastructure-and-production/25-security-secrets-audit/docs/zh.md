# 安全 —— Secrets、API Key 轮换、Audit Logs、Guardrails

> 通过集中式 vault（HashiCorp Vault、AWS Secrets Manager、Azure Key Vault）消除 secret 泛滥。绝不把凭据存进配置文件、VCS 里的 env 文件、电子表格。用 IAM role 取代静态密钥；CI/CD 用 OIDC。AI-gateway 模式是 2026 年的解法：apps → gateway → 模型供应商，gateway 在运行时从 vault 取凭据。在 vault 里轮换，所有应用几分钟内就会拿到新值 —— 不用重新部署，也没有 Slack 上“谁有新密钥”的消息。轮换策略 ≤90 天；每次 commit 都用 TruffleHog / GitGuardian / Gitleaks 扫描。Zero-trust：MFA、SSO、RBAC/ABAC、短生命周期 token、设备态势。PII 脱敏用实体识别在转发前遮蔽 PHI/PII；一致性 tokenization（Mesh 方法）把敏感值映射为稳定的占位符，让 LLM 保留代码/关系语义。网络 egress：把 LLM 服务放在专用 VPC/VNet 子网里，只把 `api.openai.com`、`api.anthropic.com` 等加入白名单；阻断其他所有出站。2026 年的事故诱因：Vercel 供应链攻击，通过被攻陷的 CI/CD 凭据窃取 env 变量，波及数千个客户部署。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级 PII 脱敏器 + 审计日志写入器)
**Prerequisites:** 第 17 阶段，第 19 课（AI Gateways），第 13 课（Observability）
**Time:** ~60 分钟

## Learning Objectives

- 列举四种 secret 管理的反模式（VCS 里的配置文件、硬编码 env、电子表格、静态密钥），并说出它们的替代方案。
- 解释“AI gateway 从 vault 取值”这一模式为何是 2026 年的生产标准。
- 实现一个带一致性 tokenization 的 PII 脱敏器（同值 → 同占位符），让语义得以保留。
- 说出 2026 年 Vercel 供应链事件，以及它对 CI/CD 凭据卫生的启示。

## 问题场景

一个实习生提交了带 API key 的 `.env`。他们很快删掉了。密钥已经进入 git 历史 —— GitGuardian 扫描抓到了，而你的轮换流程是“在 Slack 通知团队、更新 40 个配置文件、重新部署所有服务”。8 小时后，一半服务在线，另一半还在等部署窗口。

另有一处，用户 prompt 里写着“My SSN is 123-45-6789.”。prompt 发往 OpenAI。你有 BAA，但内部策略要求在转发前遮蔽 PII。你没做。

再有一处，你的 EKS 集群里的 LLM pod 能访问任意互联网主机。有人通过 DNS 查询把数据外泄到攻击者控制的域名。没有任何东西拦住它。

LLM 服务的安全必须同时解决这三条向量。Vault 支撑的凭据。PII 脱敏。网络 egress 过滤。审计日志。

## 核心概念

### 集中式 vault + IAM-role 取值

**Vault**：HashiCorp Vault、AWS Secrets Manager、Azure Key Vault、GCP Secret Manager。单一事实来源。

**IAM role**：app/gateway 通过其 IAM 身份认证，而不是静态密钥。Vault 在 token 生命周期内返回 secret。

**AI-gateway 模式**：gateway 在请求时从 vault 取 `OPENAI_API_KEY`。在 vault 里轮换；下一个请求就会拿到新密钥。无需重新部署。

### 轮换策略 ≤ 90 天

所有 API key、vault root token、CI/CD 凭据。尽可能自动化轮换。手动轮换要记录并跟踪。

### Secret 扫描

- **TruffleHog** —— 对 commit 做 regex + 熵检测。
- **GitGuardian** —— 商业产品，准确率高。
- **Gitleaks** —— 开源，在 CI 中运行。

每次 commit 都运行。发现新 secret 就阻止 PR。

### Zero-trust 姿态

- 所有账号强制 MFA。
- 通过 SAML/OIDC 实现 SSO。
- 细粒度访问用 RBAC（基于角色）或 ABAC（基于属性）。
- 短生命周期 token（以小时计，而非以天计）。
- 设备态势 —— 只允许带磁盘加密的公司设备。

### PII / PHI 脱敏

在 prompt 离开你的基础设施之前：

1. 实体识别（spaCy NER、Presidio、商业方案）。
2. 遮蔽匹配到的实体：`"My SSN is 123-45-6789"` → `"My SSN is [SSN_TOKEN_A3F]"`。
3. 一致性 tokenization（Mesh 方法）：同一个值映射到同一个占位符，让 LLM 保留关系。
4. 可选地为 LLM 响应做反向映射。

静态 regex 过滤器能捕获基本模式；NER 能捕获更多。两者都用。

### 输入 + 输出 Guardrails

输入：阻断已知 jailbreak、违禁话题；按用户限流。

输出：用 regex 清洗泄漏的 secret（API key 模式、拒绝语境中的 email 模式），用分类器检测策略违规。

### 网络 egress 白名单

把 LLM 服务放在专用子网：
- 白名单：`api.openai.com`、`api.anthropic.com`、vector DB 端点、vault 端点。
- 其他所有流量：丢弃。
- DNS 走仅允许列表的解析器（避免 DNS 隧道外泄）。

### 审计日志

对每次 LLM 调用记录不可变的日志，包含：
- 时间戳。
- 用户 / 租户。
- Prompt hash（出于隐私，不存原始 prompt）。
- 模型 + 版本。
- Token 数量。
- 成本。
- 响应 hash。
- 任何 guardrail 触发。

按监管要求保留（SOC 2 1 年，HIPAA 6 年）。

### 2026 年 Vercel 事件

供应链攻击：被攻陷的 CI/CD 凭据窃取 env 变量，波及数千个客户部署。教训：CI/CD 凭据等同于生产凭据。存进 vault。范围收窄。积极轮换。

### 需要记住的数字

- 轮换策略：≤ 90 天。
- 每次 commit 扫描：TruffleHog / GitGuardian / Gitleaks。
- Vercel 2026：CI/CD 凭据被攻陷 → 数千个客户 env 变量泄漏。
- 审计日志保留：SOC 2 = 1 年，HIPAA = 6 年。

```figure
i4-vault-rotation
```

## Use It

`code/main.py` 实现了一个带一致性 tokenization 的玩具级 PII 脱敏器，以及一个仅追加的审计日志。

## Ship It

本课产出 `outputs/skill-llm-security-plan.md`。给定监管范围与当前状态，规划 vault 迁移、脱敏器、egress、审计日志。

## Exercises

1. 运行 `code/main.py`。发送两条引用同一个 SSN 的 prompt。确认两者拿到相同的占位符。
2. 为一个运行在 EKS 上、调用 OpenAI + Anthropic + Weaviate 的 vLLM 部署设计网络 egress 策略。
3. 你在 git 历史里发现一个密钥（2 年前）。正确的应对是什么 —— 轮换密钥、清洗历史，还是两者都做？给出理由。
4. 你的审计日志每天增长 10 GB。设计保留分层（热 30d、温 12mo、冷 6yr）。
5. 论证为了把真实值反代回 LLM 响应（反向 tokenization）所增加的复杂性是否值得，还是让占位符保持可见更好。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Vault | “secrets 存储” | 集中式凭据管理服务 |
| IAM role | “基于身份的认证” | 应用承担的角色；返回短期凭据 |
| OIDC for CI/CD | “云签发的 token” | CI 里没有静态密钥 —— 通过 OIDC 认证身份 |
| TruffleHog / GitGuardian / Gitleaks | “secret 扫描器” | commit 时的 secret 检测 |
| RBAC / ABAC | “访问控制” | 基于角色 vs 基于属性 |
| PII scrubbing | “数据遮蔽” | 移除或 token 化敏感实体 |
| Consistent tokenization | “稳定占位符” | 每次都是同值 → 同 token |
| Mesh approach | “Mesh tokenization” | 保语义的 tokenization 模式 |
| Egress whitelist | “出站允许列表” | 只有许可域名可达 |
| Audit log | “不可变历史” | 用于合规的仅追加记录 |

## Further Reading

- [Doppler —— 高级 LLM 安全](https://www.doppler.com/blog/advanced-llm-security)
- [Portkey —— 用 secret references 管理 LLM API key](https://portkey.ai/blog/secret-references-ai-api-key-management/)
- [Datadog —— LLM Guardrails 最佳实践](https://www.datadoghq.com/blog/llm-guardrails-best-practices/)
- [JumpServer —— Secrets 管理最佳实践 2026](https://www.jumpserver.com/blog/secret-management-best-practices-2026)
- [Microsoft Presidio](https://github.com/microsoft/presidio) —— PII 检测与匿名化。
- [HashiCorp Vault 文档](https://developer.hashicorp.com/vault/docs)
