# 评估驱动的智能体开发

> Anthropic 的指引：「从简单的提示词开始，用全面的评估来优化它们，只在必要时才加入多步智能体系统。」评估不是最后一步。它是驱动 Phase 14 中其他每一个选择的外层循环。

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** All of Phase 14.
**Time:** ~60 minutes

## 学习目标

- 说出三个评估层——静态 benchmark、自定义离线、在线生产——以及各自的作用。
- 解释 evaluator-optimizer 的紧密循环。
- 描述 2026 年的最佳实践：评估与代码放在一起、在 CI 中运行、对 PR 设门。
- 把 Phase 14 的每一课都连接到它所生成的评估用例。

## 问题

智能体能通过演示。它们在生产中会以演示无法预测的方式失败。Benchmark 回答的是「这个模型广泛地能吗？」，而不是「这个智能体为我的产品交付正确的补丁吗？」答案是：在三个层面做评估，持续运行，并让每一条 guardrail 和每一条学到的规则都对应到一个评估用例。

## 概念

### 三个评估层

1. **静态 benchmark**——用于代码的 SWE-bench Verified（第 19 课）、用于浏览 / 桌面的 WebArena/OSWorld（第 20 课）、用于通用能力的 GAIA（第 19 课）、用于工具使用的 BFCL V4（第 06 课）。用于跨模型对比和回归门禁。污染是真实存在的：SWE-bench+ 发现了 32.67% 的解法泄露。始终报告 Verified / +-审计后的分数。

2. **自定义离线评估**——你的产品形态：
   - LLM-as-judge（Langfuse、Phoenix、Opik——第 24 课）。
   - 基于执行的评估（跑补丁、查测试）。
   - 基于轨迹的评估（把动作序列与 gold 对比；OSWorld-Human 显示顶级智能体为 gold 的 1.4-2.7 倍）。

3. **在线评估**——生产：
   - 会话回放（Langfuse）。
   - guardrail 触发的告警（第 16、21 课）。
   - 逐步成本 / 延迟追踪（第 23 课 OTel spans）。

### Evaluator-optimizer（Anthropic）

紧密循环：

1. 提议者生成输出。
2. 评估者做出判断。
3. 优化直到评估者通过。

这是 Self-Refine（第 05 课）的泛化。你在乎的任何智能体流程都可以包进 evaluator-optimizer 以获得可靠性。

### 2026 年的最佳实践

- 评估与代码放在一起。
- 在每一个 PR 的 CI 中运行。
- 用评估分数对合并设门（例如「相比 main 的回归不超过 5%」）。
- 每一条 guardrail 都对应一个评估用例。
- 每一条学到的规则（Reflexion、pro-workflow learn-rule）都对应一个失败用例。

### 把 Phase 14 串起来

Phase 14 的每一课都会生成评估用例：

| 课程 | 它生成的评估用例 |
|--------|------------------------|
| 01 Agent Loop | 预算耗尽、死循环防护 |
| 02 ReWOO | 工具失败时 planner 正确重新规划 |
| 03 Reflexion | 学到的反思在重试时生效 |
| 05 Self-Refine/CRITIC | 判定器通过优化后的输出 |
| 06 Tool Use | 参数强转生效；未知工具被拒绝 |
| 07-10 Memory | 检索引用与来源匹配；过期事实被判定无效 |
| 12 Workflow Patterns | 每种模式产出正确输出 |
| 13 LangGraph | 恢复精确复现状态 |
| 14 AutoGen Actors | DLQ 抓住崩溃的 handler |
| 16 OpenAI Agents SDK | Guardrail 在正确的输入上触发 |
| 17 Claude Agent SDK | 子智能体结果返回到 orchestrator |
| 19-20 Benchmarks | SWE-bench Verified 分数、WebArena 成功率、OSWorld 效率 |
| 21 Computer Use | 逐步安全抓住被注入的 DOM |
| 23 OTel | Spans 发出所需属性 |
| 26 Failure Modes | 检测器标记已知失败 |
| 27 Prompt Injection | PVE 拒绝被投毒的检索 |
| 28 Orchestration | Supervisor 路由到正确的专家 |
| 29 Runtime Shapes | DLQ 处理 N% 的失败 |

如果你的评估套件为每一项都有用例，你就覆盖了 Phase 14。

### 评估驱动开发在哪里会失败

- **没有基线。** 没有 last-known-good 的评估不可读。存储基线。
- **没有依据的 LLM-judge。** 判定器也会幻觉。CRITIC 模式（第 05 课）——判定器以外部工具为依据。
- **对评估过拟合。** 为评估优化会偏离生产的实际效用。轮换用例。
- **脆弱的评估。** 非确定性用例造成误报。固定种子、快照状态。

```figure
ae-eval-three-layers
```

## Build It

`code/main.py` 是一个标准库评估 harness：

- 带类别（benchmark、custom、online）的用例注册表。
- 一个被测的脚本化智能体。
- Evaluator-optimizer 循环：提议、判定、优化，直到通过或达到最大轮数。
- CI 门禁：聚合通过率 + 对基线的回归。

运行它：

```
python3 code/main.py
```

输出：逐用例通过/失败、回归标记、CI 门禁裁决。

## Use It

- 把评估用例写在与智能体代码相同的仓库里。
- 通过 CI 在每个 PR 上运行它们。
- 出现回归就让构建失败。
- 追踪通过率随时间的走势。
- 把每一次生产失败都绑定到一个新用例。

## Ship It

`outputs/skill-eval-suite.md` 为智能体产品构建一个带 CI 门禁和回归追踪的三层评估套件。

## 练习

1. 拿一个你的生产失败。写一个能复现它的评估用例。你的智能体现在能通过它吗？
2. 为你的领域构建一个带三个维度（事实性、语气、scope）的 LLM-judge 评分标准。给 50 个会话打分。
3. 把评估套件接入 CI。在 >=5% 回归时让构建失败。
4. 加一个轨迹效率指标：与 gold 轨迹相比，智能体走了多少步？
5. 把 Phase 14 的每一课都映射到你的套件中的一个评估用例。有缺的吗？那是一个要补上的缺口。

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| Static benchmark | 「现成评估」 | SWE-bench、GAIA、AgentBench、WebArena、OSWorld |
| Custom offline eval | 「领域评估」 | 在你产品形态上的 LLM-as-judge / 执行 / 轨迹 |
| Online eval | 「生产评估」 | 会话回放、guardrail 告警、成本/延迟追踪 |
| Evaluator-optimizer | 「提议-判定-优化」 | 迭代直到判定器通过 |
| CI gate | 「合并拦截器」 | 在评估回归时让构建失败 |
| Baseline | 「Last-known-good」 | 用于检测回归的参考分数 |
| Trajectory efficiency | 「超过 gold 的步数」 | 智能体步数除以人类专家最小值 |

## 延伸阅读

- [Anthropic，Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)——「从简单开始，用评估优化」
- [OpenAI，SWE-bench Verified](https://openai.com/index/introducing-swe-bench-verified/)——经过整理的 benchmark
- [Berkeley Function Calling Leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html)——工具使用 benchmark
- [Langfuse docs](https://langfuse.com/)——实践中的评估 + 会话回放