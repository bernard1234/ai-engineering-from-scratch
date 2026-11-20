# LLM Observability 技术栈选型

> 2026 年的 observability 市场分成两类。开发平台（LangSmith、Langfuse、Comet Opik）把监控与 evals、prompt 管理、session replay 打包在一起。网关/插桩工具（Helicone、SigNoz、OpenLLMetry、Phoenix）专注遥测。Langfuse 是 MIT 许可核心、OSS 平衡性很强（云版每月 5 万 events 免费）。Phoenix 是 OpenTelemetry 原生的，采用 Elastic License 2.0——非常适合漂移/RAG 可视化，但不是持久化的生产后端。Arize AX 采用零拷贝 Iceberg/Parquet 集成，声称比单体式 observability 便宜 100 倍。LangSmith 在 LangChain/LangGraph 场景领先，$39/user/mo，仅 Enterprise 支持自托管。Helicone 基于代理，15-30 分钟即可接入，每月 10 万 req 免费，但在 agent trace 上深度不足。常见的生产模式：网关（Helicone/Portkey）+ eval 平台（Phoenix/TruLens），用 OpenTelemetry 粘合。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级 trace-sampling 模拟器)
**Prerequisites:** 第 17 阶段，第 08 课（Inference Metrics），第 14 阶段（Agent Engineering）
**Time:** ~60 分钟

## Learning Objectives

- 区分开发平台（打包：evals + prompts + sessions）与网关/遥测工具（只有 traces + metrics）。
- 把六款主要工具（Langfuse、LangSmith、Phoenix、Arize AX、Helicone、Opik）映射到各自的许可证、定价与最适用场景。
- 解释 OpenTelemetry 胶水模式，让你能把一个网关工具与独立的 eval 平台组合起来。
- 指出 2026 年的成本差异点（Arize AX 的零拷贝方案 vs 单体式入库），并说明大致 100 倍的乘数。

## 问题场景

你上线了一个 LLM 功能。它能跑。但你对 prompt 失败、tool 循环、latency 回退、成本飙升或 prompt-cache 命中率毫无可见性。你 Google “LLM observability”，得到八款工具，全都声称在三个不同价位解决同一个问题。

它们解决的并不是同一个问题。LangSmith 回答“这次 LangGraph 运行为什么失败？”Phoenix 回答“我的 RAG pipeline 是否在漂移？”Helicone 回答“哪个应用在烧 token？”Langfuse 回答“我能不能把整套自托管？”不同的工具，不同的受众。

选型涉及四个维度：技术栈（LangChain？原生 SDK？多厂商？）、许可证容忍度（只要 MIT？Elastic 可以？商业授权也行？）、预算（免费额度？$100/mo？$1000/mo？）、自托管（必须？有更好？绝不？）。

## 核心概念

### 两类工具

**开发平台**把 observability 与 evals、prompt 管理、dataset 版本化、session replay 打包在一起。你跑实验，看哪个 prompt 有效，把新 prompt 对旧的胜出者做 dataset 回归。LangSmith、Langfuse、Comet Opik。

**网关/遥测工具**对推理调用做插桩——prompt、response、tokens、latency、model、cost。Helicone、SigNoz、OpenLLMetry、Phoenix。极简。可以通过 OpenTelemetry 与独立的 eval 工具组合。

### Langfuse——OSS 平衡

- 核心为 Apache / MIT 许可；通过 Docker 自托管。
- 云版免费额度：每月 5 万 events。付费：团队版 $29/mo。
- Evals、prompt 管理、traces、datasets。对开发平台的四项功能都有合理覆盖。
- 最适用：你想要 LangSmith 级的功能，但必须自托管或坚持 OSS 许可。

### Phoenix（Arize）——遥测优先，OpenTelemetry 原生

- Elastic License 2.0；自托管轻而易举。
- 在 RAG 与漂移可视化方面极其出色。embedding 空间散点图作为一等功能提供。
- 并非作为持久化的生产后端设计——主要是开发期 observability。
- 最适用：RAG pipeline 开发、漂移调试，生产环境再搭配一个独立网关。

### Arize AX——规模化打法

- 商业产品。通过 Iceberg/Parquet 做零拷贝数据湖集成。
- 声称在规模化下比单体式 observability（Datadog 级）便宜约 100 倍。算法是：你把 traces 存在自己 S3 上的 Parquet 里；Arize 直接读取。
- 最适用：每天 >10M traces、已有数据湖、想要 LLM 专属仪表盘又不想付 Datadog 的价格。

### LangSmith——LangChain/LangGraph 优先

- 商业产品，$39/user/month。仅 Enterprise 可自托管。
- 对 LangChain 与 LangGraph 技术栈是同类最佳。如果你不在其中任一上，它就没那么有吸引力。
- 最适用：坚定押注 LangChain、愿意付费的团队。

### Helicone——基于代理的最小可用方案

- 把你的 `OPENAI_API_BASE` 换成 Helicone 代理，15-30 分钟即可接入。
- MIT 许可；每月 10 万 req 免费，付费 $20/mo+。
- 包含 failover、caching、rate limits——同时充当网关。
- 在 agent / 多步 trace 上深度不足。
- 最适用：快速起步、单栈应用、需要一个组件同时提供网关 + observability。

### Opik（Comet）——OSS 开发平台

- Apache 2.0，完全 OSS。
- 功能集与 Langfuse 相似，带 Comet 血统。
- 最适用：已经在用 Comet 的 ML 团队，想在同一面板里看到 LLM observability。

### SigNoz——OpenTelemetry 优先的全栈 APM

- Apache 2.0。通过 OpenTelemetry 既能处理通用 APM，也能处理 LLM。
- 最适用：跨服务与 LLM 调用的统一 observability。

### 胶水：OpenTelemetry + GenAI 语义约定

OpenTelemetry 于 2025 年末发布了 GenAI 语义约定（`gen_ai.system`、`gen_ai.request.model`、`gen_ai.usage.input_tokens`）。能消费 OTel 的工具可以互操作。正在形成的生产模式：

1. 在每次 LLM 调用时按 GenAI 约定发出 OTel。
2. 路由到网关（Helicone / Portkey）处理日常使用。
3. 双投到 eval 平台（Phoenix / Langfuse）处理回归。
4. 归档到数据湖（Iceberg），供 Arize AX 或 DuckDB 做长期分析。

### 陷阱：在错误的层做插桩

在 agent 框架内部插桩（例如加 LangSmith traces）会让你与该框架耦合。在 HTTP/OpenAI-SDK 层插桩（通过 OpenLLMetry 或你的网关）是可移植的。

### 采样——你不可能全都保留

每天 >1M 请求时，全量 trace 保留的成本比 LLM 调用本身还高。按规则采样：100% errors、100% 高成本、5% 成功。聚合指标始终保留；长尾保留原始数据。

### 你该记住的数字

- Langfuse 云免费额度：每月 5 万 events。
- LangSmith：$39/user/month。
- Helicone 免费：每月 10 万 req。
- Arize AX 宣称：规模化下比单体式便宜约 100 倍。
- OpenTelemetry GenAI 约定：2025 年落地，2026 年广泛采用。

```figure
i4-otel-glue
```

## Use It

`code/main.py` 模拟一天 100 万条 trace，横跨不同保留策略（100% 入库、采样、采样 + errors）。报告存储成本，以及每种策略下丢失了什么。

## Ship It

本课产出 `outputs/skill-observability-stack.md`。给定技术栈、规模、预算、许可证立场，挑选工具。

## Exercises

1. 你的团队在 LangChain 上，想要 OSS 自托管的 observability。在 Langfuse 与 Opik 之间选一个并给出理由。
2. 每天 500 万 traces，Datadog 报价 $150K/month，为 Arize AX 计算盈亏平衡点。
3. 设计一套 OpenTelemetry GenAI 属性集，作为你组织规范要求每次 LLM 调用必须携带的属性。
4. 论证单靠 Phoenix 是否足以支撑生产。它在什么时候不够用？
5. Helicone 有 20ms 的代理开销。P99 TTFT 为 300 ms 时，这可以接受吗？如果 SLA 是 100 ms 呢？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| OpenLLMetry | “LLM 的 OTel” | 面向 LLM 的开源 OpenTelemetry 插桩 |
| GenAI conventions | “OTel 属性” | LLM 调用的标准 OTel 属性名 |
| LangSmith | “LangChain observability” | 与 LangChain 生态捆绑的商业平台 |
| Langfuse | “OSS 版 LangSmith” | MIT 许可、功能集相似的 OSS |
| Phoenix | “Arize 开发工具” | OpenTelemetry 原生的开发/eval 平台 |
| Arize AX | “规模化 observability” | 商业零拷贝 Iceberg/Parquet observability |
| Helicone | “代理式 observability” | 收集 LLM 遥测并提供网关功能的 HTTP 代理 |
| Opik | “Comet LLM” | Comet 出品的 Apache 2.0 OSS 开发平台 |
| Session replay | “trace 重放” | 连同 tool 调用一起重放完整的 agent session |
| Eval | “离线测试” | 在带标注的 dataset 上跑候选 model/prompt |

## Further Reading

- [SigNoz — Top LLM Observability Tools 2026](https://signoz.io/comparisons/llm-observability-tools/)
- [Langfuse — Arize AX Alternative analysis](https://langfuse.com/faq/all/best-phoenix-arize-alternatives)
- [PremAI — Setting Up Langfuse, LangSmith, Helicone, Phoenix](https://blog.premai.io/llm-observability-setting-up-langfuse-langsmith-helicone-phoenix/)
- [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- [Arize Phoenix docs](https://docs.arize.com/phoenix)
- [Helicone docs](https://docs.helicone.ai/)
