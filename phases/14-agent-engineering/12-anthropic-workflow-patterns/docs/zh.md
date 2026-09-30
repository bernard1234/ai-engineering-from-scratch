# Anthropic 的工作流模式：简单胜于复杂

> Schluntz 和 Zhang（Anthropic，2024 年 12 月）把工作流（预定义路径）与智能体（动态工具使用）区分开来。五种工作流模式覆盖了大多数情形。从直接 API 调用开始。只有当步骤无法预测时才加入智能体。

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 01 (Agent Loop)
**Time:** ~60 minutes

## 学习目标

- 说出 Anthropic 的五种工作流模式：prompt chaining、routing、parallelization、orchestrator-workers、evaluator-optimizer。
- 解释「智能体 vs 工作流」的区分，以及各自的工程成本。
- 识别出什么时候该选工作流而非智能体（以及反过来）。
- 用标准库对一个脚本化 LLM 实现全部五种模式。

## 问题

团队会为一个其实只要一次函数调用就能解决的问题去上多智能体框架。成本是真实的：框架加了层层抽象，掩盖了 prompt，隐藏了控制流，并招致过早的复杂性。Schluntz 和 Zhang 2024 年 12 月的文章是业界被引用最多的反对声音：从简单开始，只有当复杂性物有所值时才加上它。

## 概念

### 工作流 vs 智能体

- **工作流。** 通过预定义代码路径编排的 LLM 和工具。工程师拥有这个图。
- **智能体。** LLM 动态地指挥自己的工具、走出自己的步骤。模型拥有这个图。

两者各有其位。工作流更便宜、更快、更容易调试。智能体能解锁开放式问题，但让失败模式更难推理。

### 增强的 LLM

五种模式的基础：一个 LLM，接上三种能力——search（检索）、tools（动作）、memory（持久化）。任何一次 API 调用都可以用它们。

### 五种模式

1. **Prompt chaining。** 调用 1 的输出是调用 2 的输入。当任务有清晰的线性分解时使用。步骤之间可有程序化的门控。

2. **Routing。** 一个分类器 LLM 挑选调用哪个下游 LLM 或工具。当类别迥异的输入需要不同处理时使用（一级支持 vs 退款 vs 缺陷 vs 销售）。

3. **Parallelization。** 并发跑 N 次 LLM 调用，聚合结果。两种形态：sectioning（不同分块）和 voting（同一 prompt、N 次运行、多数/综合）。

4. **Orchestrator-workers。** 一个 orchestrator LLM 动态决定运行哪些 worker（也是 LLM）并综合它们的输出。与 agent loop 相似，但 orchestrator 不会无限循环。

5. **Evaluator-optimizer。** 一个 LLM 提出答案，另一个 LLM 评估它。迭代直到评估器通过。这就是被泛化的 Self-Refine（第 05 课）。

### 工作流胜过智能体的地方

- **可预测的任务。** 如果你能枚举出步骤，你就应该枚举。
- **成本受限的任务。** 工作流有界的步骤数；智能体会失控螺旋。
- **合规受限的任务。** 审计人员想读图，而不是从轨迹里推断图。

### 智能体胜过工作流的地方

- **开放式研究。** 当下一步取决于上一步返回了什么时。
- **变长任务。** 几分钟到几小时、步骤数未知的工作。
- **新领域。** 当你还不知道正确的工作流时——先探索，之后再固化。

### 上下文工程的同伴

「Effective context engineering for AI agents」（Anthropic 2025）形式化了这门相邻学科：200k 窗口是预算，不是容器。该包含什么、何时压缩、何时让上下文增长。Phase 14 的上下文压缩课（重编号前本课程中较早的第 06 课）对此有详细覆盖。

```figure
workflow-chain
```

## Build It

`code/main.py` 对一个 `ScriptedLLM` 实现了全部五种工作流模式：

- `prompt_chain(input, steps)` —— 顺序执行。
- `route(input, classifier, handlers)` —— 分类 + 派发。
- `parallel_vote(prompt, n, aggregator)` —— N 次运行，聚合。
- `orchestrator_workers(task, workers)` —— orchestrator 挑选 worker。
- `evaluator_optimizer(task, proposer, evaluator, max_iter)` —— 循环直到通过。

运行它：

```
python3 code/main.py
```

每种模式都打印它的 trace。每种模式的代码量约 10–15 行；一个框架的成本要以千行计。

## Use It

- 大多数任务用直接 API 调用。
- 只有当模式真正需要持久状态（LangGraph）、actor 模型并发（AutoGen v0.4）或角色模板化（CrewAI）时，才用框架。
- 当你想要 Claude Code harness 形态而不想重建它时，用 Claude Agent SDK。

## Ship It

`outputs/skill-workflow-picker.md` 为给定的任务描述挑选正确模式，包括决策理由，以及当工作流不够用时重构到智能体的路径。

## 练习

1. 用置信度阈值实现 routing。低于阈值 -> 升级给人类。对一级支持用例，阈值该落在哪里？
2. 给 `parallel_vote` 加超时。当一次调用挂起时会发生什么？你如何在缺票的情况下聚合？
3. 把 `evaluator_optimizer` 变成一个 bandit：跨迭代保留 top-2 输出，这样晚到的好结果不会被晚到的坏结果覆盖。
4. 把 prompt chaining 与 routing 组合：一个 router 从三条链里挑一条。对比单一「大 prompt」方案，度量 token 成本。
5. 挑一个你的生产功能。画出工作流图。数一下步数。在这里智能体真的会更好吗？

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| Workflow | 「预定义流程」 | 工程师拥有的 LLM 与工具调用图 |
| Agent | 「自主 AI」 | 模型拥有的图；动态的工具指挥 |
| Augmented LLM | 「带工具的 LLM」 | LLM + search + tools + memory；原子单元 |
| Prompt chaining | 「顺序调用」 | 调用 N 的输出是调用 N+1 的输入 |
| Routing | 「分类器派发」 | 挑选哪条链/哪个模型处理输入 |
| Parallelization | 「扇出」 | N 次并发调用；按 sectioning 或 voting 聚合 |
| Orchestrator-workers | 「派发器智能体」 | orchestrator LLM 动态挑选专家 LLM |
| Evaluator-optimizer | 「提议者 + 裁判」 | 迭代直到评估器通过；被泛化的 Self-Refine |

## 延伸阅读

- [Anthropic，Building Effective Agents（2024 年 12 月）](https://www.anthropic.com/research/building-effective-agents) —— 五种工作流模式
- [Anthropic，Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) —— 那门相邻学科
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) —— 当状态图物有所值之时
- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) —— 被产品化的 orchestrator-workers 模式