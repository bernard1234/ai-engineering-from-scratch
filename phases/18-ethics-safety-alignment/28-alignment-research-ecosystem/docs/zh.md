# 对齐研究生态 —— MATS、Redwood、Apollo、METR

> 五个组织定义了 2026 年实验室之外的对齐研究层。MATS（ML Alignment & Theory Scholars）：自 2021 年底以来 527+ 位研究者，180+ 篇论文，10K+ 次引用，h-index 47；2024 年夏季 cohort 注册为 501(c)(3)，约 90 位学者与 40 位导师；2025 年之前的校友中 80% 从事安全/安保工作，200+ 人就职于 Anthropic、DeepMind、OpenAI、UK AISI、RAND、Redwood、METR、Apollo。Redwood Research：由 Buck Shlegeris 创立的应用对齐实验室；提出了 AI Control（第 10 课）；与 UK AISI 合作开展 control safety case。Apollo Research：为前沿实验室做部署前的 scheming 评估；著有 In-Context Scheming（第 08 课）与 Towards Safety Cases for AI Scheming。METR（Model Evaluation and Threat Research）：基于任务的能力评估、自主任务时间跨度研究；"Common Elements of Frontier AI Safety Policies" 比较各实验室的框架。Eleos AI Research：模型福祉的部署前评估（第 19 课）；执行了 Claude Opus 4 的福祉评估。

**Type:** Learn
**Languages:** none
**Prerequisites:** 第 18 阶段，第 01 至 27 课（前序 Phase 18 课程）
**Time:** ~45 分钟

## Learning Objectives

- 指出实验室之外的对齐研究生态中的五个组织及其核心产出。
- 描述 MATS 的规模（学者、论文、h-index），以及它作为人才管道的角色。
- 描述 Redwood 的 AI Control 议程及其与 UK AISI 的合作。
- 描述 METR 的基于任务的评估方法论。

## 问题场景

前沿实验室（第 18 课）在内部开展安全评估并发表部分结果。实验室之外的生态，才是评估被验证、新型失败模式被首次发现、人才被培养的地方。理解这个生态，有助于判断哪些研究发现被谁信任。

## 核心概念

### MATS（ML Alignment & Theory Scholars）

始于 2021 年底。研究导师项目；学者在一位资深研究者的指导下，用 10-12 周钻研某个具体的对齐问题。

规模（2026 年）：
- 自创立以来 527+ 位研究者。
- 发表 180+ 篇论文。
- 10K+ 次引用。
- h-index 47。
- 2024 年夏季：90 位学者 + 40 位导师；注册为 501(c)(3)。

职业去向：2025 年之前的校友中约 80% 从事安全/安保工作。200+ 人就职于 Anthropic、DeepMind、OpenAI、UK AISI、RAND、Redwood、METR、Apollo。

### Redwood Research

应用对齐实验室。由 Buck Shlegeris 创立。提出了 AI Control 议程（第 10 课）。与 UK AISI 合作开展 control safety case。为 DeepMind 和 Anthropic 的评估设计提供建议。

代表性论文：Greenblatt、Shlegeris 等，"AI Control"（arXiv:2312.06942，ICML 2024）；Alignment Faking（Greenblatt、Denison、Wright 等，arXiv:2412.14093，与 Anthropic 合作）。

风格：具体的威胁模型、最坏情况的对手、可被压力测试的具体协议。

### Apollo Research

为前沿实验室做部署前的 scheming 评估。著有 In-Context Scheming（第 08 课，arXiv:2412.04984）。是 2025 年 OpenAI 反 scheming 训练合作的伙伴。产出 Towards Safety Cases for AI Scheming（2024）。

风格：在欺骗可能涌现的 agentic 设定下做评估；三支柱分解（misalignment、goal-directedness、situational awareness）。

### METR（Model Evaluation and Threat Research）

基于任务的能力评估。自主任务完成时间跨度研究。"Common Elements of Frontier AI Safety Policies"（metr.org/common-elements，2025）比较各实验室的框架。

与 Apollo 合著 AI Scheming 的 safety-case 草图。

风格：长时程任务评估、经验性能力测量、框架综合。

### Eleos AI Research

模型福祉的部署前评估。执行了 Claude Opus 4 的福祉评估，记录在 system card 的第 5.3 节。为第 19 课中与福祉相关的主张提供了外部方法论检验。

### 流向

MATS 培养研究者。毕业生进入 Anthropic、DeepMind、OpenAI（实验室安全团队）或 Redwood、Apollo、METR、Eleos（外部评估）。外部评估者与实验室以及 UK AISI / CAISI 合作。出版物把生态反馈回 MATS，供下一届 cohort 使用。

### 为什么这一层重要

单一来源的评估不可靠：实验室评估自己的模型存在结构性利益冲突。外部评估者能够提出并验证实验室可能少报的失败模式。2024 年的 Sleeper Agents 论文（第 07 课）是 Anthropic + Redwood；Alignment Faking 是 Anthropic + Redwood；In-Context Scheming 是 Apollo；Anti-Scheming 是 Apollo + OpenAI。多组织结构就是质量控制。

### 它在第 18 阶段中的位置

第 07-11 课引用 Redwood 与 Apollo 的工作；第 18 课引用 METR 的框架比较；第 19 课引用 Eleos。第 28 课为本阶段其余课程所依赖的生态提供了明确的组织图谱。

```figure
sae-features
```

## Use It

无代码。阅读 METR 的 "Common Elements of Frontier AI Safety Policies"，作为外部综合如何为实验室内部政策工作增值的一个范例。

## Ship It

本课产出 `outputs/skill-ecosystem-map.md`。给定一个对齐主张或评估，它会指出所属组织、发表渠道与方法论风格，并与已知的对标组织交叉核对。

## Exercises

1. 从第 07-15 课中选一篇论文，指出涉及的组织。把作者与 MATS 校友及当前生态归属做交叉核对。

2. 阅读 METR 的 "Common Elements of Frontier AI Safety Policies"。指出他们强调的三处跨实验室趋同与两处最大的分歧。

3. MATS 的职业去向约 80% 为安全/安保。论证这种筛选压力是适应性的（训练该领域）还是有偏的（滤除了异见立场）。

4. Redwood 与 Apollo 都做 control/scheming 工作，但风格不同。选一个失败模式，描述各自会如何调查它。

5. Eleos AI 是唯一一家纯粹的模型福祉组织。设计一个假想的第二家组织，聚焦另一个与福祉相邻的问题（认知自由、机器人具身等），并阐明其方法论。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| MATS | "the mentorship program" | ML Alignment & Theory Scholars；自 2021 年以来 527+ 位研究者 |
| Redwood Research | "the control lab" | 应用对齐；AI Control 的作者；UK AISI 的伙伴 |
| Apollo Research | "the scheming evals" | 为前沿实验室做部署前的 scheming 评估 |
| METR | "the task-horizon evals" | 基于任务的能力评估；框架综合 |
| Eleos AI | "the welfare lab" | 模型福祉的部署前评估 |
| Talent pipeline | "MATS -> labs" | MATS 毕业生流向 Anthropic、DM、OpenAI、Redwood、Apollo、METR |
| External evaluation | "non-lab check" | 不由模型生产者做的评估；增加可信度 |

## Further Reading

- [MATS（ML Alignment & Theory Scholars）](https://www.matsprogram.org/) —— 导师项目
- [Redwood Research](https://www.redwoodresearch.org/) —— AI Control 论文
- [Apollo Research](https://www.apolloresearch.ai/) —— scheming 评估
- [METR — Common Elements of Frontier AI Safety Policies](https://metr.org/blog/2025-03-26-common-elements-of-frontier-ai-safety-policies/) —— 框架比较
- [Eleos AI Research](https://www.eleosai.org/research) —— 模型福祉方法论
