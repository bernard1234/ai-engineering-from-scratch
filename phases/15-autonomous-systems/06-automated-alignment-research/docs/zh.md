# 自动化对齐研究（Anthropic AAR）

> Anthropic 让多支 Claude Opus 4.6 Autonomous Alignment Researcher 团队在彼此独立的 sandbox 中并行运行，并通过一个共享 forum 协作，而该 forum 的日志存放在任何 sandbox 之外（因此 agent 无法删除自己的记录）。在 weak-to-strong training 问题上，这些 AAR 的表现超过了人类研究者。Anthropic 自己的总结指出，prescribed workflow 往往会限制 AAR 的灵活性并降低性能。将对齐研究自动化，正是把时间线压缩到 RSP 旨在检测的那类 misalignment 风险的压缩步骤。

**Type:** Learn
**Languages:** Python（stdlib，并行研究 forum 模拟器）
**Prerequisites:** 第 15 阶段，第 05 课（AI Scientist v2）、第 15 阶段，第 04 课（DGM）
**Time:** ~60 分钟

## 问题场景

对齐研究极其消耗人类研究者的时间。可扩展监督（scalable oversight）、奖励指定（reward specification）或 weak-to-strong training 这类问题，每一次迭代都需要数周的实验。随着前沿能力提升，对齐工作的负担增长速度超过了合格研究者的供给。

Automated Alignment Research（AAR）要回答的是：那些能力强到已经跑赢对齐的前沿模型，能否也参与把差距补上。Anthropic 2026 年发布的一份由 AAR 主导的 weak-to-strong training 研究报告（alignment.anthropic.com/2026/automated-w2s-researcher/）是此类已部署系统的首批公开成果之一。

结果确实是正面的：AAR 在一个研究问题上超过了人类基线。但这个结果也把本阶段讨论过的所有担忧，集中到了同一个系统里。如果对齐研究可以被自动化，那么损害 safeguard 的那部分工作同样可以被自动化。RSP 关于 AI R&D 能力的阈值，正是围绕这个循环设定的。

## 核心概念

### 架构（依公开描述）

- **并行 agent。** 多个 Claude Opus 4.6 实例作为 AAR 运行，各自处于独立的 sandbox 中。sandbox 限制文件系统、网络与进程暴露面。
- **共享 forum。** 研究发现会发布到一个共享 forum，其存储后端位于每个 sandbox 之外。agent 可以读取该 forum；但 agent 无法从自己的 sandbox 内删除或编辑 forum 记录。
- **任务分配。** 由人类设计的任务队列把研究问题分派给 AAR。AAR 提出任务拆解、运行实验、撰写研究发现。
- **聚焦 weak-to-strong training。** 已发表的研究处理的是 weak-to-strong training——用能力较弱的监督模型去训练能力更强的学生模型。AAR 在这项任务上超过了人类研究者。

### 为什么 sandbox 之外的日志很重要

日志完整性这一性质，是受控实验与可能已被污染的实验之间的分界线。如果 AAR 能编辑自己的日志，就能掩盖失败或可疑的实验。Anthropic 直接指出了这一点：该性质是信任研究产出的必要条件，而且很难验证。

用基础设施的话说，其对应物是带有向外部存储直写（write-through）的只追加日志（例如 S3 object-lock、不可篡改的 Datadog 日志）。agent 没有修改历史记录的凭据。2026 年企业安全团队抵御勒索软件的审计留痕，用的也是同一个模式。

### prescribed workflow 的权衡

Anthropic 的报告指出，prescribed workflow 往往会限制 AAR 的灵活性并降低性能。换言之：如果由人类设计者把研究计划一步步写死，AAR 的表现会不如只给出高层目标、让它自由拆解。这与 agentic research（LangGraph、Microsoft 的 Agent Framework）领域的结论一致——过度规定细节的 scaffold 会拖累有能力的 agent。

安全上的含义很微妙。提升 AAR 表现的灵活性，恰恰也是容许未经批准的任务拆解、新颖工具使用和目标漂移的灵活性。这个权衡是一个设计空间决策：要给出多少灵活性，才能换来足以超越人类的能力，同时又不至于留出让 agent 把目标泛化到分布之外的余地？

### 压缩风险

RSP v3.0（第 19 课）引入了 AI R&D 能力阈值：以相对「人类 + AI 工具」有竞争力的成本，把 AI R&D 流水线完全自动化。DeepMind 的 FSF v3 包含一个类似的 ML R&D 自主性等级。两套框架都把这个阈值当作启动更高控制措施的触发点。

AAR 距离该阈值只差一步：它自动化了流水线的一部分（针对具体、边界清晰的任务做对齐研究），但没有覆盖端到端的能力开发循环。真正的时间线问题是，这个差距以多快的速度缩小。

压缩的时间线才是复合失效（compounding failure）的隐忧。如果对齐研究与能力研究以相近的速率复利增长，misalignment 风险面至少会以和能力一样快的速度扩张。如果能力增长得更快（这是历史趋势），差距就会拉大。这正是「AAR 是一种有条件的好事」的论据：每一份额外的对齐成果，只有在研究过程可信时，才会缩小差距。

### AAR 不能替代的东西

人类研究者设定任务队列、审阅结果，并掌握 constitution 意义上的最终权力。AAR 加速的是流水线的中段，而不是两端。Anthropic 公开的产出同时包含 AAR 的贡献，以及人类研究者对什么该发表、什么该撤回、什么该打磨的判断。

这与第 15 课的 propose-then-commit 模式被应用于研究本身是一致的：AAR 提出，人类提交。

```figure
aar-forum
```

## Use It

`code/main.py` 模拟一个多 AAR 的研究 forum。三个独立的「研究 agent」并行运行，把研究发现发布到一个只追加的 forum 上，并可选地触发篡改尝试。

观察：

- sandbox 之外的日志如何捕获日志篡改尝试。
- 在更难的问题上，允许自由拆解的任务分配如何胜过固定流程。
- 如果日志不具备防篡改（tamper-evident）能力，单个被攻陷的 AAR 如何污染 forum 的信号。

## Ship It

`outputs/skill-aar-deployment-review.md` 是一份针对自动化对齐研究流水线的部署前评审。

## Exercises

1. 运行 `code/main.py`。对比「fixed-workflow」与「free-decomposition」两种设置。自由拆解总是胜出吗？还是存在某些问题类别，让固定流程也能一较高下？

2. 修改模拟器，让其中一个 agent 尝试篡改日志。确认只追加日志能检测到这种行为。用一段话准确描述该检测信号在日志中长什么样。

3. 阅读 Anthropic 的 weak-to-strong AAR 报告。找出 AAR 胜过人类研究者的那个具体子任务。它为什么适合被自动化？

4. 设计一种任务队列分配策略，在 AAR 的灵活性（更好的结果）与 prescribed workflow 的约束（更易审计）之间取得平衡。说明你会如何对两者做 A/B 测试。

5. 阅读 RSP v3.0 的 AI R&D-4 阈值。用一段话描述：你认为什么东西一旦出现就会越过该阈值，而 AAR 目前还做不到。

## Key Terms

| 术语 | 通俗说法 | 实际含义 |
|---|---|---|
| AAR | 「Automated Alignment Researcher」 | 被自主地运行于对齐问题上的 Claude Opus 4.6 实例 |
| Weak-to-strong training | 「用一个更弱的监督者训练更强的模型」 | 一个经典的可扩展监督 benchmark，AAR 在此超过了人类 |
| Shared forum | 「agent 发布研究发现的地方」 | 只追加、位于 sandbox 之外的存储 |
| Out-of-sandbox log | 「agent 无法编辑自己的记录」 | 向外部存储的防篡改（tamper-evident）直写 |
| Prescribed workflow | 「来自人类设计者的分步计划」 | 限制 AAR；相较自由拆解常常降低性能 |
| Free decomposition | 「由 agent 决定如何拆分任务」 | 能力更强，更难审计 |
| AI R&D threshold | 「RSP/FSF 能力等级」 | 以有竞争力的成本完全自动化 R&D 流水线 |
| Compressed timeline | 「对齐与能力的竞赛」 | 如果能力比对齐复利得更快，misalignment 风险就会增长 |

## Further Reading

- [Anthropic — Automated Weak-to-Strong Researcher](https://alignment.anthropic.com/2026/automated-w2s-researcher/)——一手来源。
- [Anthropic Responsible Scaling Policy v3.0](https://anthropic.com/responsible-scaling-policy/rsp-v3-0)——AI R&D 阈值的框定方式。
- [Anthropic — Measuring AI agent autonomy](https://www.anthropic.com/research/measuring-agent-autonomy)——更宽泛的 agent 自主性框定。
- [DeepMind Frontier Safety Framework v3](https://deepmind.google/blog/strengthening-our-frontier-safety-framework/)——与 RSP 平行的 ML R&D 自主性等级。
- [Burns et al. (2023). Weak-to-Strong Generalization (OpenAI)](https://openai.com/index/weak-to-strong-generalization/)——AAR 所攻克的底层问题。
