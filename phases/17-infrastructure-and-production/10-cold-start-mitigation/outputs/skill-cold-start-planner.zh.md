---
name: cold-start-planner
description: 为 serverless LLM 部署挑选并叠加冷启动缓解手段。对各个阶段（节点、镜像、权重、引擎、首次前向）做预算，并按 SLA 匹配缓解手段。
version: 1.0.0
phase: 17
lesson: 10
tags: [cold-start, serverless, bottlerocket, model-streamer, gpu-snapshot, warm-pool, serverlessllm]
---

给定模型规模、SLA（TTFT P99）、流量形态（平稳还是突发）以及预算姿态，产出冷启动缓解计划。

产出：

1. 冷启动预算。拆解原始冷启动路径（节点供给、镜像拉取、权重载入 HBM、引擎初始化、首次前向）。对所述模型规模使用 2026 年的标称秒数。
2. 层级选择。选出能把总量压到 SLA 之下的最少层数：预置镜像（L1）、模型流式加载（L2）、GPU 快照（L3）、warm pool（L4）、分级加载（L5）。针对每层所攻击的具体阶段说明理由。
3. Warm pool 规模。为主要路径给出 `min_workers`。如果 70B+ 模型的 SLA 是 TTFT P99 < 60s，无论成本如何都必须上 warm pool。
4. 成本估算。所选 warm pool 的月度 GPU 成本，以及预期的每日冷启动次数。
5. 尾部策略。新副本上的第一个用户会怎样 —— 是被排队到热副本，还是自付冷启动税？给出具体策略（例如“10s 内把首个请求路由到任意热副本；否则落入冷启动”）。
6. 失效模式。热副本在会话中途挂掉会怎样。恢复是自动的（live migration），还是下一个请求触发冷启动？

硬性拒绝：
- 提出“加个 warm pool 就行”却不计算月度成本。
- 宣称某项缓解手段却不说明它攻击哪个具体阶段（例如只说“用 Bottlerocket”，而不说它消除了 180s 的镜像拉取）。
- 忽略 GPU 快照的按 GPU 拓扑约束 —— 如果平台迁移 SKU，快照即失效。

拒绝规则：
- 如果 SLA 是全新 70B 冷启动、无 warm pool 情况下 TTFT P99 < 5s，拒绝 —— 按 2026 年的基础设施速度这在数学上不可能。
- 如果预算不允许 warm pool 而 SLA 又要求 30s 以内的冷启动，给出平台专属的解法（Modal GPU 快照、Baseten 预热门控），并拒绝在没有这些能力的其他平台上承诺该 SLA。
- 如果运营方要求突发流量 + 70B 模型 + 缩容到零，拒绝承诺 SLA —— 没有快照或 warm pool，这笔账算不通。

输出：一页计划，列出各阶段、各层、`min_workers`、月度成本、尾部策略、失效模式。最后给出唯一需要告警的指标：最近滚动一小时内的 P99 冷启动时长。
