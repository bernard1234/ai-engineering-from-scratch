# 多智能体辩论与协作

> Du 等人（ICML 2024，《Society of Minds》）让 N 个模型实例各自独立提出答案，然后在 R 轮中互相批判以收敛。改进了事实性、规则遵循和推理能力。稀疏拓扑在 token 成本上优于全互联。

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 12 (Workflow Patterns), Phase 14 · 05 (Self-Refine and CRITIC)
**Time:** ~60 minutes

## 学习目标

- 解释辩论协议：N 个提议者，R 轮，收敛到一个共享答案。
- 描述为什么辩论能改进事实性、规则遵循和推理。
- 解释稀疏拓扑：并非每个辩论者都需要看到其他所有辩论者。
- 在一个脚本化 LLM 之上用标准库实现辩论，包含全互联和稀疏两种变体；测量 token 成本与准确率。

## 问题

Self-Refine（第 05 课）是单个模型自我批判——有群体思维的风险。CRITIC（第 05 课）把批判建立在外部工具上——但工具并非总是可用。辩论引入了第三种模式：多实例、交叉批判、通过分歧收敛。

## 概念

### Society of Minds（Du 等人，ICML 2024）

- N 个模型实例对同一问题各自独立提出答案。
- 在 R 轮中，每个模型阅读其他模型的提案并加以批判。
- 模型根据批判更新自己的答案。
- 经过 R 轮后，返回收敛后的答案。

由于成本，原始实验使用 N=3、R=2。在难题上（MMLU、GSM8K、Chess Move Validity、传记生成），准确率随智能体数量和轮数增加而提升。

跨模型组合优于单模型辩论：ChatGPT + Bard 组合 > 任何单独一个。

### 稀疏拓扑

《Improving Multi-Agent Debate with Sparse Communication Topology》（arXiv:2406.11776，2024-2025）表明全互联辩论并非总是最优。稀疏拓扑（星形、环形、hub-and-spoke）可以以更低的 token 成本达到相同的准确率。每个辩论者只看到一部分同伴。

含义：

- 全互联 N=5、R=3 = 5 × 3 = 15 个提案，每个读 4 个同伴 = 60 次批判操作。
- 星形 N=5、R=3（一个 hub + 4 个 spoke）= 15 个提案，spoke 只读 hub = 12 次批判操作。

### 辩论何时有帮助

- **事实性。** N 个独立提案，交叉检查可减少幻觉。
- **规则遵循。** 国际象棋走子合法性——一个模型漏掉规则，其他模型能抓住。
- **开放式推理。** 多种框架逐步收窄到正确答案。

### 辩论何时有害

- **对延迟敏感的 UX。** N × R 串行轮次是你可能承受不起的延迟。
- **对成本敏感的规模。** 每个问题 N × R 个 token。
- **简单的事实查询。** 一次查询比五轮辩论便宜。

### 2026 年的实际落地形态

- **Anthropic orchestrator-workers**（第 12 课）——辩论的一种变体，带一个综合步骤。
- **LangGraph supervisor**（第 13 课）——中央路由 + 专家智能体可以把辩论实现为一个节点。
- **OpenAI Agents SDK**（第 16 课）——智能体来回 handoff 以进行迭代批判。
- **多智能体评估**——将辩论与 evaluator-optimizer 配对以获得评估信号。

### 这个模式在哪里会出问题

- **收敛崩塌。** 所有智能体都收敛到第一个错误答案。用强制分歧轮次来缓解。
- **Hub 故障。** 在星形拓扑中，一个糟糕的 hub 会污染所有人。轮换或使用多个 hub。
- **提示词同质化。** 所有智能体使用相同的提示词，于是产出相同的答案。使用多样化的提示词和/或模型。

```figure
debate-converge
```

## Build It

`code/main.py` 实现了标准库版辩论：

- `Debater` 类（带逐辩论者观点漂移的脚本化 LLM）。
- `FullMeshDebate` 和 `SparseDebate` 运行器。
- 三个问题：一个事实型、一个规则型、一个推理型。
- 指标：收敛答案、收敛轮数、批判操作总数。

运行它：

```
python3 code/main.py
```

输出：每种协议的准确率与成本；稀疏在 3 个问题中的 2 个上以更低成本追平全互联。

## Use It

- **Anthropic orchestrator-workers** 用于简单的 2-3 个 worker 的辩论。
- **LangGraph** 用于带 checkpointing 的有状态多轮辩论。
- **Custom** 用于研究或专门化的正确性保证。

## Ship It

`outputs/skill-debate.md` 搭建一个多智能体辩论脚手架，拓扑、N、R 和收敛规则均可配置。

## 练习

1. 实现一条「强制分歧」规则：在第 1 轮，每个辩论者都必须提出一个不同的提案。测量对收敛速度的影响。
2. 加入置信度加权聚合：辩论者返回 (answer, confidence)；聚合器按置信度加权。有帮助吗？
3. 把某个「智能体」换成一个观点不同的脚本化 LLM。异质性会提升准确率吗？
4. 测量你的 3 个问题上全互联 vs 稀疏的 token 成本。画出成本 vs 准确率。
5. 阅读 Society of Minds 论文。把你的玩具移植到 N=5、R=3。什么会坏？什么会变好？

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| Debate | 「多智能体批判」 | N 个提议者，R 轮交叉批判，收敛 |
| Full mesh | 「人人读人人」 | 每轮每个辩论者读每个同伴 |
| Sparse topology | 「有限的同伴视野」 | 辩论者只读一部分同伴 |
| Hub-and-spoke | 「星形拓扑」 | 一个中央辩论者，N-1 个 spoke 只读 hub |
| Convergence | 「达成一致」 | 辩论者收敛到一个共享答案 |
| Society of Minds | 「Du 等人的辩论论文」 | ICML 2024 多智能体辩论方法 |

## 延伸阅读

- [Du 等人，Society of Minds（arXiv:2305.14325）](https://arxiv.org/abs/2305.14325)——经典的多智能体辩论
- [Sparse Communication Topology（arXiv:2406.11776）](https://arxiv.org/abs/2406.11776)——稀疏拓扑结果
- [Anthropic，Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)——orchestrator-workers 作为辩论的一种变体
- [Madaan 等人，Self-Refine（arXiv:2303.17651）](https://arxiv.org/abs/2303.17651)——单模型自我批判的对照物
