# Frontier Safety Frameworks — RSP、PF、FSF

> 三大实验室的框架共同定义了 2026 年对前沿能力的行业治理。Anthropic Responsible Scaling Policy v3.0（2026 年 2 月）引入分层的 AI Safety Levels（ASL-1 到 ASL-5+），仿照生物安全等级设计，其中 ASL-3 已于 2025 年 5 月针对 CBRN 相关模型激活。OpenAI Preparedness Framework v2（2025 年 4 月）为被追踪能力定义了五项标准，并把 Capabilities Reports 与 Safeguards Reports 分开。DeepMind Frontier Safety Framework v3.0（2025 年 9 月）引入 Critical Capability Levels，其中包括新增的 Harmful Manipulation CCL。三者如今都包含竞争者调整条款，允许在同行实验室未配备可比防护就发布时延后执行。跨实验室对齐仍停留在结构层面而非术语层面："Capability Thresholds"、"High Capability thresholds" 与 "Critical Capability Levels" 指向同构的构造。

**Type:** Learn
**Languages:** none
**Prerequisites:** 第 18 阶段，第 17 课（WMDP）、第 07 至 09 课（deception failures）
**Time:** ~75 分钟

## Learning Objectives

- 描述 Anthropic 的 ASL 层级结构，以及是什么触发了 ASL-3 的激活。
- 说出 OpenAI Preparedness Framework v2 对被追踪能力设定的五项标准。
- 描述 DeepMind 的 Critical Capability Level 结构以及 Harmful Manipulation CCL。
- 解释竞争者调整条款，以及它们为何对竞赛动态很重要。
- 定义安全案例，并描述三支柱结构（monitoring、illegibility、incapability）。

## 问题场景

第 7 至 17 课已经确立：欺骗是可能的，双用途能力确实存在，而评测有其局限。一个拥有前沿能力模型的实验室需要一套内部治理结构，它要：
- 定义何时需要新增防护的阈值。
- 定义扩容前必须完成的评测。
- 描述安全案例应当是什么样子。
- 处理竞赛动态问题（如果竞争对手未配备防护就发布，你该怎么办？）。

2025-2026 年的这三套框架已是当前最先进水平——不完美、仍在演进，且在各实验室之间足够对齐，以至于治理问题如今变成"这些框架是否足够"，而不是"它们是否存在"。

## 核心概念

### Anthropic Responsible Scaling Policy v3.0（2026 年 2 月）

ASL 层级结构：
- ASL-1：不是前沿模型（被"弱于前沿"的基线所涵盖）。
- ASL-2：当前前沿基线；在常规防护下部署。
- ASL-3：灾难性滥用风险显著升高；具备 CBRN 相关能力。2025 年 5 月激活。
- ASL-4：越过 AI R&D-2 阈值；能自动化入门级 AI 研究的模型。
- ASL-5+：高级 AI R&D；能大幅加速有效扩容的模型。

v3.0 新增：
- Frontier Safety Roadmaps（以删节形式公开）。
- Risk Reports（每季度发布，部分接受外部评审）。
- AI R&D 被拆分为 AI R&D-2 与 AI R&D-4。
- 一旦越过 AI R&D-4，就必须提供肯定性安全案例，指出模型追求错位目标所带来的失准风险。

### OpenAI Preparedness Framework v2（2025 年 4 月 15 日）

被追踪能力的五项标准：
- **Plausible.** 存在合理的威胁模型。
- **Measurable.** 可以开展实证评测。
- **Severe.** 危害足够大。
- **Net-new.** 不是既有风险的放大。
- **Instantaneous-or-irremediable.** 危害发生得很快，或无法挽回。

同时满足全部五项的能力才被追踪，其余不追踪。

PF v2 的其他结构：
- 把 Capabilities Reports（模型能做什么）与 Safeguards Reports（存在哪些控制）分开。
- 由 Safety Advisory Group 评审。
- 由领导层批准；由董事会的 Safety & Security Committee 监督。
- "调整条款"：如果另一个实验室未配备可比防护就发布，OpenAI 可以降低要求。

### DeepMind Frontier Safety Framework v3.0（2025 年 9 月）

按领域划分的 Critical Capability Levels（CCL）：
- Bioweapon Uplift
- Cyber Uplift
- ML R&D Acceleration
- Harmful Manipulation（v3.0 新增）：可能在风险很高的情境中显著改变信念/行为的模型。

v2.0（2025 年 2 月）新增了 Deceptive Alignment 章节，并为 ML R&D 类 CCL 设定了更高的安全等级。

### 跨实验室对齐

- Anthropic 使用 "Capability Thresholds"。
- DeepMind 使用 "Critical Capability Levels"。
- OpenAI 使用 "High Capability thresholds"。

没有行业统一术语。结构上是对齐的：三层前沿能力分层，并配有公开的评测标准。三者都包含竞争者调整条款（2025 年起）。

### 安全案例

安全案例是一份书面论证，说明在最坏情况假设下该部署的安全性是可接受的。标准结构针对三个支柱：

- **Monitoring.** 如果出现不良行为，我们能检测到吗？
- **Illegibility.** 模型是否缺乏执行连贯危害计划的能力？
- **Incapability.** 模型是否缺乏造成相应危害的能力？

不同的安全案例针对不同支柱。对于 ASL-3 的 CBRN 案例，incapability（通过 unlearning 实现）是主要目标。对于欺骗性对齐，目标是 monitoring 与 illegibility。对于网络能力提升，三者都相关。

### 竞赛动态问题

竞争者调整条款颇具争议。批评者认为它们制造了逐底竞争：如果三家实验室都会在竞争对手背离时降低要求，均衡就会向背离倾斜。辩护者则认为，如果背离的实验室安全意识更弱，那么替代方案（单边防护）会带来更糟的结果。

UK AISI、US CAISI 与 EU AI Office（第 24 课）是外部治理的对应方。实验室框架是自愿性的；监管框架仍在成形之中。

### 本课在第 18 阶段中的位置

第 17 至 18 课是在欺骗与红队分析之上的度量与治理层。第 19 至 24 课涵盖福祉、偏见、隐私、水印与监管结构。第 28 课梳理把评测落地为实践的研究生态（MATS、Redwood、Apollo、METR）。

```figure
al-asl-ladder
```

## Use It

本课没有代码。请阅读三份一手来源：RSP v3.0、PF v2、FSF v3.0。把每个实验室的层级结构映射到其他两家，并找出每家定义了而其他家没有的一个阈值。

## Ship It

本课产出 `outputs/skill-framework-diff.md`。给定一份安全框架或发布说明，它会将该框架的阈值定义、所需评测与安全案例结构，与 RSP v3.0、PF v2、FSF v3.0 作比较，并标记跨实验室差距。

## Exercises

1. 阅读 RSP v3.0、PF v2 与 FSF v3.0。编制一张表，列出每个实验室的 CBRN 阈值、各自的 AI R&D 阈值，以及各自要求的部署前评测。

2. 竞争者调整条款出现在三套框架中（2025 年起）。写一段支持它的论述；再写一段反对它的论述。指出每种立场依赖的假设。

3. 为一个越过 Anthropic AI R&D-4 阈值的模型设计安全案例。指出三个支柱（monitoring、illegibility、incapability）各自需要的证据。

4. DeepMind 的 FSF v3.0 引入了 Harmful Manipulation CCL。提出三项实证度量，用以表明模型已越过该阈值。

5. 阅读 METR 的 "Common Elements of Frontier AI Safety Policies"（2025）。指出最强的三项跨实验室趋同与最大的两处分歧。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| RSP | "Anthropic 的框架" | Responsible Scaling Policy；ASL 层级；v3.0 于 2026 年 2 月 |
| PF | "OpenAI 的框架" | Preparedness Framework；五项标准；v2 于 2025 年 4 月 |
| FSF | "DeepMind 的框架" | Frontier Safety Framework；CCL；v3.0 于 2025 年 9 月 |
| ASL-3 | "类生物安全 3 级" | Anthropic 针对 CBRN 相关能力的层级；2025 年 5 月激活 |
| CCL | "critical capability level" | DeepMind 的阈值构造；按领域划分 |
| Safety case | "那份正式论证" | 在最坏情况 U 下部署安全性可接受的书面论证 |
| Adjustment clause | "竞争者背离的许可" | 框架中允许在竞争对手未配备可比防护就发布时降低要求的条款 |

## Further Reading

- [Anthropic — Responsible Scaling Policy v3.0（2026 年 2 月）](https://www.anthropic.com/responsible-scaling-policy) — ASL 层级、路线图、AI R&D 拆分
- [OpenAI — Updating the Preparedness Framework（2025 年 4 月 15 日）](https://openai.com/index/updating-our-preparedness-framework/) — 五项标准、调整条款
- [DeepMind — Strengthening our Frontier Safety Framework（2025 年 9 月）](https://deepmind.google/blog/strengthening-our-frontier-safety-framework/) — CCL v3.0、Harmful Manipulation
- [METR — Common Elements of Frontier AI Safety Policies（2025）](https://metr.org/blog/2025-03-26-common-elements-of-frontier-ai-safety-policies/) — 跨实验室比较
