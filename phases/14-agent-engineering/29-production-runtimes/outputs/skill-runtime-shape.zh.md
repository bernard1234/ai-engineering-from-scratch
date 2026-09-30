---
name: runtime-shape
description: 挑选一个生产运行时形态（request-response、streaming、queue、event、cron、durable）并接好可观测性。
version: 1.0.0
phase: 14
lesson: 29
tags: [production, runtime, queue, event, durable, observability]
---

给定一个任务类别（预期时长、步数、触发类型、延迟预算），挑选运行时形态。

决策：

1. < 30s，用户等待 -> **request-response**。
2. 渐进式 UX 或语音 -> **streaming**。
3. 几分钟到几小时，用户不等待 -> **queue-based**。
4. 对外部事件做出反应 -> **event-driven**。
5. 周期性日常维护 -> **cron**。
6. 上述任何一种，但重启成本高 -> 加 **durable execution**。

产出：

1. 你技术栈中的形态脚手架。
2. 可观测性：OTel GenAI spans（第 23 课），后端接好（第 24 课）。
3. 对 queue：DLQ + 重试策略 + 队列深度指标。
4. 对 event：显式的订阅者注册表 + 重放路径。
5. 对 cron：锁文件或分布式锁，防止重叠运行。
6. 对 durable：checkpointer 后端 + 恢复语义。

硬性拒绝：

- 为一个 5 分钟任务用同步 HTTP。用户挂起；worker 堆积。
- 没有 DLQ 的 queue-based。失败的作业凭空消失。
- 没有 trace 导出的后台工作。在用户抱怨之前失败不可见。
- 「没有 durable state，我们重试就行。」长时程必须 checkpoint。

拒绝规则：

- 如果产品有 SLA + 重放要求，拒绝 swarm 拓扑 + 非 durable 运行时。
- 如果任务有合规约束，拒绝没有审计轨迹的 event-driven。
- 如果用户想要没有锁的 cron，拒绝。重叠的 cron 运行最好也是重复工作，最坏则是数据损坏。

输出：运行时脚手架 + 可观测性钩子 + 带 SLA、重试策略、checkpointer 选择的 README。结尾附「下一步读什么」，指向第 23 课（OTel）、第 24 课（observability），或第 17 课（用于托管长时程的 Managed Agents）。