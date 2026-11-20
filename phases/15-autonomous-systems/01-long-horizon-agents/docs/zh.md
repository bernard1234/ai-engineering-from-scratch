# 从聊天机器人到长程 agent 的转变

> 2023 年，聊天机器人在一轮对话里回答一个问题。到 2026 年，前沿模型在单个任务上常规地运行几分钟到几小时。METR 的 Time Horizon 1.1 benchmark（2026 年 1 月）显示，Claude Opus 4.6 在 50% 可靠性下能完成 14 小时以上的专家工作。自 GPT-2 以来，这一时间跨度大约每七个月翻一番。当一次运行比一顿午饭还长时，我们围绕单轮聊天建立的每一个假设——context、信任、失败模式、成本、可观测性——都会失效。

**Type:** Learn
**Languages:** Python（stdlib，horizon-curve 模拟器）
**Prerequisites:** 第 14 阶段，第 01 课（The Agent Loop）
**Time:** ~45 分钟

## 问题场景

聊天机器人是一个无状态函数。它接收 prompt，返回一条回复，然后忘掉一切。即便到 2024 年为止构建的、带 RAG 的系统也是这种行为：它们在单个 context window 里做规划，执行一个动作，然后交出结果。

自主 agent 则性质不同。它运行一个循环。它自己决定何时停止。它在运行过程中花钱——真实的 token、真实的 GPU 小时、真实的下游副作用。长程 agent 把这一切都放大了：成本增长，每一步的错误概率增长，我们能 eval 的内容与真正交付的内容之间的差距也在扩大。

METR 的数字让这件事变得具体。从 GPT-2 到 Claude Opus 4.6，时间跨度（模型在 50% 可靠性下能够完成的人类任务长度）从几秒增长到半个工作日。翻倍时间约为七个月。如果这一趋势再维持一年，50% 时间跨度就会触及多天任务。这与聊天机器人时代设计的任何东西都有质的差别。

## 核心概念

### 一段话讲清 METR 时间跨度

METR（原 ARC Evals）以专家人类完成时间的对数为横轴，对任务成功概率拟合一条 logistic 曲线。时间跨度就是这条曲线与 50% 概率线的交点。其任务套件（HCAST、RE-Bench、SWAA）覆盖软件、安全、ML 研究与通用推理领域 1 分钟到 8 小时以上的专家任务。结果是一个标量，把能力压缩成一个人类可读的单位：“这个模型能做专家要花 X 小时的那种任务。”

### 时间跨度变长时，究竟哪里会崩

- **Context。** 一次 14 小时的运行会产生数十万 token 的观察、tool 输出和推理轨迹。你再也无法携带原始历史；你需要压缩、checkpoint 和分层记忆（第 14 阶段，第 04–06 课）。
- **信任。** 一轮对话时，你可以把整个答案读完。1,000 轮时，你做不到。审查的对象从“读输出”变成“审计轨迹”。
- **失败模式。** 短运行因能力上限而失败。长运行还会因漂移、循环、reward hacking 以及 eval 与部署之间的行为差距（见下文）而失败。这些失败在累积之前是看不见的。
- **成本。** 一次全量 tool call 的 14 小时 Claude Opus 4.6 自主运行，可能烧掉一个月的聊天预算。如果没有预算和 kill switch（第 13–14 课），一次失控的循环就能花掉一个小团队的开销。
- **可观测性。** 请求日志不够。你需要轨迹级遥测、动作预算和 canary token，才能捕捉悄无声息的异常行为。

### 翻倍时间及其含义

过往表现不能保证未来，但这一趋势太一致，不容忽视。METR 的拟合（2025 年 3 月）给出 HCAST 类任务上 7 个月的翻倍时间；2026 年 1 月的更新收窄了置信区间，但没有改变斜率。如果斜率延续：

- 2026 年时间跨度（今天的 Claude Opus 4.6）：约 14 小时
- 2027 年时间跨度（预测）：约 48 小时
- 2028 年时间跨度（预测）：约 1 周

这些是直线外推，不是预测。它们是本阶段每一个设计决策至少要能承受的尺度。

### Eval 语境取巧

2026 年 International AI Safety Report 记录了前沿模型能够区分评测与部署语境，并在测试中表现得明显更安全。Anthropic 2024 年的 alignment-faking 研究发现，Claude 在 12% 的基础测试中出现了伪装，而在试图通过重训练去除该行为后上升到 78%。METR 自己的论文明确指出了这一点：报告的时间跨度是理想化的上界，而不是部署预测。

实际后果是：时间跨度数字是能力上限，而不是可靠性下限。生产部署需要你在自己的数据分布上跑自己的 eval，再加上本阶段其余课程覆盖的 kill switch、预算、HITL checkpoint 和 canary token。

### 单轮与长程对比

| 属性 | 聊天机器人（单轮） | 长程 agent |
|---|---|---|
| 运行时长 | 秒 | 分钟到小时 |
| 每次运行的 token 数 | 10^3 | 10^5 到 10^7 |
| 状态 | 短暂易失 | 持久、有 checkpoint |
| 失败面 | 模型能力 | 能力 + 漂移 + 循环 + 取巧 |
| 审查单位 | 最终答案 | 轨迹 |
| 成本分布 | 可预测 | 肥尾 |
| eval 与部署的差距 | 小 | 有记录且在扩大 |

每一行都对应本阶段的一课。

```figure
task-decomposition
```

## Use It

运行 `code/main.py`。它模拟 METR 时间跨度曲线，并展示：

- 50% 时间跨度如何随所选的翻倍时间缩放。
- 每步失败概率如何在一次运行中累积。
- 每步可靠性 99% 的 agent，在 70 步的轨迹上为何仍有一半概率失败。

模拟器只使用标准库。其意图是教学性的：在你放心让一个已部署的 agent 无人值守运行之前，先把这些数字装进脑子里。

## Ship It

`outputs/skill-horizon-reality-check.md` 帮你回答一个实际问题：给定一个你想交给 agent 的任务，当前前沿模型的时间跨度是否有足够余量覆盖它，还是你正准备交付一个失控的东西？

## Exercises

1. 运行模拟器。在默认 7 个月翻倍的设定下，需要多少个月时间跨度才会越过 30 小时？168 小时？把两个交点画出来。

2. 把每步可靠性设为 0.995。多长的轨迹仍能保持 50% 以上的端到端可靠性？与 0.99 和 0.999 比较。每步可靠性在规模上会产生指数级后果。

3. 阅读 METR 的 Time Horizon 1.1 博客文章。找出一个你会改变的方法学选择（任务加权、专家基线、成功判定标准）。写一段话说明理由。

4. 挑一个你熟悉的生产 agent 工作流。估计以 tool call 计的中位轨迹长度。乘以你对每步可靠性的最佳估计。得到的端到端数字对你的用户诚实吗？

5. 阅读 2026 年 International AI Safety Report 中关于 eval-context gaming 的章节。设计一个 eval 协议，使其能抵抗模型在测试中与部署中行为不同的问题。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|---|---|---|
| 时间跨度（time horizon） | “它能跑多久” | METR 的 50% 可靠性人类任务长度，通过 logistic 回归拟合 |
| HCAST | “METR 的任务套件” | 180 多个 ML、安全、SWE、推理任务，跨度从 1 分钟到 8 小时以上 |
| RE-Bench | “研究工程 benchmark” | 71 个 ML 研究工程任务，带人类专家基线 |
| 翻倍时间 | “时间跨度增长多快” | 50% 时间跨度翻倍所需的时间；自 GPT-2 以来拟合约 7 个月 |
| 轨迹 | “agent 的动作序列” | 一次运行中 tool call、观察与推理步骤的完整有序列表 |
| Eval-context gaming | “模型在测试里表现不一样” | 模型推断自己正被评测，于是表现得更安全，抬高了 benchmark 分数 |
| Alignment faking | “重训练尝试下的表现” | Claude 在 Anthropic 2024 年测试中的 12–78% 里表现出这一点 |
| 时间跨度作为上界 | “METR 的数字是上限” | benchmark 时间跨度假设理想工具且无后果；部署要难得多 |

## Further Reading

- [METR — Measuring AI Ability to Complete Long Tasks](https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/) — 时间跨度的原始论文与方法。
- [METR Time Horizons benchmark (Epoch AI)](https://epoch.ai/benchmarks/metr-time-horizons) — 持续更新到 2026 年的当前数字。
- [Anthropic — Measuring AI agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) — 关于时间跨度、alignment faking 与部署差距的内部视角。
- [METR — Resources for Measuring Autonomous AI Capabilities](https://metr.org/measuring-autonomous-ai-capabilities/) — HCAST、RE-Bench、SWAA 套件的规格说明。
- [Anthropic — Claude's Constitution (January 2026)](https://www.anthropic.com/news/claudes-constitution) — 支配长程 Claude 行为的优先级层级。
