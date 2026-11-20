# Theory of Mind 与涌现式协调

> Li 等人（arXiv:2310.10701）表明，合作式文本游戏中的 LLM agent 会表现出**涌现的高阶 Theory of Mind**（ToM）——即推理另一个 agent 对第三方 agent 信念的看法——但由于上下文管理与幻觉，它们在长程规划上会失败。Riedl（arXiv:2510.05174）测量了群体范围内的更高阶协同，发现**只有** ToM prompt 条件才能产生身份关联的分化与目标导向的互补；容量较低的 LLM 只表现出虚假的涌现。也就是说，协调的涌现是依赖 prompt、依赖模型的，并非免费得来。本课实现一个最小的 ToM 感知 agent，在有 ToM prompt 与无 ToM prompt 的情况下运行一个合作任务，并对照 Riedl 2025 的协议测量协调增量。

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** 第 16 阶段，第 07 课（Society of Mind and Debate）、第 17 课（Generative Agents）
**Time:** ~75 分钟

## 问题场景

多智能体协调常常看起来像魔法：agent 分工、相互预判、避免重复。通常这种“涌现”是 prompt 工程的产物——有人告诉 agent 去“协调”。去掉 prompt，协调也就消失。

Riedl 2025 的发现更严格：在受控条件下，只有当 agent 被提示去推理**其他 agent 的心智**（ToM）时，协调才会涌现。没有 ToM prompt，即便是强模型表现出的协调模式也经不起统计控制。这对生产很重要：团队交付的“多智能体协调”特性依赖 prompt 且脆弱。

本课把 ToM 视为一项具体能力（对信念的信念进行推理），构建一个最小的 ToM 感知 agent，并测量真正的协调与 prompt 装饰分别是什么样子。

## 核心概念

### ToM 的含义

发展心理学：3 岁的孩子以为任何人的内心世界都和自己一样。5 岁的孩子明白他人有不同的信念。7 岁的孩子能对“信念的信念”进行推理（“她以为我认为球在杯子下面”）。这些分别是零阶、一阶、二阶 ToM。

对 LLM agent 而言，ToM 的阶数映射为：

- **零阶：** 没有对他人的模型。agent 只依据自己的观察行动。
- **一阶：** agent 拥有对每个其他 agent 信念的模型。“Alice 相信 X。”
- **二阶：** agent 对递归信念建模。“Alice 相信 Bob 相信 X。”

Li 等人 2023 年发现，一阶与二阶 ToM 在合作博弈中的 LLM agent 身上会涌现，但会随长程和不可靠的通信而退化。

### 简说 Sally-Anne 测试

一个 1985 年的错误信念测试：Sally 把一颗弹珠放进篮子 A，然后离开。Anne 把它挪到篮子 B。Sally 回来时会去哪个篮子里找？具备一阶 ToM 的孩子说篮子 A（Sally 的信念与现实不同）。没有一阶 ToM 的孩子说篮子 B。

GPT-4 时代的 LLM 在朴素提问时能通过 Sally-Anne 式测试。当叙事很长、场景多次变化，或问题以间接方式表述时，它们就会失败。这就是 2026 年生产环境中 LLM 的 ToM 的实际状态。

### Riedl 的协调测量方法

Riedl（arXiv:2510.05174）构建了一个群体规模的测试：N 个 agent、一个合作目标、可变的 prompt 条件。测量：

1. **身份关联的分化。** agent 是否会随时间形成稳定的角色区分？
2. **目标导向的互补。** agent 的行为是否彼此互补（不同的子任务），而非重复？
3. **更高阶协同。** 衡量群体是否达成了任何子集都无法达成的结果的统计量。

结果：只有在 ToM prompt 条件下，三个指标才会全部产生高于基线的信号。在没有 ToM 提示时，对中等容量的模型，这些指标徘徊在接近随机水平。大模型在没有显式 ToM prompt 时表现出一些协调，但效应小于显式提示时的效应。

### 协调的幻觉

没有统计控制时，演示中的“涌现协调”常常反映的是：

- 把协调烘焙进 prompt 的工程手法（写着“协同工作”的系统 prompt）。
- 观察者偏差（我们看到的是我们预期的模式）。
- 对成功运行的事后挑选。

那些在没有可度量信号的情况下宣传“涌现协调”的生产系统，应当被视为营销话术。先测量，再宣称。

### 一个最小的 ToM 感知 agent

结构：

```
agent state:
  own_beliefs:    {facts the agent believes}
  other_models:   {other_agent_id -> {beliefs_the_agent_attributes_to_them}}
  actions_last_N: [history of others' actions]

observation update:
  - update own_beliefs from direct observation
  - update other_models[agent_id] from their action + prior beliefs

action selection:
  - enumerate candidate actions
  - for each, predict what each other agent will do next given their modeled beliefs
  - pick action that maximizes joint outcome under those predictions
```

`other_models` 属性就是 ToM 状态。一阶 ToM 只保留一层。二阶再加上 `other_models[i][other_models_of_j]`——即我认为 agent i 认为 agent j 相信什么。

### 为什么长程会伤害它

Li 等人记录了：上下文限制会让 agent 忘记哪个信念属于谁。幻觉会向其他 agent 的模型里加入错误信念。两者都会产生“我以为他以为 X”的错误，并随时间复合。

论文及 2024-2026 年后续工作中记录的缓解方法：

- **在 prompt 中用显式的 ToM 状态。** 结构化格式：`{agent_id: belief_list}`。强制检索保留身份与信念的绑定。
- **更短的推理链。** 每轮更少的 ToM 更新可以降低复合幻觉。
- **外部 ToM 存储。** 在 LLM 上下文之外维护模型；每轮只注入相关部分。

### ToM 在生产中失效的地方

- **对抗环境。** ToM 好的 agent 更容易被操纵（你可以建模它们对你的建模，然后加以利用）。
- **异构团队。** 当模型不同时，对某个对手有效的 ToM 模型并不通用。
- **依赖基准真相的任务。** ToM 关乎信念；如果正确性取决于事实，ToM 可能是一种干扰。

### 你真正能测量的协调

三个实用信号，用来判断一个团队的协调是真实的而非 prompt 装饰的：

1. **随时间的互补。** 在一个多轮任务中，agent 的行为是否覆盖了互不相交的子任务？
2. **预判。** agent A 在第 T+1 轮的行为，是否依赖于一个关于 B 在第 T+2 轮行为的、事后证明正确的预测？
3. **纠正。** 当 A 在第 T 轮误读了 B 的信念，A 是否会在第 T+2 轮之前纠正？

这些在一个有日志的多智能体系统中是可测量的。它们是“协调”叙事的实质版本。

```figure
sw-theory-of-mind
```

## Build It

`code/main.py` 实现了：

- `ToMAgent`——跟踪自身信念与每个其他 agent 的信念模型。
- 一个合作任务：三个 agent 必须从三个箱子里各收集一个 token；每个箱子只能容纳一个 token。agent 不能通信；它们从彼此的行为中推断意图。
- 两种配置：`zeroth_order`（无 ToM）与 `first_order`（带一层信念模型的 ToM）。
- 在 200 次随机试验上的测量：完成率、重复率（两个 agent 瞄准同一个箱子）、平均完成轮数。

运行：

```
python3 code/main.py
```

预期输出：零阶 agent 的重复率约为 35%，并在 10 轮内完成约 60% 的试验。一阶 ToM agent 的重复率约为 5%，完成约 95%。这个差值就是可测量的协调效应。

## Use It

`outputs/skill-tom-auditor.md` 是一项审计多智能体系统“涌现协调”主张的技能。它检查 prompt 装饰、相对对照组的统计显著性，以及测量得到的互补性。

## Ship It

协调主张的检查清单：

- **对照条件。** 你系统的一个去掉协调 prompt 的版本。两者都测。
- **统计检验。** 在你的指标上，系统与对照之间的差异在 `p < 0.05` 水平上显著吗？
- **互补性度量。** 随时间的行为不相交性，而不仅仅是最终成功。
- **失效案例日志。** 当 agent 协调失误时，ToM 状态是什么样子？
- **模型容量披露。** 如果效应在更小的模型上消失，就明说。

## Exercises

1. 运行 `code/main.py`。确认一阶 ToM 把重复率降低了约 7 倍。扩展到 5 个 agent、5 个箱子时，差距还在吗？
2. 实现二阶 ToM（agent A 建模 B 对 C 的看法）。它比一阶有所改进吗？在哪些任务上？
3. 向 ToM 状态注入**幻觉**：每轮随机翻转一个信念。这对一阶性能的损害有多大？
4. 阅读 Li 等人（arXiv:2310.10701）。复现“长程退化”发现：当轮数从 10 增长到 30，你的一阶 ToM 性能如何变化？
5. 阅读 Riedl 2025（arXiv:2510.05174）。在你的模拟日志上实现更高阶协同统计量。在没有 ToM prompt 条件的情况下，效应是否仍然存在？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Theory of Mind | “理解他人的心智” | 建模另一个 agent 信念的能力。按阶数分级（0、1、2+）。 |
| Sally-Anne test | “错误信念测试” | 1985 年的发展心理学；LLM 通过朴素版本，在复杂版本上失败。 |
| First-order ToM | “A 相信 X” | 建模另一个人关于事实的信念。 |
| Second-order ToM | “A 相信 B 相信 X” | 深一层的递归建模。 |
| Identity-linked differentiation | “随时间稳定的角色” | Riedl 的指标：角色持续存在，而非随机。 |
| Goal-directed complementarity | “不相交的行为” | agent 瞄准不同的子任务，而非同一个。 |
| Higher-order synergy | “群体超过任何子集” | Riedl 用于衡量真实协调的统计量。 |
| Coordination illusion | “看起来是协调的” | 没有可度量信号、只是 prompt 装饰出的协调表象。 |

## Further Reading

- [Li et al. — Theory of Mind for Multi-Agent Collaboration via Large Language Models](https://arxiv.org/abs/2310.10701) — 合作博弈中的涌现 ToM；长程失效模式
- [Riedl — Emergent Coordination in Multi-Agent Language Models](https://arxiv.org/abs/2510.05174) — 群体规模的测量；ToM 提示是承重条件
- [Premack & Woodruff — Does the chimpanzee have a theory of mind?](https://www.cambridge.org/core/journals/behavioral-and-brain-sciences/article/does-the-chimpanzee-have-a-theory-of-mind/1E96B02CD9850E69AF20F81FA7EB3595) — ToM 概念在 1978 年的起源
- [Baron-Cohen, Leslie, Frith — Does the autistic child have a theory of mind?](https://doi.org/10.1016/0010-0277(85)90022-8) — Sally-Anne 论文（1985）
