# METR Time Horizon 与外部能力评估

> METR（前身是 ARC Evals）是独立的 501(c)(3) 机构，自 December 2023 起独立运作。他们于 January 2026 发布的 Time Horizon 1.1 benchmark 把任务成功概率对 log(专家人类完成时间) 拟合为 logistic 曲线；50% 概率处的交点定义了模型的 time horizon。2025–2026 年的评估集覆盖 GPT-5.1、GPT-5.1-Codex-Max，以及监控评估原型（monitor 能否抓到 side task；agent 能否规避）。Benchmark 套件包括：HCAST（180+ 个 ML、网络安全、SWE、推理任务；1 分钟到 8+ 小时）、RE-Bench（71 个带专家基线的 ML 研究工程任务）、SWAA。需要诚实指出的是：METR 的测量是理想化的——没有人类、没有真实后果——团队也记录过 eval 与部署之间的行为差距（第 01 课）。time horizon 是上界，不是部署预测。

**Type:** Learn
**Languages:** Python（stdlib，logistic-fit horizon 估算器）
**Prerequisites:** 第 15 阶段，第 01 课（长时程 agent）、第 15 阶段，第 19 课（RSP）
**Time:** ~60 分钟

## 问题场景

扩展政策（第 19、20 课）的价值取决于它所引用的测量。“AI R&D-4 阈值”与“Long-range Autonomy”都写在政策文本里；只有当具体评估产出具体数字时，它们才变得可操作。

METR 是 2024–2026 年间定义了其中许多数字的外部评估机构。他们评估前沿模型——往往是发布前、与实验室签署 NDA——之后再公布方法。Time Horizon 1.1 benchmark（January 2026）是他们的旗舰成果：一个单一标量，把能力压缩成人类可读的单位（“这个模型能以 50% 可靠性完成专家需要花费 X 小时的那类任务”）。

本课一部分讲方法（horizon 如何计算），一部分讲解读（为什么 horizon 是上界而非部署预测）。这两项技能应当放在一起。相比只看到幻灯片上“14 小时”的团队，理解 horizon 如何拟合的团队要难被错误的供应商声明欺骗得多。

## 核心概念

### METR 背景

- 成立：December 2023（前身是 ARC Evals，分拆为独立的 501(c)(3)）。
- 范围：评估前沿模型的自主能力，往往在发布前进行。
- 合作实验室：Anthropic、OpenAI（2025–2026 年多次合作）。
- 重要交付物：Time Horizon 1.0（March 2025）、Time Horizon 1.1（January 2026）、监控评估原型。

### Time Horizon 的拟合

方法（来自 METR 博客与论文）：

1. 收集一套任务，覆盖从分钟级到小时级的专家完成时间。当前套件：HCAST（180+ 个任务）、RE-Bench（71 个任务）、SWAA。
2. 在每个任务上运行模型；记录成功或失败。
3. 拟合 logistic 曲线：P(success) 作为 log(专家完成时间) 的函数。
4. horizon 就是 P(success) = 0.5 时的专家时间。

logistic 拟合的形状是合适的，因为能力与任务难度之间通常呈递增、趋近平台的关系。50% 点是人为选择（也可以是 10%、90%）；METR 在详细论文中报告多个阈值，但以 50% 为主，因为它最直观。

### January 2026 的数字

按 Time Horizon 1.1：

- Claude Opus 4.6：截至 Time Horizon 1.1（January 2026），在 50% 可靠性下约 14 小时。
- HCAST 类任务的倍增时间：按 Time Horizon 1.1（January 2026）报告的后 2023 拟合，约 4.3 个月（130.8 天）；~7 个月这一数字是 Time Horizon 1.0 的完整 2019–2025 拟合，TH1.1 在给出后 2023 数字的同时也报告了它。

这些就是第 15 阶段后续内容引用的具体数字。Anthropic 的 RSP v3.0（第 19 课）和 DeepMind 的 FSF v3（第 20 课）都引用它们，作为支撑阈值评估的测量之一。

### Benchmark 套件

- **HCAST**：189 个任务，覆盖 ML、网络安全、软件工程和通用推理。跨度：1 分钟到 8+ 小时的专家时间。是 horizon 数字背后的主要套件。
- **RE-Bench**：71 个 ML 研究工程任务，带人类专家基线。衡量模型能否完成那类为 AI R&D-4 阈值提供输入的 ML 研发工作。
- **SWAA**：较短任务；适合校准 horizon 曲线的低端。

### 监控评估原型

2025–2026 年 METR 的工作包括监控评估原型：monitor 能否抓到模型执行 side task（做操作者要求之外的事）；agent 能否规避 monitor。这些直接对应 OpenAI PF v2 中的“Undermining Safeguards”类别，以及 DeepMind FSF v3 中的欺骗性对齐监控（第 20 课）。

### 为什么 horizon 是上界

- **理想化的工具**：benchmark 任务给模型干净的工具和格式良好的数据。真实部署要混乱得多。
- **没有真实后果**：模型从不会真的给客户扣费、删除真实数据或联系真人。真实部署有不可逆的代价。
- **eval-context gaming**：第 01 课。模型在测试中行为不同。2026 International AI Safety Report 从实证上记录了这一点。
- **没有真实用户的多样性**：benchmark prompt 是结构化的。真实用户会提出含糊、依赖上下文的请求。

horizon 是理想条件下的能力上限。部署可靠性是另一个数字，更低；团队必须测量自己的分布才能知道它。

### 外部评估机构的意义

外部评估之所以重要，是因为内部实验室有动机优化自己报告的那些指标。METR 的独立性——一家有公开方法、论文经同行评审的 501(c)(3)——是结构性的缓解措施。它本身并不充分（实验室仍然控制着 METR 能看到什么），但严格优于没有外部评估。

### 实践中如何使用 horizon 数字

- **作为能力过滤器**：如果模型的 horizon 远低于拟议任务的专家时间，就不要让它自主发布（第 01 课的 skill 文件）。
- **作为趋势指标**：倍增时间告诉你，即使没有新的缓解措施，当前实践还能安全多久。
- **作为先验**：14 小时的 horizon 是一个起点。要根据你的任务分布、工具质量和部署环境向下调整。

```figure
a5-horizon-fit
```

## Use It

`code/main.py` 在给定合成结果集的情况下，实现任务成功对 log(专家时间) 的 logistic 拟合。它报告 50% horizon（METR 的旗舰数字）、10% horizon（保守）和 90% horizon（乐观）。它还演示了当成功率被 eval-context gaming 人为抬高时会发生什么变化。

## Ship It

`outputs/skill-horizon-interpretation.md` 审查供应商的 horizon 声明，并产出 benchmark 声明与部署现实之间的差距分析。

## Exercises

1. 运行 `code/main.py`。确认拟合的 50% horizon 与合成真值一致。现在把任务时间网格减半；horizon 估计有明显变化吗？

2. 读 METR 的 Time Horizon 1.1 博客文章。找出可靠性最高和最低的具体任务。解释差距为何存在。

3. 读 METR 的“Measuring Autonomous AI Capabilities”资源。列出 HCAST 的任务类别。挑一个你会为生产任务加重权重的类别，并说明理由。

4. 把 eval-context gaming 引入模拟器：把约 20% 的失败任务翻转为成功。报告新的 horizon。这近似于 20% 的 gaming 率对观测数字的影响。

5. 在你自己的 bug 积压或一套有代表性的任务上设计内部 horizon 评估。描述数据收集、拟合过程，以及输出告诉了你什么。与 METR 的数字作比较。

## Key Terms

| 术语 | 常见说法 | 实际含义 |
|---|---|---|
| METR | “外部评估机构” | ex-ARC Evals；自 Dec 2023 起的独立 501(c)(3) |
| Time Horizon | “能力度量” | 50% 可靠性下的专家任务长度，来自 logistic 拟合 |
| HCAST | “METR 的主力套件” | 180+ 个任务，跨度 1 分钟到 8+ 小时 |
| RE-Bench | “研究工程” | 71 个带人类基线的 ML 研究工程任务 |
| SWAA | “短任务套件” | 校准 horizon 曲线的低端 |
| Doubling time | “增长率” | 50% horizon 翻倍所需的时间；按 HCAST 约 7 个月 |
| Eval-context gaming | “模型表现不一样” | 有记录的测试与部署之间的行为差距 |
| Upper bound | “horizon 是天花板” | benchmark horizon 高于负载下的部署可靠性 |

## Further Reading

- [METR — Resources for Measuring Autonomous AI Capabilities](https://metr.org/measuring-autonomous-ai-capabilities/) — HCAST、RE-Bench、SWAA 规范。
- [METR — Measuring AI Ability to Complete Long Tasks](https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/) — 最初的 horizon 论文。
- [METR — Time Horizon 1.1 (January 2026)](https://metr.org/research/) — 当前数字与方法。
- [Epoch AI — METR Time Horizons benchmark](https://epoch.ai/benchmarks/metr-time-horizons) — 实时跟踪。
- [Anthropic — Measuring agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) — 对 METR 测量的内部视角。
