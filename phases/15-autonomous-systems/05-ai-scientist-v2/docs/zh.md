# AI Scientist v2 — Workshop 级自主研究

> Sakana 的 AI Scientist v2（Yamada et al., arXiv:2504.08066）跑通了完整的研究闭环：假设、代码、实验、图表、写作、投稿。它是首个让生成论文通过 ICLR 2025 workshop 同行评审的系统。独立评估（Beel et al.）发现，42% 的实验因编码错误而失败，文献综述也经常把已有概念误标为新颖。Sakana 自己的文档警告该代码库会执行 LLM 写出的代码，并建议使用 Docker 隔离。这幅图景的两半都是重点。

**Type:** Learn
**Languages:** Python（stdlib，research-loop 状态机玩具）
**Prerequisites:** 第 15 阶段，第 03 课（AlphaEvolve）、第 15 阶段，第 04 课（DGM）
**Time:** ~60 分钟

## 问题场景

研究是一项开放式任务。与 AlphaEvolve 的算法搜索或 DGM 受 benchmark 约束的自我修改不同，研究结果没有机器可校验的正确性标准。论文由审稿人评判，而非单元测试。这让闭环更难合上——但一旦合上就更有价值，因为研究正是复利式进展所在之处。

AI Scientist v1（Sakana, 2024）从人工编写的模板出发来闭合循环。LLM 在固定的 scaffold 内填充实验。AI Scientist v2（Yamada et al., 2025）通过使用带视觉语言模型评审循环的 agentic tree search，移除了对模板的依赖。系统会生成想法、实现实验、产出图表、写出论文，并依据审稿反馈迭代。

同行评审的结论：一篇 v2 生成的论文被 ICLR 2025 workshop 接收（已披露）。独立评估的结论：该系统远未达到可靠。两者都是事实。

## 核心概念

### 架构

1. **想法生成。** LLM 在给定主题与既有文献的条件下提出研究想法。v1 使用模板；v2 在假设空间中做 agentic search。
2. **新颖性检查。** 一个文献检索步骤检查该想法是否已发表。正是在这一步，Beel et al. 的评估发现了误标——已有方法经常被归为新颖。
3. **实验计划。** agent 起草实验方案并编写代码。
4. **执行。** 代码在 sandbox 中运行。失败会被反馈进重试循环。在 Beel et al. 的测量中，42% 的实验在这一阶段因编码错误而失败。
5. **图表生成。** 视觉语言模型读取生成的图表，并为清晰度重写它们。这是 v2 的关键技术新增。
6. **写作。** LLM 起草论文，并与内部审稿人迭代。
7. **可选：投稿。** 论文被投往某个会议或期刊。

### workshop 接收结果意味着什么

一篇 v2 生成的论文在 ICLR 2025 workshop 上通过了同行评审。作者向程序委员会披露了论文的来源。这次接收只是一个数据点；它不是宣称该系统“在做研究”的许可。

重要背景：workshop 论文的门槛低于主会论文。同行评审本身噪声很大；任何一天都只有一小部分投稿被接收。一次成功是概念验证，不是可靠性主张。Nature 2026 的论文记录了端到端循环，而它本身由人类研究者共同撰写；这不是“系统写出了一篇 Nature 论文”。

### 独立评估发现了什么

Beel et al.（arXiv:2502.14297）做了一次外部评估。主要发现：

- **实验失败。** 42% 的实验因编码错误而失败（错误的 import、形状不匹配、未定义变量）。重试循环接住了一部分，但不是全部。
- **新颖性误标。** 文献检索步骤经常把已有概念标为新概念。这是研究领域的幻觉等价物。
- **呈现质量差距。** 视觉语言图表评审产出了发表级可视化，掩盖了底层的实验弱点。

最后一条发现对本阶段最重要。一个能产出有说服力的输出、却没有做有说服力的研究的系统，比一个明显失败的系统更危险，而不是更安全。eval 必须触及底层主张，而不能停在图表上。

### sandbox 逃逸的担忧

Sakana 自己的仓库 README 警告：

> 由于本软件的性质——它会执行 LLM 生成的代码——我们无法保证安全性。存在危险软件包、不受控的网络访问以及意外派生进程的风险。使用风险自负，并请考虑 Docker 隔离。

这就是在未验证领域中自主性的运行形态。LLM 写代码；代码运行；代码可以做进程被允许做的任何事。如果没有一个硬性限制文件系统、网络与进程动作的 sandbox，任何自主导向的研究 agent 都可能外泄数据、烧掉算力或重写自身。

AlphaEvolve 的 sandbox 故事更容易，因为它的 evaluator 很紧。AI Scientist v2 的循环则用开放式目标运行开放式代码。这就是为什么它需要更强的隔离（最低 Docker；首选 seccomp / gVisor），以及每一次投稿在离开系统前的人工审查。

### v2 在前沿栈中的位置

| 系统 | 目标 | 输出类型 | Evaluator | 已知失败 |
|---|---|---|---|---|
| AlphaEvolve | 算法 | 代码 | 单元测试 + benchmark | 受 evaluator 严格程度限制 |
| DGM | agent scaffold | 代码 | SWE-bench | reward hacking |
| AI Scientist v2 | 研究论文 | 文本 + 代码 + 图表 | 同行评审（弱） | 实验失败、误标、打磨掩盖弱点 |

v2 在三者中拥有最弱的自动 evaluator、最宽的输出面，以及通往公开成果的最短路径。运行层面的控制手段（sandbox、审查、披露）承担了大部分安全工作。

```figure
mx-research-loop
```

## Use It

`code/main.py` 把 v2 循环模拟为一个状态机：想法 → 新颖性检查 → 实验 → 图表 → 写作 → 评审 → 接收或迭代。每个状态都有一个可配置的失败概率，取值来自 Beel et al. 的发现。运行 N 次循环的模拟并统计：

- 有多少想法走到了投稿。
- 有多少投稿会带有打磨后的论文所掩盖的关键实验缺陷。
- 重试预算如何在质量与产量之间权衡。

## Ship It

`outputs/skill-ai-scientist-sandbox-review.md` 是一份双闸门审查清单，适用于研究循环 agent 产出的任何东西在离开 sandbox 之前。

## Exercises

1. 用默认参数运行 `code/main.py`。有多大比例的循环运行产出一篇“干净”的论文？有多大比例产出一篇带有实验失败缺陷、但被图表评审打磨掩盖的论文？

2. 默认值已经使用了 Beel et al. 的 42% / 25%。用 `--experiment-failure 0.20 --novelty-mislabel 0.10` 重新运行，再用 `--experiment-failure 0.60 --novelty-mislabel 0.40` 运行。两次运行之间，“打磨过但有缺陷”的占比如何变化？

3. 阅读 Sakana 的 AI Scientist v2 仓库 README 中关于 sandbox 要求的部分。说出你会为多日自主运行额外施加的两条限制（Docker 之外）。

4. 阅读 Beel et al. 第 4 节关于呈现质量差距的部分。设计一个额外的 evaluator，用来抓住看起来打磨过、但实验上有缺陷的论文。

5. 为一个研究 agent 的输出提出一套人工审查协议，要求它比“一个 PhD 读每一篇论文”更具可扩展性。找出瓶颈并围绕它设计。

## Key Terms

| 术语 | 人们怎么说 | 实际含义 |
|---|---|---|
| AI Scientist v1 | “Sakana 的模板化研究 agent” | 在固定 scaffold 中填充实验 |
| AI Scientist v2 | “无模板研究 agent” | 带 VLM 图表评审的 agentic tree search |
| Agentic tree search | “分支式研究 agent” | 并行扩展多个实验计划；由内部 critic 剪枝 |
| Vision-language critique | “VLM 打磨图表” | 多模态模型读取图表并为其清晰度重写 |
| Literature retrieval | “新颖性检查” | 检索既有工作以确认想法的原创性——已有记录显示会误标 |
| Polish masking | “漂亮论文，破碎研究” | 呈现质量超过实验质量；掩盖弱点 |
| Sandbox escape | “LLM 代码越狱” | agent 执行的代码做了循环设计者无意的事 |

## Further Reading

- [Yamada et al. (2025). The AI Scientist-v2](https://arxiv.org/abs/2504.08066) — 论文。
- [Sakana blog on the Nature 2026 publication](https://sakana.ai/ai-scientist-nature/) — 带同行评审背景的厂商总结。
- [Beel et al. (2025). Independent evaluation of The AI Scientist](https://arxiv.org/abs/2502.14297) — 外部评估数字。
- [Sakana AI Scientist v1 paper](https://arxiv.org/abs/2408.06292) — 模板化的前身。
- [Anthropic — Measuring AI agent autonomy](https://www.anthropic.com/research/measuring-agent-autonomy) — 对开放式研究 agent 的更广阔框架。
