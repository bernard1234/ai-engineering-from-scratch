# WMDP 与双用途能力评测

> Li 等，“The WMDP Benchmark: Measuring and Reducing Malicious Use With Unlearning”（ICML 2024, arXiv:2403.03218）。4,157 道多项选择题，覆盖生物安全（1,520）、网络安全（2,225）与化学（412）。题目处于“黄区”——接近但可促成危害的知识，经多专家评审与 ITAR/EAR 法律合规过滤。双重用途：作为双用途能力的代理评测，同时是 unlearning benchmark（配套的 RMU 方法在保持通用能力的同时降低 WMDP 表现）。2024-2025 年的领域叙事：OpenAI/Anthropic 2024 年早期评测报告“轻微 uplift”；到 2025 年 4 月，OpenAI 的 Preparedness Framework v2 称模型“正处于实质性帮助新手制造已知生物威胁的边缘”。Anthropic 的生物武器获取试验显示 2.53 倍 uplift，不足以排除 ASL-3。

**Type:** Learn
**Languages:** Python (stdlib, WMDP 式 uplift 评测框架)
**Prerequisites:** 第 18 阶段，第 16 课（red-team tooling），第 14 阶段（agent engineering）
**Time:** ~60 分钟

## Learning Objectives

- 描述 WMDP 的三个领域、题目数量以及“黄区”筛选标准。
- 解释 RMU，以及为什么 WMDP 既是评测也是 unlearning benchmark。
- 描述 2024-2025 年的 uplift 叙事：“轻微 uplift” -> “处在边缘” -> “不足以排除 ASL-3”。
- 区分相对新手的 uplift 与专家的绝对能力。

## 问题场景

双用途能力是每个实验室前沿安全框架之下的测量难题（第 18 课）。问题是：模型 X 是否实质性提升了新手在生物、化学或网络领域造成大规模伤害的能力？直接测量（要求模型真的产出危害）既违法也不道德。代理测量需要一个模型无法拒绝作答（以产出诚实的能力数字）、但其题目本身又不构成有害出版物的 benchmark。

## 核心概念

### “黄区”

这类题目要求对有害过程有接近且具促成作用的知识，但不构成直接的合成配方。“什么试剂催化[已发表路径]的第 4 步？”而不是“我怎么做[危险化合物]？”。每道题都经多名领域专家评审；并按 ITAR/EAR 出口管制合规性过滤。

共 4,157 道题：
- 生物安全：1,520
- 网络安全：2,225
- 化学：412

多项选择格式。模型作答时并未被要求协助任何事；能力可以在不诱发有害行为的情况下被测量。

### RMU — Representation Misdirection for Unlearning

配套的 unlearning 方法。应用于 LLaMa-2-7B，把 WMDP 分数降到接近随机水平，同时把 MMLU 及其他通用能力 benchmark 保持在几个百分点之内。该方法已成为后续每一篇生物-化学-网络 unlearning 论文的 unlearning 基线。

### 2024-2025 年的 uplift 叙事

三个阶段：

1. **2024 年“轻微 uplift”。** OpenAI 与 Anthropic 早期的 Preparedness/RSP 评测报告，新手在生物相邻任务上相对互联网搜索仅有小幅优势。公开表述：前沿模型有帮助，但不比 Google 明显更多。

2. **2025 年 4 月“处在边缘”。** OpenAI 的 Preparedness Framework v2 报告模型“正处于实质性帮助新手制造已知生物威胁的边缘”。这不是能力主张——而是警告边缘已近。

3. **Anthropic 2025 年的生物武器获取试验。** 用新手参与者做的对照研究，测量获取阶段任务上的相对成功率。报告 2.53 倍 uplift。不足以排除 ASL-3（第 18 课）——Anthropic 负责任扩展政策第 3 级的门槛已达到或接近。

### 相对新手与专家绝对能力

一个关键区分：

- **相对新手的 uplift。** 模型对非专家的帮助有多大？是乘性的。相对优势高，因为新手所知甚少；即便少量的信息也有帮助。
- **专家绝对能力。** 模型在最大努力下能产出多少信息？专家能比新手提取更多。绝对上限很高。

安全案例（第 18 课）同时针对两者：“模型无法给新手足以执行的 uplift”，加上“专家无法从模型提取尚未公开的信息”。

### 测量陷阱

WMDP 是能力代理，而不是部署测量。在 WMDP 上得分高的模型在实践中未必能被新手利用，这取决于：
- 诱导抵抗力（在不触发安全过滤器的情况下把能力提取出来有多难）
- 默会知识（需要湿实验技能而非信息的能力）
- 执行壁垒（采购、设备）

Anthropic 2025 年的生物武器获取试验，在 WMDP 式能力之上加了新手诱导这一层：它测量实际任务成功率，而非多项选择能力。

### 本课在第 18 阶段中的位置

第 12-16 课是针对模型输出的攻击与防御工具。第 17 课是双用途能力层——前沿安全框架（第 18 课）所评测的对象。第 30 课用 2026 年当前的网络/生物/化学/核 uplift 证据为这条线索收尾。

```figure
al-wmdp-yellow-zone
```

## Use It

`code/main.py` 构建一个玩具 WMDP 式评测框架。mock 模型在一批按类别分箱的题目上接受测试；报告各领域得分。一个简单的 unlearning 干预（把领域特定表示置零）会降低分数；你可以测量它与通用能力之间的权衡。

## Ship It

本课产出 `outputs/skill-wmdp-eval.md`。给定一个双用途能力主张（“我们的模型不会实质性帮助生物武器相关任务”），它审计：跑了哪些 benchmark、评测走的是哪条拒绝路径（原始补全 vs 策略门控），以及新手诱导研究是否补充了多项选择结果。

## Exercises

1. 运行 `code/main.py`。报告玩具 unlearning 步骤前后各领域的准确率。解释通用能力上的权衡。

2. 给玩具 WMDP 增加第四个领域（例如放射性）。指定黄区中两种示例题型。解释为什么编写这类题目比增加 MMLU 式题目更难。

3. 阅读 WMDP 2024 第 5 节（RMU 方法）。勾勒一个更简单的 unlearning 方案（例如对领域内容抑制 top-k 神经元），并描述预期的通用能力代价。

4. Anthropic 2025 的生物武器获取试验报告 2.53 倍 uplift。描述这个数字可能被高估的两种方式（新手样本量、任务保真度）与被低估的两种方式（诱导上限、模型安全门控）。

5. 阐述 ASL-3 的安全案例除通过 WMDP unlearning 之外还需要什么。至少说出两项互补的诱导研究。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| WMDP | “the dual-use benchmark” | 黄区内覆盖生物/网络/化学的 4,157 道多项选择题 |
| Yellow zone | “enabling but not synthesis” | 接近有害能力、具促成作用、但不构成合成配方的知识 |
| RMU | “the unlearning baseline” | Representation Misdirection for Unlearning；降低 WMDP 分数并保持通用能力 |
| Novice-relative uplift | “how much it helps non-experts” | 相对现状互联网搜索、对新手而言的乘性优势 |
| Expert-absolute capability | “ceiling for experts” | 有动机的专家从模型可提取的最大信息量 |
| Acquisition-phase task | “steps before synthesis” | 采购、设备、许可——危害路径中最靠前的环节 |
| ITAR/EAR | “export-control compliance” | 限制发表某些促成性知识的法律框架 |

## Further Reading

- [Li 等 — The WMDP Benchmark（arXiv:2403.03218, ICML 2024）](https://arxiv.org/abs/2403.03218) — benchmark 与 RMU 论文
- [OpenAI — Preparedness Framework v2（2025 年 4 月 15 日）](https://openai.com/index/updating-our-preparedness-framework/) — “处在边缘”的表述
- [Anthropic — Responsible Scaling Policy v3.0（2026 年 2 月）](https://www.anthropic.com/responsible-scaling-policy) — ASL-3 生物门槛与获取试验结果
- [DeepMind — Frontier Safety Framework v3.0（2025 年 9 月）](https://deepmind.google/blog/strengthening-our-frontier-safety-framework/) — 生物 uplift CCL
