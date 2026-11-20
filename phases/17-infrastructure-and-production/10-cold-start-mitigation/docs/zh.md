# Serverless LLM 的冷启动缓解

> 一个 20 GB 的模型镜像从冷到可服务，7B 要 5-10 分钟，70B 要 20 分钟以上。在真正的 serverless 世界里，这不是预热 —— 这是故障。缓解手段分五层：预置节点镜像（AWS 上的 Bottlerocket、双卷架构）、模型流式加载（NVIDIA Run:ai Model Streamer，vLLM 原生支持）、GPU 显存快照（Modal checkpoint，重启快至 10 倍）、warm pool（`min_workers=1`）、分级加载（ServerlessLLM 的 NVMe→DRAM→HBM 流水线，延迟降低 10-200 倍），以及 live migration —— 迁移输入 token（KB 级）而不是 KV cache（GB 级）。Modal 公布 2-4 秒的冷启动作为下限；Baseten 默认 5-10 秒，预热门控下可达亚秒级。本课教你如何测量、做预算，并把五层叠起来用。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级冷启动路径模拟器)
**Prerequisites:** 第 17 阶段，第 02 课（Inference Platform Economics），第 03 课（GPU Autoscaling）
**Time:** ~60 分钟

## Learning Objectives

- 列举冷启动缓解的五层，并为每层说出一个工具或模式。
- 对 70B 模型，把总冷启动时间计算为（节点供给）+（权重下载）+（权重载入 HBM）+（引擎初始化）之和。
- 解释为什么 live migration 传输的是输入 token（KB）而不是 KV cache（GB），以及代价是什么（重算）。
- 说出 warm pool 的权衡（为空闲 GPU 付费，还是接受冷启动尾部），以及 `min_workers > 0` 变为强制的 SLA 阈值。

## 问题场景

你的 serverless LLM endpoint 在夜里缩容到零。早上 8 点流量猛增。第一个请求在等待：

1. Karpenter 供给一个 GPU 节点：45-60s。
2. 容器拉取带权重的 30 GB 镜像：120-300s。
3. 引擎把权重载入 HBM：视模型规模和存储速度需 45-120s。
4. vLLM 或 TRT-LLM 初始化 CUDA graph、KV cache 池、tokenizer：10-30s。

总计：220-510s（大约 3-8 分钟）之后才返回一个 token。你的 SLA 是 2s。你上线一个 warm pool（`min_workers=1`），问题似乎消失了 —— 但现在你要 7×24 为一张空闲 GPU 付费。如果你的服务有 5 个产品、每个一个热副本，那就是每月 5 × 24 × 30 = 3,600 GPU 小时，无论有没有用户调用。

冷启动缓解要做的，就是在保持 serverless 经济性的同时，逼近常开部署的延迟。

## 核心概念

### 第 1 层 —— 预置节点镜像（Bottlerocket）

在 AWS 上，Bottlerocket 的双卷架构把操作系统与数据分离。把预拉了容器镜像的数据卷做成快照，在 `EC2NodeClass` 中引用快照 ID。新节点启动时权重已经在本地 NVMe 上 —— 第 2 步和第 3 步的一部分就消失了。与 Karpenter 原生配合。典型收益：大模型每次冷启动省 2-4 分钟。

GCP 上的等价做法：预烘焙容器层的自定义 VM 镜像。Azure 上：同样模式的托管磁盘快照。

### 第 2 层 —— 模型流式加载（Run:ai Model Streamer）

不在回答第一个请求之前加载整个文件，而是把权重逐层流式送入 GPU 显存，并在第一个 transformer block 就位后立刻开始处理。NVIDIA Run:ai Model Streamer 在 vLLM 2026 中原生提供。支持 S3、GCS 和本地 NVMe。通过把 I/O 与计算初始化重叠，大模型的权重加载时间大约减半。

### 第 3 层 —— GPU 显存快照（Modal）

Modal 在首次加载后对 GPU 状态（权重、CUDA graph、KV cache 区域）做 checkpoint。后续重启直接反序列化进 HBM —— 比重新初始化快 10 倍。这是最接近“2 秒内启动一张热 GPU”的东西。权衡：快照是按 GPU 拓扑绑定的，若 Karpenter 把你迁到不同 SKU，就需要重新做 checkpoint。

### 第 4 层 —— warm pool（min_workers=1）

最简单的缓解手段：保持一个副本始终就绪。成本是一张 GPU 7×24 的小时费率。对小模型这笔账很残酷（花 $0.85-$1.50/小时来避免 30s 冷启动），对大模型则很划算（花 $4/小时来避免 5 分钟冷启动）。warm pool 变为强制的 SLA 阈值：通常是 70B+ 模型上 TTFT P99 < 60s。

### 第 5 层 —— 分级加载（ServerlessLLM）

ServerlessLLM 把存储视为层级：NVMe（快但容量大）、DRAM（中等且可分层）、HBM（小但即时）。权重预加载到 DRAM，按需载入 HBM。论文报告冷加载相对朴素的磁盘直读 HBM 有 10-200 倍延迟降低。生产采用尚早，但已有与 vLLM 的集成。

### 第 6 层 —— live migration（附加模式）

当节点不可用（spot 抢占、节点排空）时，传统做法是冷启动另一个副本并排空请求队列。live migration 把输入 token（KB 级）迁到已加载模型的目的节点，并在目的端重算 KV cache。重算比通过网络传输 GB 级 KV cache 更便宜。适用于 disaggregated 部署。

### warm pool 的算术

对 P99 TTFT SLA 为 2s 的服务，问题不是“要不要 warm pool”，而是“多少热副本，哪些路径能拿到”。

- 高价值交互路径（实时聊天、语音 agent）：`min_workers=1-2`。
- 后台批处理路径（夜间分类）：接受缩容到零，5-10 分钟冷启动可容忍。
- 高级层级：按租户设置带独占容量的 `min_workers`。

### 先测量再优化

新节点上 70B 模型的冷启动解剖（示意）：

| 阶段 | 时间 | 缓解手段 |
|-------|------|-----------|
| 节点供给 | 50s | Bottlerocket + 预置镜像、warm pool |
| 镜像拉取 | 180s | 预置数据卷（消除） |
| 权重载入 HBM | 75s | 模型流式加载（减半）；GPU 快照（消除） |
| 引擎初始化 | 20s | 持久化 CUDA graph 缓存 |
| 首次前向 | 3s | 固有最小延迟 |
| **冷启动总计** | **328s** | |
| **缓解后总计** | **~15s** | 降低 22 倍 |

### 应该记住的数字

- Modal 冷启动：2-4s（配合 GPU 快照）。
- Baseten 默认冷启动：5-10s；预热门控下亚秒级。
- 原始 70B 冷启动：3-8 分钟。
- Run:ai Model Streamer：权重加载约 2 倍加速。
- ServerlessLLM 分级加载：延迟降低 10-200 倍（论文数字）。

```figure
cold-start-pipeline
```

## Use It

`code/main.py` 对每一种缓解手段的开启与关闭分别建模冷启动路径。报告总冷启动时间、warm pool 成本，以及 warm pool 开始划算的盈亏平衡请求速率。

## Ship It

本课产出 `outputs/skill-cold-start-planner.md`。给定 SLA、模型规模和流量形态，选出要叠加哪些缓解手段。

## Exercises

1. 运行 `code/main.py`。计算盈亏平衡请求速率：超过它之后，热副本比因超出 SLO 而丢弃请求所付的冷启动税更便宜。
2. 你部署一个 13B 模型，P99 TTFT SLA 为 3s。选出能达到该 SLA 的最小缓解组合（层数最少）。
3. Bottlerocket 预置消除了镜像拉取，但权重仍需从快照载入 HBM。若快照支撑的 NVMe 读取速度为 7 GB/s，计算 70B 模型的墙钟时间。
4. 你的 serverless 提供方提供 GPU 快照（Modal），但团队拒绝，理由是“快照会泄露 PII”。为双方辩护 —— 现实风险是什么，缓解手段是什么（临时快照、加密、命名空间隔离）？
5. 设计一套分层 warm pool 策略：付费用户、试用用户和批处理负载各需要多少热副本？给出算式。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Cold start | “the big pause” | 新副本上从请求到首 token 的时间 |
| Warm pool | “always-on minimum” | `min_workers >= 1`，保持至少一个副本就绪 |
| Pre-seeded image | “baked AMI” | 预先驻留容器权重的节点镜像 |
| Bottlerocket | “AWS node OS” | AWS 的容器优化操作系统，支持双卷快照 |
| Model streamer | “streaming load” | 让权重 I/O 与计算初始化重叠 |
| GPU snapshot | “checkpoint to HBM” | 序列化加载后的 GPU 状态；重启时反序列化 |
| Tiered loading | “NVMe + DRAM + HBM” | 存储层级体系；按需加载 |
| Live migration | “move tokens” | 传输输入（KB），在目的端重算 KV |
| `min_workers` | “warm replicas” | serverless 的最小保活副本数 |
| Scale-to-zero | “full serverless” | 空闲时零成本；接受完整的冷启动税 |

## Further Reading

- [Modal — Cold start performance](https://modal.com/docs/guide/cold-start) —— Modal 公布的 benchmark 与 checkpoint 架构。
- [AWS Bottlerocket](https://github.com/bottlerocket-os/bottlerocket) —— 预置数据卷快照模式。
- [NVIDIA Run:ai Model Streamer](https://github.com/run-ai/runai-model-streamer) —— 权重加载与计算初始化重叠。
- [Baseten — Cold starts](https://docs.baseten.co/deployment/autoscaling/cold-starts) —— 预热 playbook。
- [ServerlessLLM paper (USENIX OSDI'24)](https://www.usenix.org/conference/osdi24/presentation/fu) —— 分级加载设计。
- [NVIDIA — Disaggregated LLM Inference on Kubernetes](https://developer.nvidia.com/blog/deploying-disaggregated-llm-inference-workloads-on-kubernetes/) —— disaggregated 部署的 live migration。
