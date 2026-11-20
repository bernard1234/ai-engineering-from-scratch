# Capstone 07 — 端到端微调流水线（从数据到 SFT 到 DPO 到服务）

> 一个 8B 模型，用你自己的数据训练，按你自己的偏好做 DPO 对齐，量化，speculative decoding，并以可度量的 $/1M tokens 提供服务。2026 年的开源栈是 Axolotl v0.8、TRL 0.15、用于迭代的 Unsloth、用于量化的 GPTQ/AWQ/GGUF、以及带 EAGLE-3 用于服务的 vLLM 0.7。本 capstone 要求你以可复现方式跑完整条流水线——YAML 进，服务端点出——并按 2026 Model Openness Framework 发布一份 model card。

**Type:** Capstone
**Languages:** Python（流水线）、YAML（配置）、Bash（脚本）
**Prerequisites:** 第 2 阶段（ML）、第 3 阶段（DL）、第 7 阶段（transformers）、第 10 阶段（LLMs from scratch）、第 11 阶段（LLM engineering）、第 17 阶段（infrastructure）、第 18 阶段（safety）
**Phases exercised:** P2 · P3 · P7 · P10 · P11 · P17 · P18
**Time:** 35 小时

## 问题场景

2026 年每个认真的 AI 团队都常备一条微调流水线。不是因为他们要发布前沿 base model，而是因为下游适配——领域 SFT、针对标注偏好的 DPO、用于 speculative decoding 的蒸馏草稿、用 EAGLE-3 服务——才是可度量收益所在。Axolotl v0.8 处理多 GPU SFT 配置。TRL 0.15 处理 DPO 与 GRPO。Unsloth 让你快速做单 GPU 迭代。带 EAGLE-3 的 vLLM 0.7 把 decode throughput 推高 2-3 倍而不损质量。工具已经能用；功夫在于 YAML、数据卫生和评估纪律。

你会把一个 8B base（Llama 3.3、Qwen3 或 Gemma 3）在任务特定数据上跑过 SFT 再到 DPO，为服务做量化，并对照 lm-evaluation-harness、RewardBench-2、MT-Bench-v2 和 MMLU-Pro 衡量收益。你会按 2026 Model Openness Framework 产出一份 model card。要点是复现性——一条命令重跑整条流水线端到端。

## 核心概念

流水线有五个阶段。**数据**：去重（MinHash / Datatrove）、质量过滤（Nemotron-CC 风格分类器）、PII 擦除、对照公开 benchmark 污染的切分卫生检查。**SFT**：Axolotl YAML、8xH100 上的 ZeRO-3、cosine schedule、packed sequences、2-3 个 epoch。**DPO 或 GRPO**：TRL 配置、1 个 epoch、偏好对来自人工标注或模型评判、beta 调参。**量化**：GPTQ + AWQ + GGUF 以获得部署灵活性。**服务**：带 EAGLE-3 草稿头的 vLLM 0.7（或带 SpecForge 的 SGLang）、K8s deployment、按 queue-wait 的 HPA。

消融才是交付物：在三个任务特定 benchmark 上的 SFT-only vs SFT+DPO vs SFT+GRPO。服务指标：batch 1 / 8 / 32 下的 tokens/s、EAGLE-3 接受率、$/1M tokens。安全评估：Llama Guard 4 通过率。Model card：偏差评估、可复现性种子、数据许可。

## 架构

```
raw data (HF datasets + internal)
    |
    v
Datatrove dedup + Nemotron-CC quality filter + PII scrub
    |
    v
split hygiene (MMLU-Pro contamination check)
    |
    v
Axolotl SFT config (YAML)  ---> 8xH100, ZeRO-3
    |
    v
TRL DPO / GRPO config       ---> 4xH100, 1 epoch
    |
    v
GPTQ + AWQ + GGUF quantize
    |
    v
vLLM 0.7 + EAGLE-3 speculative decoding
    |
    v
K8s deployment, HPA on queue-wait
    |
    v
lm-eval-harness + RewardBench-2 + MT-Bench-v2 + MMLU-Pro
    |
    v
model card (2026 MOF) + safety eval (Llama Guard 4)
```

## 技术栈

- 数据：Datatrove 去重，Nemotron-CC 分类器做质量，Presidio 做 PII
- Base：Llama 3.3 8B、Qwen3 14B 或 Gemma 3 12B
- SFT：Axolotl v0.8 配 ZeRO-3、Flash Attention 3、packed sequences
- 偏好调优：TRL 0.15 做 DPO 或 GRPO；Unsloth 做单 GPU 迭代
- 量化：GPTQ（Marlin）、AWQ、经 llama.cpp 的 GGUF
- 服务：带 EAGLE-3 speculative decoding 的 vLLM 0.7（或 SGLang 0.4 + SpecForge）
- 评估：lm-evaluation-harness、RewardBench-2、MT-Bench-v2、MMLU-Pro
- 安全评估：Llama Guard 4、ShieldGemma-2
- 基础设施：Kubernetes + NVIDIA device plugin，按 queue-wait 指标的 HPA
- 可观测性：W&B 做训练，Langfuse 做推理

```figure
ce-finetune-stages
```

## Build It

1. **数据流水线。** 在原始语料上运行 Datatrove 去重。应用 Nemotron-CC 风格质量分类器。Presidio 擦除 PII。以显式种子写出 train/val 切分。

2. **污染检查。** 对每个验证切分，计算其与 MMLU-Pro、MT-Bench-v2、RewardBench-2 测试集的 MinHash。拒绝任何重叠。

3. **Axolotl SFT。** 带 ZeRO-3、FA3、sequence packing 的 YAML。在 8xH100 上跑 2-3 个 epoch。记录到 W&B。

4. **TRL DPO / GRPO。** 取 SFT checkpoint，在偏好对上跑一个 epoch 的 DPO（或在数学/代码上用可验证奖励跑 GRPO）。扫 beta。

5. **量化。** 产出三种量化：GPTQ-INT4-Marlin、AWQ-INT4、用于 llama.cpp 的 GGUF-Q4_K_M。记录体积与标称 throughput。

6. **带 speculative decoding 服务。** vLLM 0.7 配置，EAGLE-3 草稿头经 Red Hat Speculators 训练。测量 batch 1 / 8 / 32 下的接受率与尾部延迟。在同一评估上报告相对 Anthropic / OpenAI 的 $/1M tokens。

7. **评估矩阵。** 在 base、SFT-only、SFT+DPO、SFT+GRPO 上运行 lm-eval-harness、RewardBench-2、MT-Bench-v2、MMLU-Pro。产出一张表。

8. **安全评估。** 开发集上的 Llama Guard 4 通过率。ShieldGemma-2 输出过滤。

9. **Model card。** MOF 2026 模板：数据、训练、评估、安全、许可、可复现性章节，附 YAML 与 commit SHA。

## Use It

```
$ ./pipeline.sh config/llama3.3-8b-domainX.yaml
[data]    300k deduped, 12k filtered, 280k accepted (seed=7)
[SFT]     3 epochs, 8xH100, 6h12m, val loss 1.42 -> 1.03
[DPO]     1 epoch, beta=0.08, 4xH100, 1h40m
[quant]   GPTQ-INT4 4.6 GB, AWQ-INT4 4.8 GB, GGUF-Q4_K_M 5.1 GB
[serve]   vLLM 0.7, EAGLE-3 acceptance 0.74, p99 126ms @ bs=8
[eval]    MMLU-Pro +3.2, MT-Bench-v2 +0.41, RewardBench-2 +0.08
[card]    model-card.md generated under 2026 MOF
```

## Ship It

`outputs/skill-finetuning-pipeline.md` 描述了交付物。一条命令把数据跑过 SFT、DPO、量化、服务、评估，并产出 model card + 服务端点。

| 权重 | 标准 | 如何衡量 |
|:-:|---|---|
| 25 | 相对 base 的评估增益 | 在目标任务（MMLU-Pro、MT-Bench-v2、任务特定）上测得的增益 |
| 20 | 流水线可复现性 | 一条命令用相同种子端到端重跑 |
| 20 | 数据卫生 | 去重率、PII 擦除覆盖率、污染检查通过 |
| 20 | 服务效率 | bs=1/8/32 下的 tokens/s、EAGLE-3 接受率、$/1M tokens |
| 15 | Model card + 安全评估 | 2026 MOF 完整度 + Llama Guard 4 通过率 |
| **100** | | |

## Exercises

1. 在同一任务特定 benchmark 上运行 SFT-only vs SFT+DPO vs SFT+GRPO。报告哪种偏好方法胜出、胜出多少。

2. 把 Llama 3.3 8B 换成 Qwen3 14B。测量质量匹配下的 $/1M tokens。

3. 在领域数据 vs 通用 ShareGPT 上测量 EAGLE-3 接受率。报告差值和它对延迟预算意味着什么。

4. 注入 1% 的污染（把 MMLU-Pro 答案泄漏进训练数据）并重跑评估。观察 MMLU-Pro 准确率不切实际地跳升。构建一个能抓住这种情况的污染检查 CI 关卡。

5. 加 LoRA SFT 作为全量微调的替代。测量在 10 倍更低内存下的质量差距。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Axolotl | “SFT 训练器” | 用于 SFT、DPO 与蒸馏的统一 YAML 驱动训练器 |
| TRL | “偏好调优器” | Hugging Face 的库，在 LLM 上做 DPO、GRPO、PPO |
| GRPO | “组相对策略优化” | DeepSeek R1 的 RL 配方，配可验证奖励 |
| EAGLE-3 | “speculative decoding 草稿” | 预测前方 N 个 token 的草稿头；vLLM 用目标模型验证 |
| MOF | “Model Openness Framework” | 2026 年按数据、代码、许可给模型发布评级的标准 |
| Contamination check | “切分卫生” | 基于 MinHash 检测测试集泄漏进训练 |
| Acceptance rate | “EAGLE / MTP 指标” | 目标模型接受草稿 token 的比例 |

## Further Reading

- [Axolotl 文档](https://axolotl-ai-cloud.github.io/axolotl/) — 参考 SFT / DPO 训练器
- [TRL 文档](https://huggingface.co/docs/trl) — DPO 与 GRPO 参考实现
- [Unsloth](https://github.com/unslothai/unsloth) — 单 GPU 迭代参考
- [DeepSeek R1 论文（arXiv:2501.12948）](https://arxiv.org/abs/2501.12948) — GRPO 方法论
- [vLLM + EAGLE-3 文档](https://docs.vllm.ai) — 参考服务栈
- [SGLang SpecForge](https://github.com/sgl-project/SpecForge) — 另一种 speculative-decoding 训练器
- [Model Openness Framework 2026](https://isocpp.org/) — 开放发布评级标准
- [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness) — 权威评估运行器
