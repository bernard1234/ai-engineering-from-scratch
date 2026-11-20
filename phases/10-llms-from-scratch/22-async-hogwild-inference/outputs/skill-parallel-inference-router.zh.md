---
name: parallel-inference-router
description: 为推理工作负载在 voting、tree-of-thought、multi-agent、Hogwild! 与 speculative decoding 策略之间做路由。
version: 1.0.0
phase: 10
lesson: 22
tags: [parallel-inference, hogwild, speculative-decoding, tree-of-thought, multi-agent, reasoning]
---

给定推理工作负载画像（每个任务的 token 预算、任务并行特征、模型家族、部署目标、延迟预算），推荐一种并行推理策略或组合。

产出：

1. 任务分类。长推理（5k+ tokens）、中等 chain-of-thought（1k-5k）、短对话（1k 以下）或分类。决定第一轮决策。
2. 并行轴。序列内（speculative decoding）与跨序列（voting、Hogwild!、multi-agent）。多数工作负载先受益于序列内轴。
3. 策略推荐。从以下中选择：仅 speculative decoding（任何超过 100 tokens 的工作负载的安全默认值）、speculative + Hogwild!（具有可并行结构的长推理）、tree-of-thought（显式的 branch-and-prune 问题）、multi-agent（角色专业化问题）、voting ensemble（高风险分类）。
4. 参数设置。对 speculative decoding：draft 家族（默认 EAGLE-3）与 `N`（Phase 10 · 15 skill）。对 Hogwild!：worker 数 N（2 到 4，很少更多）、协调 prompt 模板、单节点部署确认。
5. 组合加速比估计。若将 speculative decoding 与 Hogwild! 结合，报告相乘后的加速比（典型范围：3x spec * 1.5-2x Hogwild! = 4.5-6x）。

硬性拒绝：
- 任何低于 2000 tokens 的工作负载使用 Hogwild!。协调开销占主导。
- 在非推理模型上使用 Hogwild!（没有涌现式协调）。
- 对没有自然角色分解的问题使用 multi-agent 框架。
- 没有显式 branch-and-prune 逻辑的 tree-of-thought（否则该策略退化为线性 CoT）。
- 跨节点运行 Hogwild!（跨节点 cache 同步太慢）。

拒绝规则：
- 如果工作负载是实验性研究，把 Hogwild! 作为实验推荐，而非生产赌注。加速比依任务而定，截至 2026 年 4 月真实部署很少见。
- 如果用户要求有保证的加速，拒绝，并解释只有 speculative decoding 具备强保证性质（输出分布保持不变）。Hogwild! 是经验性的。
- 如果用户 VRAM 有限，拒绝 Hogwild! N>2——即便 cache 共享，每个 worker 也需要自己的 activation 内存。

输出：一页纸的推荐，列出任务分类、并行轴、策略、参数与组合加速比估计。结尾用一段“回滚触发条件”，点名具体的延迟或准确率指标，若 Hogwild! 在前 100 次生产请求中没有回报，就据此回退到仅 speculative decoding。
