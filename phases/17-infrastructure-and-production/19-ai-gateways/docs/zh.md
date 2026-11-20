# AI Gateways——LiteLLM、Portkey、Kong AI Gateway、Bifrost

> gateway 坐落在你的应用与模型 provider 之间。核心特性是 provider routing、fallback、retries、rate limiting、secret references、observability、guardrails。2026 年的市场格局：**LiteLLM** 是 MIT 开源的 OSS，支持 100+ provider、兼容 OpenAI，但在约 2000 RPS 附近就撑不住（8 GB 内存，公开 benchmark 中出现级联故障）；最适合 Python、<500 RPS、开发/原型阶段。**Portkey** 定位为 control plane（guardrails、PII redaction、jailbreak detection、audit trails），2026 年 3 月转为 Apache 2.0 开源，20-40 ms 延迟开销，生产版 $49/月。**Kong AI Gateway** 构建在 Kong Gateway 之上——Kong 自己在同样的 12 核 CPU 上做的 benchmark：比 Portkey 快 228%，比 LiteLLM 快 859%；定价 $100/model/月（Plus 档最多 5 个）；如果你已经在用 Kong，适合企业采用。**Bifrost**（Maxim AI）——自动重试并可配置 backoff，OpenAI 返回 429 时 fallback 到 Anthropic。**Cloudflare / Vercel AI Gateways**——托管、零运维、基础重试。data residency 决定了是否 self-host；Portkey 和 Kong 处于中间地带，提供 OSS + 可选托管。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级 gateway-routing 模拟器)
**Prerequisites:** 第 17 阶段，第 01 课（Managed LLM Platforms）、第 16 课（Model Routing）
**Time:** ~60 分钟

## Learning Objectives

- 列举 gateway 的六项核心特性（routing、fallback、retries、rate limits、secrets、observability、guardrails）。
- 把 2026 年的四款 gateway（LiteLLM、Portkey、Kong AI、Bifrost）映射到规模上限与使用场景。
- 引用 Kong benchmark（相对 Portkey 228%，相对 LiteLLM 859%），并解释它为何对 >500 RPS 的场景至关重要。
- 在给定 data residency 和运维预算下，选择 self-hosted 还是 managed。

## 问题场景

你的产品要调用 OpenAI、Anthropic 和一个 self-hosted 的 Llama。每个 provider 的 SDK、错误模型、限流和鉴权方案都不一样。你希望有 failover（OpenAI 429 了就试 Anthropic）、单一的凭据存储、统一的 observability，以及按租户的 rate limit。

在应用层重新造这套东西，会让每个服务都耦合到每个 provider。gateway 层把它收敛到一个进程、一个 API（通常是 OpenAI 兼容的），再由它扇出到各个 provider。

## 核心概念

### 六项核心特性

1. **Provider routing**——把 OpenAI、Anthropic、Gemini、self-hosted 等藏在一个 API 后面。
2. **Fallback**——遇到 429、5xx 或质量失败时改到别处重试。
3. **Retries**——指数 backoff，限制尝试次数。
4. **Rate limits**——按租户、按键、按模型。
5. **Secret references**——运行时从 vault 拉取凭据（绝不放在应用里）。
6. **Observability**——OTel + GenAI 属性（第 17 阶段 · 13）+ 成本归因。
7. **Guardrails**——PII redaction、jailbreak detection、允许话题过滤。

### LiteLLM——MIT 开源，Python

- 100+ provider，兼容 OpenAI，支持 router 配置、fallback、基础 observability。
- 在 Kong 的 benchmark 中约 2000 RPS 就撑不住；8 GB 内存占用，持续负载下出现级联故障。
- 最适合：Python 应用、<500 RPS、开发/预发 gateway、实验性路由。
- 成本：OSS 免费；存在云端免费档。

### Portkey——control plane 定位

- 自 2026 年 3 月起为 Apache 2.0 开源。guardrails、PII redaction、jailbreak detection、audit trails。
- 每请求 20-40 ms 延迟开销。
- 生产档 $49/月，含保留期 + SLA。
- 最适合：需要 guardrails + observability 打包方案的受监管行业。

### Kong AI Gateway——主打规模

- 构建于 Kong Gateway（成熟的 API gateway 产品，lua+OpenResty）。
- Kong 自己在 12 核等价配置上的 benchmark：比 Portkey 快 228%，比 LiteLLM 快 859%。
- 定价：$100/model/月，Plus 档最多 5 个。
- 最适合：已经在用 Kong；>1000 RPS；愿意付费授权。

### Bifrost（Maxim AI）

- 自动重试，backoff 可配置。
- OpenAI 429 时 fallback 到 Anthropic 是一条标准配方。
- 较新的入局者；商业产品。

### Cloudflare AI Gateway / Vercel AI Gateway

- 托管、零运维。基础的重试与 observability。
- 最适合：部署在 Cloudflare/Vercel 上的 edge JavaScript 应用。
- 在 guardrails 和 rate limits 上不如 Kong/Portkey。

### Self-hosted 与 managed

data residency 是决定性的驱动因素。医疗和金融默认 self-host（LiteLLM、Portkey OSS 或 Kong）。消费级产品默认 managed（Cloudflare AI Gateway）或中间层（Portkey managed）。混合方案：受监管租户用 self-hosted，其余用 managed。

### 延迟预算

- LiteLLM：典型开销 5-15 ms。
- Portkey：开销 20-40 ms。
- Kong：开销 3-8 ms。
- Cloudflare/Vercel：开销 1-3 ms（edge 优势）。

gateway 延迟会直接加到 TTFT 上。若 SLA 是 TTFT P99 < 100 ms，选 Kong 或 Cloudflare。若 P99 < 500 ms，任意一款都行。

### rate-limit 语义很重要

简单的 token-bucket 在中等规模以内够用。多租户需要 sliding-window + burst allowance + 按租户分层。LiteLLM 提供 token-bucket；Kong 提供 sliding-window；Portkey 提供分层限流。

### Gateway + observability + routing 的组合

第 17 阶段 · 13（observability）+ 16（model routing）+ 19（gateways）在生产中是同一层。选一个能同时覆盖三者的工具，或者小心地把它们串起来：多数 2026 年的部署把 Helicone（observability）或 Portkey（guardrails）与 Kong（规模）组合，分担不同角色。

### 你应该记住的数字

- LiteLLM：约 2000 RPS 时崩掉，8 GB 内存。
- Portkey：开销 20-40 ms；自 2026 年 3 月起 Apache 2.0。
- Kong：比 Portkey 快 228%，比 LiteLLM 快 859%。
- Kong 定价：$100/model/月，Plus 档最多 5 个。
- Cloudflare/Vercel：edge 开销 1-3 ms。

```figure
mx-gateway-fallback
```

## Use It

`code/main.py` 在注入 429/5xx 的情况下，模拟跨 3 个 provider 的 gateway 路由与 fallback。报告 latency、retry rate 和 fallback 命中率。

## Ship It

本课产出 `outputs/skill-gateway-picker.md`。给定规模、运维姿态、合规要求、延迟预算，选出一款 gateway。

## Exercises

1. 运行 `code/main.py`。把 fallback 配置为 OpenAI→Anthropic→self-hosted。在 5% provider 错误率下，预期命中率是多少？
2. 你的 SLA 是 TTFT P99 < 200 ms，基线为 300 ms。哪些 gateway 仍在预算内？
3. 一个医疗客户要求 self-hosted + PII redaction + audit。在 Portkey OSS 与 Kong 之间选择。
4. 比较 LiteLLM 与 Kong：团队应在多高的 RPS 上限迁移？
5. 为多租户 SaaS 设计 rate-limit 策略：free 档、trial 档、paid 档。用 token-bucket 还是 sliding-window？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Gateway | “API 中间商” | 坐落在应用与 provider 之间的进程 |
| LiteLLM | “那个 MIT 的” | Python 开源，100+ provider，2K RPS 就崩 |
| Portkey | “guardrails gateway” | control plane + observability，Apache 2.0 |
| Kong AI Gateway | “主打规模的那个” | 基于 Kong Gateway，benchmark 领先 |
| Bifrost | “Maxim 家的 gateway” | 重试 + Anthropic fallback 配方 |
| Cloudflare AI Gateway | “edge 托管” | edge 部署的托管 gateway，零运维 |
| PII redaction | “数据清洗” | 发送给模型前用正则 + NER 掩码 |
| Jailbreak detection | “prompt 注入防护” | 对用户输入跑分类器 |
| Audit trail | “合规日志” | 每次 LLM 调用的不可变记录 |
| Token-bucket | “简单限流” | 基于补充速率的 rate limiter |
| Sliding-window | “精确限流” | 按时间窗口的 rate limiter，公平性更好 |

## Further Reading

- [Kong AI Gateway Benchmark](https://konghq.com/blog/engineering/ai-gateway-benchmark-kong-ai-gateway-portkey-litellm)
- [TrueFoundry — AI Gateways 2026 Comparison](https://www.truefoundry.com/blog/a-definitive-guide-to-ai-gateways-in-2026-competitive-landscape-comparison)
- [Techsy — Top LLM Gateway Tools 2026](https://techsy.io/en/blog/best-llm-gateway-tools)
- [LiteLLM GitHub](https://github.com/BerriAI/litellm)
- [Portkey GitHub](https://github.com/Portkey-AI/gateway)
- [Kong AI Gateway docs](https://docs.konghq.com/gateway/latest/ai-gateway/)
