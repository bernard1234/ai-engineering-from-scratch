# CAIS、CAISI 与 societal-scale risk

> Center for AI Safety（CAIS，旧金山，2022 年由 Hendrycks 和 Zhang 创立）发布 four-risk 框架——malicious use、AI races、organizational risks、rogue AIs——以及 May 2023 那份由数百位教授和公司领袖签署的灭绝风险声明。CAIS 的 2026 年发布物：用于前沿模型评估的 AI Dashboard、Remote Labor Index（与 Scale AI 合作）、Superintelligence Strategy Paper、AI Frontiers newsletter。另有一个不同的实体：NIST 的 Center for AI Standards and Innovation（CAISI）——面向美国政府的自愿协议，以及聚焦网络、生物和化学武器风险的未分类能力评估。CAIS 把 organizational risk 列为四项顶层风险之一：安全文化、严格审计、多层防御和信息安全都是基础，却常常被拿去与部署速度做权衡。California SB-53 若签署，将成为美国首个州级灾难性风险法规。

**Type:** Learn
**Languages:** Python（stdlib，four-risk 清单与缓解措施匹配器）
**Prerequisites:** 第 15 阶段，第 19 课（RSP）、第 15 阶段，第 20 课（PF + FSF）
**Time:** ~45 分钟

## 问题场景

第 19、20 课讲了实验室内部的扩展政策。第 21 课讲了独立的能力评估。本课讲第三种视角：塑造灾难性 AI 风险公共讨论与监管基线的公民社会与政府组织。

有两个不同的实体值得注意。CAIS 是一家非营利研究组织，发布思考 AI 风险的框架并协调公开声明。CAISI 是 NIST 内部的美国政府中心，管理与实验室的自愿协议和未分类能力评估。两个名字连读相近；使命并不重叠。从业者应当两者都了解。

实用内容在于：CAIS 的 four-risk 框架是文献中被引用最多的 societal-scale risk 分类法。安全文化与 organizational risk 是那四类之一，也是从业者最直接可控的一类。SB-53（California）若签署，将成为美国首个州级灾难性风险法规；该法案的框架方式很重要，因为在美国科技政策中，州级监管历来领先于联邦行动。

## 核心概念

### CAIS — Center for AI Safety

- 成立：2022 年于旧金山，由 Dan Hendrycks 及其同事创立（“Zhang”这一名字指一位早期合作者，而非现任联合创始人；现任领导层见 CAIS 网站）。
- 状态：501(c)(3) 非营利组织。
- 2023 年的重要产出：灭绝风险声明，由数百位研究者和 CEO 联署。声明称：“降低 AI 带来的灭绝风险，应当与流行病、核战争等其他 societal-scale risk 一起，成为全球优先事项。”
- 2026 年产出：用于前沿模型评估的 AI Dashboard、Remote Labor Index（与 Scale AI 合作）、Superintelligence Strategy Paper、AI Frontiers newsletter。

### four-risk 框架

CAIS 的框架把灾难性 AI 风险归为四个顶层类别：

1. **Malicious use**：恶意行为者利用 AI 造成伤害（生物武器合成、虚假信息、网络攻击）。
2. **AI races**：实验室、公司或国家之间的竞争压力，把部署推过安全的临界点。
3. **Organizational risks**：实验室内部动态（安全文化失守、审计不足、安全资源不足）导致糟糕的部署。
4. **Rogue AIs**：能力足够强的 AI 追求与人类福祉冲突的目标。

这不是唯一的分类法，但是被引用最多的。这些类别并不互斥——一个在竞赛中用审计换速度的组织所产出的 rogue AI，同时属于这四类。

### organizational risk 的所在

在四个类别中，organizational risk 对从业者来说最可操作。实验室的安全文化、审计严格度、防御分层和信息安全，决定了他们的模型发布时第 10–18 课的那些控制是否真的到位，还是仅仅成了没人验证的清单项。

具体的 organizational-risk 杠杆：

- **安全文化**：团队成员是否敢在不付出职业代价的情况下上报担忧？CAIS 的调查发现，这是其他杠杆的强预测因子。
- **严格审计**：外部与内部都要。只有内部审计会产出乐观的报告。
- **多层防御**：任何单一层都不充分（贯穿第 15 阶段的主题）。
- **信息安全**：模型权重泄露、eval 数据泄露、monitor 绕过技术泄露。第 19 课中的 RAND SL-4 是一个具体标准。

### CAISI — Center for AI Standards and Innovation

- 在 NIST 内部运作。
- 与前沿实验室签订自愿协议。
- 发布聚焦网络、生物和化学武器风险的未分类能力评估。
- 与 CAIS 不同；两个缩写相撞；核对 URL（nist.gov）以确认你读的是哪一个。

CAISI 的角色，是 METR 私下与实验室合作（第 21 课）的公开、面向政府的对应物。CAISI 的报告是未分类的；METR 的报告往往受 NDA 限制。两者都读，从业者能得到更完整的图景。

### California SB-53

这份加州参议院法案（2025–2026 会期）针对前沿模型带来的灾难性风险。草案中的关键条款：

- 触发州级义务的具体能力阈值。
- 面向 AI 实验室员工的吹哨人保护。
- 灾难性故障的事件报告要求。

若签署，它将成为美国首个州级灾难性风险法规。无论签署与否，该法案的框架都会影响其他州立法机构处理这一问题的方式。加州的从业者应跟踪该法案的进展；其他地方的从业者应读一读，以了解美国州级监管可能是什么样子。

### societal-scale risk 不是单层问题

第 15 阶段贯穿始终的主题——纵深防御——在社会层面同样适用。没有任何单一组织、法规或框架能闭合灾难性风险。只有满足以下条件时，这套生态才运转：

- 实验室发布扩展政策（第 19、20 课）。
- 外部评估机构产出测量（第 21 课）。
- 公民社会跟踪并公开（CAIS）。
- 政府运行自愿项目与基线监管（CAISI、SB-53）。
- 从业者构建多层控制（第 10–18 课）。

这是本阶段的最终综合：前面每一课都是这个栈中的一层，整栈的完整性比任何单层的力量都更重要。

```figure
a5-four-risks
```

## Use It

`code/main.py` 实现一个小型风险清单工具。给定一个拟议的部署，它按 four-risk 类别给该部署打标签，并返回一份缓解检查清单。它是理解框架的阅读辅助，不能替代人类判断。

## Ship It

`outputs/skill-societal-risk-review.md` 审查一个部署的 societal-scale risk 态势：它触及四类中的哪几类、已有哪些缓解措施、organizational risk 的暴露程度如何。

## Exercises

1. 运行 `code/main.py`。输入三个不同规模的合成部署。确认 four-risk 标签符合你的预期；找出一个工具少打标签或多打标签的案例。

2. 完整读一遍 CAIS 的 four-risk 论文。选一个风险类别，写两段话，谈谈你认为该类别中 2026 年最重要的进展是什么。

3. 读一份 California SB-53 的当前草案。找出你认为强化灾难性风险态势的一条条款，以及你认为削弱它的一条条款。分别给出理由。

4. 挑一个你了解的生产 AI 部署（你自己的或已公开的）。用 organizational-risk 的各子杠杆给它打分：安全文化、审计严格度、多层防御、信息安全。哪一项最弱？把它补齐到及格线要付出什么代价？

5. 勾勒一个 2028 版的 four-risk 框架，反映额外一年的能力增长和额外一年的部署经验。你会增加、删除或重组哪些内容？

## Key Terms

| 术语 | 常见说法 | 实际含义 |
|---|---|---|
| CAIS | “Center for AI Safety” | 非营利组织；four-risk 框架；2023 年灭绝风险声明 |
| CAISI | “美国政府 AI 安全” | NIST 中心；自愿协议；未分类 eval |
| Four-risk framework | “CAIS 的分类法” | malicious use、AI races、organizational risks、rogue AIs |
| Malicious use | “坏人利用 AI” | 生物武器、虚假信息、网络攻击 |
| AI races | “竞争压力” | 实验室/公司/国家把部署推过安全线 |
| Organizational risk | “实验室内部失效” | 安全文化、审计、防御、信息安全 |
| Rogue AI | “失准的 agent” | 能力强的 AI 追求与人类福祉冲突的目标 |
| California SB-53 | “州级监管” | 2025–2026 法案；若签署即美国首个州级灾难性风险法规 |

## Further Reading

- [Center for AI Safety](https://safe.ai/) — four-risk 框架的机构所在地。
- [CAIS — AI Risks that Could Lead to Catastrophe](https://safe.ai/ai-risk) — four-risk 论文。
- [CAIS — May 2023 statement on extinction risk](https://safe.ai/statement-on-ai-risk) — 简短的联署声明。
- [NIST CAISI](https://www.nist.gov/caisi) — 面向政府的 AI 标准与创新中心。
- [Anthropic — Measuring agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) — 把实验室层面的承诺与社会层面的框架连接起来。
