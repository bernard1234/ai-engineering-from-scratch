# MARL —— MADDPG、QMIX、MAPPO

> multi-agent 协调的强化学习传承，至今仍在 2026 年影响 LLM-agent 系统。**MADDPG**（Lowe 等，NeurIPS 2017，arXiv:1706.02275）提出了集中式训练、分散式执行（Centralized Training, Decentralized Execution，CTDE）：训练时每个 critic 能看到所有 agent 的状态与动作；测试时只运行本地 actor。适用于合作、竞争和混合场景。**QMIX**（Rashid 等，ICML 2018，arXiv:1803.11485）是带单调混合网络的价值分解；每个 agent 的 Q 组合成联合 Q，使 `argmax` 能被干净地分布 —— 在 StarCraft Multi-Agent Challenge（SMAC）上占主导。**MAPPO**（Yu 等，NeurIPS 2022，arXiv:2103.01955）是带集中式价值函数的 PPO；在 particle-world、SMAC、Google Research Football、Hanabi 上以极少的调参取得“出奇有效”的结果。这些算法支撑着必须以分散方式行动的 agent 团队的策略训练。MAPPO 是 **2026 年合作型 MARL 的默认 baseline**。本课用一个很小的网格世界玩具把三者各自搭起来，在接触 LLM-agent 训练之前先把这三个思想刻进肌肉记忆。

**Type:** Learn
**Languages:** Python (stdlib, small NumPy-free implementations)
**Prerequisites:** 第 09 阶段（Reinforcement Learning）、第 16 阶段，第 09 课（Parallel Swarm Networks）
**Time:** ~90 分钟

## 问题场景

LLM-agent 系统越来越多地为 agent 间协调训练策略：何时让位、何时行动、调用哪个同伴。告诉你如何训练这类策略的文献是 Multi-Agent Reinforcement Learning（MARL），它早于 LLM 浪潮，并有一小组占主导的算法。

缺少模式词汇去读 MARL 论文是很痛苦的。集中式训练加分散式执行（CTDE）、价值分解、集中式 critic 都不是空话 —— 它们是对特定问题的特定答案：

- 独立 RL（每个 agent 各自学习）从每个 agent 的视角看都是非平稳的。很糟。
- 集中式 RL（一个 agent 控制全部）无法扩展，且违反执行约束。
- CTDE 兼得两者之长：用全局信息训练，用本地策略部署。

## 核心概念

### 论文使用的三种环境

- **Particle World（multi-agent particle env）。** 带合作/竞争任务的简单 2D 物理环境。MADDPG 的原始测试床。
- **StarCraft Multi-Agent Challenge（SMAC）。** 合作式微操，部分可观测。QMIX 的测试床。离散动作，连续状态。
- **Google Research Football、Hanabi、MPE。** MAPPO 的 baseline。

不同的环境有不同的动作/观测类型。算法据此选用。

### MADDPG（2017）—— CTDE 模式

每个 agent `i` 有一个 actor `mu_i(o_i)`，把它自己的观测映射为动作。每个 agent 还有一个 critic `Q_i(x, a_1, ..., a_n)`，在训练时能看到所有观测和所有动作。actor 依据 critic 的评估、通过策略梯度更新。

```
actor update:    grad_theta_i J = E[grad_theta mu_i(o_i) * grad_a_i Q_i(x, a_1..n) at a_i=mu_i(o_i)]
critic update:   TD on Q_i(x, a_1..n) given next-state joint estimate
```

为何用 CTDE：训练时我们知道所有人的动作，借此降低每个 critic 的方差。部署时，每个 agent 只看到 `o_i` 并调用 `mu_i(o_i)`。

失效模式：critic 的规模随 N 个 agent 增长（输入包含所有动作）。没有近似手段时，超过约 10 个 agent 就无法扩展。

### QMIX（2018）—— 价值分解

仅限合作场景。全局奖励是各 agent Q 值的单调函数之和：

```
Q_tot(tau, a) = f(Q_1(tau_1, a_1), ..., Q_n(tau_n, a_n)),   df/dQ_i >= 0
```

单调性保证 `argmax_a Q_tot` 可以由每个 agent 各自选择 `argmax_{a_i} Q_i` 来计算。这正是你所需要的**分散式执行性质**。训练时，一个混合网络由各 agent 的 Q 生成 `Q_tot`。

为何 QMIX 在 SMAC 上胜出：合作式 StarCraft 微操具有同质 agent、局部观测、全局奖励 —— 与价值分解完美契合。

失效模式：单调性约束较为苛刻；某些任务的奖励结构无法单调分解（例如某个 agent 为团队做出牺牲）。扩展方法（QTRAN、QPLEX）可放宽这一约束。

### MAPPO（2022）—— 被忽视的默认选项

Multi-Agent PPO：带集中式价值函数的 PPO。每个 agent 有自己的策略；所有 agent 共享（或各自拥有）能看到完整状态的价值函数。Yu 等 2022 在五个 benchmark 上把 MAPPO 与 MADDPG、QMIX 及其扩展做对比，发现：

- 在 particle-world、SMAC、Google Research Football、Hanabi、MPE 上，MAPPO 追平或超过 off-policy MARL 方法。
- 所需超参数调优极少。
- 训练稳定；跨随机种子可复现。

在这篇论文之前，社区一直低估 on-policy MARL。在 2026 年，MAPPO 是合作型 MARL 的默认 baseline；任何新方法都必须超越它。

### 为何 LLM-agent 工程师应该关心

三种直接用途：

1. **路由训练。** 一个 meta-agent 选择由哪个子 agent 处理任务。这是一个含 N 个分散式子 agent 和一个集中式路由器的 MARL 问题。MAPPO 适用。
2. **角色涌现。** 在 generative-agent 仿真中，训练 agent 随时间采用互补角色，本质上是一个伪装的 MARL 问题。QMIX 风格的价值分解从构造上强制互补。
3. **Multi-agent 工具使用。** 当 agent 共享工具并争夺预算时，通过 CTDE 训练它们，能产出行之有效、遵守资源约束的本地策略。

实践提醒：2026 年，大多数生产环境的 LLM-agent 系统是用 prompt 表达策略，而不是训练策略。当你具备 (a) 大量交互数据、(b) 清晰的奖励信号、(c) 愿意投入训练基础设施 时，MARL 才会登场。

### 超出 RL 的 CTDE 设计模式

即使不训练，CTDE 也是一种有用的架构模式：

- 在 *设计* 阶段，假定团队完全可见。
- 在 *运行时*，强制执行分散式执行：每个 agent 只看到 `o_i`。

这个模式迫使你把每个 agent 的状态显式化，并提前思考部分可观测性。许多生产环境的 multi-agent 系统默默假定处处共享状态 —— CTDE 纪律能防止这一点。

### 非平稳性问题

当多个 agent 同时学习时，每个 agent 的环境（其中包含他人的策略）都是非平稳的。经典的单 agent RL 证明会失效。本课的 MARL 算法都在应对这一点：

- MADDPG：全局 critic 能看到所有动作，因此其价值估计是平稳的。
- QMIX：价值分解把学习移到联合 Q 空间，在那里最优性有明确的定义。
- MAPPO：集中式价值函数抑制了他人策略变化带来的方差。

在 LLM-agent 系统中，非平稳性表现为“我的 agent 上个月还好用，现在上游那个 agent 改了，我这个就出毛病了”。用 CTDE 训练 MARL 是体系化的修法；prompt 层面的修补更快，但不够持久。

### 本课不涵盖的内容

训练真正的网络属于第 09 阶段的内容。本课构建脚本化的策略版本，在不做梯度更新的前提下演示 CTDE、价值分解和集中式价值模式。目标是在你拿起完整的 MARL 库（PyMARL、MARLlib、RLlib multi-agent）之前先把这些模式内化。

```figure
sw-ctde
```

## Build It

`code/main.py` 实现了三个模式演示，全部基于一个很小的 2-agent 合作式网格世界：

- 环境：2 个 agent 位于 4x4 网格，一个奖励 pellet。任一 agent 到达 pellet 即奖励 = 1，任务结束。
- `IndependentAgents` —— 每个 agent 把其他 agent 当作环境。作为 baseline。
- `MADDPGStyle` —— 集中式 critic 计算一个联合价值；actor 策略据此更新。脚本化的策略改进。
- `QMIXStyle` —— 带单调混合器的价值分解。
- `MAPPOStyle` —— 集中式价值函数；策略依据共享 baseline 更新。

四者在相同的 episode 上运行，并报告到达目标的平均步数。CTDE 变体相比独立 baseline 收敛到更短的路径。

运行：

```
python3 code/main.py
```

预期输出：独立 agent 平均走约 6 步；CTDE 变体收敛到约 3.5 步（4x4 网格的最优是 3 步）。尽管策略是脚本化的，模式差异依然显现。

## Use It

`outputs/skill-marl-picker.md` 是一个技能，为给定的 multi-agent 任务挑选 MARL 算法：合作 vs 竞争、同质 vs 异质、动作空间类型、规模、奖励信号。

## Ship It

MARL 在生产环境中很少见。当你确实要用时：

- **从 MAPPO 开始。** 2022 年的论文已把它确立为 baseline；先复现它能省下追逐更花哨方法的数周时间。
- **记录每个 agent 的观测和动作流。** 没有逐 agent 的轨迹，调试 MARL 毫无希望。
- **把训练代码与执行代码分开。** CTDE 是一种纪律；让执行路径真的只看到 `o_i`。
- **奖励塑形警告。** MARL 对奖励设计极其敏感。塑形里埋一个协调漏洞，agent 就会学会利用它。要跑对抗测试。
- **对于 LLM agent**，先考虑 prompt 层面的策略。只有当交互数据 + 奖励信号 + 基础设施都具备时，才投入 MARL 训练。

## Exercises

1. 运行 `code/main.py`。度量独立 agent 与 MAPPO 风格 agent 之间的到达步数差距。在 6x6 网格上，这个差距会变大还是变小？
2. 实现一个竞争变体：两个 agent、一个 pellet，只有先到达者获得奖励。哪个模式能干净地处理竞争？历史上是 MADDPG。
3. 阅读 MADDPG（arXiv:1706.02275）第 3 节。用你自己的话，以符号化伪代码实现精确的 critic 更新规则。
4. 阅读 MAPPO（arXiv:2103.01955）。作者为何论证集中式价值 + PPO 在他们的 benchmark 上胜过 off-policy MARL？列出三条最有力的主张。
5. 把 CTDE 作为一种设计模式应用到一个假设的 LLM-agent 系统（例如 research agent + summarizer + coder）。设计时可得、而运行时不可得的联合信息是什么？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| MARL | “Multi-Agent RL” | 面向 multi-agent 系统的强化学习。 |
| CTDE | “Centralized Training, Decentralized Execution” | 用全局信息训练；用本地策略部署。 |
| MADDPG | “Multi-Agent DDPG” | 每个 agent 的 critic 能看到所有观测 + 动作的 CTDE。 |
| QMIX | “价值分解” | 对各 agent 的 Q 做单调混合。合作场景。 |
| MAPPO | “Multi-Agent PPO” | 带集中式价值函数的 PPO。2026 年的默认 baseline。 |
| Value decomposition | “个体 Q 之和” | 把联合 Q 表示为各 agent Q 的单调函数。 |
| Non-stationarity | “移动的目标” | 随着他人学习，每个 agent 的环境都在变。MARL 的核心问题。 |
| On-policy / off-policy | “从当前数据 / 回放中学” | PPO 是 on-policy（MAPPO）；DDPG 和 Q-learning 是 off-policy。 |
| SMAC | “StarCraft Multi-Agent Challenge” | 合作式微操 benchmark；QMIX 的起家地盘。 |

## Further Reading

- [Lowe et al. — Multi-Agent Actor-Critic for Mixed Cooperative-Competitive Environments](https://arxiv.org/abs/1706.02275) —— MADDPG；NeurIPS 2017
- [Rashid et al. — QMIX: Monotonic Value Function Factorisation for Deep Multi-Agent Reinforcement Learning](https://arxiv.org/abs/1803.11485) —— QMIX；ICML 2018
- [Yu et al. — The Surprising Effectiveness of PPO in Cooperative Multi-Agent Games](https://arxiv.org/abs/2103.01955) —— MAPPO；NeurIPS 2022
- [BAIR blog post on MAPPO](https://bair.berkeley.edu/blog/2021/07/14/mappo/) —— 对 MAPPO 结果的易读解读
- [SMAC repository](https://github.com/oxwhirl/smac) —— StarCraft Multi-Agent Challenge
