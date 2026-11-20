# Voting、Self-Consistency 与 Debate 拓扑

> 最廉价的聚合：采样 N 个相互独立的 agent，多数投票。Wang 等人 2022 年的 self-consistency 用一个模型采样 N 次做到了这一点。multi-agent 用**异构** agent 扩展它，以逃离单一栽培 —— 不同模型、不同 prompt、不同 temperature、不同 context。在多数投票之外，debate 拓扑也很重要：MultiAgentBench（arXiv:2503.01935，ACL 2025）评估了 star / chain / tree / graph 协调，发现 **graph 最适合研究型任务**，并且在超过约 4 个 agent 后出现"coordination tax"。AgentVerse（ICLR 2024）记录了两类涌现模式 —— volunteer 行为与 conformity 行为 —— 而从众既是特性（找到 consensus），也是风险（群体思维，第 24 课）。本课绘制拓扑空间，构建每个变体，并度量 coordination tax。

**Type:** Learn + Build
**Languages:** Python（stdlib）
**Prerequisites:** 第 16 阶段，第 07 课（Society of Mind and Debate）、第 14 课（Consensus and BFT）
**Time:** ~75 分钟

## 问题场景

Debate 能提升准确率（Du 等人，arXiv:2305.14325）。它也能降低准确率。debate 是否有帮助取决于四个结构性选择：

1. 谁与谁交流（topology）。
2. 多少轮（Du 2023：轮数与 agent 数量各自独立地起作用）。
3. agent 是否异构（不同底座模型打破单一栽培）。
4. 是否存在对抗性声音（steel-manning 还是 straw-manning）。

把"跑 5 个 agent 再投票"硬接到任务上的团队，往往比单 agent 还退步。这些失败并非随机。它们与拓扑和异构性相关。本课就是那张拓扑地图。

## 核心概念

### Self-consistency，单模型基线

Wang 等人 2022（"Self-Consistency Improves Chain of Thought Reasoning"）在 temperature > 0 下对同一模型采样 N 次，并对推理路径的答案做多数投票。在 GSM8K 上的结果是：相比单次贪心解码，N=40 次采样带来可观增益。Self-consistency 是 multi-agent 投票的单 agent 前身。

局限：self-consistency 使用一个底座模型。误差在构造上就相关。若模型存在系统性偏置，全部 N 个样本都共享它。

### Multi-agent 投票，异构扩展

用 N 个*不同*的 agent 替换 N 个样本。不同底座模型（Claude、GPT、Llama）、不同 prompt、不同工具访问。好处：错误不相关。代价：不同 agent 成本不同；协调它们会增加开销。

2026 年对异构 debate 的通行叫法是 **A-HMAD** —— Adversarial Heterogeneous Multi-Agent Debate。这并非普遍采用，但论文用这个词指代"不同模型进行 debate，从而减少单一栽培崩溃带来的相关错误"。

### 四种拓扑

```
star                chain               tree                graph

    ┌─A─┐           A─B─C─D         ┌──A──┐              A───B
    │   │                           │     │              │ × │
    B   C                           B     C              D───C
    │   │                          / \   / \
    D   E                         D   E F   G           (fully connected)
```

Star：一个 hub，其他所有节点只与 hub 交流。等价于没有反向通道的 supervisor-worker。
Chain：线性，每个 agent 看到前一个的输出。类似流水线。
Tree：层级式，被层级式 agent 系统使用（第 06 课）。
Graph：任意到任意。包括全连接团与任意 DAG。

### Coordination tax（MultiAgentBench）

MultiAgentBench（MARBLE，ACL 2025，arXiv:2503.01935）在一个含研究、编码、规划的任务套件上对 star、chain、tree、graph 做了基准测试。关键的实测结果：

- **Graph** 拓扑在研究型任务上胜出。信息任意到任意流动；agent 可以相互批评。
- **Star** 在快速事实型任务上胜出。hub 负责过滤与汇总。
- **Chain** 在逐步流水线（分阶段精炼）上胜出。
- 在 graph 拓扑下，**coordination tax** 在超过约 4 个 agent 后出现。实际耗时与 token 成本的增长快于质量。

4 个 agent 的上限是经验性的，不是根本性的。它反映了 2026 年 LLM 的 context 容量：每个 agent 的 context 被同伴的输出填满，而一旦所有人都能看到所有人，增加第 N+1 个 agent 的边际价值就会下降。

### Multi-Agent Debate 策略（"Should we be going MAD?"）

arXiv:2311.17371 是 2023 年对 MAD 策略的综述。被他人复现的关键发现：在相同预算下，与 self-consistency 在*结构上相似*的 MAD 变体（独立采样 + 聚合）往往不如 self-consistency。MAD 最能发挥作用的是当 agent 真正异构、且 debate 具有对抗结构（一个 agent 提出反对）时。

### AgentVerse 的涌现模式

AgentVerse（ICLR 2024，https://proceedings.iclr.cc/paper_files/paper/2024/file/578e65cdee35d00c708d4c64bce32971-Paper-Conference.pdf）记录了两类即便没有显式设计也会从 multi-agent debate 中涌现的行为：

- **Volunteer。** 一个 agent 未经提示就主动提供帮助（"I can take the next step"）。有用：它把工作分配给最适合该子任务的 agent。
- **Conformity。** 一个 agent 调整立场以迎合批评者，即便批评者是错的。这是 debate 版的谄媚（第 14 课）。

从众正是"辩论到一致"会奖励霸凌者的原因。有界轮数加一个独立 judge 可缓解这一点。

### 异构性：真正推动准确率的旋钮

2024-2026 年实践文献中的一个模式：把你 N 个 agent 中的一个换成不同的底座模型，比把 N 加 1 带来更大的准确率提升。直觉就是单一栽培 —— 每个新的独立错误来源，都比一个额外的相关样本更有价值。

在极限处，异构性胜过数量。在多数有干净 ground truth 的任务上，三个不同模型胜过同一个模型的五份副本。

### Jury 方法

Sibyl 框架（被 Minsky-LLM 文献引用）形式化了一个"jury" —— 一小群专门化 agent，在每个阶段通过投票精炼答案。与普通多数投票不同，jury 有角色：一个 agent 交叉质询，一个提供 context，一个评估合理性。Jury 方法处于普通投票（廉价、易单一栽培）与完整 MAD（昂贵、易从众）之间的中点。

### Vote-with-debate 占优的情形

- 问题有 ground truth（事实、数学、代码行为）。投票收敛才有意义。
- agent 能访问不同的来源或工具（异构性可得）。
- 轮数有界（通常 2-3 轮），且有一个独立的 judge 或 verifier。
- 预算允许 3-5 个 agent。在 graph 拓扑上超过 5-7 个后，coordination tax 占主导。

### Vote-with-debate 有害的情形

- 问题偏向意见型。agent 会收敛到看起来最自信的答案，而非最正确的答案。
- 所有 agent 共享一个底座模型。单一栽培让 consensus 变得毫无意义。
- 轮数无界。从众每次都会赢。
- 任务很简单。单 agent 配合 N=5 的 self-consistency 更便宜且同样准确。

```figure
sw-debate-topology
```

## Build It

`code/main.py` 实现：

- `run_star(agents, hub, question)` —— hub 轮询每个 worker 并聚合。
- `run_chain(agents, question)` —— 顺序精炼。
- `run_tree(root, children, question)` —— 深度为 2 的聚合的层级式结构。
- `run_graph(agents, question, rounds)` —— 全到全 debate，有界轮数。
- 一个脚本化的异构性调节：每个 agent 有一个 `error_bias`，表示其系统性的错误倾向。
- 一个度量框架，在 N=3、5、7 下运行每种拓扑，并报告 (accuracy, total_tokens, wallclock_simulated)。

运行：

```
python3 code/main.py
```

预期输出：一张 topology × N -> (accuracy, tokens, latency) 的表。在研究型任务上 graph 在 N=3-5 时胜出；在快速事实型任务上 star 胜出；graph 在 N=7 时显示出 coordination tax（延迟膨胀快于准确率）。

## Use It

`outputs/skill-topology-picker.md` 是一个 skill，它读取任务描述并推荐拓扑（star / chain / tree / graph）、N（agent 数量）、异构性画像（使用哪些底座模型）以及轮数上限。

## Ship It

对任何集成：

- 先用一个强底座模型从 **N=5 的 self-consistency** 起步。这是廉价的基线。
- 若准确率重要，升级到 **N=3 的异构投票**。度量差值。
- 只有当任务具有结构（研究、多步）且轮数有界可行时，才升级到 **debate 拓扑**。
- 始终记录少数簇。当少数派持续正确时，你就有了多样性信号。
- 在度量准确率的同时基准测试实际耗时与 token。"以 10 倍成本换取更高准确率"是一个商业决策。

## Exercises

1. 运行 `code/main.py`。绘制 graph 拓扑的 coordination-tax 曲线：accuracy vs N、tokens vs N。曲线在哪个 N 处出现拐点？
2. 实现 A-HMAD：三个带有刻意不同偏置的 agent。在第 14 课的单一栽培攻击上，全部同偏置的基线相比 A-HMAD 如何？
3. 为 graph 拓扑加入一个"judge"角色，它不投票，只给最终 consensus 打分。这会改变涌现的从众行为吗？
4. 阅读 AgentVerse 论文（ICLR 2024）。识别你的实现最强烈展现的涌现行为。你能通过改动 prompt 引出相反的行为吗？
5. 阅读 MultiAgentBench（arXiv:2503.01935）第 4 节（拓扑实验）。用你的框架在论文中的一个任务上复现"graph 胜出研究型任务"的结果。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Self-consistency | "Sample N times, vote" | Wang 2022。单一模型，N 个 temperature>0 样本，对推理路径做多数投票。 |
| Heterogeneity | "Different models" | 不同底座模型或 prompt 族的集成。打破单一栽培。 |
| MAD | "Multi-agent debate" | agent 在多轮中交换批评的泛称。见 Du 2023。 |
| A-HMAD | "Adversarial Heterogeneous MAD" | 强调不同模型 + 对抗结构的 MAD 变体。 |
| Topology | "Who talks to whom" | star、chain、tree、graph。决定信息流动。 |
| Coordination tax | "Diminishing returns" | 在 graph 上超过约 4 个 agent 后，成本增长快于质量。 |
| Volunteer behavior | "Unprompted help" | AgentVerse 涌现模式：一个 agent 主动提出承担一步。 |
| Conformity behavior | "Agreement under pressure" | AgentVerse 涌现模式：一个 agent 向批评者靠拢。 |
| Jury | "Small specialized panel" | Sibyl 式集成，带角色（examiner、context、scorer）。 |

## Further Reading

- [Wang et al. — Self-Consistency Improves Chain of Thought Reasoning](https://arxiv.org/abs/2203.11171) —— 单模型基线
- [Du et al. — Improving Factuality and Reasoning via Multiagent Debate](https://arxiv.org/abs/2305.14325) —— agent 数量与轮数各自独立地起作用
- [MultiAgentBench / MARBLE](https://arxiv.org/abs/2503.01935) —— 拓扑基准，显示 graph 最适合研究、chain 最适合流水线
- [Should we be going MAD?](https://arxiv.org/abs/2311.17371) —— MAD 策略综述；发现在同等预算下 MAD 常常输给 self-consistency
- [AgentVerse (ICLR 2024)](https://proceedings.iclr.cc/paper_files/paper/2024/file/578e65cdee35d00c708d4c64bce32971-Paper-Conference.pdf) —— volunteer 与 conformity 涌现模式
- [MARBLE repo](https://github.com/ulab-uiuc/MARBLE) —— 参考基准实现
