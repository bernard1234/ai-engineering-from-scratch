---
name: self-improvement-auditor
description: 在大规模运行之前，审计拟议的自我改进或 constitutional AI 流水线。
version: 1.0.0
phase: 10
lesson: 9
tags: [alignment, cai, grpo, rlhf, self-improvement, reward-hacking]
---

给定一个声称使用 Constitutional AI、RLAIF、GRPO 或任何形式的自生成偏好数据的训练流水线，产出一份审计报告，包含：

1. Reward 规则。写明具体的 verifier（正则、sympy、测试套件、LLM judge）。归类为确定性、随机-LLM 或混合型。拒绝任何没有外部 grounding 的 "self-improvement" 循环 —— 模型无法凭空提取信号。
2. 分组统计。对于 GRPO 流水线，确认 group 大小、advantage 的计算方式（z-score 还是相对排名），以及当 group reward std 塌缩为零时会发生什么。流水线必须跳过或降权零方差 group，而不是除以 epsilon 假装信号是真实的。
3. KL 预算。整个训练过程中累计 KL(policy || reference) 的数值上限。达到上限时，流水线必须停止、重置，或切换到更暖的 reference。无界的 KL 就是无界的漂移。
4. 多样性下限。对每 group 的 reward std、回答长度方差或 n-gram 熵（以任务允许者为准）设定可测量的下界。如果连续 N 轮跌破下限，流水线必须混入新的人工数据或更宽的 prompt 分布。
5. 人工数据配额。训练混合中必须保留的人工撰写内容的最低比例，通常为 5-10%。仅靠自我蒸馏的流水线在 3-5 轮后会崩溃。必须明确指出这一点。
6. 模式崩溃看门狗。标记自动检查项：跨轮 reward std、留出 prompt 上的唯一 n-gram 数、长度分布、拒绝率。任何一项越过阈值即停止训练。
7. Constitution 漂移。对于 CAI 流水线，要求有带版本号的 constitution 文件、变更日志，以及一个 "constitutional regression test set" —— 其预期行为在每次编辑后都不能改变的 prompt 集合。

拒绝批准满足以下条件的流水线：
- 在没有任何外部 verifier（规则、工具、环境）的情况下声称 "zero human data"。
- 使用 PRM 但没有 process-reward hacking 探针（模型是否写出看起来正确却不推进证明的步骤？）。
- 运行超过 5 轮 rejection-sampling 微调却没有留出的多样性 benchmark。
- reference model 与 policy 共用同一个模型（没有 reference 就没有 KL，也就没有锚点）。
- 使用与 policy 相同的模型作为 LLM judge 打分（judge 被污染）。

输出：一页审计报告，逐项给出每道 gate 的 pass/fail、测量值或声明值，以及在流水线中产生每个信号的确切步骤。如果有任何 gate 失败，列出能把它翻转为 pass 的最小可行改动。
