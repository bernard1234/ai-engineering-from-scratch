# Anthropic Responsible Scaling Policy v3.0

> RSP v3.0 于 2026 年 2 月 24 日生效，取代 2023 年的政策。双层缓解：区分 Anthropic 单方面会做什么，以及被框定为全行业建议的内容（包括 RAND SL-4 安全标准）。把 Frontier Safety Roadmaps 和 Risk Reports 增设为常设文档，而非一次性交付物。放弃了 2023 年的暂停承诺。引入 AI R&D-4 阈值：一旦跨过，Anthropic 必须发布一份肯定性论证，指出错位风险与缓解措施。Claude Opus 4.6 并未跨过它。Anthropic 在 v3.0 公告中表示，“自信地排除这一点正变得困难”。SaferAI 给 2023 年 RSP 的评级是 2.2；他们把 v3.0 下调到 1.9，使 Anthropic 与 OpenAI、DeepMind 一起落入“弱”RSP 类别。定性阈值取代了 2023 年的定量承诺；移除暂停条款是最尖锐的倒退。

**Type:** Learn
**Languages:** Python (stdlib, RSP threshold decision engine)
**Prerequisites:** 第 15 阶段，第 06 课（AAR）、第 15 阶段，第 07 课（RSI）
**Time:** ~45 分钟

## 问题场景

前沿实验室发布的 scaling policy 既是技术文档，也是治理文档，还是向监管者发出的信号，三者兼而有之。RSP v3.0 是 Anthropic 当前的文档。细读它的重要性不在于遵守它是强制的（它并非强制），而在于这套框架塑造了一个实验室如何构想灾难性风险，以及如何向公众传达取舍。

v3.0 与 v2.0 的差异是有用的分析单元。新增了什么：Frontier Safety Roadmaps、Risk Reports、AI R&D-4 阈值。移除了什么：2023 年的暂停承诺。重新表述了什么：把双层缓解时间表拆分为 Anthropic 单方面与行业建议两部分。外部评审——SaferAI——把评分从 2.2（v2）下调到 1.9（v3.0）。一份 scaling policy 就是这样在看起来更精致的同时变得不那么严格的。

## 核心概念

### 双层缓解时间表

- **Anthropic 单方面行动**：无论其他实验室怎么做、Anthropic 都会做的事。越过阈值即停止训练、特定的安全措施、特定的部署门禁。
- **全行业建议**：Anthropic 认为整个行业应当共同做的事。包括 RAND SL-4 安全标准。这些不是 Anthropic 一方的承诺，而是政策倡导。

双层结构在 v2 中并不存在。它意味着读者需要看清每项承诺落在哪一栏。一项安全措施若在“全行业建议”栏，那就不是 Anthropic 的承诺，而是 Anthropic 的期望。

### AI R&D-4 阈值

这是 RSP v3.0 认定为下一个重要阈值的 capability level。具体来说：一个能以有竞争力的成本自动化相当大一部分 AI 研究的模型。一旦 Anthropic 认为某个模型跨过了它，就必须在继续扩展之前发布一份肯定性论证，指出错位风险与缓解措施。

根据 v3.0 公告，Claude Opus 4.6 并未跨过它。文档还补充道：“自信地排除这一点正变得困难。”这一措辞很重要；它承认该阈值近到足以成为一个现实的关切，而不是一个推测性的上限。

第 06 课（Automated Alignment Research）和第 07 课（Recursive Self-Improvement）直接指向这一阈值。自动化对齐研究者跨过研究质量的门槛，正是 AI R&D-4 阈值正在逼近的证据。

### Frontier Safety Roadmaps 与 Risk Reports

v3.0 把两类产物提升为常设文档：

- **Frontier Safety Roadmap**：前瞻性文档，描述计划开展的安全工作、能力预期与缓解研究。
- **Risk Report**：针对特定模型在发布后的回溯性文档，描述观测到的能力与残余风险。

两者都是公开的，都按声明的节奏更新。其效用在于：读者可以追踪 Anthropic 在 Roadmap 里说要做的事，与它在 Risk Report 里报告的内容之间如何对照。

### 移除暂停条款

2023 年的 RSP 包含一项明确的暂停承诺：如果模型跨过特定的能力阈值，训练将暂停，直到缓解措施到位。v3.0 用更温和的表述替换了明确的暂停（发布肯定性论证，若缓解措施充足则继续推进）。SaferAI 和其他分析者直接指出，这是新文档中最强的倒退。

为这一改动辩护的政策论点是：2023 年的定量阈值到了 2026 年的能力 benchmark 上变得无法企及，因为这些 benchmark 本身被重新标定了。反方论点是：scaling policy 里的暂停条款是一种承诺装置；移除它也就移除了政策的可信度。

### SaferAI 的降级

SaferAI 是一家为 RSP 式文档评级的独立机构。他们的公开评级：2023 年 Anthropic RSP 得 2.2 分（满分标准中 4.0 是当前最好的 RSP，1.0 是名义水平）。v3.0 得 1.9 分。这让 Anthropic 从“中等”掉到“弱”，与 OpenAI 和 DeepMind 同属弱类别。

按 SaferAI 的说法，降级因素包括：
- 定性阈值取代了定量阈值。
- 暂停承诺被移除。
- AI R&D-4 阈值的缓解被描述为“肯定性论证”，而非具体措施。
- 评审机制依赖 Anthropic 的 Safety Advisory Group，独立监督有限。

### 本课不是什么

这不是一堂关于合规的课。RSP v3.0 不是法规；没有任何东西强制 Anthropic 遵守它。这堂课讲的是以它应得的细致与怀疑去阅读这份文档。scaling policy 是前沿实验室就灾难性风险姿态发出的主要公开信号。对于任何其工作依赖前沿能力的人来说，善于阅读它们是一项实用技能。

```figure
a5-rsp-ladder
```

## Use It

`code/main.py` 实现了一个小型决策引擎，复刻 RSP 阈值评估的形状：给定一个候选模型和一组能力测量值，返回 AI R&D-4 阈值是否被跨过、所需的肯定性论证章节，以及部署能否推进。它被刻意做得很简单；重点是把文档里的逻辑显式化。

## Ship It

`outputs/skill-scaling-policy-review.md` 对照 v3.0 参考评审一份 scaling policy（Anthropic、OpenAI、DeepMind 或内部）：双层结构、阈值、暂停承诺、独立评审。

## Exercises

1. 运行 `code/main.py`。喂进三个不同能力水平的合成模型。确认阈值评估器的行为符合预期，并产出正确的肯定性论证模板。

2. 完整阅读 RSP v3.0（32 页）。找出所有落在“全行业建议”层的承诺。其中哪些在 v2 中本会是“Anthropic 单方面”？

3. 阅读 SaferAI 的 RSP 评分方法。把他们的评分细则套用到该文档上，复现他们给 v3.0 的 1.9 分。哪一行细则最推动了这次降级？

4. 2023 年的暂停承诺被移除了。提出一项替代承诺，既保住政策的可信度，又承认 2026 年 benchmark 重标定的问题。

5. 把 RSP v3.0 与 OpenAI Preparedness Framework v2（第 20 课）做比较。挑一个 v3.0 更强的领域。再挑一个 Preparedness Framework 更强的领域。

## Key Terms

| 术语 | 人们怎么说 | 它实际是什么意思 |
|---|---|---|
| RSP | “Anthropic 的 scaling policy” | Responsible Scaling Policy；v3.0 于 2026 年 2 月 24 日生效 |
| AI R&D-4 | “研究自动化阈值” | 以有竞争力的成本自动化相当大一部分 AI 研究的能力 |
| Affirmative case | “安全论证” | 公开发布的论证，说明风险已被识别、缓解措施充足 |
| Frontier Safety Roadmap | “前瞻计划” | 关于计划安全工作和预期能力的常设文档 |
| Risk Report | “对某模型的回溯” | 关于发布后观测能力与残余风险的常设文档 |
| Two-tier mitigation | “单方面 vs 行业” | 把 Anthropic 的承诺与行业建议分开 |
| Pause commitment | “2023 条款” | 明确承诺暂停训练；在 v3.0 中被移除 |
| SaferAI rating | “独立 RSP 评分” | 第三方评分细则；v3.0 得 1.9（v2 为 2.2） |

## Further Reading

- [Anthropic — Responsible Scaling Policy v3.0](https://anthropic.com/responsible-scaling-policy/rsp-v3-0) — 完整 32 页政策。
- [Anthropic — RSP v3.0 announcement](https://www.anthropic.com/news/responsible-scaling-policy-v3) — 相对 v2 的变更摘要。
- [Anthropic — Frontier Safety Roadmap](https://www.anthropic.com/responsible-scaling-policy/roadmap) — RSP v3.0 中链接的常设文档。
- [Anthropic — Risk Report: February 2026](https://www.anthropic.com/feb-2026-risk-report) — 对 Claude Opus 4.6 的回溯，它是发布时的那款前沿模型。
- [Anthropic — Measuring agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) — 把 AI R&D-4 与实测自主性联系起来。
