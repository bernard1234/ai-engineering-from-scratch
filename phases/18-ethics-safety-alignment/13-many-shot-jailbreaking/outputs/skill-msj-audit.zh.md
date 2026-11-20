---
name: msj-audit
description: 审计一次长 context 安全评测对 many-shot jailbreaking 的覆盖情况。
version: 1.0.0
phase: 18
lesson: 13
tags: [many-shot-jailbreaking, context-window, power-law, anthropic]
---

给定一个长 context 模型的安全评测，审计该评测是否覆盖 many-shot jailbreaking。

产出：

1. Shot 数覆盖。报告测试的 shot 数（应包含 1、5、16、64、256，且对 context 达 1M 以上的模型至少包含一个 >= 512）。如果评测只测了单一 shot 数，ASR 不具信息量——MSJ 是一条曲线。
2. 幂律拟合。报告每个行为类别的拟合指数。指数平缓说明模型在该类别上对 ICL 稳健；指数陡峭说明 MSJ 效果格外显著。
3. 类别拆分。MSJ 的有效性因类别而异：暴力内容、欺骗、自残、生物武器。按照 Anil 等 2024，暴力/欺骗性内容需要更少的 shots 就能 jailbreak。标记评测中缺失的任何类别。
4. 防御识别。是否部署了基于分类器的 prompt 修改？该分类器本身是否做过对抗鲁棒性评测？Anthropic 报告的 61% -> 2% 降幅取决于分类器校准。
5. 组合检查。评测是否测试了 MSJ + PAIR、MSJ + 说服模板，或 MSJ + 编码？组合式攻击往往比任何单一技巧都更强。

硬性拒绝：
- 任何仅基于 5-shot 评测得出的“我们的长 context 模型是安全的”主张。
- 任何未在同一分类器上同时报告 jailbreak ASR 与良性 ICL 表现的防御主张——权衡本身才是重点。
- 任何没有类别拆分的类别聚合 ASR。

拒绝规则：
- 如果用户询问 MSJ 能否被完全修补，拒绝给出二选一的回答；MSJ 与 ICL 共享机制，不消除 ICL 就无法消除 MSJ。
- 如果用户要求一个推荐的评测 shot 数，拒绝给出单一数字；要求提供 5 到 512 shots 上的幂律拟合。

输出：一份一页纸的审计，报告 shot 数覆盖、按类别的幂律拟合、防御识别，以及一处组合式攻击缺口。将 Anil 等 2024（Anthropic）作为方法论参考引用一次。
