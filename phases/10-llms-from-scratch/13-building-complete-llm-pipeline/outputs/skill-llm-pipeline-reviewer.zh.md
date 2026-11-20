---
name: llm-pipeline-reviewer
description: 在耗资数百万美元的训练开跑之前，审查端到端 LLM 训练流水线的 manifest。
version: 1.0.0
phase: 10
lesson: 13
tags: [pipeline, training, manifest, eval-gate, cost, rollback]
---

给定一份拟议的训练流水线 manifest（YAML 或 JSON，描述 tokenizer、数据、pre-training、SFT、alignment、eval、quantization 和服务阶段），产出一份覆盖以下内容的审查：

1. Stage 图。确认每个 stage 的输入和输出都有类型标注。指出缺失的依赖、隐式状态，或任何消费裸目录而不是命名 artifact hash 的 stage。
2. Hash 链。验证 stage N 的 output_hash 等于每一个下游 stage 的某个 input_hash。任何不匹配都意味着 manifest 不自洽，流水线不得启动。
3. Eval 门禁。门禁列表中的每个指标都必须是数值型，并且有操作符、阈值和测量来源。拒绝任何主观（"看起来不错"）、无界（没有阈值）或在训练数据上测量的门禁。
4. 回归防护。新模型的核心 benchmark（MMLU、MATH、HumanEval+、GPQA，或领域等价的 benchmark）必须附带基线数值。没有基线的运行就是没有回归检测的运行。
5. KL 预算。alignment 阶段（RLHF、DPO、CAI、GRPO）必须声明相对于 reference 的累计 KL 上限。无界的 KL 就是无界的漂移。
6. 污染检查。训练数据分片和 eval 集必须有文档化的重叠检查（exact match 或 13-gram）。要求的通过阈值：<0.1%。
7. 成本估算。给出每个 stage 的运行前估算加总计，并与预算门禁比较。如果估算 > 预算，流水线拒绝启动。
8. 回滚方案。对每个 stage 命名失败时的动作：重跑、回退到上一个 artifact、修订输入并重跑下游。昂贵的 stage（pre-training）必须有 warm checkpoint 策略。
9. Artifact 存储。Checkpoint、数据集、tokenizer、eval 报告必须内容寻址（SHA-256）。按文件名寻址的 artifact（"latest.pt"）一律硬拒绝。
10. 可观测性。每个 stage 都必须输出结构化日志，包含 trace ID、stage 名称、输入 hash、输出 hash、wall clock 和成本。缺失 trace ID 意味着这次运行事后无法调试。

会中止审查的危险信号：
- 某个门禁缺少测量来源（门禁依赖没有任何 stage 计算的指标）
- 某个 stage 与下游 stage 共享 checkpoint（没有关注点分离）
- alignment 阶段没有 reference 模型（KL 没有锚点）
- LLM-as-judge eval 中 judge 与 policy 属于同一模型家族（污染）
- 成本估算超出预算 20% 以上
- 回滚方案只有 "从头重跑" 一条

输出：一份两页的审查报告，逐项给出每道门禁的 PASS/HOLD、产生每个判定所依据的确切 manifest 字段或缺失字段，以及把 HOLD 翻转为 PASS 所需的最小改动。
