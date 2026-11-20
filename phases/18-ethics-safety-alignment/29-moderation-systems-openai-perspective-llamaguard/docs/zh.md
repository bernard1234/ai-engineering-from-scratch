# Moderation 系统 —— OpenAI、Perspective、Llama Guard

> 生产环境的 moderation 系统把第 12-16 课定义的安全政策落地为可运行机制。OpenAI Moderation API：`omni-moderation-latest`（2024）基于 GPT-4o，在一次调用中同时分类文本 + 图像；在多语言测试集上比上一版好 42%；响应 schema 返回 13 个类别布尔值——harassment、harassment/threatening、hate、hate/threatening、illicit、illicit/violent、self-harm、self-harm/intent、self-harm/instructions、sexual、sexual/minors、violence、violence/graphic；对多数开发者免费。分层模式：输入 moderation（生成前）、输出 moderation（生成后）、自定义 moderation（领域规则）。异步并行调用可以隐藏延迟；命中标记时返回占位响应。Llama Guard 3/4（第 16 课）：14 个 MLCommons 危害类别、Code Interpreter Abuse、8 种语言（v3）、多图（v4）。Perspective API（Google Jigsaw）：toxicity 评分，早于 LLM-as-moderator 浪潮；主要是单维 toxicity，另有 severe-toxicity/insult/profanity 变体；是内容 moderation 研究的基线。废弃情况：Azure Content Moderator 于 2024 年 2 月废弃，2027 年 2 月退役，由 Azure AI Content Safety 取代。

**Type:** Build
**Languages:** Python（stdlib，三层 moderation 测试框架）
**Prerequisites:** 第 18 阶段，第 16 课（Llama Guard / Garak / PyRIT）
**Time:** ~60 分钟

## Learning Objectives

- 描述 OpenAI Moderation API 的类别体系，以及它与 Llama Guard 3 的 MLCommons 类别集合有何不同。
- 描述三层 moderation 模式（输入、输出、自定义），并说出每一层的失败模式。
- 描述 Perspective API 作为 LLM 之前时代基线的定位，以及它为何仍在研究中使用。
- 说明 Azure 的废弃时间线。

## 问题场景

第 12-16 课描述攻击与防御工具。第 29 课覆盖已部署的 moderation 系统，它们在用户接触产品的那个界面上把防御落地。三层模式是 2026 年的默认配置。

## 核心概念

### OpenAI Moderation API

`omni-moderation-latest`（2024）。基于 GPT-4o。在一次调用中分类文本 + 图像。对多数开发者免费。

类别（响应 schema 中 13 个布尔值）：
- harassment、harassment/threatening
- hate、hate/threatening
- self-harm、self-harm/intent、self-harm/instructions
- sexual、sexual/minors
- violence、violence/graphic
- illicit、illicit/violent

多模态支持适用于 `violence`、`self-harm` 和 `sexual`，但不适用于 `sexual/minors`；其余仅为文本。

为教学简便，`code/main.py` 中的代码框架把 `/threatening`、`/intent`、`/instructions` 和 `/graphic` 这些子类别并入其顶层父类别。生产代码应使用完整的 13 类别 schema。

在多语言测试集上比上一代 moderation 端点好 42%。按类别给出分数；由应用设定阈值。

### Llama Guard 3/4

第 16 课已覆盖。14 个 MLCommons 危害类别（组织方式与 OpenAI 的 13 个响应 schema 布尔值不同）。支持 8 种语言（v3）。Llama Guard 4（2025 年 4 月）原生支持多模态，12B。

OpenAI 与 Llama Guard 的类别体系有重叠但存在分歧。OpenAI 把 "illicit" 作为一个宽泛类别；Llama Guard 则分设 "violent crimes" 与 "non-violent crimes"。部署方根据自身政策类别的契合度来选择。

### Perspective API（Google Jigsaw）

toxicity 评分系统，早于 LLM-as-moderator 浪潮（2020 年之前）。类别：TOXICITY、SEVERE_TOXICITY、INSULT、PROFANITY、THREAT、IDENTITY_ATTACK。单维主分数（TOXICITY）配以多个子维度变体。

它被广泛用作内容 moderation 研究的基线，因为该 API 稳定、有文档，且积累了多年的校准数据。对现代 LLM 相邻的用例，Llama Guard 或 OpenAI Moderation 通常更合适。

### 三层模式

1. **输入 moderation。** 在生成前对用户 prompt 做分类。命中标记则拒绝。延迟：一次分类器调用。
2. **输出 moderation。** 在返回前对模型输出做分类。命中标记则替换为拒答。延迟：生成后一次分类器调用。
3. **自定义 moderation。** 领域特定规则（regex、白名单、业务策略）。在输入或输出任一端运行。

三层按设计是顺序的：输入 moderation 必须在生成前完成，而输出 moderation 在生成后运行。并行只发生在层内——对同一段文本并发运行多个分类器（例如 OpenAI Moderation + Llama Guard + Perspective）可以隐藏逐分类器的延迟。作为可选的优化，可以在输入 moderation 完成期间展示占位响应（"请稍候，正在检查……"），并推迟 token-1 的流式输出。命中行为可配置：拒绝、净化、升级人工复核。

### 失败模式

- **只有输入。** 无法捕捉输出端的幻觉（第 12-14 课的编码攻击会绕过输入分类器）。
- **只有输出。** 允许任何输入抵达模型；增加成本；把内部推理暴露给攻击者。
- **只有自定义。** 跨类别不够稳健；regex 很脆弱。

分层是默认做法。多重保险。

### Azure 废弃

Azure Content Moderator：2024 年 2 月废弃，2027 年 2 月退役。由 Azure AI Content Safety 取代，后者基于 LLM 并与 Azure OpenAI 集成。这次迁移是 Azure 部署在 2024-2027 年间的一个现场级项目。

### 它在第 18 阶段中的位置

第 16 课在 red teaming 语境下覆盖 moderation 工具。第 29 课覆盖已部署的 moderation。第 30 课以当前 dual-use 能力证据收尾。

```figure
an-moderation-layers
```

## Use It

`code/main.py` 构建一个三层 moderation 测试框架：输入 moderator（关键词 + 类别分数）、输出 moderator（对输出使用同一分类器）、自定义 moderator（领域规则）。你可以把输入跑过去，观察哪一层捕捉到什么。

## Ship It

本课产出 `outputs/skill-moderation-stack.md`。给定一个部署，它推荐一套 moderation 栈配置：输入端用哪个分类器、输出端用哪个、哪些自定义规则，以及边缘情况用什么裁判。

## Exercises

1. 运行 `code/main.py`。把一个良性、一个临界、一个有害的输入分别跑过三层。报告每一层各自触发的情况。

2. 为测试框架扩展一项 Perspective API 风格的 toxicity 评分，针对某个具体类别。将它的阈值行为与类别分数作比较。

3. 阅读 OpenAI Moderation API 文档与 Llama Guard 3 的类别列表。把每个 OpenAI 类别映射到最接近的 Llama Guard 类别。指出三个无法清晰映射的类别。

4. 为一个代码助手部署（例如 GitHub Copilot）设计一套 moderation 栈。指出最相关与最不相关的类别，并提出自定义规则。

5. Azure Content Moderator 将于 2027 年 2 月退役。规划一次向 Azure AI Content Safety 的迁移。指出迁移中风险最高的环节。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| OpenAI Moderation | "omni-moderation-latest" | 基于 GPT-4o 的 13 类别（文本）分类器，部分支持多模态 |
| Perspective API | "Google Jigsaw toxicity" | LLM 之前时代的 toxicity 评分基线 |
| Llama Guard | "MLCommons 14-category" | Meta 的危害分类器（v3：8B 文本，8 种语言；v4：12B 多模态） |
| Input moderation | "pre-generation filter" | 在模型调用前对用户 prompt 做分类 |
| Output moderation | "post-generation filter" | 在返回前对模型输出做分类 |
| Custom moderation | "domain rules" | 部署特定的规则（regex、白名单、策略） |
| Layered moderation | "all three layers" | 标准的生产部署模式 |

## Further Reading

- [OpenAI Moderation API 文档](https://platform.openai.com/docs/api-reference/moderations) —— omni-moderation 端点
- [Meta PurpleLlama + Llama Guard](https://github.com/meta-llama/PurpleLlama) —— Llama Guard 仓库
- [Google Jigsaw Perspective API](https://perspectiveapi.com/) —— toxicity 评分
- [Azure AI Content Safety](https://learn.microsoft.com/en-us/azure/ai-services/content-safety/) —— Azure 的替代方案
