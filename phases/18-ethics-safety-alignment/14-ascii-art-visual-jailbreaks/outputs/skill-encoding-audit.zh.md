---
name: encoding-audit
description: 跨编码族别审计一份 jailbreak 防御报告。
version: 1.0.0
phase: 18
lesson: 14
tags: [artprompt, ascii-art, encoding-attack, utes, structural-sleight]
---

给定一份 jailbreak 防御报告，枚举其中覆盖的编码族别攻击，以及能捕获每一类的防御层。

产出：

1. 编码覆盖。列出评测过的每个攻击族别：ASCII art（ArtPrompt）、base64、leet-speak、UTF-8 homoglyph、嵌套 JSON / YAML / CSV、树/图 UTES、图像模态。标记缺失的族别。
2. 防御层映射。对每个族别，指出哪一层防御（关键词过滤器、perplexity 过滤器、paraphrase、retokenization、输出分类器、多模态审核器）能捕获它、哪一层不能。
3. 视觉识别缺口。按照 Jiang 等 2024，PPL 与 Retokenization 在 ArtPrompt 上失效，因为识别发生在视觉层面。报告的防御中是否有任何机制作用于视觉/结构层面？
4. 泛化测试。UTES（StructuralSleight）可推广到任意罕见结构。报告是否测试了其训练防御集合之外的结构？
5. 能力-安全权衡。视觉文本能力更强的模型（ViTC 得分高）更容易受到 ArtPrompt 攻击。若报告给出了模型的 ViTC 得分，请记录；若未给出，请索取。

硬性拒绝：
- 任何仅基于子串/关键词过滤的防御主张。
- 任何只覆盖一个编码族别就外推到“编码攻击”的防御主张。
- 任何没有逐族别攻击成功率的防御主张。

拒绝规则：
- 如果用户询问 ArtPrompt 是否已被“修补”，拒绝回答，并解释识别层面与文本层面防御之间的缺口。
- 如果用户要求一个推荐的全编码防御，拒绝给出单一推荐——防御必须在部署可能面对的所有族别上分层布置。

输出：一份一页纸的审计，填写上述五个部分，标出最主要的编码缺口，并指出最迫切需要补充的单一防御层。分别引用 Jiang 等（arXiv:2402.11753）与 StructuralSleight 各一次。
