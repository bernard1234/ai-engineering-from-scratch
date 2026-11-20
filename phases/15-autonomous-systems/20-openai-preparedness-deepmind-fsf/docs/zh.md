# OpenAI Preparedness Framework 与 DeepMind Frontier Safety Framework

> OpenAI Preparedness Framework v2（2025 年 4 月）引入 Research Categories——Long-range Autonomy、Sandbagging、Autonomous Replication and Adaptation、Undermining Safeguards——与 Tracked Categories 区分开来。Tracked Categories 触发 Capabilities Reports 加 Safeguards Reports，由 Safety Advisory Group 评审。DeepMind 的 FSF v3（2025 年 9 月，Tracked Capability Levels 于 2026 年 4 月 17 日加入）把 autonomy 并入 ML R&D 和 Cyber 两个领域（ML R&D autonomy level 1 = 以有竞争力的成本、相对人类 + AI 工具完全自动化 AI R&D 流水线）。FSF v3 通过针对工具性推理滥用的自动化监控，明确处理欺骗性对齐。需要诚实说明的是：PF v2 中的 Research Categories（包括 Long-range Autonomy）不会自动触发缓解；政策措辞是“潜在”。DeepMind 自己也说，如果工具性推理增强，自动化监控“将无法长期保持充足”。

**Type:** Learn
**Languages:** Python (stdlib, three-framework decision-table diff tool)
**Prerequisites:** 第 15 阶段，第 19 课（Anthropic RSP）
**Time:** ~45 分钟

## 问题场景

第 19 课细读了 Anthropic 的 scaling policy。本课通过阅读 OpenAI 与 DeepMind 的文档来补全图景。这三份文档是同宗产物，回答同一个问题——前沿实验室何时应当暂停或对模型设门禁——它们在少数类别上趋于一致，在若干重要之处出现分歧。

趋同之处：三者都把长时程自主性标为值得追踪的能力类别。三者都承认欺骗性行为（alignment faking、sandbagging）是一类特定的风险。三者都有内部评审机构。分歧之处：OpenAI 把类别拆成“Tracked”（强制缓解）与“Research”（不自动触发）。DeepMind 把自主性并入两个领域，而非单独命名。实验室们把这叫 Tracked vs Research、Critical vs Moderate，或 Tier-1 vs Tier-2；一项能力落在哪个桶里的运营后果，在各实验室之间并不相同。

把它们放在一起读，是有用的练习。同一项能力在 Anthropic 那里可能是“强制缓解”，在 OpenAI 那里是“受监控但不触发”，在 DeepMind 那里是“在特定领域内受追踪”。政策姿态很重要。

## 核心概念

### OpenAI Preparedness Framework v2（2025 年 4 月）

结构：

- **Tracked Categories**：触发 Capabilities Reports（模型能做什么）加 Safeguards Reports（已有哪些缓解）。部署前由 Safety Advisory Group 评审。
- **Research Categories**：实验室正在追踪、但尚未承诺具体缓解的模型能力。包括 Long-range Autonomy、Sandbagging、Autonomous Replication and Adaptation、Undermining Safeguards。

v2 的关键框架是：Research Categories 不会自动触发缓解。政策措辞是“潜在”缓解。需要盯住的具体差异就在于此：一个类别落在 Tracked 还是 Research，正是“设门禁”与“仅观测”之间的铰链。

### DeepMind Frontier Safety Framework v3（2025 年 9 月；Tracked Capability Levels 于 2026 年 4 月 17 日加入）

结构：

- **Critical Capability Levels (CCLs)**：横跨五个领域的能力阈值：Cyber、Bio、ML R&D、CBRN、Autonomy（并入 ML R&D 与 Cyber）。
- **Tracked Capability Levels**：2026 年 4 月加入的额外粒度。具体例子：ML R&D autonomy level 1 = 以有竞争力的成本、相对人类 + AI 工具完全自动化 AI R&D 流水线。
- **欺骗性对齐监控**：明确承诺对工具性推理滥用做自动化监控。

自主性的框架与 OpenAI 不同。DeepMind 不把“Autonomy”保留为顶层领域；它被并入自主性会造成危害的那些领域（ML R&D 与 Cyber）。论点是：脱离领域的自主性是没有风险的能力；反方论点是：跨领域的自主性是一种元风险，框架应当予以命名。

### 三者的共同点

- 内部 Safety Advisory Group（分别叫 Anthropic SAG、OpenAI SAG、DeepMind 内部委员会）。高能力模型在部署前接受评审。
- 明确把欺骗性对齐 / alignment faking 列为风险类别。
- 按声明节奏发布的常设产物（Anthropic：Frontier Safety Roadmap、Risk Report；OpenAI：Capabilities 与 Safeguards Reports；DeepMind：FSF 更新周期）。
- 都承认仅靠监控的防御存在上限。DeepMind 说得很明确：“自动化监控将无法长期保持充足。”

### 三者的分歧

- **Anthropic**：v3.0 移除了暂停承诺；AI R&D-4 阈值是点名的下一道门禁。
- **OpenAI**：Tracked vs Research 的二分；Research Categories（包括 Long-range Autonomy）不会自动设门禁。
- **DeepMind**：自主性并入其他领域；Tracked Capability Levels 在 2026 年 4 月增加了粒度。

### Sandbagging：一个让三者都变复杂的具体能力

Sandbagging（模型在评估中策略性地故意表现不佳）在 OpenAI 的 Research Categories 里。Anthropic 的 RSP v3.0 通过评估上下文差距（第 01 课）来处理它。DeepMind 通过 FSF v3 中的欺骗性对齐监控来处理它。

如果模型在评估中故意放水，那么每个框架的能力阈值都会被低估。框架只有在测量有效时才有效。这就是为什么除了实验室自评之外，还需要外部测量（第 21 课，METR）和对抗性评估。

### 政策阅读技能

- 定位：你关心的每一项能力都应当能在政策中找到。如果找不到，政策就没有覆盖它。
- 分类：它是 Tracked（触发缓解）还是 Research（受追踪但不触发）？OpenAI 明确这么叫；Anthropic 和 DeepMind 有各自的对应物。
- 节奏：政策是按声明的日程更新，还是只在特定事件之后更新？声明过的节奏更强。
- 独立性：外部评审是强制的还是可选的？Anthropic 与 Apollo 和美国 AI Safety Institute 合作；OpenAI 与 METR 合作；DeepMind 主要靠内部 SAG。

```figure
a5-tracked-vs-research
```

## Use It

`code/main.py` 实现了一个小型的决策表 diff 工具。给定一项能力（autonomy、deceptive alignment、R&D automation、cyber uplift 等），它输出三份政策各自如何分类该能力，以及会触发哪些缓解。它是阅读辅助工具，不是政策工具。

## Ship It

`outputs/skill-cross-policy-diff.md` 针对一项具体能力产出跨政策比较，以这三个框架为参照。

## Exercises

1. 运行 `code/main.py`。确认 diff 工具的输出，至少对两项你能对照源文档核实的能力与政策一致。

2. 完整阅读 OpenAI Preparedness Framework v2。找出每一个 Research Category。对每一个，用一句话写明它为什么在 Research 而不在 Tracked。

3. 完整阅读 DeepMind FSF v3，再加上 2026 年 4 月的 Tracked Capability Levels 更新。找出 ML R&D autonomy level 1 的具体评估标准。你会如何在外部测量它？

4. Sandbagging 在 OpenAI 的 Research Categories 里。设计一个评估，迫使一个 sandbagging 的模型暴露其真实能力。引用第 01 课关于 eval-context-gaming 的讨论。

5. 就一项具体能力（由你选择）比较这三份政策。说出你认为哪份政策的分类最严格、哪份最不严格。用源文本佐证。

## Key Terms

| 术语 | 人们怎么说 | 它实际是什么意思 |
|---|---|---|
| Preparedness Framework | “OpenAI 的 scaling policy” | PF v2（2025 年 4 月）；Tracked vs Research 两类 |
| Tracked Category | “强制缓解” | 触发 Capabilities + Safeguards Reports；SAG 评审 |
| Research Category | “仅监控” | 受追踪但无自动缓解；包括 Long-range Autonomy |
| Frontier Safety Framework | “DeepMind 的 scaling policy” | FSF v3（2025 年 9 月）+ Tracked Capability Levels（2026 年 4 月） |
| CCL | “Critical Capability Level” | DeepMind 按领域划分的阈值（Cyber、Bio、ML R&D、CBRN） |
| ML R&D autonomy level 1 | “R&D 自动化” | 以有竞争力的成本完全自动化 AI R&D 流水线 |
| Sandbagging | “策略性放水” | 模型在 eval 中故意表现不佳；在 OpenAI Research Categories 里 |
| Instrumental reasoning | “手段-目的推理” | 关于如何达成目标的推理；DeepMind 监控的目标 |

## Further Reading

- [OpenAI — Updating our Preparedness Framework](https://openai.com/index/updating-our-preparedness-framework/) — v2 公告。
- [OpenAI — Preparedness Framework v2 PDF](https://cdn.openai.com/pdf/18a02b5d-6b67-4cec-ab64-68cdfbddebcd/preparedness-framework-v2.pdf) — 完整文档。
- [DeepMind — Strengthening our Frontier Safety Framework](https://deepmind.google/blog/strengthening-our-frontier-safety-framework/) — FSF v3 公告。
- [DeepMind — Updating the Frontier Safety Framework (April 2026)](https://deepmind.google/blog/updating-the-frontier-safety-framework/) — Tracked Capability Levels 的新增。
- [Gemini 3 Pro FSF Report](https://storage.googleapis.com/deepmind-media/gemini/gemini_3_pro_fsf_report.pdf) — FSF 格式 Risk Report 的示例。
