---
name: moderation-stack
description: 为生产部署推荐一套 moderation 栈配置。
version: 1.0.0
phase: 18
lesson: 29
tags: [openai-moderation, perspective, llama-guard, layered-moderation, azure-content-safety]
---

给定一个生产部署，跨三层推荐一套 moderation 栈配置。

产出：

1. 输入分类器。选择 OpenAI Moderation、Llama Guard 3/4 或 Perspective API。与政策类别体系匹配。对多模态部署，选 Llama Guard 4 或 OpenAI omni-moderation。
2. 输出分类器。可与输入分类器相同或不同。阈值要与下游风险模型匹配。
3. 自定义领域规则。枚举通用分类器捕捉不到的领域特定规则：财务建议免责声明、医疗建议拒答、法律免责声明模式。
4. 边缘情况的裁判。明确人工升级路径。硬性拒绝是终局的；模糊案例在 SLA 内转人工复核。
5. 迁移计划。如果栈中还有 Azure Content Moderator，要在 2027 年 2 月退役前规划向 Azure AI Content Safety 迁移。

硬性拒绝：
- 任何没有输出 moderation 的部署（仅有输入是不够的）。
- 任何在受监管界面（金融、医疗、法律）上没有自定义领域规则的部署。
- 任何仅依赖 LLM 之前时代分类器（Perspective）来支撑现代聊天应用的部署。

拒绝规则：
- 如果用户索要唯一最佳分类器，拒绝——分类器的选择取决于政策类别体系。
- 如果用户索要阈值，拒绝给单一数字——阈值取决于风险容忍度与下游影响。

输出：一份一页纸的建议，填满五节内容，指出每一层所用的分类器，并标出迁移义务。分别引用 OpenAI Moderation 文档与 Llama Guard 3/4 参考资料各一次。
