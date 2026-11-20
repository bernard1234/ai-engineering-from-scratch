# Society of Mind 与多智能体辩论

> Minsky 在 1986 年提出的前提——智能是一群专家的社会——每隔十年就会被重新发现。2023 年，Du 等人把它变成了一套具体算法：多个 LLM 实例给出答案、阅读彼此的答案、相互批判并更新。经过 N 轮，它们收敛到一个共识，在六项推理与事实性任务上胜过零样本 CoT 与反思。有两个发现很重要：**多个 agent** 与 **多轮交互** 各自独立地带来收益。社会胜过单 agent 独白；多轮交换胜过一次性的投票。

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** 第 16 阶段，第 04 课（Primitive Model）
**Time:** ~60 分钟

## 问题场景

自洽（self-consistency）——对同一个模型多次采样并取多数答案——是你能加装的最便宜的推理改进。它有效，但很快就饱和。你把采样数翻倍，也可能看不到再一次有意义的跃升。

辩论打破了这种饱和。不再是同一个模型的 N 个独立采样，而是 N 个 agent 阅读彼此的推理并修正。样本之间的相关性下降（它们不再是 i.i.d.），而收敛点往往是对的——在 i.i.d. 投票自信地给出错误答案的地方。

## 核心概念

### Du 等人 2023 年的算法

出自 arXiv:2305.14325（ICML 2024）：

1. N 个 agent 各自给出问题的初始答案。
2. 对于第 r = 2..R 轮：每个 agent 会看到其他 agent 在第 r-1 轮的答案，并被要求“考虑这些答案，给出你更新后的答案”。
3. 经过 R 轮后，对最终答案进行多数投票。

论文在 MMLU、GSM8K、传记写作、MATH 和事实性 benchmark 上做了测试。辩论始终胜过 CoT 与 Self-Reflection。

### 两个独立的旋钮

同一篇论文的消融实验：

- **只看 agent 数量**（1 轮，N 个 agent 多数投票）在多数任务上胜过单 agent，但会进入平台期。
- **只看轮数**（1 个 agent 看到自己此前的推理）几乎没有帮助——这是反思已知的弱点。
- **两者结合**才带来大幅跃升。真正驱动收益的，是多个 agent 之间的多轮交换。

### 为什么有效

两个机制：

1. **暴露于分歧。** 当一个 agent 看到另一个 agent 得出不同结论的推理链时，它要么必须为自己的结论辩护，要么必须更新。无论哪种，第 r+1 轮的上下文都比第 r 轮更丰富。
2. **降低相关误差。** 在自洽中，所有样本都来自同一个模型，因此误差是相关的——你平均之后会得到一个自信的错误答案。不同模型或不同随机种子可以降低相关性。不同的*辩论视角*会进一步去相关。

### 异构辩论

A-HMAD 及相关后续工作为不同的 agent 使用*不同的基础模型*。Llama + Claude + GPT 同台辩论可以缓解单一文化坍缩（monoculture collapse，见第 26 课），因为一个模型家族的相关误差并不会被其他模型家族共享。

缺点是：一个较弱的模型参与辩论，可能把共识拖向它的错误答案（见 “Should we be going MAD?”，arXiv:2311.17371）。

### NLSOM——129 个 agent 的扩展

Zhuge 等人（“Mindstorms in Natural Language-Based Societies of Mind”，arXiv:2305.17066）把这一想法扩展到 129 个成员的社会。结果是：专业化与自组织随规模涌现，系统在视觉问答等任务上胜过单 agent。

### 失效模式

- **谄媚级联。** 所有 agent 都顺从那个听起来最自信的 agent。辩论坍缩成最大声的那个人说了算。通过提示设定对抗性角色（“必须有一个 agent 论证相反立场”）会有所帮助。
- **话题漂移。** 多轮辩论会偏离原始问题。缓解方法：每一轮都重新注入原始问题。
- **算力膨胀。** N 个 agent × R 轮 = N·R 次 LLM 调用，且每次调用的上下文都在增长。5 个 agent、5 轮的辩论就是 25 次上下文不断增长的调用。每个问题的成本可能超过单次 CoT 调用的 10 倍。

```figure
multi-agent-debate
```

## Build It

`code/main.py` 在一个数学问题上运行 3 个 agent × 3 轮的辩论，每个 agent 起始于一个不同（可能错误）的答案。agent 是脚本化的——每个 agent 通过按脚本化置信度对邻居答案加权平均来“更新”。逐轮日志中可以看到收敛过程。

演示展示两个关键效应：

- 单轮交换就能让 agent 更接近正确答案。
- 第 2 轮之后的额外轮数收益递减（与 Du 等人的平台期一致）。

运行：

```
python3 code/main.py
```

## Use It

`outputs/skill-debate-configurator.md` 为新任务配置一场辩论：agent 数量、轮数、异构性（同模型还是混合模型）、角色分配（对称还是单对抗）。它还会在运行前估算 token 成本。

## Ship It

如果你要交付辩论系统：

- **把轮数上限设为 3。** Du 等人表明 3 轮就能捕获大部分收益。更多轮数带来的是成本，而非质量。
- **把 agent 数量上限设为 5。** 超过 5 个，上下文膨胀与成本会占主导。
- **默认异构。** 池中至少有两个不同的基础模型。
- **对抗席位。** 让一个 agent 无论怎样都被指示去持不同意见。可打破谄媚。
- **记录每一轮。** 隐藏中间轮次的辩论系统无法调试，也无法审计。

## Exercises

1. 运行 `code/main.py`，然后把轮数设为 5，观察收益递减。到第几轮时，额外的收敛就不再出现？
2. 增加第四个 agent，赋予对抗性角色：总是不同意当前多数。这会破坏收敛还是改善收敛？
3. 绘制（打印）每一轮的共识得分（处于多数答案的 agent 比例）。它在什么时候达到 1.0，而这是否等同于“正确”？
4. 阅读 Du 等人第 4 节的消融实验。用这段代码复现“仅多 agent”对比“仅多轮”对比“两者兼有”的结果。
5. 阅读 “Should we be going MAD?”（arXiv:2311.17371），列出轮转（round-robin）之外的两种辩论变体——例如 judge-led、chain-of-debate、adversarial。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Society of Mind | “Minsky 的想法” | 智能即相互作用的专家；1986 年的框架如今通过 LLM 辩论被落地实现。 |
| Multi-agent debate | “agent 互相争论” | N 个 agent 提出答案、相互批判、经过 R 轮修正，再多数投票。 |
| Consensus | “他们达成一致” | 并非认识论意义上的真相——只是处于多数答案的比例。可能是自信的错。 |
| Rounds | “交换步骤” | 一轮 = 每个 agent 阅读其他 agent 并更新一次。 |
| Heterogeneous debate | “混合模型家族” | 使用不同的基础模型来降低误差相关性。 |
| Sycophancy cascade | “大家都附和最大声的那个” | 一种辩论失效：agent 不论对错都顺从最自信的 agent。 |
| NLSOM | “129 个 agent 的社会” | 自然语言的社会思维；Zhuge 等人的规模化版本。 |
| Correlated error | “同一个模型，同一个 bug” | 自洽为何会饱和；跨不同视角的辩论可以去除相关性。 |

## Further Reading

- [Du et al. — Improving Factuality and Reasoning in Language Models through Multiagent Debate](https://arxiv.org/abs/2305.14325) — 参考论文，ICML 2024
- [Zhuge et al. — Mindstorms in Natural Language-Based Societies of Mind](https://arxiv.org/abs/2305.17066) — 129 个 agent 的 NLSOM
- [Should we be going MAD? A Look at Multi-Agent Debate Strategies for LLMs](https://arxiv.org/abs/2311.17371) — 对多种辩论变体进行基准测试
- [Debate project page](https://composable-models.github.io/llm_debate/) — Du 等人的代码、演示和消融细节
