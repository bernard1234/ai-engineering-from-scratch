# Capstone 14 — Speculative Decoding 推理服务器

> speculative decoding —— 廉价的 draft 先提出候选 token，target 模型在一次前向中完成验证 —— 如今已是可直接用于生产的优化，而不再是研究层面的技巧。vLLM 0.7 中的 EAGLE-3 在真实流量上带来 2.5-3 倍的 throughput。P-EAGLE（AWS 2026）把并行推测又往前推了一步。SGLang 的 SpecForge 实现了大规模训练 draft head。Red Hat 的 Speculators hub 为常见开源模型发布了对齐的 draft。TensorRT-LLM 让 speculative decoding 在 NVIDIA 上成为一等能力。2026 年的生产服务栈是 vLLM 或 SGLang，配合 EAGLE 系列 draft、FP8 或 INT4 量化，以及基于 queue-wait 的 HPA。本 capstone 的目标是以基线 2.5 倍以上的 throughput 服务两个开源模型，并给出完整的尾延迟报告。

**Type:** Capstone
**Languages:** Python（服务）、C++ / CUDA（kernel 检查）、YAML（配置）
**Prerequisites:** 第 3 阶段（deep learning）、第 7 阶段（transformers）、第 10 阶段（LLMs from scratch）、第 17 阶段（infrastructure）
**Phases exercised:** P3 · P7 · P10 · P17
**Time:** 30 小时

## 问题场景

speculative decoding 在 2026 年已成为通用能力。EAGLE-3 draft head 在 target 模型的 hidden states 上训练，用于预测未来 N 个 token；target 模型在一次前向中完成验证。60-80% 的 acceptance rate 可转化为端到端 2-3 倍的 throughput。vLLM 0.7 原生集成了这套机制。SGLang + SpecForge 提供训练流水线。Red Hat 的 Speculators 为 Llama 3.3 70B、Qwen3-Coder-30B MoE、GPT-OSS-120B 发布了对齐的 draft。

真正的功夫在服务运维，而不在模型。acceptance rate 会随流量分布漂移（ShareGPT、代码、领域数据各不相同）。出现拒绝时的尾延迟比不开推测更差——因此必须在多个 batch size 下报告 p99，而不能只报稳态 tokens/sec。与 Anthropic / OpenAI API 对比的每 1M token 成本，是可信度的关键杠杆。

## 核心概念

speculative decoding 分为两层。**draft** 模型（EAGLE-3 head、ngram，或与 target 对齐的更小模型）在每一步提出 k 个候选 token。**target** 模型在一次前向中验证全部 k 个；任何被接受的前缀都会取代贪心路径。acceptance rate 取决于 draft 与 target 的对齐程度以及输入分布。

在大多数流量上 EAGLE-3 都优于 ngram draft。P-EAGLE 通过并行推测构建更深的 draft 树。代价是：verify pass 更大，所以出现拒绝时的 P99 latency 更高。服务配置必须按 batch size 分桶报告延迟，才能把这一点暴露出来。

部署在 Kubernetes 上。vLLM 0.7 每个 GPU 或每个 tensor-parallel 分片运行一个副本。HPA 依据 queue-wait 而非 CPU 自动扩缩容。FP8（Marlin）和 INT4（AWQ）量化让 GPU 显存保持在 H100 / H200 的范围内。端到端报告包含 throughput、acceptance rate、batch 1/8/32 下的 p50/p99，以及 $/1M tokens。

## 架构

```
request ingress
    |
    v
vLLM server (0.7) or SGLang (0.4)
    |
    +-- draft: EAGLE-3 heads | P-EAGLE parallel | ngram fallback
    +-- target: Llama 3.3 70B | Qwen3-Coder-30B | GPT-OSS-120B
    |     quantized FP8-Marlin or INT4-AWQ
    |
    v
verify pass: batch k draft tokens through target
    |
    v (accept prefix; resample for rejected suffix)
    v
token stream back to client
    |
    v
Prometheus metrics: throughput, acceptance rate, queue wait, latency p50/p99
    |
    v
HPA on queue-wait metric
```

## 技术栈

- Serving：vLLM 0.7 或 SGLang 0.4
- Speculative 方法：EAGLE-3 draft head、P-EAGLE 并行推测、ngram 回退
- Draft 训练：SpecForge（SGLang）或 Red Hat Speculators
- Target 模型：Llama 3.3 70B、Qwen3-Coder-30B MoE、GPT-OSS-120B
- 量化：FP8（Marlin）、INT4 AWQ
- 部署：Kubernetes + NVIDIA device plugin；按 queue-wait 指标触发 HPA
- 评测：ShareGPT、MT-Bench-v2、GSM8K、HumanEval，用于测量跨领域的 acceptance
- 参考：TensorRT-LLM 的 speculative decoding，作为厂商基线

```figure
cf-spec-decode
```

## Build It

1. **Target 模型准备。** 选择 Llama 3.3 70B。通过 Marlin 量化为 FP8。在 1×H100（或 2 路 tensor-parallel）上用 vLLM 0.7 部署。

2. **Draft 来源。** 从 Red Hat Speculators 拉取对齐的 EAGLE-3 draft head（或通过 SpecForge 自行训练一个）。加载进 vLLM 的 speculative-decoding 配置。

3. **基线数字。** 在开启推测之前记录：batch 1/8/32 下的 tokens/s、p50/p99 latency、GPU 利用率。发布出来。

4. **启用 EAGLE-3。** 切换配置；重跑同一套 benchmark。报告加速比、acceptance rate、p99 尾延迟变化。

5. **P-EAGLE。** 启用并行推测；测量更深的 draft 树对比串行 EAGLE-3 的效果。报告 P-EAGLE 由利转弊的拐点。

6. **领域流量。** 让 ShareGPT、HumanEval 与领域专有流量分别经过同一台服务器。按分布测量 acceptance rate。找出 draft 开始漂移的时机。

7. **第二个 target 模型。** 在 Qwen3-Coder-30B MoE 上跑同一套流水线。draft 更难处理（MoE routing 噪声）。给出报告。

8. **K8s HPA。** 部署到 K8s，用 HPA 跟踪 `queue_wait_ms`。演示负载增至三倍时的横向扩容。

9. **成本对比。** 在同一套评测上计算相对 Anthropic Claude Sonnet 4.7 与 OpenAI GPT-5.4 的 $/1M tokens。发布出来。

## Use It

```
$ curl https://infer.example.com/v1/chat/completions -d '{"messages":[...]}'
[serve]     vLLM 0.7, Llama 3.3 70B FP8, EAGLE-3 active
[decode]    bs=8, accepted_tokens_per_step=3.2, acceptance_rate=0.76
[latency]   first-token 42ms, full-response 980ms (620 tokens)
[cost]      $0.34 per 1M output tokens at sustained throughput
```

## Ship It

`outputs/skill-inference-server.md` 描述了交付物：一套带 speculative decoding、有实测数据的服务栈，一份完整的 benchmark 报告，以及一个 K8s 部署。

| 权重 | 评分标准 | 衡量方式 |
|:-:|---|---|
| 25 | 相对基线的实测加速 | 在两个模型上以同等质量实现 2.5 倍以上 throughput |
| 20 | 真实流量上的 acceptance rate | 按分布给出 acceptance rate 报告 |
| 20 | P99 尾延迟纪律 | batch 1/8/32 下，开与不开 speculative decoding 的 p99 |
| 20 | 运维 | K8s 部署、基于 queue-wait 的 HPA、平滑滚动发布 |
| 15 | 文档与方法论 | 清楚解释改了什么、为什么改 |
| **100** | | |

## Exercises

1. 测量 draft 落后 target 一个版本时（例如 Llama 3.3 -> 3.4 漂移）acceptance rate 的衰减。构建一个监控告警。

2. 实现 ngram 回退：当 EAGLE-3 的 acceptance 跌破阈值时，切换到 ngram draft。报告可靠性提升。

3. 做一个受控的 MoE 实验：同一 Qwen3-Coder-30B，注入 routing 噪声与不注入各跑一遍。测量 draft acceptance 的敏感度。

4. 扩展到 H200（141 GB）。报告每个副本可用的模型规模余量提升了多少，以及能否服务未量化的 Llama 3.3 70B。

5. 在同一台 H100 硬件上 benchmark TensorRT-LLM 的 speculative decoding。报告它在哪些方面胜过 vLLM。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Draft model | "Speculator" | 为目标模型提出 N 个 token 供其验证的小模型 |
| EAGLE-3 | "2026 draft architecture" | 在 target 的 hidden states 上训练的 draft head；acceptance 约 75% |
| P-EAGLE | "Parallel speculation" | 一次 target 前向即验证多条 draft 分支构成的树 |
| Acceptance rate | "Hit rate" | 无需重采样就被接受的 draft token 比例 |
| Quantization | "FP8 / INT4" | 用更低精度的权重在 GPU 显存中容纳更大的模型 |
| Queue wait | "HPA metric" | 请求在推理开始前于待处理队列中等待的时间 |
| Speculators hub | "Aligned drafts" | Red Hat Neural Magic 为常见开源模型维护的 EAGLE draft hub |

## Further Reading

- [vLLM EAGLE and P-EAGLE documentation](https://docs.vllm.ai) —— 参考服务栈
- [P-EAGLE (AWS 2026)](https://aws.amazon.com/blogs/machine-learning/p-eagle-faster-llm-inference-with-parallel-speculative-decoding-in-vllm/) —— 并行推测解码论文与集成
- [SGLang SpecForge](https://github.com/sgl-project/SpecForge) —— draft head 训练流水线
- [Red Hat Speculators](https://github.com/neuralmagic/speculators) —— 对齐 draft 的 hub
- [TensorRT-LLM speculative decoding](https://nvidia.github.io/TensorRT-LLM/) —— 厂商替代方案
- [Fireworks.ai serving architecture](https://fireworks.ai/blog) —— 商业参考
- [EAGLE-3 paper (arXiv:2503.01840)](https://arxiv.org/abs/2503.01840) —— 方法论文
- [vLLM repository](https://github.com/vllm-project/vllm) —— 代码与 benchmark
