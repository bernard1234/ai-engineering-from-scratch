# 面向 LLM 的群体优化（PSO、ACO）

> 仿生优化正在 LLM 领域重新流行起来。**LMPSO**（arXiv:2504.09247）使用 PSO，其中每个粒子的速度是一个 prompt，由 LLM 生成下一个候选；它在结构化序列输出（数学表达式、程序）上表现良好。**Model Swarms**（arXiv:2410.11163）把每个 LLM 专家视为模型权重流形上的一个 PSO 粒子，仅用 200 个样本就在 9 个数据集上相对 12 个 baseline 报告了 **13.3% 的平均增益**。**SwarmPrompt**（ICAART 2025）将 PSO + Grey Wolf 混合用于 prompt 优化。**AMRO-S**（arXiv:2603.12933）是受 ACO 启发的信息素专家机制，用于 multi-agent LLM 路由 —— **4.7 倍加速**、可解释的路由证据、将推理与学习解耦的质量门控异步更新。本课在 prompt 参数空间上实现 PSO、在 agent 路由上实现 ACO，度量这些经典算法为何契合 LLM 时代，以及何时不适用。

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** 第 16 阶段，第 09 课（Parallel Swarm Networks）、第 14 课（Consensus and BFT）
**Time:** ~75 分钟

## 问题场景

你有一个在任务 eval 上得分 62% 的 prompt，想把它继续提升。天真的做法是不依赖梯度的手工微调，可它的可扩展性很差。强化学习需要奖励信号以及足够的 rollout 才能训练。对 prompt 做反向传播其实不可能 —— prompt 是一个离散字符串，而不是可微参数。

经典的仿生优化 —— PSO 面向连续搜索空间，ACO 面向路径选择 —— 正是为这一情形设计的：无梯度、基于种群、单次评估成本低。把它们与 LLM 结合来完成无梯度搜索步骤，你就会得到一个出奇实用的优化器。

同样的模式也适用于 multi-agent 系统中的 agent *路由*。ACO 风格的信息素轨迹记录哪个 agent 在哪类任务上表现最好，让路由器利用这条轨迹，并通过信息素衰减使路由可以被重新发现。

## 核心概念

### PSO 回顾（Kennedy & Eberhart 1995）

Particle Swarm Optimization：连续搜索空间中的粒子种群。每个粒子有位置 `x_i` 和速度 `v_i`。每次迭代：

```
v_i <- w * v_i + c1 * r1 * (p_best_i - x_i) + c2 * r2 * (g_best - x_i)
x_i <- x_i + v_i
evaluate fitness(x_i)
update p_best_i if improved
update g_best if global best
```

其中 `p_best` 是粒子自身的最优，`g_best` 是整个 swarm 的最优，`w, c1, c2` 分别是惯性、认知、社会权重，`r1, r2` 是随机因子。

### 面向 LLM 输出的 PSO —— LMPSO

arXiv:2504.09247 将 PSO 适配到 LLM 生成的结构化输出（数学表达式、程序）。每个粒子是一个候选输出。速度是一个 *prompt*，描述如何把当前输出朝个体最优/全局最优修改。LLM 根据速度 prompt 生成新输出。速度的“惯性”是一个类似“做小幅增量改动”的 prompt。

它在以下情况下表现良好：
- 输出是结构化的（可解析、可评估）。
- 适应度是自动的（测试运行、算术求值）。
- 种群规模较小（约 10-30 个粒子），使 LLM 总调用次数保持可控。

当适应度需要人工审查时它表现不佳 —— 每次迭代的成本会变得难以承受。

### Model Swarms

arXiv:2410.11163 把 PSO 从输出层移到 *模型* 层。每个“粒子”是一个专家 LLM（参数）。swarm 通过无梯度更新把参数朝集体最优移动。报告结果：在 9 个数据集上相对 12 个 baseline 取得 13.3% 的平均增益，每次迭代仅用 200 个样本。

关键洞见在于：LLM 专家模型在共享参数流形（adapter 权重、LoRA 增量）中本来就彼此邻近。在这个低维子空间上做 PSO 既便宜又有效。

### ACO 回顾（Dorigo 1992）

Ant Colony Optimization：蚂蚁在图上移动；每条路径都有一条信息素轨迹。蚂蚁的移动概率按信息素强度加权。完成任务的蚂蚁会按其解的质量成比例地释放信息素。信息素随时间衰减。

### AMRO-S —— 面向 agent 路由的 ACO

arXiv:2603.12933 将 ACO 用于 multi-agent 路由。每个任务类型是一个“目的地”；每个 agent 是一条可能的路线。信息素会强化产出良好输出的路线。关键贡献：

- **可解释的路由证据。** 信息素强度是一个人类可读的信号。
- **质量门控的异步更新。** 只有质量检查通过后信息素才更新，从而将推理与学习解耦。
- 在 multi-agent 路由 benchmark 上取得 **4.7 倍加速**。

质量门控很关键：没有它，快但错的 agent 会累积信息素，系统就会锁定在糟糕的路线上。

### 何时为 LLM 使用 PSO / ACO

**在以下情况使用 PSO：**
- 搜索空间是连续的，或可映射到连续参数（prompt embedding、LoRA 权重、数值生成参数）。
- 适应度评估便宜且自动。
- 种群规模可以很小（10-30）。

**在以下情况使用 ACO：**
- 你有路由或路径选择问题。
- 决策会随时间被强化（相同的任务类型反复出现）。
- 你需要为路由决策提供可解释的证据。

**在以下情况两者都不要用：**
- 适应度需要人工审查（每次迭代过于昂贵）。
- 搜索空间是离散组合型的，PSO 覆盖不了（改用遗传算法）。
- 实时决策需要严格延迟（相对于单遍启发式，PSO/ACO 收敛很慢）。

### 为何仿生方法依然胜出

基于梯度的方法需要可微信号。LLM 输出和路由决策并非轻易可微。伪梯度方法（强化学习得到的路由器、DPO 风格的 prompt 调优器）可行，但需要昂贵的训练。

PSO 和 ACO 只需要一个 *评估器* 函数。只要能给候选输出或路由决策打分，就能在该空间上做优化。这大大降低了适用门槛。

### 实际局限

- **种群预算。** N 个粒子 × T 次迭代 × 单次评估成本。若 LLM eval 每次约 $0.02，一个 20 粒子、运行 50 次迭代的 PSO 成本约 $20。据此做好规划。
- **探索与利用。** 信息素衰减率和 PSO 惯性之间存在权衡；衰减太快 → 忘记已有解；太慢 → 卡在早期局部最优。
- **灾难性漂移。** 若适应度地形发生偏移（新的数据分布），两种算法都可能先收敛再发散。请监控最优适应度的稳定性。

```figure
swarm-stigmergy
```

## Build It

`code/main.py` 实现了：

- `LMPSO` —— 在数值 prompt 参数（temperature、top_k 权重）上做 PSO。每个粒子的“LLM 生成”由脚本化的适应度函数模拟。运行该算法 30 次迭代并展示 g_best 收敛。
- `AMRO_S` —— ACO 风格的路由。3 个 agent、4 种任务类型、信息素矩阵、100 个被路由任务。按时间打印（task_type → agent 选择）分布，以展示轨迹的形成。
- 对比：同一任务流上的随机路由 vs ACO 路由。度量质量和延迟。

运行：

```
python3 code/main.py
```

预期输出：
- LMPSO：g_best 适应度在 30 次迭代中从随机水平提升到接近最优。
- AMRO-S：信息素表按任务类型稳定到正确的 agent；ACO 路由在质量上比随机路由高约 30-40%，同时也降低延迟（更少的重试）。

## Use It

`outputs/skill-swarm-optimizer.md` 帮助在 PSO、ACO、遗传算法和基于梯度的优化器之间，为 LLM / agent 优化问题做出选择。

## Ship It

- **从小规模开始。** 10-20 个粒子，20-50 次迭代。只有在收敛曲线显示出明显增益时才扩大规模。
- **逐次迭代记录信息素或 g_best。** 没有轨迹就调试 swarm 优化器会非常痛苦。
- **对更新做质量门控。** 尤其是 ACO 路由：快但错的 agent 绝不能累积信息素。
- **在分布偏移时重置衰减。** 当你的 eval 分布改变时，陈旧的信息素会失效；暂时重置或把衰减率翻倍。
- **限制每次迭代的成本。** 输出每迭代成本指标。每次迭代花费 $500 却只增益 0.5% 的 PSO 不可上线。

## Exercises

1. 运行 `code/main.py`。观察 LMPSO 的收敛。把种群规模分别设为 5、10、20、50。在哪个规模上收敛时间开始饱和？
2. 实现一个“灾难性漂移”实验：在第 30 次迭代后改变适应度函数。PSO 适应的速度有多快？重置 `p_best` 是否有帮助？
3. 给 AMRO-S 增加质量门控：只在 eval 分数 > 0.7 的运行中释放信息素。与无门控版本相比，这如何改变收敛？
4. 阅读 LMPSO（arXiv:2504.09247）。把论文中“速度即 prompt”的概念映射回你的数值速度。模拟中丢失了什么，又保留了什么？
5. 阅读 AMRO-S（arXiv:2603.12933）。实现解耦的“推理快速路径”与异步信息素更新。在持续负载下这如何改变系统延迟？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| PSO | “Particle Swarm Optimization” | Kennedy-Eberhart 1995。基于种群的无梯度优化器。 |
| ACO | “Ant Colony Optimization” | Dorigo 1992。通过信息素轨迹做路径/路线优化。 |
| LMPSO | “PSO 结合 LLM 生成” | arXiv:2504.09247。速度是一个 prompt；LLM 产生候选。 |
| Model Swarms | “在专家权重上做 PSO” | arXiv:2410.11163。在模型参数子空间上做无梯度更新。 |
| AMRO-S | “面向 agent 路由的 ACO” | arXiv:2603.12933。覆盖 task-type × agent 的信息素矩阵。 |
| p_best / g_best | “个体最优 / 全局最优” | 目前找到的每粒子最优解与全 swarm 最优解。 |
| Pheromone | “路由记忆” | 边上的强度；随时间衰减；按质量释放。 |
| Quality-gated update | “只从好的运行中学习” | 以质量检查为条件的信息素释放。 |
| Catastrophic drift | “分布偏移” | 适应度地形变化；旧的 p_best 和信息素失效。 |

## Further Reading

- [Kennedy & Eberhart — Particle Swarm Optimization](https://ieeexplore.ieee.org/document/488968) —— 1995 年的 PSO 论文
- [Dorigo — Ant Colony Optimization](https://www.aco-metaheuristic.org/about.html) —— 1992 年 ACO 基础
- [LMPSO — Language Model Particle Swarm Optimization](https://arxiv.org/abs/2504.09247) —— 面向结构化 LLM 输出的 PSO
- [Model Swarms — gradient-free LLM expert optimization](https://arxiv.org/abs/2410.11163) —— 在模型权重子空间上的 PSO
- [AMRO-S — ant-colony multi-agent routing](https://arxiv.org/abs/2603.12933) —— 带质量门控的信息素驱动路由
