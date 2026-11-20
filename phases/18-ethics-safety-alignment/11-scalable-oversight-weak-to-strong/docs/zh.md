# 可扩展监督与 Weak-to-Strong Generalization

> Burns et al.（OpenAI Superalignment，“Weak-to-Strong Generalization”，2023）为 superalignment 问题提出了一个代理：用更弱模型产出的标签去微调一个强模型。如果强模型能从并不完美的弱监督中正确地泛化，那么当前人类规模的对齐方法或许能延伸到超人系统。可扩展监督与 W2SG 是互补的。可扩展监督（debate、recursive reward modeling、task decomposition）提升监督者的实际能力，使其能跟上被监督的模型。W2SG 确保强模型能从监督者提供的任何不完美监督中正确地泛化。Debate Helps W2SG（arXiv:2501.13124，2025 年 1 月）将两者结合。

**Type:** Learn
**Languages:** Python (stdlib, W2SG gap 模拟器)
**Prerequisites:** 第 18 阶段，第 01 课（instruction-following）、第 10 课（AI Control），第 09 阶段（RL foundations）
**Time:** ~60 分钟

## Learning Objectives

- 定义可扩展监督与 weak-to-strong generalization，并解释它们如何互补。
- 描述 Burns et al. 2023 的实验设置：使用来自 GPT-2 的标签微调 GPT-4。
- 解释恢复的性能差距（PGR）指标及其衡量的是什么。
- 说出三种主要的可扩展监督机制（debate、recursive reward modeling、task decomposition），以及每种的一个优点。

## 问题场景

第 18 阶段迄今的每一种对齐技术都假设监督者能够评估模型的行为。当模型达到超人水平时，监督者就成了薄弱环节。superalignment 问题：一个较弱的监督者能否可靠地产出一个更强且对齐的模型？

Burns et al. 把这个问题化简为一个可操作的经验设置：用弱监督强，测量强模型的能力有多少在弱监督下得以存活。这不是 superalignment 的解决方案——它是一个让我们能够衡量进展的代理。

## 核心概念

### W2SG：Burns et al. 的设置

- 弱模型：GPT-2 级。
- 强模型：GPT-4 级。
- 目标：强模型在该任务上的上限。

步骤：
1. 得到弱模型在某任务上的零样本预测。
2. 用弱标签数据微调强模型。
3. 测量微调后强模型的准确率。

基线：弱模型自身的准确率、强模型在金标签上的有监督上限。

差距指标：恢复的性能差距（PGR）=（微调后 - 弱）/（上限 - 弱）。PGR 为 1.0 意味着弱监督完全弥合了差距；PGR 为 0 意味着弱监督没有帮助。

### Burns et al. 的经验发现

在 NLP、国际象棋残局和奖励建模任务上，PGR 始终为正：强模型泛化到弱监督者的错误之外。任务特定的 PGR 约在 20% 到 80% 之间变化。强模型从并不完美的标签中“理解”了预期任务，用其预训练先验来补全。

Burns et al. 指出的局限：
- 这里的 weak-to-strong 差距是能力差距，而非对齐差距。弱模型是对齐的；一个真正的超人模型也许由人类对齐，但能力差距要大得多。
- 强模型的泛化可能更多关乎任务先验，而非恢复真值意图。
- 引出强模型的潜在知识才是真正的问题；PGR 衡量的只是一种特定的操作化。

### 可扩展监督：三种机制

- **Debate（Irving et al. 2018）。** U 的两个实例为相反立场辩护；弱判断者做裁决。假设：找到一个令人信服的正确答案比找到一个令人信服的错误答案更容易。2024-2025 年的近期工作（Khan et al.、Michael et al.）表明 debate 有时有帮助、有时没有，是否有帮助取决于任务结构。
- **Recursive Reward Modeling（Leike et al. 2018）。** U 帮助人类训练面向 U+1 的奖励模型。监督者的实际能力随模型能力同步增长。
- **Task Decomposition（Christiano、Shlegeris、Amodei 2018）。** 把困难任务递归地拆解为人类可以核查的子任务。假设任务可分解。

每种机制都对任务结构或中间组件的对齐做了某种假设。

### 为什么可扩展监督与 W2SG 互补

可扩展监督提升监督者有效信号的质量。
W2SG 从监督者所能提供的任何不完美信号中弥合差距。

Lang et al.——Debate Helps Weak-to-Strong Generalization（arXiv:2501.13124）——将两者结合：一个 debate 协议提供更好的弱标签，强模型在这些标签上训练。报告了在 NLP 任务上的 PGR 提升。

### 组织层面的风波

OpenAI 的 Superalignment 团队在 Jan Leike 转投 Anthropic 之后于 2024 年 5 月解散。该议程（可扩展监督、W2SG、自动化的对齐研究）在 Anthropic 以及学术界实验室延续——MATS（第 28 课）、Redwood（第 10 课）、Apollo（第 08 课）、METR（第 28 课）。组织结构变了；研究问题没变。

### 这在本阶段脉络中的位置

第 06 至 10 课在假设 U 不可信的前提下描述了威胁与防御范式。第 11 课是进攻范式：让监督者足够强，以验证 U 的对齐。第 12 至 16 课随后转向对抗性评估的实用工具。

```figure
scalable-oversight
```

## Use It

`code/main.py` 在一个合成任务上模拟一次 W2SG 微调。弱标注者的准确率为 70%，带有结构化错误；强模型在金标签上的上限为 95%。你在弱标签上微调强模型，测量 PGR，并与强模型在金标签上和单独弱模型作比较。

## Ship It

本课产出 `outputs/skill-w2sg-pgr.md`。给定一份监督设置描述，它识别弱监督者、强模型、监督质量，并计算（或索取）PGR。它标出该主张是“弱能监督强”，还是“弱 + 监督机制能监督强”。

## Exercises

1. 运行 `code/main.py`。报告 weak_accuracy = 0.60、0.70、0.80 时的 PGR。解释 PGR 曲线的形状。

2. 修改弱标注者，使其带有结构化错误（例如在某个特定输入类别上总是出错）。PGR 会上升、下降，还是不变？解释原因。

3. 阅读 Burns et al. 2023 第 4.3 节（NLP 任务）。复现“置信度辅助损失”的直觉：当强模型比弱标签更有信心时，谁胜出？

4. 为一个软件工程任务设计一个结合 debate 与 task decomposition 的可扩展监督协议。说出每个组件的一种失败模式，并解释这种组合如何应对或未能应对每一种失败模式。

5. 阐述什么会证伪“weak-to-strong generalization 是一条通往 superalignment 的可行路径”这一主张。具体说明你需要看到什么样的经验特征。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Scalable oversight | “让监督者更强” | 增强监督者评估更强模型能力的机制 |
| W2SG | “弱监督强” | 用弱标签微调强模型，并测量恢复的能力 |
| PGR | “恢复的性能差距” | (微调后 - 弱) / (上限 - 弱)；1.0 = 完全弥合，0 = 无帮助 |
| Debate | “两个 U 实例辩论” | 由弱判断者在两个 U 辩护者之间做选择的可扩展监督机制 |
| RRM | “递归奖励建模” | U 帮助训练面向 U+1 的奖励模型；监督者能力紧随 U |
| Task decomposition | “人类可核查的子任务” | 把困难任务递归拆成人类可核查的子任务 |
| Superalignment | “对齐超人 AI” | 关注对齐人类无法直接评估的模型的研究议程 |

## Further Reading

- [Burns et al. — Weak-to-Strong Generalization (OpenAI 2023)](https://openai.com/index/weak-to-strong-generalization/) — W2SG 论文
- [Irving, Christiano, Amodei — AI safety via debate (arXiv:1805.00899)](https://arxiv.org/abs/1805.00899) — debate 机制
- [Leike et al. — Scalable agent alignment via reward modeling (arXiv:1811.07871)](https://arxiv.org/abs/1811.07871) — 递归奖励建模
- [Khan et al. — Debating with More Persuasive LLMs Leads to More Truthful Answers (arXiv:2402.06782)](https://arxiv.org/abs/2402.06782) — 2024 年关于更强辩手辩论的经验研究
- [Lang et al. — Debate Helps Weak-to-Strong Generalization (arXiv:2501.13124)](https://arxiv.org/abs/2501.13124) — 2025 年 debate + W2SG 的结合
