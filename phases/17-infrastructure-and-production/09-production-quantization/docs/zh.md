# 生产环境量化 —— AWQ、GPTQ、GGUF K-quants、FP8、MXFP4/NVFP4

> 量化格式不是普适选择 —— 它是硬件、serving engine 和负载的函数。GGUF Q4_K_M 或 Q5_K_M 占据 CPU 与 edge，通过 llama.cpp 和 Ollama 交付。当你需要在同一底座上做 multi-LoRA 时，vLLM 内部的 GPTQ 胜出。AWQ 配合 Marlin-AWQ kernel，在 7B 级模型上给出约 741 tok/s，并在 INT4 下取得最佳 Pass@1 —— 这是 2026 年数据中心的默认选择。FP8 是 Hopper、Ada 和 Blackwell 上的中间地带 —— 近乎无损且支持广泛。NVFP4 和 MXFP4（Blackwell 微缩放）比较激进，需要 per-block 验证。有两个陷阱会咬到团队：校准数据集必须匹配部署领域；KV cache 与权重量化是两回事 —— AWQ 课上那句“我的模型现在只有 4 GB”忘掉了生产 batch size 下 10-30 GB 的 KV cache。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级跨格式显存与吞吐对比)
**Prerequisites:** 第 10 阶段，第 13 课（Quantization foundations），第 17 阶段，第 04 课（Serving Engine Internals）
**Time:** ~75 分钟

## Learning Objectives

- 说出 2026 年六种生产环境量化格式及其各自的最佳适用场景。
- 给定硬件（CPU vs GPU、Hopper vs Blackwell）、引擎（vLLM、TRT-LLM、llama.cpp）和负载（日常聊天、推理、multi-LoRA），选出一种格式。
- 计算指定格式节省的权重显存，以及未被触及的 KV cache 占用。
- 说出那个会在领域流量上拉低量化模型效果的校准数据集陷阱。

## 问题场景

量化降低显存和 HBM 带宽占用，而这正是 decode 所需要的。FP16 的 70B 模型是 140 GB 权重。把权重量化到 INT4（AWQ 或 GPTQ）后模型是 35 GB —— 能装进一张 H100 并留出 KV cache 的空间，这一点很关键，因为在 128 个并发序列、2k context 的情况下，光 KV cache 就有 20-30 GB。

但量化不是免费的。激进量化会损害质量，尤其是在推理密集型任务上。不同格式适配不同引擎。不同硬件原生支持不同精度。2026 年的格式动物园是真实存在的，你不能照抄别人的选择 —— 必须基于自己的栈来选。

## 核心概念

### 六种格式

| 格式 | 位数 | 最佳场景 | 引擎 |
|--------|------|-----------|---------|
| GGUF Q4_K_M / Q5_K_M | 4-5 | CPU、edge、笔记本 | llama.cpp、Ollama |
| GPTQ | 4-8 | vLLM 上的 multi-LoRA | vLLM、TGI |
| AWQ | 4 | 数据中心 GPU 生产 | vLLM（Marlin-AWQ）、TGI |
| FP8 | 8 | Hopper/Ada/Blackwell 数据中心 | vLLM、TRT-LLM、SGLang |
| MXFP4 | 4 | Blackwell 多用户 | TRT-LLM |
| NVFP4 | 4 | Blackwell 多用户 | TRT-LLM |

### GGUF —— CPU/edge 的默认选择

GGUF 是文件格式，本身不是量化方案 —— 它把 K-quant 变体（Q2_K、Q3_K_M、Q4_K_M、Q5_K_M、Q6_K、Q8_0）打包在一个容器里。Q4_K_M 和 Q5_K_M 是生产默认值 —— 4-5 bit 下接近 BF16 的质量。它是 CPU 或 edge 服务的最佳选择，因为 llama.cpp 是迄今为止最快的 CPU 推理引擎。

在 vLLM 中的吞吐代价：7B 上约 93 tok/s —— 该格式并未针对 GPU kernel 优化。当部署目标是 CPU/edge 时用 GGUF。其他情况不要用。

### GPTQ —— vLLM 中的 multi-LoRA

GPTQ 是一种带校准过程的训练后量化算法。Marlin kernel 让它在 GPU 上很快（相对非 Marlin 的 GPTQ 有 2.6 倍加速）。7B 上约 712 tok/s。

它独有的优势：GPTQ-Int4 在 vLLM 中支持 LoRA adapter。如果你在服务一个底座模型外加 10-50 个微调变体（每个是一个 LoRA），GPTQ 就是你的路径。截至 2026 年初，NVFP4 还不支持 LoRA。

### AWQ —— 数据中心 GPU 的默认选择

Activation-aware Weight Quantization。在量化过程中保护约 1% 最显著的权重。Marlin-AWQ kernel：相对朴素实现有 10.9 倍加速。7B 上约 741 tok/s，在 INT4 各格式中 Pass@1 最佳。

新的 GPU 服务选 AWQ，除非你需要 multi-LoRA（GPTQ）或更激进的 Blackwell FP4（NVFP4）。

### FP8 —— 可靠的中间地带

8-bit 浮点。近乎无损。支持广泛。Hopper Tensor Core 原生加速 FP8。Blackwell 继承此能力。当质量不可妥协时（推理、医疗、代码生成），FP8 是 2026 年的安全默认值。显存节省只有 INT4 的一半，但质量风险低得多。

### MXFP4 / NVFP4 —— Blackwell 的激进方案

微缩放 FP4。每个权重块有自己的 scale factor。激进，但在 Blackwell Tensor Core 上由硬件加速。相对 FP8 把每 token 的字节数减半 —— 这就是第 17 阶段 · 07 中的经济收益。

注意事项：
- 尚不支持 LoRA（2026 年初）。
- 推理密集型负载上质量下降明显。
- 每个模型都要在你的 eval set 上验证。

### 校准陷阱

AWQ 和 GPTQ 需要校准数据集 —— 通常是 C4 或 WikiText。对领域模型（代码、医疗、法律），用通用网页文本做校准会让算法对“保护哪些权重”做出错误判断。HumanEval 上 Pass@1 可能掉好几个点。

解决办法：用 in-domain 数据校准。通常几百条领域样本就够。上线前在 eval set 上测试。

### KV cache 陷阱

AWQ 把权重压到 4 bit。KV cache 是独立的，仍保持 FP16/FP8。对一个用 AWQ 的 70B 模型：

- 权重：约 35 GB（从 140 GB 压到 INT4）。
- 128 并发 × 2k context 的 KV cache：约 20 GB。
- 激活：约 5 GB。
- 总计：约 60 GB —— 能装进 H100 80GB。

天真地说“我把模型量化到了 4 GB”忘掉了另外的 30-50 GB。要整体规划 HBM 预算。

另外，KV cache 量化（FP8 KV 或 INT8 KV）是另一个有自身权衡的选择 —— 它直接影响 attention 精度，并不是免费的收益。

### AWQ INT4 对推理任务是危险的

Chain-of-thought、数学、长 context 代码生成 —— 这些都明显受激进量化拖累。AWQ INT4 在 MATH 上损失约 3-5 个点。对推理密集型负载，交付 FP8 或 BF16；接受显存成本。

### 2026 年选择指南

- CPU/edge 服务：GGUF Q4_K_M。就这样。
- GPU 服务、日常聊天、无 LoRA：AWQ。
- GPU 服务、multi-LoRA：GPTQ 配 Marlin。
- 推理负载：FP8。
- Blackwell 数据中心、质量已验证：NVFP4 + FP8 KV。
- 拿不准：对每个候选格式跑一次 1,000 样本的 eval。

```figure
gpu-memory-breakdown
```

## Use It

`code/main.py` 对一系列模型规模计算六种格式的显存占用（权重 + KV + 激活）与相对吞吐。展示出 KV cache 在哪儿占主导、权重压缩在哪儿划算、以及 FP8 在哪儿是安全选择。

## Ship It

本课产出 `outputs/skill-quantization-picker.md`。给定硬件、模型规模、负载类型和质量容忍度，它选出一种格式并产出校准/验证计划。

## Exercises

1. 运行 `code/main.py`。对一个 70B 模型、128 并发、2k context，计算每种格式的总 HBM。哪种格式能让你装进一张 H100 80GB？
2. 你有一个 7B 代码模型。选一种格式并说明理由。如果你对质量容忍度判断错了，恢复路径是什么？
3. 计算为医疗领域模型校准 AWQ 所需的校准数据集规模。为什么更多数据并不总是更好？
4. 阅读 Marlin-AWQ kernel 的论文或发布说明。用三句话解释为什么 AWQ 在 7B 上达到 741 tok/s，而原始 GPTQ 只有约 712。
5. 什么时候把 AWQ 权重和 FP8 KV cache 组合使用有意义，什么时候应把 KV 保持在 BF16？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| GGUF | “llama.cpp format” | 打包 K-quant 变体的文件格式；CPU/edge 默认 |
| Q4_K_M | “Q4 K M” | 4-bit K-quant medium；GGUF 的生产默认 |
| GPTQ | “gee pee tee q” | 带校准的训练后 INT4；在 vLLM 中支持 LoRA |
| AWQ | “a w q” | Activation-aware INT4；Marlin kernel；INT4 下最佳 Pass@1 |
| Marlin kernels | “fast INT4 kernels” | 为 Hopper 上 INT4 定制的 CUDA kernel；10 倍加速 |
| FP8 | “eight-bit float” | Hopper/Ada/Blackwell 上的安全精度默认 |
| MXFP4 / NVFP4 | “microscaling four” | Blackwell 4-bit FP，带 per-block scale factor |
| Calibration dataset | “cal data” | 用于选取量化参数的输入文本；必须匹配领域 |
| KV cache quantization | “KV INT8” | 与权重分开的选择；影响 attention 精度 |

## Further Reading

- [VRLA Tech — LLM Quantization 2026](https://vrlatech.com/llm-quantization-explained-int4-int8-fp8-awq-and-gptq-in-2026/) —— 对比 benchmark。
- [Jarvis Labs — vLLM Quantization Complete Guide](https://jarvislabs.ai/blog/vllm-quantization-complete-guide-benchmarks) —— 按格式划分的吞吐数字。
- [PremAI — GGUF vs AWQ vs GPTQ vs bitsandbytes 2026](https://blog.premai.io/llm-quantization-guide-gguf-vs-awq-vs-gptq-vs-bitsandbytes-compared-2026/) —— 逐格式的选择建议。
- [vLLM docs — Quantization](https://docs.vllm.ai/en/latest/features/quantization/index.html) —— 支持的格式与参数。
- [AWQ paper (arXiv:2306.00978)](https://arxiv.org/abs/2306.00978) —— AWQ 的原始表述。
- [GPTQ paper (arXiv:2210.17323)](https://arxiv.org/abs/2210.17323) —— GPTQ 的原始表述。
