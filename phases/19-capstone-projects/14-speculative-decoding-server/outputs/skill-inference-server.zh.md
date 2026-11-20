---
name: inference-server
description: 交付一个采用 EAGLE-3 或 P-EAGLE draft、带 K8s 自动扩缩容的 speculative-decoding 推理服务器，并给出完整的 throughput/latency/cost 报告。
version: 1.0.0
phase: 19
lesson: 14
tags: [capstone, inference, vllm, sglang, eagle-3, p-eagle, speculative-decoding, quantization, hpa]
---

给定两个开源 target 模型（Llama 3.3 70B 与 Qwen3-Coder-30B MoE 或 GPT-OSS-120B），交付一套带 speculative decoding、量化和 Kubernetes 自动扩缩容的生产服务栈。发布实测加速比与尾延迟数据。

构建计划：

1. 在 vLLM 0.7（或 SGLang 0.4）下用 FP8 Marlin 量化部署 target 模型。
2. 从 Red Hat Speculators 加载对齐的 EAGLE-3 draft（或通过 SpecForge 训练一个）。
3. 基线数据：不开推测时 batch 1/8/32 下的 tokens/s 与 p50/p99 latency。
4. 启用 EAGLE-3。重跑同一套 benchmark。报告加速比、acceptance rate、p99 尾延迟变化。
5. 启用 P-EAGLE 并行推测；报告更深的树在何处有利、在何处有害的拐点。
6. 跨分布跑 benchmark：ShareGPT、HumanEval、领域数据。发布 acceptance rate 的漂移情况。
7. 在第二个 target 模型（MoE）上重复；找出 routing 噪声对 draft acceptance 的敏感度。
8. 部署到 Kubernetes，用 HPA 跟踪 `queue_wait_ms`。演示负载增至三倍时的横向扩容。
9. 在匹配的评测上对比相对 Anthropic Claude Sonnet 4.7 与 OpenAI GPT-5.4 的每 1M token 成本。

评估标准：

| 权重 | 评分标准 | 衡量方式 |
|:-:|---|---|
| 25 | 相对基线的实测加速 | 在两个模型上以同等质量实现 2.5 倍以上 throughput |
| 20 | 真实流量上的 acceptance rate | 按分布给出 acceptance rate 报告 |
| 20 | P99 尾延迟纪律 | batch 1/8/32 下，开与不开 speculative decoding 的 p99 |
| 20 | 运维 | K8s 部署、基于 queue-wait 的 HPA、平滑发布、先摘流再升级 |
| 15 | 文档与方法论 | 指标推导清晰、基线匹配 |

硬性淘汰项：

- 只报稳态 throughput 而不报尾延迟。
- HPA 依据 CPU 而不是 queue-wait。在 GPU 饱和时会来回震荡。
- 忽视 draft 与 target 的版本对齐。漂移的 draft 比不开推测更贵。
- 成本对比遗漏了托管 API 的 prompt 缓存折扣。

拒绝规则：

- 拒绝在没有滚动摘流的情况下上线服务。请求在途时原地升级属于不合格。
- 拒绝报告跨分布聚合后的 acceptance rate。必须按分布分别报告。
- 拒绝在没有匹配的非推测数字的情况下声称 speculative decoding 在 bs=32 时获胜。

交付物：一个仓库，包含 vLLM / SGLang 配置、EAGLE-3 draft 下载脚本、K8s 部署清单、基于 queue-wait 的 HPA 配置、ShareGPT / HumanEval / 领域数据的 benchmark harness、$/1M tokens 对比表，以及一份说明文档，点名 speculative decoding 引入的三个尾延迟回退，以及分别修复它们的缓解手段（batch gating、ngram 回退、量化微调）。
