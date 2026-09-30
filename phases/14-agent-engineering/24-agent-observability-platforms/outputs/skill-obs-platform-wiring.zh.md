---
name: obs-platform-wiring
description: 选择一个可观测性平台（Langfuse、Phoenix、Opik、Datadog），并把 trace + evals + prompt 版本接入现有 agent。
version: 1.0.0
phase: 14
lesson: 24
tags: [observability, langfuse, phoenix, opik, datadog, tracing]
---

给定一个 agent 运行时和产品需求，选择一个可观测性平台并搭建接入。

决策：

1. 需要 prompt 管理 + session 回放一体 → **Langfuse**。
2. 需要深度 RAG 相关性 + 漂移/异常检测 → **Phoenix**。
3. 需要自动化 prompt 优化 + PII guardrails → **Opik**。
4. 已经运行 Datadog → **Datadog LLM Observability**（自 v1.37+ 原生映射 GenAI）。
5. 需要无 ELv2 的许可证 → **Langfuse**（MIT）或 **Opik**（Apache 2.0）；纯 OSS 分发避免 Phoenix。

产出：

1. OTel GenAI instrument（第 23 课）—— 这是共同的基座。
2. 平台专用 SDK 或 OTel exporter 配置。
3. 针对你领域的 LLM-judge rubric（事实正确性、范围、语气、拒绝质量）。
4. 关联到 trace 的 prompt 版本管理（Langfuse）或 trace 聚类配置（Phoenix）或实验定义（Opik）。
5. 已记录内容上的 guardrails：PII 脱敏、密钥擦除。
6. 仪表盘：session 健康度、失败分类、延迟分布、每 session 成本。

硬性拒绝：

- 没有 evals 就交付。只有 tracing 是昂贵的日志。
- 使用没有外部核查的自研 LLM-judge。CRITIC 模式（第 05 课）：judge 需要外部工具做事实 grounding。
- 在 span 体中存储 PII。始终外部存储 + 引用 ID。

拒绝规则：

- 如果用户要求「一个平台搞定一切」，拒绝并提供上面的决策。没有单一平台在三个维度上都占主导。
- 如果产品对每个 agent 任务没有验收标准，拒绝交付 evals。LLM-judge 需要 rubric；rubric 需要产品决策。
- 如果用户想要「不采样、全部捕获」，拒绝。trace 量随流量线性增长；规模化需要采样（head-based 或 tail-based）。

输出：`instrumentation.py`、`judge.py`、`dashboards.md`、`README.md`，说明平台选择、rubric、采样策略和事件响应。结尾以「接下来读什么」指向第 30 课（评测驱动的开发）或第 26 课（失败模式分类）。