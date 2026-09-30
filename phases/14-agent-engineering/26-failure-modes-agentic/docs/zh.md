# 失败模式：智能体为何会坏掉

> MASFT（Berkeley，2025）把 14 种多智能体失败模式归入 3 个类别。Microsoft 的 Taxonomy 记录了现有 AI 失败如何在智能体场景中被放大。业界现场数据收敛到五种反复出现的模式：幻觉化动作、scope creep、级联错误、上下文丢失、工具误用。

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 05 (Self-Refine and CRITIC), Phase 14 · 24 (Observability)
**Time:** ~60 minutes

## 学习目标

- 说出 MASFT 的三个失败类别，以及每个类别中至少四种具体模式。
- 解释为什么智能体失败会放大现有的 AI 失败模式（偏见、幻觉）。
- 描述业界反复出现的五种模式及其缓解措施。
- 实现一个标准库检测器，为智能体轨迹打上失败模式标签。

## 问题

团队交付的智能体在 90% 的轨迹上都能工作。那 10% 的失败并非随机噪声——它们落入少数几个反复出现的类别。一旦你能叫出它们的名字，你就能监控并修复它们。

## 概念

### MASFT（Berkeley，arXiv:2503.13657）

Multi-Agent System Failure Taxonomy。14 种失败模式聚成 3 个类别。标注者间 Cohen's Kappa 为 0.88——这些类别可以被可靠地区分。

核心主张：失败是多智能体系统中根本性的设计缺陷，而不是要靠更好的基座模型来修复的 LLM 局限。

### Microsoft Taxonomy of Failure Mode in Agentic AI Systems

- 现有的 AI 失败（偏见、幻觉、数据泄露）在智能体场景中被放大。
- 新的失败源自自主性：规模化下的非预期动作、工具误用、任务漂移。
- 这份白皮书是智能体产品的风险登记册。

### Characterizing Faults in Agentic AI（arXiv:2603.06847）

- 失败源自编排、内部状态演化以及与环境交互。
- 不仅仅是「坏代码」或「坏模型输出」。

### LLM Agent Hallucinations Survey（arXiv:2509.18970）

两种主要表现形式：

1. **指令遵循偏离（Instruction-following Deviation）**——智能体不遵循 system prompt。
2. **长程上下文误用（Long-range Contextual Misuse）**——智能体忘记或误用前几轮对话中的上下文。

子意图错误：遗漏（Omission，跳过步骤）、冗余（Redundancy，重复步骤）、乱序（Disorder，步骤顺序错乱）。

### 业界反复出现的五种模式

Arize、Galileo、NimbleBrain 2024-2026 年的现场分析收敛到：

1. **幻觉化动作（Hallucinated actions）。** 智能体调用了一个不存在的工具，或捏造了参数。
2. **Scope creep。** 智能体把任务扩展到用户要求之外（多建了 PR、多发了几封邮件）。
3. **级联错误（Cascading errors）。** 一个错误调用触发下游连锁效应。一次 phantom SKU 幻觉触发四次 API 调用——一次跨系统事故。
4. **上下文丢失（Context loss）。** 长时程任务忘记前几轮的约束。
5. **工具误用（Tool misuse）。** 用错误的参数调用正确的工具，或干脆调用错误的工具。

级联是杀手。智能体无法区分「我失败了」和「任务不可能完成」，并常常在 400 错误上幻觉出一条成功消息来闭合循环。

### 缓解：每一步都设门

在推理链的每一步都设自动化验证门，对照环境状态检查事实依据。具体来说：

- 逐步安全分类器（第 21 课）。
- 工具调用参数校验（第 06 课）。
- 将检索到的内容与已知事实交叉核对（第 05 课，CRITIC）。
- 通过重新探测状态来检测成功幻觉（文件真的被创建了吗？）。

### 失败监控哪里会出问题

- **只标记崩溃。** 大多数智能体失败产出的输出看起来都是有效的。需要内容层面的检查。
- **没有基线。** 漂移检测需要一个 last-known-good；没有它你无法说「这正在变差」。
- **过度告警。** 每次失败都发一个 page。要做聚类和限流。

```figure
failure-cascade
```

## Build It

`code/main.py` 实现了一个标准库版失败模式标注器：

- 一个覆盖五种模式的合成轨迹数据集。
- 每种模式的检测器函数（针对工具调用、输出、重复动作的签名模式）。
- 一个标注器，为每条轨迹打标签并报告模式分布。

运行它：

```
python3 code/main.py
```

输出：逐轨迹标签 + 聚合分布，这是对 Phoenix 的轨迹聚类所呈现内容的廉价复现。

## Use It

- **Phoenix** 用于生产漂移聚类（第 24 课）。
- **Langfuse** 用于会话回放 + 标注。
- **Custom** 用于你的可观测性平台无法检测的领域特定签名。

## Ship It

`outputs/skill-failure-detector.md` 生成针对你领域的失败模式检测器，并接入一个轨迹存储。

## 练习

1. 加一个「成功幻觉」检测器：智能体返回成功，但目标状态没有改变。
2. 从你构建过的产品里标注 100 条真实轨迹。哪种模式占主导？修复它的成本是多少？
3. 实现一个「级联半径」指标：给定第 N 步的一次失败，它影响了多少下游步骤？
4. 阅读 MASFT 的 14 种失败模式。挑出适用于你产品的三种。编写检测器。
5. 把一个检测器接入 CI 作业：如果 >=5% 的轨迹被标记出某种模式，就让构建失败。

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| MASFT | 「多智能体失败分类」 | Berkeley 的 14 模式分类 |
| Cascading error | 「涟漪式失败」 | 一个早期错误传播过 N 个步骤 |
| Context loss | 「忘了约束」 | 长时程轮次丢失前几轮的事实 |
| Tool misuse | 「错误工具 / 错误参数」 | 调用有效，但调用方式错误 |
| Success hallucination | 「伪造完成」 | 智能体在 400 上声称成功；状态未变 |
| Scope creep | 「越界」 | 智能体做了比要求更多的事 |
| Instruction-following deviation | 「不服从」 | 无视 system prompt 或用户约束 |
| Sub-intention errors | 「计划缺陷」 | 计划执行中的遗漏、冗余、乱序 |

## 延伸阅读

- [Cemri 等人，MASFT（arXiv:2503.13657）](https://arxiv.org/abs/2503.13657)——14 种失败模式、3 个类别
- [Microsoft，Taxonomy of Failure Mode in Agentic AI Systems](https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/final/en-us/microsoft-brand/documents/Taxonomy-of-Failure-Mode-in-Agentic-AI-Systems-Whitepaper.pdf)——风险登记册
- [Arize Phoenix](https://docs.arize.com/phoenix)——实践中的漂移聚类
- [Anthropic，Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)——何时更简单的模式能完全避开这些模式
