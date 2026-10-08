# Tree of Thoughts 与 LATS：刻意搜索

> 一条思维链轨迹没有回头的余地。ToT（Yao 等人，2023）把推理变成一棵树，每个节点都带自我评估。LATS（Zhou 等人，2024）在蒙特卡洛树搜索下把 ToT 与 ReAct 和 Reflexion 统一起来。Game of 24 从 4%（CoT）提升到 74%（ToT）；LATS 在 HumanEval 上达到 92.7% 的 pass@1。

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 01 (Agent Loop), Phase 14 · 03 (Reflexion)
**Time:** ~75 minutes

## 学习目标

- 把推理框定为搜索：节点是「thoughts」，边是「expansions」，价值是「有多有前途」。
- 用标准库实现一个带自我评估打分的 ToT 式 BFS 树搜索。
- 扩展到一个玩具 LATS MCTS 循环，含 select / expand / simulate / backpropagate。
- 判断什么时候搜索值得付出 token 倍数的代价（Game of 24、代码生成），什么时候单条轨迹就够（简单问答）。

## 问题

思维链是一次线性行走。如果第一步就错了，后续每一步都建立在一个糟糕的前提上。在 Game of 24（用四个数字和 + − × ÷ 凑出 24）上，GPT-4 的 CoT 只有 4% 的准确率。模型在早期就选错了子表达式，然后无法恢复。

推理真正需要的，是提出多个候选、评估它们、挑出有前途的、并在遇到死胡同时回头的能力。这就是搜索。Tree of Thoughts 和 LATS 是两种经典表述。

## 概念

### Tree of Thoughts（Yao 等人，NeurIPS 2023）

每个节点是一个连贯的中间步骤（「一个 thought」）。每个节点可以扩展出 K 个子 thought。LLM 用一个打分提示词对每个节点自我评估。搜索探索这棵树——BFS、DFS 或 beam。

```
                     (root: "find 24 from 4 6 4 1")
                    /               |            \
           ("6 - 4 = 2")    ("4 + 1 = 5")    ("4 * 6 = 24")  <- Score: HIGH
              /   \              |                  |
          ...    ...          ...                finish
```

自我评估是承重的那块。论文展示了三种变体：`sure / likely / impossible` 分类、`1..10` 数值打分，以及在候选之间投票。三种都在 Game of 24 上大幅超过 CoT（GPT-4 从 4% 到 74%）。

### LATS（Zhou 等人，ICML 2024）

LATS 在 MCTS 下统一了 ToT、ReAct 和 Reflexion。LLM 扮演三个角色：

- **Policy**：提出候选的下一步动作（ReAct 式）。
- **Value function**：给一段部分轨迹打分（ToT 式自我评估）。
- **Self-reflector**：失败时写下一段自然语言反思（Reflexion 式），并用它为未来的 rollout 重新播种。

环境反馈（观察）混入 value function，让搜索由真实的工具结果而非仅模型意见来引导。论文当时的成绩：GPT-4 的 HumanEval pass@1 达 92.7%（SOTA），GPT-3.5 的 WebShop 平均 75.9（接近基于梯度的微调）。

### 极简 MCTS

每次迭代四个阶段：

1. **Select** —— 用 UCT（树的上置信界）从根走到一个叶子。
2. **Expand** —— 通过 policy 生成 K 个子节点。
3. **Simulate** —— 用 policy 从某个子节点 rollout，用 value function（或环境奖励）给叶子打分。
4. **Backpropagate** —— 沿路径向上更新访问次数和价值估计。

UCT 公式：`Q(s, a) + c * sqrt(ln N(s) / N(s, a))`。第一项是 exploitation；第二项是 exploration。按任务调 `c`。

### 成本现实

搜索会爆炸 token。ToT 在 Game of 24 上用掉 CoT 的 100–1000 倍 token。LATS 类似。这并不免费；把搜索留给：

- 单条轨迹可证明显不足的任务（Game of 24、复杂代码）。
- 墙钟时间不如正确性重要的任务。
- 有廉价、可靠 value function 的任务（代码的单元测试、数学的显式目标）。

如果你的任务只有一个正确答案、且评估器有噪声，搜索常常让事情更糟——它会找到一个「分数不错」的错误答案。

### 2026 年的定位

大多数生产智能体并不跑 LATS。它们跑带基于工具验证的 ReAct（CRITIC，第 05 课）。搜索出现在专门的细分领域：

- 用测试作为 value function 的编码智能体（HumanEval 式）。
- 探索多条查询路径的深度研究智能体。
- LangGraph 子图内部的重规划工作流。

AlphaEvolve（第 11 课）是 2025 年的极端形态：对代码做进化搜索、机器可验证的适应度、前沿级收益（56 年来首个 4x4 矩阵乘法改进）。

```figure
tree-of-thoughts
```

## Build It

`code/main.py` 实现了：

- 在一个风格化的「挑选算术运算」任务上的一个微型 ToT BFS。
- 在同一任务上的一个玩具 LATS MCTS 循环（Select / Expand / Simulate / Backpropagate），带 UCT 选择。
- 一个把符号分数与自我评估分数组合起来的 value function。

运行它：

```
python3 code/main.py
```

trace 展示 ToT 用 BFS 每个节点扩展三个候选，与 LATS 通过 MCTS 收敛到最佳 rollout 的对比。两者都打印了 token 计数。

## Use It

LangGraph 把 ToT 式探索作为子图模式发布；LangChain 团队关于 LATS 的博客（2024 年 5 月）是参考教程。LlamaIndex 发布了一个 `TreeOfThoughts` 智能体。对大多数 2026 年的生产智能体来说，这个模式藏在 `if task_complexity > threshold: use_search()` 的门后面——见第 05 课的 evaluator-optimizer 模式。

## Ship It

`outputs/skill-search-policy.md` 给定任务形态、预算和评估器保真度，在 linear ReAct、ToT、LATS 和进化搜索之间做出选择。

## 练习

1. 用 UCT c=0.1 和 c=2.0 分别跑玩具 LATS。trace 里有什么变化？
2. 把 value function 换成一个噪声更大的打分器（加随机抖动）。MCTS 还能找到最佳叶子吗？它能容忍的最低信噪比是多少？
3. 实现 beam-search ToT（每层保留 top-k）并与 BFS 对比。在紧张的 token 预算下哪个更好？
4. 读 LATS 第 5.1 节。复现 HumanEval 的轨迹数量：要多少次 rollout 才能达到论文报告的 pass@1？
5. 读 LATS 论文关于「LATS 什么时候帮助较小」的讨论。写一段决策规则，把任务形态映射到搜索策略。

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|-----------|------------------|
| Tree of Thoughts | 「分支式 CoT」 | Yao 等人——带自我评估的 thought 节点树 |
| LATS | 「用于 LLM 的 MCTS」 | Zhou 等人——在 MCTS 下统一 ToT + ReAct + Reflexion |
| UCT | 「上置信界」 | 平衡 exploitation（Q）与 exploration（ln N / n）的选择公式 |
| Value function | 「这个状态有多好」 | 提示词化的 LLM 分数或环境奖励；喂给 backprop |
| Policy | 「动作提出者」 | ReAct 式生成器；产出候选的下一个 thought/action |
| Rollout | 「模拟轨迹」 | 用 policy 从一个节点走到叶子，用 value 打分 |
| Backpropagate | 「更新祖先」 | 把叶子的奖励沿路径上推，更新访问计数和 Q |
| Search cost | 「token 爆炸」 | Game of 24 上是 CoT 的 100–1000 倍；采用前先预算 |

## 延伸阅读

- [Yao 等人，Tree of Thoughts（arXiv:2305.10601）](https://arxiv.org/abs/2305.10601)——经典原论文
- [Zhou 等人，LATS（arXiv:2310.04406）](https://arxiv.org/abs/2310.04406)——带 Reflexion 反馈的 MCTS
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)——用于搜索的子图模式
- [AlphaEvolve（arXiv:2506.13131）](https://arxiv.org/abs/2506.13131)——带程序化评估器的进化搜索
