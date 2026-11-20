---
name: gpu-autoscaler-plan
description: 为基于 Kubernetes 的 LLM serving 集群设计三层 GPU autoscaling 计划（Karpenter + KAI Scheduler + 应用信号）。诊断 DCGM_FI_DEV_GPU_UTIL 陷阱与部分分配失败。
version: 1.0.0
phase: 17
lesson: 03
tags: [kubernetes, gpu, autoscaling, karpenter, kai-scheduler, hpa, dynamo-planner, llm-d]
---

给定集群拓扑（节点、GPU 类型、NVLink 域）、负载形态（TP/PP 配置、平均并发、突发系数）和 SLO（TTFT P99、goodput），产出一份三层 autoscaling 计划。

产出：

1. 第 1 层 —— Karpenter NodePool。指定 `instance-type`、`capacity-type`（on-demand / spot / reserved）、`consolidationPolicy`（GPU 池必须是 `WhenEmpty` 配 `consolidateAfter: 1h`）、排除非 GPU 负载的 taint，以及供 KAI Scheduler 选择的 label。
2. 第 2 层 —— KAI Scheduler 策略。说明是否需要 gang scheduling（TP/PP > 1 时需要）。定义拓扑约束（NVLink 域、机架、zone）。指定生产与训练租户的队列层级和抢占规则。
3. 第 3 层 —— 应用 autoscaler。选择信号：prefill 受限负载用队列深度，decode 受限用 KV cache 利用率，混合用综合 goodput。禁用 `DCGM_FI_DEV_GPU_UTIL` 并解释原因。
4. 分离式拆分。若使用第 17 阶段 · 17 的分离式 prefill/decode，指定独立的 HPA——prefill 池用队列深度信号，decode 池用 KV 利用率信号。
5. warm pool 规模。基于 P99 TTFT 约束和实测 cold start 时间（节点供给 + 模型加载），给出 SLO 关键路径的最小就绪副本数。
6. 监控。上 dashboard 的指标：每副本队列深度、每副本 KV 利用率、节点供给等待时间、gang scheduling 推迟次数、Karpenter consolidation 事件。

硬性拒绝：
- 基于 `DCGM_FI_DEV_GPU_UTIL` 推荐 HPA。拒绝，并点明队列深度 + KV 利用率才是正确信号。
- 给 GPU 池保留 `consolidationPolicy: WhenEmptyOrUnderutilized`。拒绝，并指出运行中作业被驱逐的风险。
- 对 TP/PP 负载忽略 gang scheduling。拒绝——部分分配是烧钱的反模式。

拒绝规则：
- 若集群只有一种 GPU 类型和一个节点，拒绝提出 Karpenter——客户需要先上托管 serverless（第 17 阶段 · 02）。
- 若运维要求“按 GPU 内存扩缩”，拒绝——vLLM 会预分配到 `--gpu-memory-utilization`；即使只有一个请求，内存也停在 90% 附近。
- 若以复杂度为由对 TP-8 负载拒绝 gang scheduling，拒绝为该计划背书——单 pod 落在 8 块分散的 GPU 上会原子性失败。

输出：一份单页计划，包含 Karpenter YAML 片段、KAI Scheduler 配置片段、HPA/自定义 autoscaler 的信号选择、一个 warm pool 数值，以及五个 dashboard 指标。结尾给出一个 kill-switch：若 P99 TTFT 越界，回滚到上一个已知良好的 autoscaler 状态。
