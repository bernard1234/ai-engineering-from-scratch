# 推理指标 —— TTFT、TPOT、ITL、Goodput、P99

> 四个指标决定一次推理部署是否正常。TTFT 是 prefill 加排队加网络。TPOT（等价于 ITL）是每个 token 在 memory-bound decode 阶段的开销。端到端延迟是 TTFT 加 TPOT 乘以输出长度。吞吐是整个集群聚合的每秒 token 数。但对产品真正重要的是 goodput —— 同时满足所有 SLO 的请求占比。高吞吐、低 goodput 意味着你在处理那些永远无法按时送达用户的 token。2026 年 TRT-LLM 上 Llama-3.1-8B-Instruct 的参考数字：mean TTFT 162 ms，mean TPOT 7.33 ms，mean E2E 1,093 ms。永远报告 P50、P90、P99 —— 不要只报均值。还要当心测量陷阱：GenAI-Perf 在计算 ITL 时排除 TTFT，LLMPerf 则包含它；同一次运行两个工具给出的 TPOT 不一致。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级百分位计算器与 goodput 报告器)
**Prerequisites:** 第 17 阶段，第 04 课（Serving Engine Internals）
**Time:** ~60 分钟

## Learning Objectives

- 精确定义 TTFT、TPOT、ITL、E2E、throughput 和 goodput，并说出每个指标度量的是哪个环节。
- 解释为什么均值是 LLM 服务的错误统计量，以及如何读 P50/P90/P99。
- 构造一个 SLO 多约束（例如 TTFT<500 ms 且 TPOT<15 ms 且 E2E<2 s），并据此计算 goodput。
- 说出两个在同一次运行上对 TPOT 给出不同结果的 benchmark 工具，并解释原因。

## 问题场景

“我们的吞吐是每秒 15,000 token。”那又怎样？如果 40% 的请求端到端超过了 2 秒，用户早就放弃了会话。单看吞吐并不能说明产品是否可用。

推理有多个延迟维度，每个维度以不同方式失效。Prefill 是计算受限的，随 prompt 长度增长。Decode 是显存带宽受限的，随 batch size 增长。排队延迟是运维问题。网络是物理距离问题。你需要为每个维度设独立指标，需要百分位数，还需要一个综合指标回答“用户是否得到了他期望的体验” —— 那就是 goodput。

## 核心概念

### TTFT —— 首 token 时间

`TTFT = queue_time + network_request + prefill_time`

Prompt 很长时 prefill 占主导。在 H100 上的 Llama-3.3-70B FP8 上，32k 的 prompt 纯 prefill 就需要约 800 ms。排队时间是负载下调度器的行为。网络请求是包含 TLS 在内的链路时间。TTFT 是用户在任何内容流回之前看到的延迟。

### TPOT / ITL —— token 间延迟

同一个量有很多名字。`TPOT`（time per output token）、`ITL`（inter-token latency）、`decode latency per token` —— 都是同一件事。它是首 token 之后连续流式 token 之间的时间。

`TPOT = (decode_forward_time + scheduler_overhead) / tokens_produced`

在同样的 Llama-3.3-70B H100 栈上启用 chunked prefill，TPOT 均值约 7 ms。不启用 chunked prefill 时，当邻近序列正在做长 prefill，TPOT 会飙到 50 ms。看 P99，不要看均值。

### E2E 延迟

`E2E = TTFT + TPOT * output_tokens + network_response`

输出较长（>500 token）时，E2E 由 TPOT 主导。输出短但 prompt 长时，E2E 由 TTFT 主导。报告按输出长度分桶的 E2E。

### 吞吐

`throughput = total_output_tokens / elapsed_time`

聚合指标。告诉你集群效率。不告诉你单个请求的健康状况。

### Goodput —— 你真正关心的指标

`goodput = fraction of requests meeting (TTFT <= a) AND (TPOT <= b) AND (E2E <= c)`

SLO 是一个多约束。只有当每个约束都满足时请求才算“好”。Goodput 就是这个占比。60% goodput 下的高吞吐是失败。99% goodput 下的较低吞吐才是目标。

2026 年，goodput 是 MLPerf Inference v6.0 提交以及 AI 平台厂商内部 SLA 追踪所用的指标。

### 为什么均值是错的统计量

LLM 延迟分布是右偏的。一个 decode batch 里有一个长 prefill 的邻居时，可能 500 个 token 的 TPOT 约 7 ms，20 个 token 的 TPOT 约 60 ms。均值 TPOT 是 9 ms。P99 TPOT 是 65 ms。用户会经常撞上 P99 —— 这正是他们离开的原因。

永远报告三元组（P50、P90、P99）。对用户体验而言，P99 才是你要优化的。

### 参考数字 —— 2026 年 TRT-LLM 上的 Llama-3.1-8B-Instruct

- mean TTFT：162 ms
- mean TPOT：7.33 ms
- mean E2E：1,093 ms
- P99 TPOT：视 chunked-prefill 配置在 10-25 ms 之间变化。

这些是 NVIDIA 公布的参考点。它们随模型规模（70B 会是 3-5 倍）、硬件（H100 vs B200 约 3 倍）和负载而变。

### 测量陷阱

2026 年最常用的两个 benchmark 工具在同一次运行上对 TPOT 给出不同结果：

- **NVIDIA GenAI-Perf**：在 ITL 计算中排除 TTFT。ITL 从第 2 个 token 开始。
- **LLMPerf**：包含 TTFT。ITL 从第 1 个 token 开始。

对一个 TTFT 500 ms、100 个输出 token、总 decode 700 ms 的请求，GenAI-Perf 报告 `ITL = 700/99 = 7.07 ms`，LLMPerf 报告 `ITL = 1200/100 = 12.00 ms`。工具选择改变了数字。

永远说明用的是哪个工具。永远公布定义。

### 构造 SLO

2026 年一个 70B 聊天模型合理的面向消费者 SLO：

- TTFT P99 <= 800 ms。
- TPOT P99 <= 25 ms。
- 输出 <300 token 时 E2E P99 <= 3 s。
- Goodput 目标 >= 99%。

企业级 SLO 会收紧 TTFT（200-400 ms）并放宽 E2E。关键是把它们写下来，测量三者，并把 goodput 作为单一综合指标追踪。

### 如何测量

- 跑真实流量或贴近真实的合成流量（LLMPerf 用 `--mean-input-tokens 800 --stddev-input-tokens 300 --mean-output-tokens 150`）。
- benchmark 运行按峰值并发的 2 倍设定目标。
- 跑 30-50 轮，对合并样本取百分位。
- 公布时带上工具名、工具版本、模型、硬件、并发、prompt 分布。

```figure
throughput-latency
```

## Use It

`code/main.py` 是一个玩具级 goodput 计算器。生成合成的延迟分布，套用一个 SLO，算出 goodput。它还展示了同一条 trace 上 GenAI-Perf 与 LLMPerf 的 TPOT 差异。

## Ship It

本课产出 `outputs/skill-slo-goodput-gate.md`。给定负载和 SLO，它产出一份可直接用于 CI/CD 的 benchmark 配方，以 goodput 而非吞吐作为部署门禁。

## Exercises

1. 运行 `code/main.py`。生成一个带 1% 尾部尖峰的分布。把 P99 TPOT 从 30 ms 收紧到 15 ms 时，goodput 如何变化？
2. 一个供应商宣称“Llama 3.3 70B H100 上 15,000 tok/s”。在相信它之前，说出你要问的三个问题。
3. 为什么 chunked prefill 能保护 P99 TPOT，却不能改善均值 TPOT？
4. 为一个语音助手（首 token 是被听到而非读到的）构造消费者 SLO。哪个指标对用户最可见？
5. 阅读 LLMPerf README 和 GenAI-Perf 文档。找出这三者之外工具之间还有分歧的其他三个指标。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| TTFT | “time to first token” | 排队 + 网络 + prefill；长 prompt 时由 prefill 主导 |
| TPOT | “time per output token” | 首 token 之后每个 token 的 memory-bound decode 开销 |
| ITL | “inter-token latency” | 多数工具中等于 TPOT（并非全部 —— 见 GenAI-Perf） |
| E2E | “end to end” | TTFT + TPOT * output_len；再加上响应侧网络 |
| Throughput | “tok/s” | 集群效率；没有延迟百分位就没用 |
| Goodput | “SLO-met rate” | 同时满足所有 SLO 约束的请求占比 |
| P99 | “tail” | 百分之一的最差延迟；用户体感指标 |
| SLO multi-constraint | “the joint” | 三个延迟上界的 AND；任一被违反即请求失败 |
| GenAI-Perf vs LLMPerf | “the tool trap” | 两个工具对 ITL 是否包含 TTFT 存在分歧 |

## Further Reading

- [NVIDIA NIM — LLM Benchmarking Metrics](https://docs.nvidia.com/nim/benchmarking/llm/latest/metrics.html) —— TTFT、ITL、TPOT 的权威定义。
- [Anyscale — LLM Serving Benchmarking Metrics](https://docs.anyscale.com/llm/serving/benchmarking/metrics) —— 另一种定义与测量配方。
- [BentoML — LLM Inference Metrics](https://bentoml.com/llm/inference-optimization/llm-inference-metrics) —— 真实部署上的应用测量。
- [LLMPerf](https://github.com/ray-project/llmperf) —— 基于 Ray 的开源 benchmark。
- [GenAI-Perf](https://github.com/triton-inference-server/perf_analyzer/blob/main/genai-perf/README.md) —— NVIDIA 的 benchmark 工具。
- [MLPerf Inference](https://mlcommons.org/benchmarks/inference-datacenter/) —— 业界公认的基于 goodput 的 benchmark。
