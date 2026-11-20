# LLM 路由层 — LiteLLM、OpenRouter、Portkey

> Provider lock-in 代价高昂。不同的 tool-calling 负载适合不同的模型。Routing 网关提供统一的 API 表面、重试、failover、成本追踪和 guardrails。2026 年有三种典型方案占据主导：LiteLLM（开源自托管）、OpenRouter（托管 SaaS）、Portkey（生产级，2026 年 3 月开源）。本课梳理决策标准，并动手实现一个基于 stdlib 的路由网关。

**Type:** Learn
**Languages:** Python（stdlib，routing + failover + 成本追踪）
**Prerequisites:** 第 13 阶段，第 02 课（function calling）、第 13 阶段，第 17 课（gateways）
**Time:** ~45 分钟

## Learning Objectives

- 区分自托管、托管和生产级三类 routing 方案。
- 实现一条 fallback 链，按既定优先级在 provider 失败时重试。
- 跨 provider 追踪每次请求的成本和 token 用量。
- 针对给定的生产约束，在 LiteLLM、OpenRouter 和 Portkey 之间做出选择。

## 问题场景

以下场景中 provider routing 很重要：

1. **成本。** Claude Sonnet 的成本是 Haiku 的 3 倍。分诊任务用 Haiku 就够；综合任务则值得上 Sonnet。按请求 route。

2. **Failover。** OpenAI 出了一小时故障，每个请求都失败。你希望自动回退到 Anthropic，而不必重新部署。

3. **延迟。** 实时聊天 UI 需要快速的首 token 时间；批量摘要器则不需要。按延迟 SLA route。

4. **合规。** 欧盟用户必须留在欧盟区域。按区域 route。

5. **实验。** 在同一负载上 A/B 两个模型。按测试分组 route。

在每处集成里手写这些逻辑既重复又繁琐。Routing 网关提供一套 OpenAI 兼容 API，其余交给它处理。

## 核心概念

### OpenAI 兼容代理形态

大家都说 OpenAI 那套 schema。Routing 网关暴露 `/v1/chat/completions`，接受 OpenAI schema，内部代理到 Anthropic / Gemini / Cohere / Ollama / 任意后端。客户端无需关心。

### 模型别名

代码里不写死某个快照 id，而是写 `our_smart_model`。网关把别名映射到真实模型。当某个 provider 发布新一代模型时，你在服务端改别名，代码一行都不用动。

### Fallback 链

```
primary: openai/gpt-4o
on 5xx: anthropic/claude-3-5-sonnet
on 5xx: google/gemini-1.5-pro
on 5xx: refuse
```

网关在配置中定义这条链。重试要计入预算，避免 fallback 级联把成本顶爆。

### 语义缓存

完全相同或近乎相同的 prompt 命中缓存，而不是打到 provider。在重复的 agent 循环中，节省可达 30% 到 60%。缓存 key 基于 embedding；近似 prompt 共享同一个缓存槽。

### Guardrails

Gateway 层的 guardrails：

- **PII 脱敏。** 发送 prompt 前做正则或基于 ML 的处理。
- **策略违规。** 拒绝含违禁内容的 prompt。
- **输出过滤。** 清洗 completion 中的泄漏。

Portkey 和 Kong 都内置了成体系的 guardrails。LiteLLM 则将其作为可选项。

### 按 key 限流

一个 API key 对应一个团队。按 key 的预算可防止某个团队吃光共享配额。大多数网关都支持这一点。

### 自托管与托管的权衡

| 因素 | LiteLLM（自托管） | OpenRouter（托管） | Portkey（生产级） |
|--------|----------------------|----------------------|----------------------|
| 代码 | 开源，Python | 托管 SaaS | 开源（2026 年 3 月）+ 托管 |
| 部署 | 部署一个 proxy | 注册即用 | 两者皆可 |
| Provider | 100+ | 300+ | 100+ |
| 计费 | 自己的 key | OpenRouter 额度 | 自己的 key |
| 可观测性 | OpenTelemetry | Dashboard | 完整 OTel + PII 脱敏 |
| 最适合 | 想要完全掌控的团队 | 快速原型验证 | 需要合规的生产环境 |

当你有 SRE 团队并希望数据主权时，LiteLLM 胜出。当你想要单一订阅且不想管基础设施时，OpenRouter 胜出。当你需要开箱即用的 guardrails 和合规能力时，Portkey 胜出。

### 成本追踪

每个请求都携带 `provider`、`model`、`input_tokens`、`output_tokens`。乘以每个模型的单 token 价格（取自网关维护的价目表）。再按用户 / 团队 / 项目聚合。

### MCP 与 routing

网关既可以 route LLM 调用，也可以 route MCP sampling 请求。当 sampling 请求的 modelPreferences 偏好某个特定模型时，网关会翻译到正确的后端。这正是 第 13 阶段，第 17 课（MCP gateway）与本课的 routing 网关有时会合并为一个服务的原因。

### Routing 策略

- **静态优先级。** 取列表第一个；出错则往下回退。
- **负载均衡。** 轮询或加权。
- **成本感知。** 选择满足延迟 / 质量要求的最便宜模型。
- **延迟感知。** 选择最近 N 分钟内最快的模型。
- **任务感知。** Prompt 分类器把编码任务分到一个模型，把摘要任务分到另一个。

```figure
tp-router-failover
```

## Use It

`code/main.py` 用约 150 行实现了一个 routing 网关：接受 OpenAI 形态的请求，翻译到各 provider 的 stub，运行优先级 fallback 链，追踪每次请求的成本，并对输入做一遍 PII 脱敏。用三个场景运行它：正常请求、主 provider 故障触发 fallback、PII 泄漏被脱敏捕获。

重点看：

- `ROUTES` 字典：alias -> 按优先级排列的具体 provider 列表。
- Fallback 循环在 5xx 时重试。
- 成本追踪器把 token 用量乘以每个模型的费率。
- PII 脱敏器在转发前擦除 SSN 形态的模式。

## Ship It

本课产出 `outputs/skill-routing-config-designer.md`。给定负载画像（延迟、成本、合规），该 skill 会选择 LiteLLM / OpenRouter / Portkey，并生成一份 routing 配置。

## Exercises

1. 运行 `code/main.py`。触发故障场景；确认 fallback 落到第二个 provider，且成本被正确归集。

2. 加入语义缓存：以 prompt 的 SHA256 作为查询 key；缓存命中时立即返回。测量重复调用节省的成本。

3. 加入一个 prompt 分类器，把 "code ..." 开头的 prompt route 到偏好智能的 alias，把 "summarize ..." 开头的 prompt route 到偏好速度的 alias。

4. 设计按团队的预算：每个团队有月度支出上限；达到上限后网关拒绝请求。选定一种执行粒度（按请求或按时间窗口）。

5. 并排阅读 LiteLLM、OpenRouter 和 Portkey 的文档。分别说出每家独有的一个特性。

## Key Terms

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|------------------------|
| Routing gateway | "LLM proxy" | 位于多个 provider 之前的一层单一 API 表面 |
| OpenAI 兼容 | "会讲 OpenAI schema" | 接受 `/v1/chat/completions` 形态，并翻译到任意后端 |
| 模型别名 | "our_smart_model" | 代码中的名字，由网关映射到具体模型 |
| Fallback 链 | "重试列表" | 失败时依次尝试的 provider 有序列表 |
| 语义缓存 | "prompt embedding 缓存" | key 是 prompt 的 embedding；近似重复共享一次缓存命中 |
| Guardrails | "输入/输出过滤器" | 脱敏 PII、拒绝策略违规 |
| 按 key 限流 | "团队预算" | 限定到某个 API key 的配额 |
| 成本追踪 | "按请求花费" | 汇总 token 用量 x 每模型价格 |
| LiteLLM | "那个开源代理" | 可自托管的 OSS routing 网关 |
| OpenRouter | "那个托管 SaaS" | 基于额度计费的托管网关 |
| Portkey | "生产级选项" | 开源 + 托管，内置 guardrails |

## Further Reading

- [LiteLLM — 文档](https://docs.litellm.ai/) — 自托管 routing 网关
- [OpenRouter — 快速开始](https://openrouter.ai/docs/quickstart) — 托管 routing SaaS
- [Portkey — 文档](https://portkey.ai/docs) — 带 guardrails 的生产级 routing
- [TrueFoundry — LiteLLM vs OpenRouter](https://www.truefoundry.com/blog/litellm-vs-openrouter) — 决策指南
- [Relayplane — 2026 年 LLM 网关对比](https://relayplane.com/blog/llm-gateway-comparison-2026) — 厂商调研
