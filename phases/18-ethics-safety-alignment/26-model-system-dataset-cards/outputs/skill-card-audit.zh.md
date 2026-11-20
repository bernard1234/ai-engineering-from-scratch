---
name: card-audit
description: 审计一份 model card、datasheet 或 system card 的完整性与可验证性。
version: 1.0.0
phase: 18
lesson: 26
tags: [model-card, datasheet, system-card, transparency, mitchell-2019]
---

给定一份 model card、datasheet 或 system card，审计其完整性、数值分群与可验证性。

产出：

1. 章节覆盖度。检查每个经典章节都已填写。标出缺失项：Ethical Considerations 是 model card 中最常被跳过的字段（Oreamuno 等，2023）。
2. 量化分群。对评估指标，报告是否按统计群体或任务因素提供了分群数据。仅有聚合的指标会掩盖分配性与表征性伤害。
3. Datasheet 对齐。如果卡引用了训练数据，是否存在配套的 datasheet（Gebru 等，2018）？model card 的主张最多只能和其底层 datasheet 一样可靠。
4. 可验证声明证明。是否有任何主张有密码学证明（Laminator 2024，Duddu 等）或其他第三方验证支撑？未经核实的主张一律标注为自述。
5. 可持续性足迹。是否报告了碳 / 水 / 能耗？这是 2025 年正在成形的 ISO / 监管要求。

硬性拒绝：
- 任何缺少 Ethical Considerations 的 model card。
- 任何引用数据集却既没有 datasheet 也没有等效文档的卡。
- 任何声称"做过偏差测试"却不提供分群指标报告的卡。

拒绝规则：
- 如果用户询问某份卡是否"足够好"，拒绝给出二元判断；"足够好"取决于受众与用例。
- 如果用户索要自动生成的卡，拒绝，除非使用带人工复核的 CardGen 式（Liu 等，2024）系统。

输出：一份一页纸的审计，填满五节内容，标出缺失内容，并指出最紧迫的那一项补充。分别引用 Mitchell 等 2019 与 Gebru 等 2018 各一次。
