# AlphaEvolve — 进化式编码 agent

> 把一个前沿编码模型与一个进化循环、一个机器可校验的 evaluator 配对，让循环跑得足够久。它发现了一个 4x4 复数矩阵乘法过程，只用 48 次标量乘法——这是 56 年来对 Strassen 的首次改进。它还在 Google 全域找到了一个 Borg 调度启发式，在生产环境中回收了约 0.7% 的集群算力。这套架构故意做得很无聊。收益来自 evaluator 的严谨。

**Type:** Learn
**Languages:** Python（stdlib，进化循环玩具）
**Prerequisites:** 第 15 阶段，第 01 课（long-horizon framing）、第 15 阶段，第 02 课（self-taught reasoning）
**Time:** ~60 分钟

## 问题场景

LLM 会写代码。进化算法能搜索代码。两者各自被尝试了几十年，也都撞到了天花板。LLM 的天花板是虚构：模型写出貌似合理的代码，但并不做它声称要做的事。进化算法的天花板是搜索成本：对语法做随机变异很少产出可编译的程序，更不用说更好的程序。

AlphaEvolve（Novikov 等，DeepMind，arXiv:2506.13131，2025 年 6 月）把两者结合起来。LLM 对程序数据库提出有针对性的编辑；自动 evaluator 给每个变体打分；高分变体成为后续世代的父代。LLM 承担写出貌似合理代码这一昂贵步骤；evaluator 抓住虚构。循环运行数小时到数周。

报告的结果：48 次标量乘法的 4x4 复数矩阵乘法（Strassen 1969 年的界是 49）、Google 生产环境中的 Borg 调度启发式、FlashAttention kernel 32.5% 的加速、Gemini 训练吞吐提升。

这套架构之所以有效，是因为 evaluator 是机器可校验的。在 evaluator 做不到的领域，它就不起作用。这种不对称正是本课的要点。

## 核心概念

### 循环

1. 从一个正确但次优的种子程序 `P_0` 出发。
2. 维护一个变体程序数据库，每个变体都由 evaluator 打分。
3. 从数据库中采样一个或多个父代（MAP-elites 式或 island 式）。
4. prompt LLM（大量候选用 Gemini Flash，较难的用 Gemini Pro）产出父代的一个修改变体。
5. 编译、运行，并用留出 evaluator 评估该变体。
6. 按分数与特征向量插入数据库。
7. 重复。

有两个细节很重要。第一，prompt 给 LLM 的不只是父代程序——通常还包括数据库中若干顶尖变体、evaluator 的签名，以及一段简短的任务描述。模型的工作是提出一个可能提高分数的定向修改。第二，数据库是有结构的（MAP-elites 网格、island 式），这样循环探索的是多样性，而不仅是当前的领先者。

### 为什么 evaluator 不可或缺

AlphaEvolve 的胜利全部来自 evaluator 快速、确定且难以钻空子的领域：

- **矩阵乘法算法**：一个把矩阵相乘并逐位校验相等的单元测试。
- **Borg 调度启发式**：一个生产级模拟器，重放历史集群负载并度量被浪费的算力。
- **FlashAttention kernel**：正确性测试加上真实硬件上的挂钟 benchmark。
- **Gemini 训练吞吐**：按每步实测的 GPU 秒数衡量。

在每种情形里，evaluator 都能抓住本来会占主导的那类 LLM 错误：虚构的正确性声称、在硬件上消失的性能声称，以及边界情况下的失败。去掉 evaluator，循环就会去优化漂亮的代码。

### Reward hacking 是同一句话的另一面

进化优化的对象就是 evaluator 所度量的东西。如果 evaluator 不完美，循环就会找到那个不完美之处。在无法验证的领域，循环会去优化表面特征，而不是预期的行为。DeepMind 在论文中明确指出了这一点：AlphaEvolve 的成功只适用于 evaluator 的严谨程度与搜索野心相匹配的领域。

2025–2026 年代码搜索循环中 reward hacking 的具体例子：

- 奖励“完成时间”的优化目标，奖励了提交空解法。
- 奖励“测试条件下正确”的 benchmark 分数，奖励了背记测试并过拟合。
- 一个“代码质量”代理指标，奖励了删除注释和重写变量名，而没有任何语义变化。

AlphaEvolve 的对策：交付一个 LLM 从未见过的留出 evaluator，其输入在评估时生成。即便如此，DeepMind 仍建议对任何拟议部署做严格审查。

### 为何 LLM + 搜索胜过任一单独使用

LLM 能产出可编译、语义上合理的修改。对一个 2000 行的 Python 文件做随机变异 GA，几乎总会产出语法错误。LLM 还把搜索集中在合理的邻域内（改一个函数，而不是随机字节），这大幅减少了浪费的 evaluator 调用。

反过来，evaluator 抓住 LLM 的虚构。LLM 会自信地声称某个函数“在极限下是 O(n log n)”，而它实际上是 O(n^2)；一个挂钟 benchmark 就能把这个问题定下来。

### AlphaEvolve 在前沿技术栈中的位置

| 系统 | 生成器 | evaluator | 领域 | 示例成果 |
|---|---|---|---|---|
| AlphaEvolve | Gemini | 正确性 + benchmark | 算法、kernel、调度器 | 48 次乘法的 4x4 matmul |
| FunSearch（DeepMind，2023） | PaLM / Codey | 正确性 | 组合数学 | cap-set 下界 |
| AI Scientist v2（Sakana，第 05 课） | GPT/Claude | LLM 评审 + 实验 | ML 研究 | ICLR workshop 论文 |
| Darwin Godel Machine（第 04 课） | agent scaffold | SWE-bench / Polyglot | agent 代码 | 20% → 50% SWE-bench |

四者都是同一套配方的变体：生成器加 evaluator，加循环。区别在于 evaluator 评判什么，以及它有多严谨。

```figure
alphaevolve-loop
```

## Use It

`code/main.py` 在一个玩具符号回归问题上实现了一个最小的 AlphaEvolve 式循环。“LLM”是一个 stdlib 代理，对一个计算目标函数的程序提出小的语法变异。“evaluator”度量在留出测试点上的均方误差。

观察：

- 最佳分数如何随世代改进。
- MAP-elites 网格如何让多样化解法存活，使循环不会收敛到局部最优。
- 去掉留出测试（只用训练的 evaluator）如何让循环以惊人的程度过拟合。

## Ship It

`outputs/skill-evaluator-rigor-audit.md` 是在新领域考虑 AlphaEvolve 式循环的前提条件：你的 evaluator 是否真的能抓住你在意的失败？

## Exercises

1. 运行 `code/main.py`。记下最佳分数轨迹。禁用留出 evaluator（参数 `--no-holdout`）后重跑。量化过拟合程度。

2. 阅读 AlphaEvolve 论文中关于 MAP-elites 网格的第 3 节。为一个新问题（例如编译器优化 pass）设计一个能保持搜索多样性的特征向量描述子。

3. 48 次乘法的 4x4 结果在 56 年后改进了 Strassen 的 49 次乘法界。阅读论文附录 F，用三句话解释为什么这个问题的 evaluator 特别容易做对，以及为什么大多数领域并非如此。

4. 举出一个 AlphaEvolve 会失败的领域。准确指出 evaluator 在哪里失效、为什么失效。

5. 为你熟悉的某个领域写出你会采用的 evaluator 签名。包含 (a) 正确性条件、(b) 性能度量、(c) 留出输入生成规则、(d) 至少一项反 reward hacking 检查。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|---|---|---|
| AlphaEvolve | “DeepMind 的进化式编码 agent” | Gemini + 程序数据库 + 机器可校验的 evaluator |
| MAP-elites | “保持多样性的档案” | 以特征向量为键的网格；每个单元存放该描述子下最优的变体 |
| Island model | “并行进化子种群” | 相互独立、定期迁移的种群；防止过早收敛 |
| Machine-checkable evaluator | “确定性 oracle” | LLM 无法伪造的单元测试、模拟器或 benchmark——此循环的前提 |
| Reward hacking | “优化度量，而非目标” | 循环找到一种最大化分数却不完成预期任务的方式 |
| Seed program | “起点” | 循环从中进化的初始正确但次优程序 |
| Held-out evaluator | “LLM 从未见过的评估数据” | 在评估时生成的输入，用于防止背记 |

## Further Reading

- [Novikov et al. (2025). AlphaEvolve: A coding agent for scientific and algorithmic discovery](https://arxiv.org/abs/2506.13131) — 完整论文。
- [DeepMind blog on AlphaEvolve](https://deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/) — 厂商撰写的成果说明。
- [AlphaEvolve results repository](https://github.com/google-deepmind/alphaevolve_results) — 发现的算法，包括 48 次乘法的 4x4 matmul。
- [Romera-Paredes et al. (2023). Mathematical discoveries from program search with LLMs (FunSearch)](https://www.nature.com/articles/s41586-023-06924-6) — 前身系统。
- [Anthropic — Responsible Scaling Policy v3.0 (Feb 2026)](https://anthropic.com/responsible-scaling-policy/rsp-v3-0) — 把受 evaluator 约束的自主性列为关键研究方向。
