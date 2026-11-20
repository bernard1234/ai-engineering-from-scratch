# Kubernetes 上的 GPU Autoscaling —— Karpenter、KAI Scheduler、Gang Scheduling

> 三层，而不是一层。Karpenter 动态供给节点（一分钟内完成，比 Cluster Autoscaler 快 40%）。KAI Scheduler 负责 gang scheduling、拓扑感知和分层队列——它避免了 7/8 部分分配的陷阱：七个节点干等、为一个缺失的 GPU 烧钱。应用层 autoscaler（NVIDIA Dynamo Planner、llm-d Workload Variant Autoscaler）按推理专用信号扩缩——队列深度、KV cache 利用率——而不是 CPU/DCGM 占空比。经典的 HPA 陷阱是：`DCGM_FI_DEV_GPU_UTIL` 是占空比度量，100% 可能是 10 个请求，也可能是 100 个。vLLM 会预分配 KV cache 内存，因此内存永远不会触发缩容。本课教你组合这三层，并避开 Karpenter 默认的 `WhenEmptyOrUnderutilized` 策略——它会在推理进行中终止正在运行的 GPU 作业。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级队列深度 autoscaler 模拟器)
**Prerequisites:** 第 17 阶段，第 02 课（Inference Platform Economics），第 04 课（Serving Engine Internals）
**Time:** ~75 分钟

## Learning Objectives

- 画出三层 autoscaling（节点供给、gang scheduling、应用层），并点名每层使用的工具。
- 解释为什么 `DCGM_FI_DEV_GPU_UTIL` 对 vLLM 是错误的 HPA 信号，并点出两个替代（队列深度、KV cache 利用率）。
- 描述 gang scheduling 以及 KAI Scheduler 所避免的部分分配失败模式（8 个 GPU 中 7 个空闲）。
- 点出会终止运行中 GPU 作业的 Karpenter consolidation 策略（`WhenEmptyOrUnderutilized`），并说明 2026 年的安全替代。

## 问题场景

你的团队在 Kubernetes 上发布一个 LLM serving 服务。你用 `DCGM_FI_DEV_GPU_UTIL` 作为信号配了 HPA。业务时段服务利用率钉在 100%。HPA 从不扩容——它已经认为你满了。你手动加一个副本；TTFT 下降。HPA 依旧不扩。这个信号在骗你。

另一边，节点你用 Cluster Autoscaler。一个 1M token 的 prompt 在凌晨 2 点到达；集群花 3 分钟供给节点，请求超时。

再一边，你部署一个 70B 模型，需要跨 2 个节点的 8 个 GPU。集群有 7 个空闲 GPU，还有 1 个散在 3 个节点上。Cluster Autoscaler 为那 1 个缺失的 GPU 供给节点。七个节点干等 4 分钟烧钱，直到 Kubernetes 把最后一块 GPU 拉起来。

三层，三种不同的失败模式。2026 年的 GPU 感知 autoscaling 不是“打开 HPA”。它是把节点供给、gang scheduling 和应用信号 autoscaling 组合起来。

## 核心概念

### 第 1 层 —— 节点供给（Karpenter）

Karpenter 监测 pending 的 pod，并在约 45-60 秒内供给节点（对 GPU 节点，Cluster Autoscaler 通常要 90-120 秒）。它按 `NodePool` 约束动态挑选实例类型——如果你的 pod 需要 8 块 H100 而集群没有匹配的节点，Karpenter 直接供给一个，而不是扩展现有的组。

**consolidation 陷阱**：Karpenter 默认的 `consolidationPolicy: WhenEmptyOrUnderutilized` 对 GPU 池很危险。它会终止正在运行的 GPU 节点，把 pod 迁移到更便宜的合适规格实例。对推理负载，这意味着驱逐正在运行的请求，并在新节点上重新加载 70B 模型。损失是数分钟的容量，加上请求失败。

GPU 池的安全设置：

```yaml
disruption:
  consolidationPolicy: WhenEmpty
  consolidateAfter: 1h
```

让 Karpenter 在一小时后合并真正为空的节点，但绝不驱逐正在运行的作业。

### 第 2 层 —— gang scheduling（KAI Scheduler）

KAI Scheduler（项目名先是 “Karp” 后改名）负责默认 kube-scheduler 不做的事：

**Gang scheduling** —— 全有或全无地调度。一个需要 8 个 GPU 的分布式推理 pod，要么 8 个一起启动，要么一个都不启。没有它，你会掉进部分分配陷阱：8 个 pod 中 7 个启动、无限等待、烧钱。

**拓扑感知** —— 知道哪些 GPU 共享 NVLink、哪些在同一机架、哪些之间有 InfiniBand。据此放置 pod。一个 DeepSeek-V3 67B 的 tensor-parallel 负载必须留在一个 NVLink 域内；KAI Scheduler 会遵守这一点。

**分层队列** —— 多个团队带着优先级和配额竞争同一个 GPU 池。只有当优先级规则允许时，Team A 的生产负载才会被 Team B 的训练作业抢占。

KAI 作为次级调度器与 kube-scheduler 一起部署；你通过注解让负载使用它。Ray 和 vLLM production-stack 都已集成。

### 第 3 层 —— 应用层信号

**HPA 陷阱**：`DCGM_FI_DEV_GPU_UTIL` 是一个占空比指标——它度量每个采样区间内 GPU 是否在做工。100% 利用率可能是 10 个并发请求，也可能是 100 个；无论哪种 GPU 都处于忙碌。按占空比扩缩就是盲扩。

更糟的是，vLLM 及类似引擎会预分配 KV cache 内存（最高到 `--gpu-memory-utilization`）。即使只有一个请求，内存占用也停留在 90% 附近。基于内存的 HPA 从不缩容。

**2026 年的替代信号**：

- 队列深度（等待 prefill 的请求数）。
- KV cache 利用率（分配给活跃 sequence 的 block 占比）。
- 每副本的 P99 TTFT（你的 SLA 信号）。
- Goodput（每秒满足所有 SLO 的请求数）。

NVIDIA Dynamo Planner 和 llm-d Workload Variant Autoscaler 消费这些信号并扩缩副本。对 LLM serving，它们完全取代 HPA。

### 何时用哪个

| 规模决策 | 工具 |
|----------------|------|
| 增删节点 | Karpenter |
| 调度多 GPU 作业 | KAI Scheduler |
| 增删副本 | Dynamo Planner / llm-d WVA（或基于队列深度的自定义 HPA） |
| 选择 GPU 类型 | Karpenter NodePool |
| 抢占低优先级 | KAI Scheduler 队列 |

### 分离式 prefill/decode 让一切更复杂

如果你运行分离式 prefill/decode（第 17 阶段 · 17），你会有两类扩缩触发不同的 pod：prefill pod 按队列深度扩缩，decode pod 按 KV cache 压力扩缩。llm-d 把它们暴露为独立的 `Services`，各带 per-role HPA。不要把单个 HPA 放在两者前面。

### cold start 在这里同样重要

cold start 缓解（第 17 阶段 · 10）正是节点供给时间变得用户可见的地方。Karpenter 45-60 秒的预热，加上 20GB 模型加载，再加上引擎初始化，意味着一个从零开始的请求要花 2-5 分钟。对 SLO 关键路径保留一个 warm pool（`min_workers=1`），或在应用层使用 Modal 式的 checkpointing。

### 你应该记住的数字

- Karpenter 节点供给：约 45-60s，对比 Cluster Autoscaler 约 90-120s（GPU 节点）。
- KAI Scheduler 避免部分分配浪费——7/8 陷阱。
- `DCGM_FI_DEV_GPU_UTIL` 作为 HPA 信号：坏掉了；改用队列深度或 KV 利用率。
- Karpenter `WhenEmptyOrUnderutilized`：会终止运行中的 GPU 作业。推理场景用 `WhenEmpty + consolidateAfter: 1h`。

```figure
autoscaling
```

## Use It

`code/main.py` 在突发型 GPU 负载上模拟三层 autoscaler。比较朴素 HPA（占空比）、队列深度 HPA 和 KAI gang 调度扩缩。报告未满足的请求、GPU 空闲分钟数和综合评分。

## Ship It

本课产出 `outputs/skill-gpu-autoscaler-plan.md`。给定集群拓扑、负载形态和 SLO，它设计一份三层 autoscaling 计划。

## Exercises

1. 运行 `code/main.py`。在突发型负载下，朴素占空比 HPA 丢掉的请求中，有多少被队列深度 HPA 接住？差异来自哪里？
2. 为一个在 H100 SXM5 上服务 Llama 3.3 70B FP8 的集群设计 Karpenter NodePool。指定 `capacity-type`、`disruption.consolidationPolicy`、`consolidateAfter`，以及一个把非 GPU 负载挡在这些节点之外的 taint。
3. 你的团队报告部署卡在 Pending，原因是“有 GPU 可用但 pod 调度不上”。诊断——这是 Karpenter、kube-scheduler 还是 KAI Scheduler 的问题？哪些指标能确认？
4. 为分离式 prefill pod 选一个扩缩信号，为 decode pod 选另一个不同的信号。两者都要论证。
5. 计算 `WhenEmptyOrUnderutilized` consolidation 陷阱在一个 7x24 生产服务上的成本——该服务平均每天 60 次请求被丢弃事件，P99 TTFT > 10s。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Karpenter | “节点供给器” | Kubernetes 节点 autoscaler；亚分钟级供给 |
| Cluster Autoscaler | “旧版扩缩器” | Kubernetes 节点 autoscaler 的前身；更慢，基于组 |
| KAI Scheduler | “GPU 调度器” | 负责 gang + 拓扑 + 队列的次级调度器 |
| Gang scheduling | “全有或全无” | 原子地调度 N 个 pod，否则全部推迟 |
| Topology awareness | “机架感知” | 依据 NVLink/IB/机架位置放置 pod |
| `DCGM_FI_DEV_GPU_UTIL` | “GPU 利用率” | 占空比指标；不是 LLM 的扩缩信号 |
| Queue depth | “等待中的请求” | prefill 受限扩缩的正确 HPA 信号 |
| KV cache utilization | “内存压力” | decode 受限扩缩的正确 HPA 信号 |
| Consolidation | “Karpenter consolidation” | 为换更便宜的实例类型而终止节点 |
| `WhenEmpty + 1h` | “安全 consolidation” | 不驱逐运行中 GPU 作业的策略 |

## Further Reading

- [KAI Scheduler GitHub](https://github.com/kai-scheduler/KAI-Scheduler) —— 设计文档和配置示例。
- [Karpenter Disruption Controls](https://karpenter.sh/docs/concepts/disruption/) —— consolidation 策略语义与 GPU 安全默认值。
- [NVIDIA — Disaggregated LLM Inference on Kubernetes](https://developer.nvidia.com/blog/deploying-disaggregated-llm-inference-workloads-on-kubernetes/) —— Dynamo Planner 的扩缩信号。
- [Ray docs — KAI Scheduler for RayClusters](https://docs.ray.io/en/latest/cluster/kubernetes/k8s-ecosystem/kai-scheduler.html) —— Ray 集成模式。
- [AWS EKS Compute and Autoscaling Best Practices](https://docs.aws.amazon.com/eks/latest/best-practices/aiml-compute.html) —— 托管 Kubernetes 的专项指南。
- [llm-d GitHub](https://github.com/llm-d/llm-d) —— Workload Variant Autoscaler 设计。
