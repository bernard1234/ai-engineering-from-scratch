# 硬件专用推理编译 —— Blackwell 上的 FP8 与 NVFP4

> 硬件专用推理编译用可移植性换吞吐，而 TensorRT-LLM —— 只支持 NVIDIA、为 Blackwell 调优 —— 是这笔交换划算得最清楚的例子。在 GB200 NVL72 上配合 Dynamo 编排，SemiAnalysis InferenceX 在 2026 年 Q1-Q2 测得 120B 模型每百万 token $0.012，而 H100 + vLLM 为 $0.09/M —— 7 倍的经济差距。这套栈是三种浮点方案叠加：FP8 对 KV cache 和 attention kernel 仍然关键，因为它具备所需的动态范围；NVFP4（4-bit 微缩放）负责权重和激活；multi-token prediction（MTP）与 disaggregated prefill/decode 再叠加 2-3 倍。Day-0 模型支持直接加载 FP4 权重，无需训练后转换。2026 年工程团队的代价是：TRT-LLM 开源但绑定 NVIDIA —— 专用于 CUDA 与 Blackwell —— 采用它就等于用可移植性换吞吐。在下决心之前，先按你的模型组合和硬件算一笔账。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级 FP8/NVFP4 显存与成本计算器)
**Prerequisites:** 第 17 阶段，第 04 课（Serving Engine Internals），第 10 阶段，第 13 课（Quantization）
**Time:** ~75 分钟

## Learning Objectives

- 解释为什么即使权重是 NVFP4，FP8 对 KV cache 和 attention 仍然关键。
- 计算前沿模型在 BF16、FP8、NVFP4 下的 HBM 占用，并推理节省来自哪里。
- 说出 TRT-LLM 利用的 Blackwell 专属特性（day-0 FP4、MTP、disaggregated serving、all-to-all primitive）。
- 判断什么时候 TRT-LLM 的 NVIDIA 锁定值得相对 Hopper 上 vLLM 的 7 倍成本差距。

## 问题场景

2026 年推理经济学的边界问题是“每美元能跑多少 token”。答案取决于四个叠在一起的选择：硬件代际（Hopper H100/H200 vs Blackwell B200/GB200）、精度（BF16 → FP8 → NVFP4）、serving engine（vLLM vs SGLang vs TRT-LLM）以及编排方式（plain vs disaggregated vs Dynamo）。

在 Hopper 上跑 vLLM，一个 120B MoE 大约是每百万 token $0.09。在 Blackwell 上用 TRT-LLM + Dynamo，同一个模型约 $0.012 —— 便宜 7 倍。其中一部分差距来自硬件（Blackwell 的单卡 LLM 吞吐是 Hopper 的 11-15 倍）。另一部分来自这套栈：FP4 权重、MTP draft、disaggregated prefill/decode，以及用于 MoE expert 通信的 NVLink 5 all-to-all。

你无法在 NVIDIA 栈之外复现这一点。这就是权衡 —— 用可移植性换经济性。理解每种栈选择各自贡献了差距中的哪一部分，正是本课的目的。

## 核心概念

### 为什么 FP8 仍是 KV cache 的下限

2026 年的一个常见错误：以为 NVFP4 适用于所有地方。并非如此。KV cache 需要 FP8（8-bit 浮点），因为它存储的 attention key 和 value 跨越很宽的动态范围。把 KV 量化到 FP4 会造成灾难性的精度损失 —— 分布的尾部被砍掉，attention score 崩塌。FP8 的指数位给了 KV cache 所需的动态范围。

NVFP4（2025-2026）用于权重和激活。微缩放：每个权重块都有自己的 scale factor，于是小块可以覆盖不同的动态范围，而不会出现 per-tensor scale 的损失。对激活而言 FP4 撑得住，因为一层之内的激活取值范围小。

Blackwell 上的典型配置：

- 权重：NVFP4（4-bit 微缩放）。
- 激活：NVFP4。
- KV cache：FP8。
- Attention 累加器：FP32（softmax 稳定性）。

### TRT-LLM 用到的 Blackwell 专属 primitive

- **Day-0 FP4 权重**：模型提供方直接发布 FP4 权重；TRT-LLM 无需训练后转换即可加载。FP4 不需要 AWQ / GPTQ 步骤。
- **Multi-token prediction（MTP）**：与 EAGLE 思路相同（第 17 阶段 · 05），但集成进了 TRT-LLM 构建。
- **Disaggregated serving**：prefill 和 decode 分在独立的 GPU 池上，KV cache 通过 NVLink 或 InfiniBand 传输。与 Dynamo 思路相同（第 17 阶段 · 20）。
- **All-to-all 通信 primitive**：NVLink 5 把 MoE expert 通信延迟相对 Hopper 削减 3 倍。TRT-LLM 的 MoE kernel 就是为此调优的。
- **NVFP4 + MXFP8 微缩放**：在 Blackwell Tensor Core 上由硬件加速处理 scale factor。

### 应该记住的数字

- HGX B200 在 GPT-OSS-120B 上经 TRT-LLM 为每百万 token $0.02。
- GB200 NVL72 经 Dynamo（编排 TRT-LLM）为每百万 token $0.012。
- H100 + vLLM 在可比负载上约每百万 token $0.09。
- TRT-LLM 三个月的更新带来 2.8 倍吞吐提升（2026）。
- 单卡 LLM 吞吐，Blackwell 相对 Hopper 为 11-15 倍。
- MLPerf Inference v6.0（2026 年 4 月）：Blackwell 在每一个提交任务上都占优。

### FP4 在质量上究竟付出多少代价

NVFP4 很激进。在推理密集型负载上（chain-of-thought、数学、长 context 代码生成），FP4 权重会明显退化。per-block 校准能缓解但不能消除。交付推理模型的团队常常用 FP8 权重 + FP4 激活作为折中，或者干脆留在 H200 上全程 FP8。

规则：在采用 NVFP4 权重之前，永远先在你的 eval set 上验证任务质量。

### 为什么这是一个 NVIDIA 锁定决策

TRT-LLM 是 C++ + CUDA + 闭源 kernel。模型需要针对特定 GPU SKU 编译。没有 AMD，没有 Intel，没有 ARM。如果你的基础设施策略是多厂商，那么对由 TRT-LLM 服务的层级来说 TRT-LLM 不可行 —— 你仍然可以在混合硬件上用 vLLM 提供服务。如果你是纯 NVIDIA，7 倍的差距足以抵得上这把锁。

### 2026 年的实用配方

对于年推理账单 $100M+ 的情况，跑在 Hopper + vLLM 上等于把 7-10 倍留在了桌上。把成本占主导的负载迁移到 Blackwell + TRT-LLM + Dynamo。把实验层留在 H100 + vLLM 上以保证模型迭代速度。每个经 NVFP4 转换的模型上线前都要验证质量。

### disaggregation 的额外加成

TRT-LLM 的 disaggregated serving（prefill 与 decode 分池）在第 17 阶段 · 20 深入讨论。在 Blackwell 上，倍率会叠加：FP4 权重 × MTP 加速 × disaggregated 部署 × cache-aware routing。7 倍这个数字假设了完整栈。

```figure
pipeline-parallel
```

## Use It

`code/main.py` 计算三种栈的 HBM 占用、decode 吞吐（memory-bound 区间）以及 $/M-token：H100 + BF16 + vLLM、H100 + FP8 + vLLM、B200 + NVFP4/FP8 + TRT-LLM。运行它可以看到叠加效应，以及每次变更各自贡献了差距的多少。

## Ship It

本课产出 `outputs/skill-trtllm-blackwell-advisor.md`。给定负载、模型规模和年 token 量，它判断 Blackwell + TRT-LLM 这套栈是否值得接受 NVIDIA 锁定。

## Exercises

1. 运行 `code/main.py`。对一个 30% 激活参数的 120B MoE，计算 H100 BF16、H100 FP8 和 B200 NVFP4/FP8 上的 memory-bandwidth 受限 decode 吞吐。最大的跃升来自哪里？
2. 一个客户每年在 H100 + vLLM 上花 $2M。鉴于 7 倍的经济差距，他们需要在 12 个月内摊销迁移到 TRT-LLM 的成本，盈亏平衡所需购买的 Blackwell GPU 数量是多少？
3. NVFP4 权重转换后你看到 MATH 上精度掉了 3 个点。说出两条恢复路径：一条质量优先（保留 FP8 权重），一条成本优先（用 in-domain 数据校准）。
4. 阅读 MLPerf v6.0 推理结果。哪个任务的 Blackwell 相对 Hopper 差距最小，为什么？
5. 计算 405B 模型在 NVFP4 权重 + FP8 KV cache、128k context 下所需的 HBM。它能装进单个 GB200 NVL72 节点吗？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| FP8 | “eight-bit float” | 8-bit 浮点；因动态范围而用于 KV cache 和 attention |
| NVFP4 | “four-bit micro” | NVIDIA 的 4-bit 微缩放 FP 格式；Blackwell 上的权重与激活 |
| MXFP8 | “MX eight” | 微缩放 FP8 变体；在 Blackwell Tensor Core 上硬件加速 |
| Day-0 FP4 | “ship FP4 weights” | 模型提供方直接发布 FP4 权重；没有训练后转换步骤 |
| MTP | “multi-token prediction” | TRT-LLM 集成的 speculative decoding draft（第 17 阶段 · 05） |
| Disaggregated serving | “split prefill/decode” | prefill 与 decode 分在独立 GPU 池；KV 经 NVLink/IB 传输 |
| All-to-all | “MoE expert comm” | 把 token 路由到 expert GPU 的通信模式；NVLink 5 削减 3 倍 |
| InferenceX | “SemiAnalysis inference bench” | 2026 年业界公认的每 token 成本 benchmark |

## Further Reading

- [NVIDIA — Blackwell Ultra MLPerf Inference v6.0](https://developer.nvidia.com/blog/nvidia-blackwell-ultra-sets-new-inference-records-in-mlperf-debut/) —— 2026 年 4 月的 MLPerf 结果。
- [NVIDIA — MoE Inference on Blackwell](https://developer.nvidia.com/blog/delivering-massive-performance-leaps-for-mixture-of-experts-inference-on-nvidia-blackwell/) —— NVLink 5 all-to-all 与 MoE kernel。
- [TensorRT-LLM Overview](https://nvidia.github.io/TensorRT-LLM/overview.html) —— 官方引擎文档。
- [NVIDIA — Introducing Dynamo](https://developer.nvidia.com/blog/introducing-nvidia-dynamo-a-low-latency-distributed-inference-framework-for-scaling-reasoning-ai-models/) —— TRT-LLM 之上的 disaggregated 编排。
- [MLPerf Inference](https://mlcommons.org/benchmarks/inference-datacenter/) —— 发布 Blackwell 数字的 benchmark 套件。
