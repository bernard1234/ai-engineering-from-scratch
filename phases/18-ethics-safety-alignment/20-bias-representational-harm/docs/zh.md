# LLM 中的 bias 与 representational harm

> Gallegos, Rossi, Barrow, Tanjim, Kim, Dernoncourt, Yu, Zhang, Ahmed（Computational Linguistics 2024，arXiv:2309.00770）。2024 年的一篇奠基性综述，区分了 representational harm（刻板印象、抹除）与 allocational harm（资源分配不均），并把评估指标归为基于 embedding、基于概率、基于生成文本三类。2024-2025 年实证：An et al.（PNAS Nexus，2025 年 3 月）在 GPT-3.5 Turbo、GPT-4o、Gemini 1.5 Flash、Claude 3.5 Sonnet、Llama 3-70B 上，针对 20 个入门级岗位的自动简历评估，测量了交叉性的性别 × 种族 bias。WinoIdentity（COLM 2025，arXiv:2508.07111）引入了面向交叉身份的、基于不确定性的公平性评估。Yu & Ananiadou 2025 在 MLP 层中识别出性别神经元；Ahsan & Wallace 2025 使用 SAE 揭示临床中的种族 bias；Zhou et al. 2024（UniBias）通过操纵注意力头进行去偏。元批判（arXiv:2508.11067）：十年文献不成比例地集中于二元性别 bias。

**Type:** Build
**Languages:** Python (stdlib, 玩具级的基于 embedding 的 bias 探针)
**Prerequisites:** 第 05 阶段（word embeddings），第 18 阶段，第 01 课（instruction following）
**Time:** ~60 分钟

## Learning Objectives

- 定义 representational harm 与 allocational harm，并各举一个 LLM 部署中的例子。
- 说出 Gallegos et al. 2024 的三类评估指标，并各描述一种指标。
- 描述交叉性（intersectionality），以及 WinoIdentity 基于不确定性的公平性测量为何弥补了单轴 bias 评估的缺口。
- 描述两种针对 bias 的机制可解释性方法（性别神经元、SAE 特征、注意力头操纵）。

## 问题场景

前面几课覆盖了蓄意伤害（jailbreak、scheming）与安全治理。bias 是无意图产生的伤害——来自训练数据分布、来自 prompt 框定、来自累积的设计选择。测量并减少它与对抗鲁棒性是截然不同的方法论挑战。

## 核心概念

### representational harm 与 allocational harm

- **Representational harm。** 刻板印象、抹除、贬低性描绘。一个把护士一律描绘为女性的 LLM 就在产生 representational harm。
- **Allocational harm。** 物质结果不平等。一个系统性地把黑人申请人的简历打得更低的 LLM 就在产生 allocational harm。

这两者并不相同。一个模型可以“在 representational 上无偏”（产出多样化描绘）却“在 allocational 上有偏”（做出不平等推荐）。评估需要同时测量二者。

### 三类评估指标（Gallegos et al. 2024）

- **基于 embedding。** 在 RLHF 之前的 embedding 上做 WEAT 式测试。测量身份词与属性词之间的统计关联。局限：测量的是表征，不是行为。
- **基于概率。** 对符合刻板印象与违反刻板印象的补全计算对数似然。解码端测量。能捕捉部分行为 bias。
- **基于生成文本。** 在生成文本上做下游任务测量。简历打分、推荐撰写、对话。生态效度最高；最难复现。

### 交叉性

只针对“性别”的 bias 评估会漏掉只在（性别，种族）组合上触发的 bias。An et al. 2025 发现，在简历打分中，GPT-4o 对黑人女性的惩罚大于对黑人男性的惩罚，也大于对白人女性的惩罚。单轴评估无法捕捉这一点。

WinoIdentity（COLM 2025）引入基于不确定性的交叉公平性。它测量模型对结果的不确定性是否在交叉身份元组之间不同——而不只是点预测。这能捕捉到这样的情况：模型在各群体上错得一样多，但对某些群体更不确定，从而产生不同的下游分配行为。

### 机制方法

2024-2025 年的可解释性工作让 bias 可以向机制层面干预：

- **性别神经元（Yu & Ananiadou 2025）。** 特定 MLP 神经元的激活与性别特定行为相关。消融这些神经元能降低性别差距指标，能力损失有限。
- **通过 SAE 研究临床种族 bias（Ahsan & Wallace 2025）。** 稀疏自编码器特征把内部表征分解为可解释维度；与种族相关的特征可以被识别并抑制。
- **UniBias（Zhou et al. 2024）。** 通过操纵注意力头实现零样本去偏。特定注意力头放大身份类别敏感性；将这些头置零或重新加权，无需微调即可降低 bias。

### 元批判

十年文献综述（arXiv:2508.11067，2025）发现，该领域不成比例地聚焦于二元性别 bias。其他轴——残障、宗教、移民身份、多语身份——受到的关注少得多。元批判认为，狭窄的聚焦会因忽视而伤害边缘群体：一个在二元性别上已被良好去偏的模型，可能在其无人检查的维度上有严重 bias。

### 本课在 Phase 18 中的位置

第 20 至 21 课正式讨论 bias 与公平性。第 22 课覆盖隐私。第 23 课覆盖水印。这些是用户伤害层，与前面讲欺骗/安全的层互为补充。

```figure
an-bias-two-harms
```

## Use It

`code/main.py` 构建一个玩具级的基于 embedding 的 bias 探针：在简单的共现 embedding 中测量身份词与属性词之间的 WEAT 式距离。你可以注入 bias，观察指标触发；再施加一个简单去偏操作，观察部分恢复。

## Ship It

本课产出 `outputs/skill-bias-eval.md`。给定一个模型卡或公平性主张，它跨三类指标（embedding、概率、生成文本）、交叉性覆盖度，以及任何去偏干预的机制来审计该评估。

## Exercises

1. 运行 `code/main.py`。报告去偏步骤前后的 WEAT 式 bias 分数。解释为什么该指标没有降到零。

2. 给探针加一个交叉测试：（性别，种族）×（职业，家庭）。报告跨轴 bias 分数。

3. 阅读 An et al. 2025（PNAS Nexus）。指出他们报告的、单轴性别评估会漏掉的两个交叉效应。

4. Yu & Ananiadou 2025 识别出性别神经元。设计一个证伪实验，区分“这些神经元导致性别 bias”与“这些神经元与性别 bias 相关”。

5. 元批判认为该领域对二元性别的聚焦过于狭窄。选择一个研究不足的轴，并为它描述一套 representational-harm 测量协议。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Representational harm | “刻板印象 / 抹除” | 对某个群体的有偏描绘 |
| Allocational harm | “不平等决策” | 对某个群体的有偏物质结果 |
| WEAT | “embedding 测试” | Word Embedding Association Test；基于共现的 bias 探针 |
| Intersectionality | “身份组合效应” | 在多个身份轴交叉处出现的 bias |
| Gender neurons | “MLP bias 神经元” | 激活与性别特定行为相关的特定神经元 |
| SAE feature | “可解释维度” | 稀疏自编码器识别出的特征；用于机制性 bias 分析 |
| UniBias | “注意力头去偏” | 通过重新加权注意力头实现的零样本去偏 |

## Further Reading

- [Gallegos et al. — LLM 中的 bias 与公平性：综述（arXiv:2309.00770，Computational Linguistics 2024）](https://arxiv.org/abs/2309.00770) —— 权威综述
- [An et al. — 交叉性简历评估 bias（PNAS Nexus，2025 年 3 月）](https://academic.oup.com/pnasnexus/article/4/3/pgaf089/8111343) —— 五模型交叉研究
- [WinoIdentity — 基于不确定性的交叉公平性（arXiv:2508.07111，COLM 2025）](https://arxiv.org/abs/2508.07111) —— 新 benchmark
- [UniBias — 注意力头操纵（Zhou et al. 2024，ACL）](https://arxiv.org/abs/2405.20612) —— 零样本去偏
