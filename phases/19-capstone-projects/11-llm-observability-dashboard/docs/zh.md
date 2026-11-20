# Capstone 11 — LLM 可观测性与评测仪表盘

> Langfuse 转向了 open-core。Arize Phoenix 发布了 2026 年的 GenAI semconv 映射。Helicone 与 Braintrust 都在按用户归因成本这件事上加倍投入。Traceloop 的 OpenLLMetry 成了事实上的 SDK 插桩方案。生产形态是：ClickHouse 存 trace，Postgres 存元数据，Next.js 做 UI，再加一小批跑在采样 trace 上的 eval 任务（DeepEval、RAGAS、LLM-judge）。自托管一个，从至少四个 SDK 家族摄取数据，并示范在五分钟内捕获一次注入的回归。

**Type:** Capstone
**Languages:** TypeScript（UI）、Python / TypeScript（摄取 + 评测）、SQL（ClickHouse）
**Prerequisites:** 第 11 阶段（LLM engineering）、第 13 阶段（tools）、第 17 阶段（infrastructure）、第 18 阶段（safety）
**Phases exercised:** P11 · P13 · P17 · P18
**Time:** 25 小时

## 问题场景

2026 年，凡是跑生产流量的 AI 团队都会在模型旁边维持一个可观测性平面。成本归因。幻觉检测。漂移监控。越狱信号。SLO 仪表盘。PII 泄露告警。开源参考实现——Langfuse、Phoenix、OpenLLMetry——都在 OpenTelemetry GenAI 语义约定上收敛为摄取 schema。现在你可以用一个 SDK 给 OpenAI、Anthropic、Google、LangChain、LlamaIndex 与 vLLM 插桩，并发出互相兼容的 span。

你要构建一个自托管仪表盘：从至少四个 SDK 家族摄取数据，在采样 trace 上跑一小批 eval 任务，检测漂移并告警。衡量门槛是：给定一次刻意注入的回归（某个 prompt 开始产出 PII），仪表盘要在五分钟内捕获并触发告警。

## 核心概念

摄取走 OTLP HTTP。SDK 产出 GenAI-semconv span：`gen_ai.system`、`gen_ai.request.model`、`gen_ai.usage.input_tokens`、`gen_ai.response.id`、`llm.prompts`、`llm.completions`。span 落入 ClickHouse 做列式分析；元数据（users、sessions、apps）落入 Postgres。

eval 以批任务形式跑在采样 trace 上。DeepEval 为 faithfulness、toxicity 与 answer relevance 打分。当 trace 携带检索上下文时，RAGAS 为检索指标打分。自定义 LLM-judge 跑领域特定检查（PII 泄露、违反策略的响应）。eval 运行会以 eval span 的形式写回同一个 ClickHouse，并链接到父 trace。

漂移检测随时间观察 embedding 空间的分布（对 prompt embedding 计算 PSI 或 KL 散度），再加上 eval 分数趋势。告警先进入 Prometheus Alertmanager，再转到 Slack / PagerDuty。UI 是 Next.js 15 加 Recharts。

## 架构

```
production apps:
  OpenAI SDK  +  Anthropic SDK  +  Google GenAI SDK
  LangChain + LlamaIndex + vLLM
       |
       v
  OpenTelemetry SDK with GenAI semconv
       |
       v  OTLP HTTP
  collector (ingest, sample, fan-out)
       |
       +-------------+-----------+
       v             v           v
   ClickHouse    Postgres    S3 archive
   (spans)       (metadata)  (raw events)
       |
       +---> eval jobs (DeepEval, RAGAS, LLM-judge)
       |     sampled or all-trace
       |     write eval spans back
       |
       +---> drift detector (PSI / KL on prompt embeddings)
       |
       +---> Prometheus metrics -> Alertmanager -> Slack / PagerDuty
       |
       v
   Next.js 15 dashboard (Recharts)
```

## 技术栈

- 摄取：OpenTelemetry SDK + GenAI 语义约定；OTLP HTTP 传输
- Collector：OpenTelemetry Collector，带 tail-sampling processor（用于成本控制）
- 存储：span 存 ClickHouse，元数据存 Postgres，原始事件归档到 S3
- 评测：DeepEval、RAGAS 0.2、Arize Phoenix evaluator pack、自定义 LLM-judge
- 漂移：每周对池化后的 prompt embedding（sentence-transformers）计算 PSI / KL
- 告警：Prometheus Alertmanager -> Slack / PagerDuty
- UI：Next.js 15 App Router + Recharts + server actions
- 开箱支持的 SDK：OpenAI、Anthropic、Google GenAI、LangChain、LlamaIndex、vLLM

```figure
ce-otel-drift
```

## Build It

1. **Collector 配置。** OpenTelemetry Collector 配 OTLP HTTP receiver，一个保留 100% 错误 trace、10% 成功 trace 的 tail-sampler，以及到 ClickHouse 与 S3 的 exporter。

2. **ClickHouse schema。** 表 `spans`，列与 GenAI semconv 对齐：`gen_ai_system`、`gen_ai_request_model`、`input_tokens`、`output_tokens`、`latency_ms`、`prompt_hash`、`trace_id`、`parent_span_id`，再加一个存长 payload 的 JSON 包。按 user_id 与 app_id 加二级索引。

3. **SDK 覆盖测试。** 用每个 SDK（OpenAI、Anthropic、Google、LangChain、LlamaIndex、vLLM）写一个小客户端应用，并挂上 OpenLLMetry 自动插桩。验证每个都产出规范 GenAI span 并落入 ClickHouse。

4. **eval 任务。** 一个定时任务读取最近 15 分钟的采样 trace，跑 DeepEval 的 faithfulness、toxicity 与 answer relevance。输出是链接到父 trace 的 eval span。

5. **自定义 LLM-judge。** 一个 PII 泄露 judge：给定一条响应，调用一个 guard LLM 为 PII 泄露的可能性打分。高分响应进入分诊队列。

6. **漂移检测。** 每周任务在本周池化的 prompt embedding 与过去 4 周基线之间计算 PSI。PSI 超过阈值则告警。

7. **仪表盘。** Next.js 15，页面包括：总览（spans/sec、cost/user、p95 latency）、trace（搜索 + 瀑布图）、eval（faithfulness 趋势、toxicity）、漂移（PSI 随时间变化）、告警。

8. **告警链路。** Prometheus exporter 读取 eval 分数聚合与 latency 分位数；Alertmanager 把 warning 路由到 Slack，把 critical 违约路由到 PagerDuty。

9. **回归探针。** 注入一个 bug：被评测的 chatbot 有 1% 的概率开始泄露假的 SSN。测量 MTTR：从 bug 部署到 Slack 告警。

## Use It

```
$ curl -X POST https://my-otel-collector/v1/traces -d @trace.json
[collector]  accepted 1 trace, 3 spans
[clickhouse] inserted 3 spans (app=chat, user=u_42)
[eval]       DeepEval faithfulness 0.82, toxicity 0.03
[drift]      weekly PSI 0.08 (below 0.2 threshold)
[ui]         live at https://obs.example.com
```

## Ship It

`outputs/skill-llm-observability.md` 是交付物。给定一个 LLM 应用，仪表盘摄取它的 trace、跑 eval、在漂移时告警，并在 Next.js 中呈现按用户的成本拆分。

| 权重 | 标准 | 衡量方式 |
|:-:|---|---|
| 25 | trace schema 覆盖 | 产出规范 GenAI span 的 SDK 家族数量（目标：6+） |
| 20 | eval 正确性 | DeepEval / RAGAS 分数相对人工标注集 |
| 20 | 仪表盘 UX | 注入回归上的 MTTR（目标低于 5 分钟） |
| 20 | 成本 / 规模 | 持续以 1k spans/sec 摄取且无积压 |
| 15 | 告警 + 漂移检测 | Prometheus/Alertmanager 链路端到端跑通 |
| **100** | | |

## Exercises

1. 为 Haystack 框架加自定义插桩。验证规范 span 带着忠实的 `gen_ai.*` 属性落入 ClickHouse。

2. 在同一批 trace 上把 DeepEval 换成 Phoenix 的 evaluator。测量两个 eval 引擎之间的分数漂移。

3. 细化漂移检测器：按 app-id 而非全局计算 PSI。展示每个 app 的漂移轨迹。

4. 增加一个“用户影响”页面：按用户的成本与按用户的失败率，配 sparkline。

5. 构建一个 tail-sampling 策略：保留 100% toxicity > 0.5 的 trace，其余按 10% 分层采样。测量由此引入的采样偏差。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| GenAI semconv | “OTel 的 LLM 属性” | 2025 年 OpenTelemetry 规范中面向 LLM span 属性的定义（system、model、tokens） |
| Tail sampling | “trace 跑完再采样” | Collector 在 trace 完成后决定保留还是丢弃（可以窥探错误） |
| PSI | “群体稳定性指标” | 比较两个分布的漂移指标；通常 > 0.2 意味着有意义的漂移 |
| LLM-judge | “用模型做评测” | 让一个 LLM 按评分细则给另一个 LLM 的输出打分（faithfulness、toxicity、PII） |
| Tail-sampling policy | “保留规则” | 决定哪些 trace 落盘、哪些丢弃的规则；错误 + 采样率 |
| Eval span | “关联的 eval trace” | 携带 eval 分数、链接到原始 LLM 调用 span 的子 span |
| Cost per user | “单位经济” | 一个时间窗口内归因到某个 user_id 的美元成本；核心产品指标 |

## Further Reading

- [Langfuse](https://github.com/langfuse/langfuse) — open-core 可观测性平台的参考实现
- [Arize Phoenix](https://github.com/Arize-ai/phoenix) — 漂移支持很强的另一个参考
- [OpenLLMetry (Traceloop)](https://github.com/traceloop/openllmetry) — 自动插桩 SDK 家族
- [OpenTelemetry GenAI 语义约定](https://opentelemetry.io/docs/specs/semconv/gen-ai/) — 摄取 schema
- [Helicone](https://www.helicone.ai) — 另一个托管式可观测性方案
- [Braintrust](https://www.braintrust.dev) — 另一个 eval 优先的平台
- [ClickHouse 文档](https://clickhouse.com/docs) — 列式 span 存储
- [DeepEval](https://github.com/confident-ai/deepeval) — evaluator 库
