---
name: finetuning-pipeline
description: 运行一条可复现的“数据到 SFT 到 DPO 到服务”微调流水线，带消融、量化和 2026 Model Openness Framework 的 model card。
version: 1.0.0
phase: 19
lesson: 07
tags: [capstone, fine-tuning, axolotl, trl, dpo, grpo, vllm, eagle-3, mof]
---

给定一个 base model（Llama 3.3 8B、Qwen3 14B 或 Gemma 3 12B）和一个任务特定数据集，构建一条单命令流水线，产出一个服务端点与一份可复现的 model card。

构建计划：

1. 数据阶段：Datatrove 去重、Nemotron-CC 风格质量过滤、Presidio PII 擦除、带种子的 train/val 切分。
2. 污染检查：对 MMLU-Pro、MT-Bench-v2、RewardBench-2 做 MinHashLSH。有重叠即拒绝。
3. SFT：Axolotl v0.8 配 ZeRO-3、Flash Attention 3、packed sequences，在 8xH100 上跑 2-3 个 epoch。
4. 偏好调优：TRL 0.15 DPO（或用可验证奖励的 GRPO）跑 1 个 epoch，扫 beta。
5. 量化：GPTQ-INT4-Marlin + AWQ-INT4 + GGUF-Q4_K_M。
6. 服务：带 EAGLE-3 speculative decoding 的 vLLM 0.7（草稿头经 Red Hat Speculators 或 SGLang SpecForge）。K8s deployment，按 queue-wait 的 HPA。
7. 评估：在 base/SFT-only/SFT+DPO/SFT+GRPO 上跑 lm-evaluation-harness、RewardBench-2、MT-Bench-v2、MMLU-Pro。
8. 安全：Llama Guard 4 通过率、ShieldGemma-2 输出过滤。
9. 按 2026 Model Openness Framework 的 model card，含数据、训练、评估、安全、可复现性章节。

评估评分表：

| 权重 | 标准 | 衡量方式 |
|:-:|---|---|
| 25 | 相对 base 的评估增益 | 在 MMLU-Pro、MT-Bench-v2、任务特定 benchmark 上测得的增益 |
| 20 | 流水线可复现性 | 用相同种子的一键重跑产出匹配的哈希 |
| 20 | 数据卫生 | 去重率、PII 擦除覆盖率、污染检查通过 |
| 20 | 服务效率 | batch 1/8/32 下的 tokens/s、EAGLE-3 接受率、$/1M tokens |
| 15 | Model card + 安全评估 | 2026 MOF 完整度 + Llama Guard 4 通过率 |

硬性驳回：

- 跳过 MinHash 污染检查的流水线。把 MMLU-Pro 泄漏进训练是经典的评估作弊失败模式。
- 没有附种子或 YAML 的训练运行。可复现性是硬性要求。
- 没有 EAGLE-3 或等价 speculative decoding 配置的服务。baseline 的 tokens/s 不是 2026 年的门槛。
- 缺少安全评估。每次微调都随附 Llama Guard 4 通过率。

拒绝规则：

- 拒绝发布一份声称 benchmark 分数却不附 lm-eval-harness commit SHA 的 model card。
- 拒绝在许可禁止衍生模型的数据上微调。MOF 会对数据许可评级。
- 拒绝在未于评估矩阵上测量质量损失的情况下交付量化模型。

产出：一个仓库，包含流水线编排器、Llama 3.3 8B + 一个备用 base 的 YAML、SFT 与 DPO 的 W&B 运行日志、量化产物、服务端点、三 benchmark 评估矩阵、安全评估、2026 MOF model card，以及一份关于你发现并修复的三个最大数据卫生问题的总结。
