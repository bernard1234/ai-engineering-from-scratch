# 基准测试：SWE-bench、GAIA、AgentBench

> 2026 年有三套基准测试锚定 agent 评测。SWE-bench 测试代码补丁。GAIA 测试通用工具使用。AgentBench 测试多环境推理。要了解它们的构成、它们的污染问题，以及它们没有衡量什么。

**Type:** Learn
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 06 (Tool Use)
**Time:** ~60 minutes

## 学习目标

- 说出 SWE-bench 的测试 harness（FAIL_TO_PASS），并解释为什么它以单元测试为门槛。
- 解释 SWE-bench Verified（OpenAI，500 个任务）为什么存在，以及它移除了什么。
- 描述 GAIA 的设计：对人类简单、对 AI 困难；三个难度等级。
- 说出 AgentBench 的八个环境，以及它对开源 LLM 的主要阻碍。
- 总结 SWE-bench+ 的污染发现及其影响。

## 问题

排行榜告诉你哪个模型在某个基准测试上获胜。它不会告诉你：

- 这个基准测试是否被污染（解决方案出现在训练数据中、测试集泄露）。
- 这个基准测试衡量的是否是你关心的东西（代码 vs 浏览 vs 通用能力）。
- 评测器是否稳健（AST 匹配、状态检查、人工复核）。

在你引用某个数字之前，先了解这三套锚定基准测试及其失败模式。

## 概念

### SWE-bench（Jimenez 等人，ICLR 2024 oral）

- 来自 12 个热门 Python 仓库的 2,294 个真实 GitHub issue。
- Agent 得到：修复前 commit 的代码库 + 自然语言的 issue 描述。
- Agent 产出：一个补丁。
- 评测器：应用补丁，运行仓库的测试套件。补丁必须把 FAIL_TO_PASS 测试翻转（之前失败、现在通过），同时不破坏 PASS_TO_PASS 测试。

SWE-agent（Yang 等人，2024）在发布时达到 12.5%，它强调的是 agent-computer 接口（文件编辑器命令、模型能理解的搜索语法）。

### SWE-bench Verified

OpenAI，2024 年 8 月。人工筛选的 500 任务子集。移除了歧义的 issue、不可靠的测试，以及修复方案不明确的任务。是「你的 agent 能否交付真实补丁？」的主要基准。

### 污染

- 超过 94% 的 SWE-bench issue 早于大多数模型的训练截止时间。
- **SWE-bench+** 发现：32.67% 的成功补丁在 issue 文本中泄露了解决方案（模型在描述中看到了修复），另有 31.08% 因测试覆盖薄弱而可疑。
- Verified 更干净，但并非完全没有污染。

实际含义：一个在 SWE-bench 上得分 50% 的模型，在 SWE-bench+ 上可能只得 35%。如果你声称 SWE-bench 表现，请始终同时报告两者。

### GAIA（Mialon 等人，2023 年 11 月）

- 466 个问题；其中 300 个保留用于 huggingface.co/gaia-benchmark 的私有排行榜。
- 设计理念：「对人类在概念上简单（92%），但对 AI 困难（带插件的 GPT-4：15%）。」
- 测试推理、多模态、网页、工具使用。
- 三个难度等级；Level 3 需要跨模态的长工具链。

GAIA 是你要衡量「通用能力」时运行的基准。不要把它与代码专用基准混淆。

### AgentBench（Liu 等人，ICLR 2024）

- 跨代码（Bash、DB、KG）、游戏（Alfworld、LTP）、网页（WebShop、Mind2Web）和开放式生成的 8 个环境。
- 多轮，每个切分约 4k–13k 轮。
- 主要发现：长期推理、决策制定和指令遵循是开源 LLM 追赶商业模型的主要阻碍。

### 这些基准没有衡量什么

- 真实世界的运营成本（token、墙钟时间）。
- 对抗性条件下的安全行为。
- 在你所在领域的表现（用你自己的 evals，第 30 课）。
- 尾部失败（基准测试取平均值；生产运维关心的是最差的 1%）。

### 基准测试在哪里会出错

- **单一数字执念。** SWE-bench 50% 告诉你的事，不如 P50/P75/P95 的成本 + 步数分布多。
- **污染声明。** 报告 SWE-bench 却不提 Verified 或 SWE-bench+ 是具有误导性的。
- **把基准当开发目标。** 针对基准优化会偏离生产实用性。

```figure
ae-swebench-gate
```

## Build It

`code/main.py` 实现了一个玩具级的 SWE-bench 风格 harness：

- 合成的 bug 修复任务（3 个任务）。
- 一个脚本化的「agent」，负责提出补丁。
- 一个测试运行器，检查 FAIL_TO_PASS（bug 现已修复）和 PASS_TO_PASS（没有任何东西被破坏）。
- 一个基于问题分解深度的 GAIA 风格难度分类器。

运行它：

```
python3 code/main.py
```

输出展示每个任务 + 每个难度的解决率，并让评测器规则变得具体。

## Use It

- 代码 agent 用 **SWE-bench Verified**。始终报告 Verified 分数。
- 通用 agent 用 **GAIA**。使用私有排行榜切分。
- 多环境对比用 **AgentBench**。
- 你产品的实际形态用**自定义 evals**（第 30 课）。

## Ship It

`outputs/skill-benchmark-harness.md` 为任意「代码库-任务」对构建一个 SWE-bench 风格的 harness，带 FAIL_TO_PASS / PASS_TO_PASS 门槛。

## 练习

1. 把这个玩具 harness 移植到一个真实仓库上运行（选一个你自己的）。为已知 bug 写 3 个 FAIL_TO_PASS 测试。
2. 增加一个步数指标。在你的 3 个任务上，每个解决需要多少 agent 步数？
3. 阅读 SWE-bench+ 论文。实现一个解决方案泄露检查（把 issue 文本与 diff 做模式匹配）。
4. 从公开切分下载一道 GAIA 题目。追踪一个 GPT-4 级 agent 会做什么。它需要哪些工具？
5. 阅读 AgentBench 的逐环境分解。哪个环境对应你的产品界面？那里的「SOTA」是什么样的？

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| SWE-bench | 「代码 agent 基准」 | 2,294 个 GitHub issue；补丁必须翻转 FAIL_TO_PASS 测试 |
| SWE-bench Verified | 「干净的 SWE-bench」 | 500 个人工筛选的任务，OpenAI |
| FAIL_TO_PASS | 「修复门槛」 | 之前失败的测试，补丁后必须通过 |
| PASS_TO_PASS | 「无回归门槛」 | 之前通过的测试，之后仍必须通过 |
| GAIA | 「通用基准」 | 466 道人类易解 / AI 难解的多工具问题 |
| AgentBench | 「多环境基准」 | 8 个环境；长时程多轮 |
| Contamination | 「训练集泄露」 | 基准任务出现在模型训练中 |
| SWE-bench+ | 「污染审计」 | 在成功的 SWE-bench 补丁中发现 32.67% 的解决方案泄露 |

## 延伸阅读

- [Jimenez 等人，SWE-bench（arXiv:2310.06770）](https://arxiv.org/abs/2310.06770) —— 原始基准
- [OpenAI，SWE-bench Verified](https://openai.com/index/introducing-swe-bench-verified/) —— 人工筛选子集
- [Mialon 等人，GAIA（arXiv:2311.12983）](https://arxiv.org/abs/2311.12983) —— 通用基准
- [Liu 等人，AgentBench（arXiv:2308.03688）](https://arxiv.org/abs/2308.03688) —— 多环境套件
