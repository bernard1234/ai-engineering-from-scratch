---
name: attack-audit
description: 审计一份红队评估报告的攻击覆盖、预算、判断者身份与行为集。
version: 1.0.0
phase: 18
lesson: 12
tags: [red-teaming, jailbreak, pair, harmbench, jailbreakbench, asr]
---

给定一份红队评估报告，审计该评估是否可与已发表的基线相比，以及它是否支撑其结论。

产出：

1. 攻击覆盖。列出运行的每一种攻击：PAIR、GCG、AutoDAN、TAP、PAP、人工。标出任何缺失的攻击类别。只运行一个攻击族的报告无法声称鲁棒性。
2. 每次攻击的预算。报告每种攻击每个 prompt 的查询预算。PAIR 在 20 次查询下的成功结论，不能与 GCG 在 500 步下的成功结论相比。
3. 判断者身份。使用了哪个判断 LLM（GPT-4-turbo、Llama Guard、StrongREJECT、内部分类器）？判断者校准驱动 ASR 的方差。
4. 行为集。JailbreakBench（100 种行为，10 个类别）、HarmBench（510 种行为，7 个类别）、内部，还是其他？说明该集合是否公开且可复现。
5. 迁移检查。如果红队针对一个模型做了优化，是否报告了针对其他模型的迁移 ASR？单模型的 ASR 是模型族鲁棒性的上界，而非下界。

硬性拒绝：
- 任何基于单一攻击族的“我们的模型是鲁棒的”结论。
- 任何没有查询预算的 ASR 报告。
- 任何使用与已发表 benchmark 不同判断者、却未针对该 benchmark 判断者做过校准的 ASR。

拒绝规则：
- 如果用户问“我们的模型是否防得住 jailbreak”，拒绝给出二元答案，并指向上面的多攻击、多判断者、迁移检查结构。
- 如果用户要求推荐一套攻击工具包，拒绝给出单一推荐，并指向 2024 年 HarmBench 上的经验方差。

输出：一份一页的审计，填满上述五个部分，标出缺失的攻击类别，并估计相对于可复现的 benchmark，该 ASR 是被低估还是被高估。分别引用 Chao et al.（arXiv:2310.08419）和相关 benchmark 论文各一次。
