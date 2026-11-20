# 自主编码 agent 全景（2026）

> SWE-bench Verified 在不到三年内从 4% 涨到 80.9%。同一个 Claude Sonnet 4.5 在 SWE-agent v1 上得 43.2%，在 Cline 自主模式下得 59.8%——围绕模型的 scaffold 现在和模型本身一样重要。OpenHands（原 OpenDevin）是最活跃的 MIT 许可平台，其 CodeAct 循环直接在 sandbox 中执行 Python 动作，而不是发 JSON tool call。这些头条数字掩盖了一个方法论问题：SWE-bench Verified 的 500 个任务中有 161 个只需 1–2 行改动，而对同样的前沿模型，SWE-bench Pro（10+ 行任务）的分数只有 23–59%。

**Type:** Learn
**Languages:** Python（stdlib，CodeAct 与 JSON tool call 对比）
**Prerequisites:** 第 14 阶段，第 07 课（Tool use）、第 15 阶段，第 01 课（Long-horizon agents）
**Time:** ~45 分钟

## 问题场景

「哪个 coding agent 最好」是个错误的问题。正确的问题是：在与我的工作相匹配的任务分布上、用我将在生产中运行的 scaffold，我能得到怎样的端到端可靠性？

2022 到 2026 年间，这个领域认识到 scaffold——检索层、planner、sandbox、编辑-验证循环、反馈格式——是承重的。Claude Sonnet 4.5 在 SWE-agent v1 上于 SWE-bench Verified 得 43.2%；同一个模型放进 Cline 的自主 scaffold 里则得 59.8%。16.6 个绝对百分点之差，权重相同。基座模型只是一个组件；循环才是产品。

与之相伴的问题是，benchmark 饱和会掩盖回退。SWE-bench Verified 已接近饱和，而简单任务长尾（500 个任务里有 161 个要求 ≤2 行）把顶端分数抬高。真实世界质量在 SWE-bench Pro（10+ 行改动）这类分布上衡量得更好——在那里，同样的领跑者仍然停留在 23–59%。

## 核心概念

### SWE-bench，一段话

SWE-bench（Jimenez 等人）拿带有已知标准补丁（ground-truth patch）的真实 GitHub issue，要求 agent 产出一个能让测试套件通过的补丁。SWE-bench Verified（OpenAI，2024）是一个经人工筛选的 500 任务子集，移除了含糊和损坏的任务。SWE-bench Pro 是更难的继任者——需要 10+ 行改动的任务，当前前沿 agent 停留在 23–59%。

### 2022 → 2026 的曲线究竟说明了什么

- **2022**：研究模型在原始 SWE-bench 上约 4%。
- **2024**：GPT-4 + Devin 式 scaffold 约 14%；SWE-agent 约 12%。
- **2025**：Claude 3.5/3.7 Sonnet 在 Aider 与 SWE-agent 内把分数推进到 40–55% 区间。
- **2026**：Claude Sonnet 4.5 及其前沿竞争者，在 SWE-bench Verified 上达到 70–80%+。Epoch AI 的排行榜实时追踪这些数字。

这一斜率源自三个叠加的来源：更好的基座模型、更好的 scaffold（CodeAct、reflection、verifier 循环）、更好的 benchmark（Verified 去除了噪声）。

### CodeAct 与 JSON tool call

OpenHands（All-Hands-AI，arXiv:2407.16741，原 OpenDevin）押了一个特定的架构注：与其让模型发出 JSON tool call、由宿主解码并执行，不如让模型发出 Python 代码，由 Jupyter 式内核在 sandbox 中运行。agent 可以在一次动作内遍历文件、串联工具，并捕获自己的异常。

权衡是：

- **JSON tool call**：每个动作是一轮；易审计；组合性有限；默认安全，因为每次调用都经过显式校验器。
- **CodeAct**：一次动作可以是整个程序；具备组合性；需要加固的 sandbox（OpenHands 使用 Docker 隔离）；失效模式包括 sandbox 运行时允许的任何东西。

两种架构都在生产中使用。CodeAct 在开放平台（OpenHands、smolagents）中占主导。JSON tool call 在托管服务（Anthropic Managed Agents、OpenAI Assistants）中仍占主导，因为那里由提供商控制执行器。

### 2026 全景中的 scaffold

| Scaffold | 许可证 | 执行模型 | 显著特性 |
|---|---|---|---|
| OpenHands（OpenDevin） | MIT | Docker 中的 CodeAct | 最活跃的开放平台；事件流可回放 |
| SWE-agent | MIT | Agent-Computer Interface（ACI） | 首个端到端 SWE-bench scaffold |
| Aider | Apache-2 | 在本地仓库里以 diff 方式编辑 | 极简 scaffold，回归稳定性强 |
| Cline | Apache-2 | 带工具策略的 VS Code agent | 在 Sonnet 4.5 上得分最高的开放 scaffold |
| Devin（Cognition） | 专有 | 托管 VM + planner | 首个「AI 软件工程师」产品类别 |
| Claude Code | 专有 | Permission modes + routines | 第 10 课详细讲解 agent 循环 |

### 为什么 scaffold 占主导

一次 coding 运行是一条长程轨迹（第 01 课）。可靠性会跨步骤复利。scaffold 在三个地方买到分数：

1. **检索**：找到该读的正确文件是那个不显眼的瓶颈。SWE-agent 的 ACI、OpenHands 的文件索引、Aider 的 repo-map 都在攻击这一点。
2. **Verifier 循环**：运行测试、读栈追踪、重新尝试，在 SWE-bench 上就是 10+ 个百分点的差距。
3. **失效隔离**：出错时回滚的 sandbox 能防止损害累积。同一个模型，有和没有 verifier 循环，看起来像两个不同的产品。

### Benchmark 饱和与真实分布

OpenHands 作者与 Epoch AI 都指出，SWE-bench Verified 有一条简单长尾：500 个任务里有 161 个只需 1–2 行改动。高分部分由这条长尾驱动。SWE-bench Pro 限定为 10+ 行改动，即便是前沿系统，分数也回落到 23–59% 区间。你的生产分布几乎肯定更接近 Pro 而非 Verified。

选择 agent 的含义：在你自己的 bug 积压上跑一个类似 Pro 的子集。真正重要的分数，是在能代表你所交付内容的任务上的分数。

```figure
a5-scaffold-delta
```

## Use It

`code/main.py` 在一个固定的迷你任务分布上对比两种玩具 agent scaffold：

1. 一个**JSON tool call** scaffold，每轮执行一次动作。
2. 一个**CodeAct** scaffold，每次动作可以发出一个小 Python 片段。

两者都使用桩「模型」（确定性规则），使对比把 scaffold 与模型质量隔离开。输出显示 CodeAct scaffold 用更少的轮次解出更多任务，代价是每次动作的爆炸半径更大。

## Ship It

`outputs/skill-scaffold-audit.md` 帮你在采纳前审计一个拟议的 coding-agent scaffold：检索质量、verifier 是否存在、sandbox 隔离，以及 benchmark 与分布的匹配度。

## Exercises

1. 运行 `code/main.py`。在同一任务集上，每种 scaffold 各需多少轮？各自的单动作爆炸半径是多少？

2. 阅读 OpenHands 论文（arXiv:2407.16741）。论文主张在复杂任务上 CodeAct 胜过 JSON tool call。找出论文承认的一种失效模式，并用一句话说明这种模式在生产中何时会占主导。

3. 从你的 bug 积压里挑一个需要跨两个文件、改动 10+ 行的任务。估计前沿模型在（a）JSON tool call 与（b）CodeAct 下的端到端成功概率。为这一差距给出理由。

4. SWE-bench Verified 有 161 个单文件、1–2 行的任务。构造一个排除它们之后的分数。排行榜会如何洗牌？

5. 阅读「Introducing SWE-bench Verified」（OpenAI）。解释用于移除含糊任务的具体方法，并指出筛选过程会漏掉的一个类别。

## Key Terms

| 术语 | 通俗说法 | 实际含义 |
|---|---|---|
| SWE-bench | 「编码 benchmark」 | 带有已知标准补丁与测试套件的真实 GitHub issue |
| SWE-bench Verified | 「清洗过的子集」 | 500 个经人工筛选的任务，仍含简单长尾 |
| SWE-bench Pro | 「更难的子集」 | 10+ 行改动；前沿停留在 23–59% |
| CodeAct | 「代码即动作」 | agent 发出 Python；Jupyter 式内核在 sandbox 中执行 |
| JSON tool call | 「函数调用」 | 每次动作都是一段结构化 JSON 载荷，执行前先校验 |
| Scaffold | 「agent 框架」 | 围绕基座模型的检索 + planner + 执行器 + verifier 循环 |
| ACI（Agent-Computer Interface） | 「SWE-agent 的格式」 | 为 LLM 易用性而非人类 shell 设计的命令集 |
| Verifier loop | 「测试-重试」 | 运行测试、读输出、修改补丁；非模型因素中最大的可靠性增益 |

## Further Reading

- [Jimenez et al. — SWE-bench](https://www.swebench.com/)——原始 benchmark 与方法论。
- [OpenAI — Introducing SWE-bench Verified](https://openai.com/index/introducing-swe-bench-verified/)——筛选子集是如何构建的。
- [Wang et al. — OpenHands: An Open Platform for AI Software Developers](https://arxiv.org/abs/2407.16741)——CodeAct 架构与事件流设计。
- [Epoch AI — SWE-bench leaderboard](https://epoch.ai/benchmarks)——实时追踪的分数。
- [Anthropic — Measuring agent autonomy](https://www.anthropic.com/research/measuring-agent-autonomy)——长程 coding-agent 可靠性的框定。
