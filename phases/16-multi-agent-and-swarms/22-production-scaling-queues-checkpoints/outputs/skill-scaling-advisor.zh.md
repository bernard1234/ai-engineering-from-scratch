---
name: scaling-advisor
description: 为多 agent 生产系统给出 durable execution 选型建议。依据具体负载与状态保留需求，在 FastAPI + Postgres、LangGraph runtime、Temporal、Restate 与自研之间做选择。
version: 1.0.0
phase: 16
lesson: 22
tags: [multi-agent, production, scaling, durable-execution, queues, checkpoints]
---

给定一份多 agent 生产部署计划，推荐 durable execution 基底。

产出：

1. **负载画像。** 并发 agent run 数（p50、p99）。单 run 时长（秒到小时）。需要 human-in-the-loop 等待的 run 占比。部署频率。
2. **状态画像。** 单 run 状态大小（KB 到 MB）。保留需求（checkpoint 历史多少秒，或完整审计日志）。确定性：run 能否从 checkpoint 确定性重放，还是只能从日志重放？
3. **副作用画像。** 哪些副作用需要 exactly-once（支付、外部 API、邮件）？哪些能容忍 at-least-once（只读 tool）？exactly-once 需要 outbox 模式。
4. **推荐档位。**
   - 档位 1（Bedi 法则）：FastAPI + Postgres。约 100 个并发 run 以下、时长不足一小时、简单重试。
   - 档位 2：LangGraph runtime 或 Temporal。长达数小时的 run、中断/恢复、结构化重试。
   - 档位 3：自研 + outbox + event sourcing。专门需求、高吞吐、严格审计。
5. **部署模型。** 单版本还是 rainbow/canary？长时间运行的有状态负载必须用 rainbow。
6. **异步 / 线程边界。** 哪些部分是异步（LLM 调用、tool I/O），哪些是线程/进程（CPU 密集的后处理、embedding）。
7. **可观测性。** 单 run trace、super-step 审计、重试计数器。trace 存储（与 checkpoint store 分开）。

硬性否决：

- 对一个 10 并发的原型推荐 Temporal。仪式成本 > 价值。
- thread-per-job 的 LLM 调用架构。I/O 密集 + 每线程 1MB 无法扩展。
- 付费副作用没有 outbox 模式的设计。重复扣费代价高昂。
- 多小时 agent run 用单版本部署。每次推代码用户就丢状态。

拒绝规则：

- 若负载未知且未压测，推荐档位 1 加负载测试。过早优化浪费时间。
- 若用户想要 tokenized / 区块链持久化系统，说明 durable execution 引擎通常解决不了这个（自行写 event sourcing）；对 tokenized 流程建议做法律审查。
- 若团队没有 on-call 工程师，Temporal / LangGraph runtime 的维护属于配置不足；在 on-call 到位前推荐档位 1。

输出：一份两页的简讯。先用一句话给出建议（"当前负载用档位 1（FastAPI + Postgres + outbox）；当 p99 run 时长超过 10 分钟或并发 run 超过 200 时，升级到 LangGraph runtime。"），然后是上面七个部分。最后给出 90 天升级路径：要盯的指标、升级阈值、runbook 纲要。
