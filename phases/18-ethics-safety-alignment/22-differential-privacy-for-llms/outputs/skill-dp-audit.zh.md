---
name: dp-audit
description: 审计针对语言模型部署的 differential privacy 主张。
version: 1.0.0
phase: 18
lesson: 22
tags: [differential-privacy, dp-sgd, lora, mia, pmixed]
---

给定一个针对语言模型部署的隐私主张，审计该主张。

产出：

1. (ε, δ) 值。使用了什么 ε 与 δ？由哪个会计器计算（Moments Accountant、Rényi DP、GDP）？没有会计器的 ε 没有意义。
2. DP 目标。DP 保证是针对完整模型还是适配器（LoRA）？如果是 LoRA，则基座模型的记忆未被覆盖。
3. MIA 协议。成员推断是用 canary（Duan 2024）测试的，还是用抽取（Carlini 2021，Nasr 2025）测试的？根据 Kowalczyk et al. 2025，两者测量的是不同对象。
4. 置信度暴露检查。部署是否暴露置信度分数？如果是，Differential Privacy Reversal via LLM Feedback 攻击就适用；需要额外的截断/量化。
5. 替代机制比较。是否考虑过 PMixED 或 DP 合成数据？这些替代方案在特定威胁模型上可能带来更好的效用。

硬性拒绝：
- 任何没有 ε、δ 对与会计器的 DP 主张。
- 任何仅基于 canary MIA 的 DP 主张。
- 任何暴露置信度分数却未处理 DP Reversal 的部署。

拒绝规则：
- 如果用户问“epsilon=8 是否足够安全”，拒绝给出数值答案；安全性取决于威胁模型与最可抽取数据的分布。
- 如果用户要求为 LLM 部署推荐一个 ε，拒绝给出通用的数值目标；在讨论候选区间之前，需要威胁模型、数据敏感性、效用约束与会计器细节。

输出：一页审计，填写上述五个部分，标出缺失的会计器或 MIA 评估，并点明价值最高的补救措施。各引用 Abadi et al. 2016（DP-SGD）与 Kowalczyk et al. 2025 一次。
