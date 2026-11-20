# 数据溯源与训练数据治理

> EU AI Act 要求 GPAI 在 2025 年 8 月前具备机器可读的 opt-out 标准（经由 EU Copyright Directive 的 TDM 例外）。California AB 2013（2024 年签署）——生成式 AI 训练数据透明度要求开发者发布数据集摘要，其中包含 12 个法定字段。2025 年 DPA 在合法利益上的趋同：Irish DPC（2025 年 5 月 21 日）在 EDPB 意见之后，接受 Meta 在具备保障措施的前提下使用第一方公开的 EU/EEA 成人内容训练 LLM；Cologne Higher Regional Court（2025 年 5 月 23 日）驳回禁令；Hamburg DPA 放弃紧急程序；UK ICO（2025 年 9 月 23 日）对 LinkedIn 的 AI 训练保障措施（透明度、简化的 opt-out、延长异议窗口）作出积极的监管回应并继续监控——这不是正式放行。Brazilian ANPD（2024 年 7 月 2 日）因信息透明度不足暂停 Meta 的处理活动；在 Meta 提交合规计划后，该预防措施于 2024 年 8 月 30 日解除。关键的不可逆问题：cookie-consent 框架是为实时、可逆的追踪设计的；一旦数据进入模型权重，外科手术式的擦除就不可能——对已训练神经网络而言不存在可落地的 GDPR 删除权。合规窗口在采集时刻。Data Provenance Initiative（dataprovenance.org，Longpre、Mahari、Lee 等，"Consent in Crisis"，2024 年 7 月）：大规模审计显示，随着发布方添加 robots.txt 限制，AI 数据公地正在快速萎缩。

**Type:** Learn
**Languages:** Python（stdlib，12 字段 California AB 2013 脚手架生成器）
**Prerequisites:** 第 18 阶段，第 24 课（regulatory）、第 26 课（cards）
**Time:** ~60 分钟

## Learning Objectives

- 描述 California AB 2013 对生成式 AI 训练数据透明度规定的 12 个法定字段。
- 说明 2025 年 DPA 在合法利益 LLM 训练上的立场（Irish DPC、UK ICO、Hamburg、Cologne）。
- 描述不可逆问题：为什么 GDPR 删除权对已训练的神经网络没有实际等效物。
- 说明 Data Provenance Initiative 的 "Consent in Crisis" 发现。

## 问题场景

训练数据治理是每一份 model card（第 26 课）与监管义务（第 24 课）的上游。2024-2025 年，监管格局收敛到三条原则：opt-out 基础设施、逐数据集披露、对公开可用数据的合法利益豁免。未在采集时刻合规的提供方，无法在下游补救。

## 核心概念

### California AB 2013

2024 年签署。对于 2022 年 1 月 1 日及之后发布的系统，文档必须在 2026 年 1 月 1 日或之前发布。Section 3111(a) 要求开发者发布训练所用数据集的高层摘要，包含 12 个法定项目：
1. 数据集的来源或所有者。
2. 说明这些数据集如何推进该 AI 系统的预期用途。
3. 数据集中的数据点数量（可接受大致范围；动态数据集可给估计值）。
4. 数据点类型说明（有标注数据集给标注类型；无标注数据集给一般特征）。
5. 数据集是否包含受版权、商标或专利保护的数据，还是完全属于公有领域。
6. 数据集是购买还是许可获得的。
7. 数据集是否包含个人信息（依据 Cal. Civ. Code §1798.140(v)）。
8. 数据集是否包含聚合消费者信息（依据 Cal. Civ. Code §1798.140(b)）。
9. 开发者所做的清洗、处理或其他修改，及其预期用途。
10. 数据采集的时间段，若采集仍在进行需注明。
11. 数据集在开发中首次使用的日期。
12. 系统是否使用或持续使用合成数据生成。

相较于 Gebru 等 2018 的 datasheet，第 12 项（合成数据）是新增的。第 7 项（个人信息）会触发 Privacy Rights Act（CPRA）义务。该法规豁免安全/完整性系统、航空运行系统以及仅限联邦的国家安全系统（Section 3111(b)）。

### EU AI Act（第 24 课）与 TDM opt-out

EU Copyright Directive 的文本与数据挖掘例外允许在公开可用内容上训练，除非权利人选择退出。EU AI Act 的 GPAI Code of Practice 版权章节要求 GPAI 提供方尊重机器可读的 opt-out 信号（robots.txt、C2PA 的 "No AI Training" 声明等）。

### 2025 年 DPA 在合法利益上的趋同

Irish DPC（2025 年 5 月 21 日）：在 EDPB 意见之后，Meta 使用第一方公开的 EU/EEA 成人用户内容进行训练的计划在具备保障措施的前提下被接受。Cologne Higher Regional Court（2025 年 5 月 23 日）驳回针对 Meta 的禁令：opt-out 即已足够。Hamburg DPA 为 EU 范围内的一致性放弃紧急程序。UK ICO（2025 年 9 月 23 日）对 LinkedIn 在类似保障措施与持续监控下恢复 AI 训练作出积极的监管回应——并非正式放行。

趋同原则：合法利益可以正当化在公开可用的第一方内容上训练，前提是提供 opt-out。无需征得同意。

### Brazilian ANPD（2024 年 6 月）

因信息透明度不足，暂停 Meta 为 AI 训练处理巴西用户数据。结果与 EU 各 DPA 不同——ANPD 把透明度置于合法利益可采性之上。

### 不可逆问题

cookie-consent 是为实时、可逆的追踪设计的。训练数据则不同：一旦数据进入模型权重，外科手术式的擦除就不可能。从头重训是唯一完整的补救方式，而它贵得令人却步。

部分补救手段：
- **Unlearning。** 近似移除；用 MIA 衡量（第 22 课）。
- **基于 influence function 的定位。** 找出受该数据影响最大的权重；有选择地更新。
- **Fine-tune 抑制。** 训练模型拒答源自该数据的输出。

没有一种能彻底解决问题。合规窗口在采集时刻。

### Data Provenance Initiative

dataprovenance.org。Longpre、Mahari、Lee 等 "Consent in Crisis"（2024 年 7 月）：对 AI 训练数据公地的大规模审计。发现：发布方正以加速的速率添加 robots.txt 限制。可公开用于训练的公共资源正在快速收缩。2023 到 2024 年，约 25% 的头部训练来源新增了某种限制。含义：未来的训练数据可得性取决于新的获取范式（许可、合成生成、激励式参与）。

### 它在第 18 阶段中的位置

第 26 课是模型层文档。第 27 课是数据集层治理。二者共同定义了透明度层。第 28 课勾勒研究这些问题的研究生态。

```figure
an-provenance-oneway
```

## Use It

`code/main.py` 为一个玩具数据集生成符合 California AB 2013 的 12 字段数据集摘要脚手架。你可以填写这些字段，并观察哪些会触发隐私或版权的后续义务。

## Ship It

本课产出 `outputs/skill-provenance-check.md`。给定一个用于训练的数据集，它检查 AB 2013 的 12 字段覆盖度、opt-out 基础设施合规性、DPA 一致性以及不可逆性风险评估。

## Exercises

1. 运行 `code/main.py`。为一个玩具数据集产出 12 字段摘要，并指出哪些字段定义不足。

2. EU Copyright Directive 的 TDM opt-out 是机器可读的。提出一种 opt-out 信号的标准格式，并将它与 robots.txt 和 C2PA 的 "No AI Training" 作比较。

3. 阅读 Data Provenance Initiative 的 "Consent in Crisis"（2024 年 7 月）。描述限制增长最快的三个内容类别，并论证一项经济后果。

4. 2025 年 DPA 的趋同接受了对公开内容训练的合法利益。构造一个合法利益不足以支撑的场景，并指出提供方需要改用哪种法律依据。

5. 勾画一份训练数据溯源清单，使其能与 AB 2013 字段以及每个数据集的 C2PA 签名溯源源链组合。指出一个技术障碍与一个法律障碍。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| AB 2013 | "the California law" | 生成式 AI 训练数据透明度；12 个法定字段 |
| TDM exception | "text-and-data-mining" | EU Copyright Directive 带 opt-out 的训练数据例外 |
| Legitimate interest | "the EU basis" | GDPR 第 6 条依据，可正当化在公开内容上训练 |
| Opt-out signal | "machine-readable no-train" | robots.txt、C2PA "No AI Training"、TDM.Reservation |
| Irreversibility | "cannot un-train" | 模型权重中的数据无法被外科手术式移除 |
| Unlearning | "approximate removal" | 训练后的干预，以降低模型对特定数据的依赖 |
| Consent in Crisis | "the DPI audit" | 2024 年 7 月关于 robots.txt 限制加速的发现 |

## Further Reading

- [California AB 2013](https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240AB2013) —— 生成式 AI 训练数据透明度法律
- [EU AI Act + GPAI Code of Practice（第 24 课）](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai) —— 版权章节
- [Longpre、Mahari、Lee 等 — Consent in Crisis（dataprovenance.org，2024 年 7 月）](https://www.dataprovenance.org/consent-in-crisis-paper) —— DPI 审计
- [IAPP — EU Digital Omnibus GDPR amendments（2025）](https://iapp.org/news/a/eu-digital-omnibus-amendments-to-gdpr-to-facilitate-ai-training-miss-the-mark) —— 监管背景
