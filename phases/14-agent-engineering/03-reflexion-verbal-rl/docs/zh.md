# Reflexion：言语强化学习

> 基于梯度的 RL 需要成千上万次试验和一整个 GPU 集群才能修复一个失败模式。Reflexion（Shinn 等人，NeurIPS 2023）用自然语言做到了这一点：每次失败的试验之后，智能体会写下一段反思，存入情景记忆，并让下一次试验以这段记忆为条件。这正是 Letta 的 sleep-time compute、Claude Code 的 CLAUDE.md learnings，以及 pro-workflow 的 learn-rule 背后的模式。

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 01 (Agent Loop), Phase 14 · 02 (ReWOO)
**Time:** ~60 minutes

## 学习目标

- 说出 Reflexion 的三个组成部分（Actor、Evaluator、Self-Reflector）以及情景记忆的作用。
- 用标准库实现一个 Reflexion 循环，包含二元评估器、反思缓冲和全新重试。
- 针对给定任务，在标量、启发式和自我评估三种反馈来源之间做出选择。
- 解释为什么言语强化能捕捉到基于梯度的 RL 需要成千上万次试验才能修复的错误。

## 问题

一个智能体在任务上失败了。在标准 RL 中，你需要再跑成千上万次试验、计算梯度、更新权重。昂贵、缓慢，而且大多数生产智能体并不会为每一次失败都准备一份训练预算。

Reflexion（Shinn 等人，arXiv:2303.11366）提出了一个不同的问题：如果智能体只是思考一下自己为什么失败，然后把这段思考放进提示词里再试一次呢？没有权重更新。没有梯度。只是把自然语言存在各次试验之间。

结果是：在 ALFWorld 上，它击败了 ReAct 和其他未微调的基线；在 HotpotQA 上，它比 ReAct 有所改进；在代码生成（HumanEval/MBPP）上，它当时达到了最先进的水平。而这一切都没有用到哪怕一个梯度步。

## 概念

### 三个组成部分

```
Actor         : generates a trajectory (ReAct-style loop)
Evaluator     : scores the trajectory — binary, heuristic, or self-eval
Self-Reflector: writes a natural-language reflection on the failure
```

再加上一种数据结构：

```
Episodic memory: list of prior reflections, prepended to the next trial's prompt
```

一次试验运行 Actor。Evaluator 给它打分。如果分数低，Self-Reflector 产出一段反思（「我选错了工具，因为我把问题误读成了在问 X，而它实际在问 Y」）。反思进入情景记忆。下一次试验全新开始，但能看到这段反思。

### 三种评估器类型

1. **标量（Scalar）** —— 一个外部二元信号。ALFWorld 成功或失败。HumanEval 测试通过或失败。最简单、信号最强。
2. **启发式（Heuristic）** —— 预定义的失败特征。「如果智能体连续两次产出了同一个动作，标记为卡住。」「如果轨迹超过 50 步，标记为低效。」
3. **自我评估（Self-evaluated）** —— LLM 给自己的轨迹打分。在没有 ground truth 可用时必不可少。信号较弱；与基于工具的验证（第 05 课——CRITIC）搭配使用效果好。

2026 年的默认做法是混合：有标量信号时用标量，没有时用自我评估，启发式作为安全护栏。

### 为什么它能泛化

Reflexion 与其说是一种新算法，不如说是一个被命名的模式。几乎每一个生产级的「自愈」智能体都在跑它的某种变体：

- Letta 的 sleep-time compute（第 08 课）：一个独立的智能体反思过去的对话，并写入 memory blocks。
- Claude Code 的 `CLAUDE.md` / 「save memory」模式：反思被捕获为 learnings，前置到未来的会话中。
- pro-workflow 的 `/learn-rule` 命令：修正被捕获为显式规则。
- LangGraph 的 reflection 节点：一个给输出打分、并在需要时路由到 refine 的节点。

它们都源自同一个洞见：自然语言是一种足够丰富的媒介，足以在两次运行之间承载「我从失败中学到了什么」。

### 它什么时候有效、什么时候无效

Reflexion 有效的情况：

- 存在清晰的失败信号（测试失败、工具错误、答案错误）。
- 任务类别是可复现的（同一种问题可以被再次提出）。
- 反思有改进轨迹的空间（有足够的行动预算）。

Reflexion 无效的情况：

- 智能体第一次尝试就已经成功了。
- 失败是外部原因（网络中断、工具损坏）——对「网络断了」的反思无助于未来的运行。
- 反思变成了迷信——把一次性偶发失败的叙事存了下来。

2026 年的坑：memory rot。反思不断累积；有些过时了，有些是错的；随着情景缓冲的增长，重跑变得越来越慢。缓解手段：定期压缩（第 06 课）、给反思加 TTL，或用一个独立的 sleep-time 清理智能体（Letta）。

```figure
react-trace
```

## Build It

`code/main.py` 在一个玩具谜题上实现了 Reflexion：产出一个三元素列表，使其求和等于目标值。Actor 产出候选列表；Evaluator 检查求和；Self-Reflector 写一行关于哪里出了问题的话。反思进入情景记忆，供下一次试验使用。

组成部分：

- `Actor` —— 一个脚本化策略，在看到反思后会改进。
- `Evaluator.binary()` —— 对目标求和的通过/失败判断。
- `SelfReflector` —— 生成一句对失败的一行诊断。
- `EpisodicMemory` —— 一个有界列表，带 TTL 语义。

运行它：

```
python3 code/main.py
```

trace 展示了三次试验。试验 1 失败，一段反思被存储，试验 2 看到反思并改进但仍然失败，试验 3 成功。与基线运行（无反思）对比——它一直停在试验 1 的答案上。

## Use It

LangGraph 把 reflection 作为一个节点模式发布。Claude Code 的 `/memory` 命令和 pro-workflow 的 `/learn-rule` 把情景缓冲外化为一个 markdown 文件。Letta 的 sleep-time compute 在空闲时间运行 Self-Reflector，让主智能体保持低延迟。OpenAI Agents SDK 并不直接提供 Reflexion；你需要用一个自定义 Guardrail 按分数拒绝轨迹，再加一个能跨运行存续的 memory `Session` 来构建它。

## Ship It

`outputs/skill-reflexion-buffer.md` 创建并维护一个带反思捕获、TTL 和去重的情景缓冲。给定一个任务类别和一次失败，它产出一段真正有助于下一次试验的反思（而不是一句泛泛的「下次小心点」）。

## 练习

1. 把二元评估器换成返回距离度量（离目标有多远）的标量评估器。收敛更快吗？
2. 给反思加一个 10 次试验的 TTL。过了这个点之后，旧反思是帮倒忙还是帮正忙？
3. 实现启发式评估器：如果同一个动作重复出现，就把试验标记为卡住。它与 Self-Reflector 如何相互作用？
4. 用一个忽略反思的对抗式 Actor 跑 Reflexion。要迫使 Actor 注意到反思，最低限度的反思提示词工程是什么？
5. 读 Reflexion 论文关于 AlfWorld 的第 4 节。概念性地复现 130% 的成功率提升：与 vanilla ReAct 相比，关键差异是什么？

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|-----------|------------------|
| Reflexion | 「自我修正」 | Shinn 等人 2023——Actor、Evaluator、Self-Reflector 加上情景记忆 |
| Verbal reinforcement | 「不用梯度的学习」 | 前置到下一次试验提示词里的自然语言反思 |
| Episodic memory | 「按任务的反思」 | 针对一个任务类别的过往反思的有界缓冲 |
| Scalar evaluator | 「二元成功信号」 | 来自 ground truth 的通过/失败或数值分数 |
| Heuristic evaluator | 「基于模式的检测器」 | 预定义的失败特征（例如死循环、步数过多） |
| Self-evaluator | 「对自己轨迹的 LLM 裁判」 | 没有 ground truth 时的低信号兜底——与基于工具的验证搭配 |
| Memory rot | 「过时的反思」 | 情景缓冲被废弃条目填满；用压缩/TTL 修复 |
| Sleep-time reflection | 「异步自我反思」 | 在热路径之外运行 Self-Reflector，让主智能体保持快速 |

## 延伸阅读

- [Shinn 等人，Reflexion: Language Agents with Verbal Reinforcement Learning（arXiv:2303.11366）](https://arxiv.org/abs/2303.11366)——经典原论文
- [Letta，Sleep-time Compute](https://www.letta.com/blog/sleep-time-compute)——生产环境中的异步反思
- [Anthropic，Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)——把情景缓冲作为 context 的一部分来管理
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)——reflection 节点模式
