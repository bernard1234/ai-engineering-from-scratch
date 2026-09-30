# Agent 可观测性：Langfuse、Phoenix、Opik

> 2026 年有三款开源 agent 可观测性平台占据主导。Langfuse（MIT）—— 每月 6M+ 安装量，tracing + prompt 管理 + evals + session 回放。Arize Phoenix（Elastic 2.0）—— 深度 agent 专用 evals、RAG 相关性、OpenInference 自动 instrument。Comet Opik（Apache 2.0）—— 自动化 prompt 优化、guardrails、LLM-judge 幻觉检测。

**Type:** Learn
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 23 (OTel GenAI)
**Time:** ~45 minutes

## 学习目标

- 说出三大开源 agent 可观测性平台及其许可证。
- 区分各自最强的领域：Langfuse（prompt 管理 + sessions）、Phoenix（RAG + 自动 instrument）、Opik（优化 + guardrails）。
- 解释为什么到 2026 年 89% 的组织报告已具备 agent 可观测性。
- 实现一个带 LLM-judge 评测的标准库 trace 到仪表盘流水线。

## 问题

OTel GenAI（第 23 课）给了你 schema。你还需要一个平台来摄取 span、运行评测、存储 prompt 版本、暴露回归。三个竞争者各自强调生命周期的不同部分。

## 概念

### Langfuse（MIT）

- 每月 6M+ SDK 安装量、19k+ GitHub stars。
- 特性：tracing、带版本管理和 playground 的 prompt 管理、评测（LLM-as-judge、用户反馈、自定义）、session 回放。
- 2025 年 6 月：此前的商业模块（LLM-as-a-judge、标注队列、prompt 实验、Playground）以 MIT 开源。
- 最强于：端到端可观测性 + 紧密的 prompt 管理闭环。

### Arize Phoenix（Elastic License 2.0）

- 更深度的 agent 专用评测：trace 聚类、异常检测、RAG 的检索相关性。
- 原生 OpenInference 自动 instrument。
- 与托管的 Arize AX 搭配用于生产。
- 没有 prompt 版本管理——定位为更广泛平台旁的漂移/行为回归工具。
- 最强于：RAG 相关性、行为漂移、异常检测。

### Comet Opik（Apache 2.0）

- 通过 A/B 实验的自动化 prompt 优化。
- Guardrails（PII 脱敏、主题约束）。
- LLM-judge 幻觉检测。
- 来自 Comet 自己的测量基准：Opik 日志 + evals 用时 23.44s vs Langfuse 327.15s（约 14 倍差距）——把厂商基准当作方向性参考。
- 最强于：优化闭环、自动化实验、guardrail 执行。

### 行业数据

据 Maxim（2026 年现场分析）：89% 的组织已具备 agent 可观测性；质量问题是首要生产障碍（32% 的受访者提到它）。

### 选择一个

| 需求 | 选择 |
|------|------|
| 带 prompt 管理的一体化 | Langfuse |
| 深度 RAG 评测 + 漂移 | Phoenix |
| 自动化优化 + guardrails | Opik |
| 开放许可、不要 ELv2 | Langfuse（MIT）或 Opik（Apache 2.0） |
| Datadog / New Relic 集成 | 任意——它们都导出 OTel |

### 这个模式在哪里会出错

- **没有评测策略。** 没有评测的 tracing 只是昂贵的日志。
- **自研的 LLM-judge 没有 grounding。** CRITIC 模式（第 05 课）适用——judge 需要外部工具做事实核查。
- **prompt 版本没有关联到 trace。** 当生产回归时，你无法二分定位到引发它的 prompt。

```figure
wb-trace-ingest
```

## Build It

`code/main.py` 实现一个标准库 trace 收集器 + LLM-judge 评测器：

- 摄取 GenAI 形态的 span。
- 按 session 分组，标记失败的运行（guardrail 触发、低置信度评测）。
- 一个脚本化 LLM-judge，按 rubric 给 agent 回复打分。
- 一个类仪表盘摘要：失败率、首要失败原因、评测分数分布。

运行它：

```
python3 code/main.py
```

输出：每个 session 的评测分数和失败分类，与 Langfuse/Phoenix/Opik 会展示的内容一致。

## Use It

- **Langfuse** 自托管或云端；通过 OTel 或它们的 SDK 接入。
- **Arize Phoenix** 自托管；自动 instrument OpenInference。
- **Comet Opik** 自托管或云端；自动化优化闭环。
- **Datadog LLM Observability** 用于已经运行 Datadog 的混合运维+ML 团队。

## Ship It

`outputs/skill-obs-platform-wiring.md` 选择一个平台，并把 trace + evals + prompt 版本接入现有 agent。

## 练习

1. 导出一周的 OTel trace 到 Langfuse 云端（免费层）。哪些 session 失败了？为什么？
2. 为你的领域写一个 LLM-judge rubric（事实正确性、语气、范围遵守）。在 50 条 trace 上测试。
3. 对比 Langfuse 的 prompt 版本管理与 Phoenix 的 trace 聚类。哪个能更快告诉你什么坏了？
4. 阅读 Opik 的 guardrail 文档。把一个 PII 脱敏 guardrail 接入你的一次 agent 运行。
5. 在你的语料上对三者做基准。忽略厂商公布的数字；自己测量。

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| Tracing | 「span 收集器」 | 摄取 OTel / SDK span；按 session 索引 |
| Prompt management | 「prompt CMS」 | 关联到 trace 的带版本 prompt |
| LLM-as-judge | 「自动化评测」 | 独立 LLM 按 rubric 给 agent 输出打分 |
| Session replay | 「trace 回放」 | 逐步回看历史运行以调试 |
| RAG relevancy | 「检索质量」 | 检索到的上下文是否匹配查询 |
| Trace clustering | 「行为分组」 | 聚类相似运行以做漂移检测 |
| Guardrail enforcement | 「日志时策略」 | 对已记录内容的 PII/毒性/范围检查 |

## 延伸阅读

- [Langfuse 文档](https://langfuse.com/) —— tracing、evals、prompt 管理
- [Arize Phoenix 文档](https://docs.arize.com/phoenix) —— 自动 instrument、漂移
- [Comet Opik](https://www.comet.com/site/products/opik/) —— 优化 + guardrails
- [OpenTelemetry GenAI 语义约定](https://opentelemetry.io/docs/specs/semconv/gen-ai/) —— 三者共同消费的 schema