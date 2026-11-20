# 评估与协调 Benchmark

> 五个 2025-2026 年的 benchmark 覆盖了多 agent 评估空间。**MultiAgentBench / MARBLE**（ACL 2025，arXiv:2503.01935）用里程碑 KPI 评估 star/chain/tree/graph 拓扑；**graph 在研究中表现最佳**，认知规划带来约 3% 的里程碑达成提升。**COMMA** 评估多模态、信息不对称的协调；包括 GPT-4o 在内的最先进模型也难以击败随机基线。**MedAgentBoard**（arXiv:2505.12371）覆盖四类医疗任务，常常发现多 agent 并不优于单 LLM。**AgentArch**（arXiv:2509.10769）对企业 agent 架构做 benchmark，考察 tool 使用 + 记忆 + 编排的组合。**SWE-bench Pro**（[arXiv:2509.16941](https://arxiv.org/abs/2509.16941)）包含跨 41 个仓库的 1865 道题，覆盖商业应用、B2B 服务与开发者工具；前沿模型在 Pro 上约 23%，而在 Verified 上 70%+ —— 这是对污染问题的一次现实检验。据报道 Claude Opus 4.7（2026 年 4 月）在 Pro 上借助显式 agent-teams 协调达到 **64.3%**（尚无 Anthropic 一手来源发布 —— 视为初步结果）；Verdent（agent scaffold）在 Verified 上达到 **76.1% pass@1**（[Verdent 技术报告](https://www.verdent.ai/blog/swe-bench-verified-technical-report)）。**AAAI 2026 Bridge Program WMAC**（https://multiagents.org/2026/）是 2026 年的社区焦点。本课基于 MARBLE 的指标，跑一遍拓扑-指标的扫描，并钉死"仅通过 SWE-bench Verified 并不等于泛化证据"这一规则。

**Type:** Learn
**Languages:** Python (stdlib)
**Prerequisites:** 第 16 阶段，第 15 课（Voting and Debate Topology）、第 23 课（Failure Modes）
**Time:** ~75 分钟

## 问题场景

当一篇论文声称"我们的多 agent 系统更好"时，问题是：比什么更好、在什么上更好、怎么衡量的？2023-2024 年的多 agent 评估是一片混乱 —— 每个人自选指标、自选基线、自选任务集。2025-2026 年的 benchmark 把它规范起来了。

没有共享 benchmark，你无法有意义地比较两个多 agent 系统。更糟的是，没有留出 benchmark，前沿模型会遭到污染。到 2025 年年中，SWE-bench Verified 已在训练语料中部分被污染；前沿模型分数虚高；Pro 被设计成未被污染的现实检验。

本课列举 2026 年的五个正典 benchmark，说明各自衡量什么，并教你带着怀疑去读 benchmark 声明。

## 核心概念

### MultiAgentBench（MARBLE）—— ACL 2025

arXiv:2503.01935。在研究、编码与规划任务上评估四种协调拓扑（star、chain、tree、graph）。基于里程碑的 KPI 追踪部分进展，而不仅看最终成功。

测得的结果：

- 研究场景中 **graph** 拓扑最佳；支持 any-to-any 互评。
- 逐步精炼的编码任务中 **chain** 最佳。
- 快速事实整合中 **star** 最佳。
- 在 graph 上超过约 4 个 agent 后出现**协调税**。
- **认知规划**在各拓扑上带来约 3% 的里程碑达成提升。

何时用：你想在同一口径下比较协调拓扑。MARBLE 仓库（https://github.com/ulab-uiuc/MARBLE）提供了评估器。

### COMMA —— 多模态信息不对称

覆盖 agent 拥有不同观察模态、必须在信息不完全共享的情况下协调的任务。报告结果令人不安：包括 GPT-4o 在内的前沿模型，在 COMMA 的 agent-agent 协作上难以击败**随机基线**。信号是：多 agent 多模态能力训练不足、评估不足 —— LLM 处理单模态协作尚可；多模态协调则崩塌。

何时用：你的系统涉及多模态或信息不对称的协调。COMMA 的零结果是对"先测量再宣称"的警告。

### MedAgentBoard —— 领域压力测试

arXiv:2505.12371。四类医疗任务：诊断、治疗方案规划、报告生成、患者沟通。比较 multi-agent 与 single-LLM 与传统规则系统。

发现：在多数类别上多 agent **并不**优于 single-LLM。多 agent 的优势很窄 —— 当子任务清晰可分离时（诊断 + 治疗）任务分解有帮助；当协调开销超过专业化收益时（报告生成）反而有害。

何时用：你的领域有清晰的 single-LLM 基线。如果 MedAgentBoard 的教训可推广，许多提出的多 agent 系统都属过度设计。

### AgentArch —— 企业架构

arXiv:2509.10769。企业场景中把 tool 使用、记忆与编排叠在一起。Benchmark 隔离每一层的贡献：加 tool 有多大帮助？加记忆？加多 agent 编排？

何时用：你在设计企业 agent 栈，需要为每一层正名。AgentArch 帮你避免为无法衡量价值的功能买单。

### SWE-bench Pro —— 现实检验

arXiv:2509.16941。跨 41 个仓库的 1865 道题，覆盖商业应用、B2B 服务与开发者工具。设计上**未被污染**，晚于训练截止。前沿模型在 Pro 上约 23%，而在 Verified 上 70%+。这个差距就是污染信号。

2026 年 4 月的分数：
- Claude Opus 4.7 在 Pro 上：**64.3%**（据报道配合显式 agent-teams 协调；尚无 Anthropic 一手来源发布 —— 视为初步结果）。
- Verdent（agent scaffold）在 Verified 上：**76.1% pass@1**（[技术报告](https://www.verdent.ai/blog/swe-bench-verified-technical-report)）。
- 无 agent scaffolding 的前沿模型 Pro 原始分数：约 23-35%（[SWE-bench Pro 论文](https://arxiv.org/abs/2509.16941)）。

要点："我们超过了 SWE-bench Verified"不再构成能力证据。Pro 才是当前的门槛测试。Agent-team scaffolding 在 Pro 上带来可测的增益（约 30-40 个百分点），这是 2026 年支持多 agent 协调最有力的经验论据之一。

### AAAI 2026 WMAC

AAAI 2026 Bridge Program —— Workshop on Multi-Agent Coordination（https://multiagents.org/2026/）。2026 年多 agent AI 研究的社区焦点。录用论文与 workshop 论文集是评估新方法的正典场合；生产决策应优先采信 WMAC 录用的结论，而非 arXiv 预印本。

### 批判性地读 benchmark 声明 —— 2026 检查清单

当有人宣称某个多 agent 结果时：

1. **哪个 benchmark，哪个 split？** SWE-bench Verified 与 Pro 差别巨大。报在错误 split 上的数字毫无价值。
2. **污染检查。** Benchmark 是否在该模型训练截止之后发布？若不是，谨慎对待。
3. **基线对比。** 对比 single-LLM 基线、对比随机、对比既有 multi-agent 工作。而不是"对比同系统的未调优版"。
4. **统计显著性。** N 次试验、p 值、置信区间。前沿模型方差大；单次运行会误导。
5. **任务多样性。** 一个任务还是多个？泛化对生产很重要。
6. **成本披露。** 每任务 token 数、墙钟时间。20 倍成本换 90% 的解法是商业决策，不是能力声明。

### 所有 benchmark 都测不好的方面

- **长时程协调。** 持续数天的墙钟交互。当前所有 benchmark 都跑得短。
- **对抗韧性。** 当一个 agent 恶意或被攻陷时会发生什么？
- **部署中的漂移。** Benchmark 是静态的；生产分布会移动。
- **成本归一化性能。** 多数 benchmark 报原始准确率，而非每美元准确率。

为你真正在意的那条轴自建内部 benchmark，往往才是正解。

```figure
a5-bench-gap
```

## Build It

`code/main.py` 是一个非交互式演练：

- 在一个玩具任务上模拟 3 个多 agent 系统。
- 为每个系统计算 MARBLE 风格的里程碑指标。
- 通过从"训练"集中扣留任务来跑污染检查。
- 显式与随机基线对比。
- 打印 benchmark 声明记分卡。

运行：

```bash
python3 code/main.py
```

预期输出：系统记分卡，含原始准确率、里程碑达成、每任务成本、相对随机基线的差值，以及污染检查备注。

## Use It

`outputs/skill-benchmark-reader.md` 读取任何多 agent benchmark 声明并套用审视清单。输出：一个等级与注意事项。

## Ship It

生产评估纪律：

- **自建内部 benchmark**，反映你真实的生产分布。公开 benchmark 有参考价值，但不能替代。
- **每次比较都带随机基线。** 若你在协调任务上无法大幅超越随机，这个任务可能是提法有问题。
- **准确率与成本并列报告。** token 成本与墙钟时间。运维团队两者都需要。
- **每季度重建 benchmark。** 生产分布会移动；过时的 benchmark 会误导。
- **避免对公开 benchmark 过拟合。** 若你的团队专门针对 SWE-bench Pro 的数字优化，生产上就会退步。

## Exercises

1. 运行 `code/main.py`。指出三个模拟系统中哪个每里程碑成本最优。它是否与原始准确率最高的系统一致？
2. 读 MultiAgentBench（arXiv:2503.01935）。针对你自己的任务域，判断 MARBLE 会推荐四种拓扑中的哪一种。用论文结果论证。
3. 读 SWE-bench Pro 论文。具体是什么让它抗污染？同样的技术能否用于你在意的其他 benchmark？
4. 读 COMMA 关于多模态协调的发现。设计一个可加入内部 benchmark 的简单多模态协调任务。什么才算有用信号？
5. 对一篇近期多 agent 论文的头条结果套用 benchmark 声明检查清单。你会给这个声明什么等级？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| MARBLE | "MultiAgentBench" | ACL 2025；star/chain/tree/graph 拓扑 + 里程碑 KPI。 |
| COMMA | "多模态 benchmark" | 多模态信息不对称协调；前沿模型难以击败随机。 |
| MedAgentBoard | "领域压力测试" | 四类医疗任务；常常发现多 agent 不优于 single-LLM。 |
| AgentArch | "企业 benchmark" | tool + 记忆 + 编排的叠加。 |
| SWE-bench Pro | "抗污染" | 1865 道题、41 个仓库；约 23% vs Verified 的 70%+（这就是污染信号）。 |
| Milestone achievement | "部分得分" | 奖励进展而非只看最终成功的 benchmark。 |
| Contamination | "benchmark 泄漏进训练" | 发布后，benchmark 逐渐进入训练语料；分数虚高。 |
| WMAC | "AAAI 2026 Bridge Program" | Workshop on Multi-Agent Coordination；社区焦点。 |

## Further Reading

- [MultiAgentBench / MARBLE](https://arxiv.org/abs/2503.01935) —— 带里程碑 KPI 的拓扑 benchmark
- [MARBLE 仓库](https://github.com/ulab-uiuc/MARBLE) —— 参考实现
- [MedAgentBoard](https://arxiv.org/abs/2505.12371) —— 领域压力测试；多 agent 常不占优
- [AgentArch](https://arxiv.org/abs/2509.10769) —— 企业 agent 架构
- [SWE-bench 排行榜](https://www.swebench.com/) —— 前沿模型的 Verified 与 Pro 分数
- [AAAI 2026 WMAC](https://multiagents.org/2026/) —— 2026 年的社区焦点
