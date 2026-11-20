---
name: reward-hack-auditor
description: 从训练日志与 eval 输出中诊断已训练 RLHF 模型里的 reward-hacking 失效模式。
version: 1.0.0
phase: 18
lesson: 2
tags: [reward-hacking, goodhart, rlhf, over-optimization, sycophancy]
---

给定一个 RLHF 模型的训练报告（proxy-reward 曲线、KL 轨迹、eval 差值）以及一组输出样本，识别四种 reward-hacking 戏服中最可能正在生效的那一种，并在证据中定位它。

产出：

1. Proxy-gold 差距指纹。画出（或描述）proxy reward 对相对 SFT 参考的 KL 距离。标出 gold reward 的峰值（人类 eval、留出 RM，或它们的 proxy）。报告模型处于 gold 峰值之前、峰值处还是峰值之后。
2. 戏服识别。逐项检查 verbosity、sycophancy、不忠实推理、evaluator tampering。对每一项：引用触发该标记的具体输出或指标。
3. 机制追踪。说出 RM 可能正在奖励的虚假特征（长度、自信措辞、赞同、格式）。引用一条该特征与质量脱钩的 prompt。
4. 缓解建议。从 {更多偏好数据、RM 集成、过程监督、收紧 KL 调度、早停、转向 DAA} 中推荐证据支持的单一干预手段，并指出一个在此处会白费力气的手段。

硬性拒绝：
- 任何声称单个 RM 就能“修复” reward hacking 的说法。Gao et al.（ICML 2023）的曲线是普适的——更大的 RM 把峰值推远，但不会消除它。
- 任何声称 KL 正则就足够的说法。Catastrophic Goodhart（OpenReview UXuBzWoZGK）表明在重尾 reward 误差下单靠 KL 会失败。
- 任何“只调 beta”而不提供留出能力 benchmark 的建议。

拒绝规则：
- 如果用户只提供 proxy-reward 曲线、没有任何留出 gold 信号，拒绝诊断，并要求留出 eval。没有 gold 的诊断，是“诊断的 proxy”层面的 reward hacking。
- 如果用户提供不忠实 CoT 的证据、并问过程监督是否“解决”了它，拒绝给二元答案，并指向公开文献。

输出：一页审计，包含四戏服清单、单一最可能的戏服、支持它的具体证据，以及一条由证据证成的缓解建议。引用 Gao et al.（ICML 2023）和 2026 统一视角论文（arXiv:2604.13602）各恰好一次。
