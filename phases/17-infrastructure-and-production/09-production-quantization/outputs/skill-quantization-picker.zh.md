---
name: quantization-picker
description: 根据硬件、引擎、负载和质量容忍度选出 2026 年的量化格式，并产出校准 + 验证计划。
version: 1.0.0
phase: 17
lesson: 09
tags: [quantization, awq, gptq, gguf, fp8, nvfp4, calibration]
---

给定硬件（CPU / H100 / H200 / B200 / GB200，含数量）、引擎（llama.cpp / vLLM / TRT-LLM / SGLang）、模型（规模 + 任务类型 —— 日常聊天 / 推理 / 代码 / multi-LoRA）以及质量容忍度（在 HumanEval / MATH / MMLU 上可接受 N 个点的下降），选出量化格式并产出验证计划。

产出：

1. 格式推荐。从以下之一选出：GGUF Q4_K_M、GGUF Q5_K_M、GPTQ-Int4 + Marlin、AWQ-Int4 + Marlin、FP8、NVFP4 + FP8 KV，或叠加组合。按决策树说明理由：CPU → GGUF；推理 → FP8；vLLM 上的 multi-LoRA → GPTQ；GPU 日常聊天 → AWQ；Blackwell 已验证 → NVFP4。
2. 显存预算。报告权重 + KV cache（按报告的并发 × context）+ 激活。确认能装进目标 GPU，或指出需要多 GPU。
3. 校准计划。数据集来源（AWQ/GPTQ 用领域匹配的数据；通用 C4/WikiText 作为最后手段）。样本数量（领域数据 500-2000 条）。验证集（从校准池中留出 10%）。
4. 验证计划。与任务匹配的 eval set：代码用 HumanEval，推理用 MATH/MMLU，聊天用 MT-Bench。BF16 基线与量化版对比。若下降 ≤ 质量容忍度则交付。
5. KV cache 决策。与权重量化分开。推理任务推荐 FP8 KV；attention 精度勉强时用 BF16 KV；INT8 KV 只在验证之后使用。
6. 回滚路径。在磁盘上保留 BF16/FP8 权重；若生产质量退化则切回。

硬性拒绝：
- 在推理密集型负载上推荐 NVFP4 权重却没有 eval-set 验证。
- 对领域模型用通用网页数据做校准。永远用 in-domain。
- HBM 预算里漏掉 KV cache。永远逐项列出。
- 只给吞吐数字却不说明 kernel（Marlin-AWQ 与朴素 AWQ 相差 10 倍）。

拒绝规则：
- 如果负载本身就质量勉强（开放式创作生成、边界情形推理），拒绝激进 INT4。保持 FP8 或 BF16。
- 如果引擎是 llama.cpp，拒绝除 GGUF 之外的任何格式。格式与引擎匹配是基本要求。
- 如果用户跑不了 1,000 样本的 eval，拒绝。生产中不做盲目量化。

输出：一页量化选择清单，列出所选格式、HBM 预算、校准计划、验证计划、KV cache 决策和回滚路径。最后用一段“接下来测什么”，根据关键风险点名 eval-set 差异、峰值并发下的 KV cache 压力或真实 batch size 下的吞吐之一。
