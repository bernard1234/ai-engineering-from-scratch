# Disaggregated Prefill/Decode——NVIDIA Dynamo 与 llm-d

> Prefill 是 compute-bound；decode 是 memory-bound。把两者放在同一块 GPU 上跑，总会浪费其中一种资源。Disaggregation 把它们拆到独立的资源池，并通过 NIXL（RDMA/InfiniBand，或 TCP 回退）在两者之间传输 KV cache。NVIDIA Dynamo（GTC 2025 announce，1.0 GA）位于 vLLM/SGLang/TRT-LLM 之上——它的 Planner Profiler + SLA Planner 会自动按比例匹配 prefill:decode 配比以满足 SLO。NVIDIA 公布的吞吐提升大致在这个量级——developer.nvidia.com（2025-06）显示，在 medium-latency 区间，GB200 NVL72 + Dynamo 上的 DeepSeek-R1 MoE 约有 6 倍提升；Dynamo 产品页（developer.nvidia.com，无日期）宣称在 GB300 NVL72 + Dynamo 上相对 Hopper 最高可达 50 倍 MoE 吞吐。“30 倍”这个数字是社区对完整 Blackwell + Dynamo + DeepSeek-R1 报告的一个汇总；我们没有找到任何一个明确写出 30 倍的原始来源，因此把它当作方向性说法。llm-d（Red Hat + AWS）是 Kubernetes 原生的：prefill / decode / router 作为独立的 Service，按角色做 HPA。llm-d 0.5 增加了分层 KV offloading、cache-aware 的 LoRA 路由、UCCL 网络、scale-to-zero。经济账：多份客户披露的内部汇总显示，在恒定 SLA 下从 colocated serving 切换到基于 Dynamo 的 disaggregated serving，$2M 级别的推理支出可节省 30–40%（即每年 $600-800K）；具体的 $2M→$600-800K 数字是内部汇总，不是单一公开案例研究——请把它当作数量级锚点，而不是引用来源。短 prompt（<512 tokens、短输出）不值得付出传输成本。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级 disaggregated-vs-colocated 模拟器)
**Prerequisites:** 第 17 阶段，第 04 课（Serving Engine Internals），第 08 课（Inference Metrics）
**Time:** ~75 分钟

## Learning Objectives

- 解释为什么 prefill 与 decode 有各自最优的 GPU 配比，并量化 colocation 下的浪费。
- 画出 disaggregated 架构：prefill 池、decode 池、经 NIXL 的 KV 传输、router。
- 说出 disaggregation 不划算的条件（短 prompt、短输出）。
- 区分 NVIDIA Dynamo（stack-above）与 llm-d（Kubernetes 原生），并为各自匹配合适的运维场景。

## 问题场景

你在 8 张 H100 上跑 Llama 3.3 70B。在混合负载（长 prompt + 短输出）下，GPU 在 decode 期间空转，因为大部分算力花在了 prefill 上。在另一种负载（短 prompt + 长输出）下，情况正好相反。把 prefill 与 decode colocated 意味着你得为两者都超额配置。

预算影响：20-40% 的 GPU 时间被浪费在错误的那类资源上。你买 H100 算力去跑 memory-bound 的 decode，或者买 H100 的 HBM 带宽去跑 compute-bound 的 prefill。两者都是昂贵的浪费。

Disaggregation 把 prefill 与 decode 拆到各自按瓶颈定容的独立池。KV cache 通过高带宽互联从 prefill 池传输到 decode 池。

## 核心概念

### 为什么瓶颈不同

**Prefill**——用一次前向把整个输入 prompt 跑过 transformer。矩阵乘法占主导；compute-bound。H100 FP8 大约能提供 ~2000 TFLOPS 的有效吞吐。batch 效率好——一次前向处理很多 token。

**Decode**——一次生成一个 token，每次迭代都要读取全部权重。memory-bandwidth-bound。HBM3 大约能提供 ~3 TB/s。只有高并发时 batch 效率才好——权重读取能摊到整个 batch 上。

把两者 colocate：你买的 GPU 要同时擅长两者。H100 两者都不错，但无论哪种用法成本一样。到一定规模，你会想让 prefill 池用 H100 / 偏算力；decode 池用 H200 / 偏内存，或者用激进量化。

### 架构

```
            ┌──────────────┐
  Request → │    Router    │ ───────────────────────┐
            └──────┬───────┘                        │
                   │                                │
                   ▼ (prompt only)                  │
            ┌──────────────┐    KV cache    ┌───────▼──────┐
            │ Prefill pool │ ─── NIXL ────► │ Decode pool  │
            │  (compute)   │                │  (memory)    │
            └──────────────┘                └──────┬───────┘
                                                   │ tokens
                                                   ▼
                                                 Client
```

NIXL 是 NVIDIA 的节点间传输层。在有 RDMA/InfiniBand 时用它，否则回退到 TCP。传输延迟是真实存在的——在 70B FP8 上，一个 4K-token prompt 的 KV cache 通常要 20-80 ms。这就是为什么短 prompt 不值得 disaggregation：传输税超过了节省。

### Dynamo vs llm-d

**NVIDIA Dynamo**（GTC 2025 announce，1.0 GA）：
- 作为 orchestrator 位于 vLLM、SGLang、TRT-LLM 之上。
- Planner Profiler 测量负载，SLA Planner 自动配置 prefill:decode 配比。
- Rust 核心，Python 可扩展。
- 吞吐提升：NVIDIA 报告称，在 medium-latency 区间，GB200 NVL72 + Dynamo 上的 DeepSeek-R1 MoE 有 6 倍提升（developer.nvidia.com，2025-06）；社区关于完整 Blackwell + Dynamo + DeepSeek-R1 栈“最高 30 倍”的说法缺乏单一原始来源，应视为方向性。
- GB300 NVL72 + Dynamo：据 Dynamo 产品页（developer.nvidia.com，无日期），相对 Hopper 最高可达 50 倍 MoE 吞吐。

**llm-d**（Red Hat + AWS，Kubernetes 原生）：
- Prefill / decode / router 作为独立的 Kubernetes Service。
- 按角色做 HPA，信号分别用队列深度（prefill）/ KV 利用率（decode）。
- `topologyConstraint packDomain: rack` 把 prefill+decode clique 打包到同一机架，以获得高带宽 KV 传输。
- llm-d 0.5（2026）：分层 KV offloading、cache-aware 的 LoRA 路由、UCCL 网络、scale-to-zero。

想要一个托管的 stack-above orchestrator，就用 Dynamo。想要 Kubernetes 原生原语、并坚定投入 CNCF 生态，就用 llm-d。

### 经济账

内部汇总（不是单一公开案例研究——数量级锚点）：

- 每年 $2M 的推理支出用在 colocated serving 上。
- 切换到基于 Dynamo 的 disaggregated 方案。
- 请求量相同，P99 latency SLA 相同。
- 报告节省：每年 $600K–$800K（降低 30–40%）。
- 没有新增硬件。

这个数字是我们从多份客户披露中综合出来的，而非单一可引用的案例研究；最接近的公开数据点是 Baseten 在 Dynamo KV routing 上的 2 倍更快 TTFT / 61% 更高吞吐（baseten.co，2025-10），以及 VAST + CoreWeave 关于在 40–60% KV 命中率下每美元多 60–130% tokens 的预测（vastdata.com，2025-12）。节省来自给每个池合理定容；prefill 偏重的负载（带 8K+ 前缀的 RAG）比均衡负载受益更多。

### 什么时候不该 disaggregate

- prompt < 512 tokens 且输出 < 200 tokens：传输税盖过收益。
- 小集群（< 4 张 GPU）：池子多样性不足。
- 团队无法运维两个按角色伸缩的 GPU 池：Dynamo 有帮助但并不轻松。
- 没有 RDMA fabric：TCP 的传输税更重。

### router 如何与第 17 阶段 · 11 集成

Disaggregated 的 router 是 KV-cache-aware 的（第 17 阶段 · 11）。一个请求落到持有其前缀的 decode 池上——如果没有匹配，就走 prefill → decode。命中率与 disaggregation 会叠加——cache-aware 的 router 决定了是否还需要一次新的 prefill。

### 真正的数字在 Blackwell 上的 MoE

GB300 NVL72 + Dynamo 相对 Hopper 基线显示 50 倍 MoE 吞吐。MoE 的 expert 路由在 prefill 上偏算力，在 decode 上偏内存（expert cache），因此 disaggregation 是双重收益。2026 年 frontier 模型 serving 以 MoE 为主（DeepSeek-V3、未来的 GPT-5 变体）。

### 你该记住的数字

Benchmark 数字会漂移——NVIDIA 与推理栈每个季度都会发布更新后的结果。引用前请重新核对。

- GB200 NVL72 + Dynamo 上的 DeepSeek-R1：在 medium-latency 区间，相对基线约 6 倍吞吐（developer.nvidia.com，2025-06）；社区关于完整 Blackwell + Dynamo 栈“最高 30 倍”的说法是没有单一原始来源的方向性汇总。
- GB300 NVL72 + Dynamo：相对 Hopper 最高可达 50 倍 MoE 吞吐（developer.nvidia.com，无日期）。
- 节省锚点（内部汇总，非单一案例研究）：在恒定 SLA 下，从每年 $2M 的支出中省下 $600-800K。
- Disaggregation 阈值：prompt >512 tokens + 输出 >200 tokens。
- 经 NIXL 的 KV 传输：70B FP8 上 4K-prompt 的 KV 为 20-80 ms。

```figure
prefill-decode-split
```

## Use It

`code/main.py` 模拟 colocated 与 disaggregated serving。报告吞吐、每请求成本，以及 prompt 长度的交叉点。

## Ship It

本课产出 `outputs/skill-disaggregation-decider.md`。给定负载与集群，判断是否该 disaggregate。

## Exercises

1. 运行 `code/main.py`。在什么 prompt 长度上，disaggregation 会胜过 colocation？
2. 为一个 P99 前缀长度 8K、输出 300 的 RAG 服务设计 prefill 池与 decode 池。
3. Dynamo vs llm-d：为一个纯 Kubernetes、没有 Python 运行时偏好的团队选一个。
4. 计算 KV 传输成本：70B FP8 上 4K prefill = ~500 MB KV。在 RDMA 100 GB/s 下，传输 = 5 ms。在 TCP 10 GB/s 下 = 50 ms。哪个对你的 SLA 更重要？
5. MoE 的 expert 路由会改变 KV 访问模式。对每个 token 激活不同 expert 的 MoE，disaggregation 表现如何？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Disaggregated serving | “拆分 prefill/decode” | 为每个阶段使用独立的 GPU 池 |
| NIXL | “NVIDIA 传输层” | Dynamo 的节点间 KV 传输（RDMA/TCP） |
| NVIDIA Dynamo | “the orchestrator” | vLLM/SGLang/TRT-LLM 之上的 stack-above 协调器 |
| llm-d | “Kubernetes 原生” | Red Hat + AWS 的 K8s disaggregated 栈 |
| Planner Profiler | “Dynamo 自动配置” | 测量负载，配置池配比 |
| SLA Planner | “Dynamo 策略” | 自动按比例匹配 prefill:decode 以满足 SLO |
| `packDomain: rack` | “llm-d 拓扑” | 把 prefill+decode 打包到同机架以加速 KV |
| UCCL | “统一 collective” | llm-d 0.5 的 scale-to-zero 网络层 |
| MoE expert routing | “每 token 一个 expert” | DeepSeek-V3 模式；disaggregation 有帮助 |

## Further Reading

- [NVIDIA — Introducing Dynamo](https://developer.nvidia.com/blog/introducing-nvidia-dynamo-a-low-latency-distributed-inference-framework-for-scaling-reasoning-ai-models/)
- [NVIDIA — Disaggregated LLM Inference on Kubernetes](https://developer.nvidia.com/blog/deploying-disaggregated-llm-inference-workloads-on-kubernetes/)
- [TensorRT-LLM Disaggregated Serving blog](https://nvidia.github.io/TensorRT-LLM/blogs/tech_blog/blog5_Disaggregated_Serving_in_TensorRT-LLM.html)
- [llm-d GitHub](https://github.com/llm-d/llm-d)
- [llm-d 0.5 release notes](https://github.com/llm-d/llm-d/releases)
