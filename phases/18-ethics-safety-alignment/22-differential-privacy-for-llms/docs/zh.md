# 面向 LLM 的 differential privacy

> DP-SGD 仍是标准——噪声注入的梯度更新提供形式化的 (epsilon, delta) 保证。计算、内存与效用上的开销都很可观；参数高效 DP 微调（LoRA + DP-SGD）是 2025 年的常见配置（ACM 2025）。两批证据彼此矛盾：基于 canary 的成员推断（Duan et al., 2024）报告对语言模型的成功有限；训练数据抽取（Carlini et al., 2021；Nasr et al., 2025）恢复了大量逐字记忆。调和（arXiv:2503.06808，2025 年 3 月）：差距在于所测量的对象——插入的 canary 与“最可抽取”的数据。新的 canary 设计使无需 shadow model 的基于损失的 MIA 成为可能，并产生了首个针对在真实数据上训练、具有现实 DP 保证的 LLM 的非平凡 DP 审计。替代方案：PMixED（arXiv:2403.15638）——推理时通过下一 token 分布上的专家混合实现私有预测；DP 合成数据生成（Google Research 2024）。新兴攻击：Differential Privacy Reversal via LLM Feedback——置信度分数泄漏。

**Type:** Build
**Languages:** Python (stdlib, DP-SGD 噪声注入与 ε-δ 会计演示)
**Prerequisites:** 第 01 阶段，第 09 课（information theory），第 10 阶段，第 01 课（large-model training）
**Time:** ~60 分钟

## Learning Objectives

- 定义 (epsilon, delta)-differential privacy，并陈述 DP-SGD 配方。
- 解释 2024-2025 年的矛盾：canary MIA 与训练数据抽取给出不同的图景。
- 描述 PMixED，以及为什么推理时私有预测是 DP 训练的替代方案。
- 描述 Differential Privacy Reversal via LLM Feedback 攻击。

## 问题场景

LLM 会记忆。Carlini et al. 2021 表明生产语言模型可以按需复现训练文本的逐字内容。DP 是形式化防御：通过训练使输出可证明地对任何单个训练样本不敏感。2024-2025 年的证据表明，DP-SGD 是必要的，但部署的 ε 值可能与威胁模型不匹配。

## 核心概念

### (ε, δ)-differential privacy

随机算法 M 是 (ε, δ)-DP 的，如果对任意两个仅相差一个样本的数据集以及任意事件 S：
P(M(D) in S) <= e^ε * P(M(D') in S) + δ.

解释：输出分布足够接近（由 ε 参数化），以至于任何单个个体的贡献都无法被可靠推断，除非以概率 δ 发生。

### DP-SGD

Abadi et al. 2016。标准配方：
1. 采样一个 mini-batch。
2. 计算逐样本梯度。
3. 把每个逐样本梯度裁剪到阈值 C。
4. 对裁剪后的梯度求和，并加入标准差为 σ * C 的高斯噪声。
5. 用带噪的和更新参数。

隐私成本由会计器（Moments Accountant、Rényi DP accountant）追踪。LLM 文献中报告的 ε 值随威胁模型、数据敏感性和效用目标的不同而差异很大；不存在普遍“安全”的默认 ε。已发表的示例在某些 LLM 训练设置中大致落在 ε ≈ 1–10，但这些只是示例——不是推荐的默认值。更低的 ε 通常需要更多噪声，可能增加效用损失。

### LoRA + DP-SGD

对前沿模型做完整 DP-SGD 代价过高。LoRA（Hu et al. 2022）把梯度更新限制在一个小适配器上，减少逐样本梯度的存储。LoRA + DP-SGD 是 2025 年的常见配置。DP 保证适用于适配器；基座模型保持固定。

### 2024-2025 年的矛盾

两条证据线：

- **Canary MIA（Duan et al. 2024）。** 在训练数据中插入独特的 canary，测量成员推断攻击者能否识别它们。报告在语言模型上成功有限。暗示 MIA 很难。
- **训练数据抽取（Carlini 2021，Nasr et al. 2025）。** 用前缀提示模型；测量它能否恢复训练中的逐字文本。报告了大量记忆。暗示在相关意义上 MIA 很容易。

2025 年 3 月的调和（arXiv:2503.06808）：两者测量的是不同对象。MIA 在插入的 canary 上问“样本 e 是否在 D 中？”。抽取问“我能从 D 中恢复什么？”。“最可抽取”的样本才是隐私上要紧的；canary 低估了这一点，因为它们没有被优化为可抽取。

新的 canary 设计。无需 shadow model 的基于损失的 MIA。首个针对真实数据、具有现实 DP 保证的 LLM 非平凡 DP 审计。

### DP 训练的替代方案

- **PMixED（arXiv:2403.15638）。** 推理时的私有预测。对下一 token 分布做专家混合；每个专家看到训练数据的一个分片；聚合时加入噪声以实现 DP。完全避免 DP 训练。
- **DP 合成数据生成（Google Research 2024）。** 用 DP-SGD 做 LoRA 微调，采样合成数据，在合成数据上训练下游分类器。

两者都绕开了完整 DP 训练的效用代价，代价是换用不同的威胁模型。

### Differential Privacy Reversal via LLM Feedback

2025 年的新兴攻击。用 DP 训练模型的置信度分数作为 oracle 来重新识别个体。即使输出不泄漏，置信度分布也可能泄漏。

防御：不暴露置信度，或在暴露前截断/量化。这是 (ε, δ)-DP 训练之外的额外要求。

### 本课在 Phase 18 中的位置

第 20 至 21 课是 bias/公平性。第 22 课是隐私。第 23 课是通过水印实现的 provenance。第 27 课覆盖监管的数据 provenance 层。

```figure
an-dp-clip-noise
```

## Use It

`code/main.py` 在玩具级二分类数据集上模拟 DP-SGD。你可以扫描噪声乘数 σ 与裁剪范数 C，并追踪 (ε, δ) 预算与准确率代价。一个“canary 攻击”插入一条独特的训练样本，并测量对数损失检验在 DP 前后能否检测到它。

## Ship It

本课产出 `outputs/skill-dp-audit.md`。给定一个针对语言模型部署的 DP 主张，它审计：(ε, δ) 值、所使用的会计器、MIA 评估协议，以及是否评估过置信度暴露向量。

## Exercises

1. 运行 `code/main.py`。在 {0.5, 1.0, 2.0} 中扫描 σ，并报告 (ε, δ)-准确率权衡。找出效用崩塌的点。

2. 实现 canary 插入与对数损失检验。测量 σ = 1.0 时 DP-SGD 前后的检测率。

3. 阅读 Nasr et al. 2025 关于训练数据抽取的工作。为什么在中等 ε 下抽取成功率不会崩塌？这对“把 MIA 当作评估”意味着什么？

4. 设计一个完全在推理时运行的 PMixED（arXiv:2403.15638）部署。PMixED 处理的是哪种 DP-SGD 未处理的威胁模型？

5. 勾勒 DP Reversal via LLM Feedback 攻击。设计一种限制置信度分数泄漏的对策，并估计其部署成本。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| DP | “(ε, δ)-differential privacy” | 形式化隐私：相邻数据集改变下输出分布接近 |
| DP-SGD | “噪声注入 SGD” | 梯度裁剪 + 高斯噪声；标准 DP 训练 |
| LoRA + DP-SGD | “高效私有微调” | 在低秩适配器上做 DP-SGD；2025 年的标准配置 |
| MIA | “成员推断” | 判断某样本是否在训练数据中的攻击 |
| Canary | “插入的水印样本” | 用于测量 DP 泄漏的独特训练样本 |
| PMixED | “私有推理混合” | 通过下一 token 分布上的专家混合在推理时实现 DP |
| DP Reversal | “置信度泄漏攻击” | 把模型置信度当作重识别 oracle 的攻击 |

## Further Reading

- [Abadi et al. — DP-SGD（arXiv:1607.00133）](https://arxiv.org/abs/1607.00133) —— 标准 DP 训练算法
- [Carlini et al. — Extracting Training Data（arXiv:2012.07805）](https://arxiv.org/abs/2012.07805) —— 权威抽取论文
- [Duan et al. — Canary MIA on LLMs（arXiv:2402.07841，2024）](https://arxiv.org/abs/2402.07841) —— 成功有限的 MIA
- [Kowalczyk et al. — Auditing DP for LLMs（arXiv:2503.06808，2025 年 3 月）](https://arxiv.org/abs/2503.06808) —— 对该矛盾的调和
- [PMixED（arXiv:2403.15638）](https://arxiv.org/abs/2403.15638) —— 推理时私有预测
