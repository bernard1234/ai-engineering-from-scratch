# A/B 测试 LLM 功能——GrowthBook、Statsig 与“感觉还行”的问题

> 传统 A/B 测试并非为非确定性的 LLM 而设计。关键区别：eval 回答“模型能不能干这活？”A/B 测试回答“用户在意吗？”两者都必需；靠 vibe check 上线已经结束了。2026 年该测什么：prompt engineering（措辞）、model selection（GPT-4 vs GPT-3.5 vs OSS；准确率 vs 成本 vs 延迟）、generation parameters（temperature、top-p）。真实案例：某 chatbot 的 reward model 变体带来 +70% 对话长度和 +30% 留存；Nextdoor AI 的主题行实验在 reward function 精调后带来 +1% CTR；Khan Academy 的 Khanmigo 在延迟与数学准确率之间迭代权衡。平台格局：**Statsig**（2025 年 9 月被 OpenAI 以 $1.1B 收购）——sequential testing、CUPED、一体化。**GrowthBook**——开源、warehouse-native、Bayesian + Frequentist + Sequential 引擎、CUPED、SRM 检查、Benjamini-Hochberg + Bonferroni 校正。你依据 warehouse-SQL 偏好，以及“被 OpenAI 收购”对你的组织是否重要来做选择。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级 sequential test 模拟器)
**Prerequisites:** 第 17 阶段，第 13 课（Observability）、第 20 课（Progressive Deployment）
**Time:** ~60 分钟

## Learning Objectives

- 区分 eval（“模型能不能干这活”）与 A/B 测试（“用户在意吗”）。
- 列举三个可测轴（prompt、model、参数），并为每个轴挑选指标。
- 解释 CUPED、sequential testing 和 Benjamini-Hochberg 多重比较校正。
- 依据 warehouse-SQL 姿态和对公司收购的立场，选择 Statsig 或 GrowthBook。

## 问题场景

你手工调了一个 system prompt。感觉更好了。你上线了。转化率的变化却落在噪声里。你怪指标。或者你上线了新模型，转化率却没动——是模型退化了，还是变化太小检测不到？你不知道，因为你没做 A/B 就上线了。

eval 回答的是模型能否在一个带标签的集合上完成某项任务。它们不回答用户是否更喜欢输出。只有受控的在线实验能回答这个问题，而且前提是实验有足够的 power、能控制 non-determinism、并对多重比较做了校正。

## 核心概念

### Eval 与 A/B 测试

**Evals**——离线、带标签的集合、评判者（rubric、LLM-as-judge 或人工）。回答：“在这个固定分布上，输出是否正确 / 有用 / 安全？”

**A/B 测试**——在线、真实用户、随机化。回答：“新变体是否推动了对用户有意义的指标？”

两者都必需。eval 在暴露前抓住回归；A/B 在之后确认产品影响。

### 该测什么

1. **Prompt engineering**——措辞、system-prompt 结构、示例。指标：任务成功率、用户留存、cost/request。
2. **Model selection**——GPT-4 vs GPT-3.5-Turbo vs Llama-OSS。指标：准确率（任务）+ cost/request + latency P99。多目标。
3. **Generation parameters**——temperature、top-p、max_tokens。指标：任务相关（输出多样性 vs 确定性）。

### CUPED——方差缩减

Controlled-experiments Using Pre-Experiment Data。在比较后期之前先回归掉前期的方差。典型方差缩减：30-70%。有效样本量免费提升。

实现：Statsig 和 GrowthBook 都实现了。

### Sequential testing

经典 A/B 假设固定样本量。sequential 检验（“看一眼就决定”）在反复查看下控制假阳性率。always-valid 的 sequential 过程（mSPRT、Howard 的 confidence sequences）让你在胜负已分时提前停止。

### 多重比较校正

在 95% 置信度下跑 20 个 A/B 测试，纯凭运气就会产生一个假阳性。Bonferroni 校正收紧每个测试的 α；Benjamini-Hochberg 控制 false-discovery rate。GrowthBook 两者都实现。

### SRM——样本比例不匹配

分配哈希把用户随机到各个变体。如果 50/50 的切分实际给出 47/53，说明某处坏了——SRM 检查会标记它。两个平台都实现了。

### Statsig vs GrowthBook

**Statsig**：
- 2025 年 9 月被 OpenAI 以 $1.1B 收购。托管 SaaS。
- Sequential testing、CUPED、held-out 人群。
- 一体化：feature flags + 实验 + observability。
- 最适合：团队本来就想要一个打包产品，不在意 OpenAI 的所有权。

**GrowthBook**：
- 开源（MIT）；warehouse-native（直接从 Snowflake/BigQuery/Redshift 读取）。
- 多种引擎：Bayesian、Frequentist、Sequential。
- CUPED、SRM、Bonferroni、BH 校正。
- self-host 或托管云。
- 最适合：warehouse-SQL 型团队，数据团队掌控指标层，偏好 OSS。

### Non-determinism 让 power 计算变复杂

同一个 prompt 会产出不同输出。传统 power 计算假设观测独立同分布。在 LLM 的 non-determinism 下，有效样本量低于名义值。把所需样本量乘以约 1.3-1.5 倍作为安全余量。

### 真实案例结果

- Chatbot 的 reward model 变体：+70% 对话长度，+30% 留存。
- Nextdoor 主题行：reward function 精调后 +1% CTR。
- Khan Academy Khanmigo：在延迟与数学准确率之间迭代权衡。

### 反模式：靠 vibe 上线

每个资深工程师都能举出一个“感觉更好”就上线、根本没过 A/B 的功能。其中大多数让产品指标回归，而团队几个月都没察觉。A/B 是那根强制线。

### 你应该记住的数字

- Statsig 被 OpenAI 收购：$1.1B，2025 年 9 月。
- GrowthBook：MIT 开源；Bayesian + Frequentist + Sequential。
- CUPED 方差缩减：30-70%。
- LLM non-determinism → 样本量增加 30-50% 缓冲。

```figure
mx-sequential-test
```

## Use It

`code/main.py` 模拟一个带固定边界与 sequential 边界的 sequential A/B 测试。展示 sequential 如何让你提前停止。

## Ship It

本课产出 `outputs/skill-ab-plan.md`。给定功能变更、负载、基线，选择平台、gate 与样本量。

## Exercises

1. 运行 `code/main.py`。若期望提升 5%、基线转化 3%，要达到 80% power 需要多大样本量？
2. 为一家医疗监管的 on-prem 客户在 Statsig 与 GrowthBook 之间做选择。
3. 设计一个 A/B，测试 GPT-4 vs GPT-3.5 在每解决工单成本上的表现。主指标、护栏指标、次要指标各是什么？
4. 你的 canary 通过了，但 A/B 显示转化 -1.2%。你上线吗？写出升级标准。
5. 对前期方差为后期 60% 的数据应用 CUPED。计算有效样本量的提升。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Eval | “离线测试” | 对模型能力的带标签集合评估 |
| A/B test | “实验” | 在用户上做真实随机对比 |
| CUPED | “方差缩减” | 用前期回归降低方差 |
| Sequential test | “可偷看的测试” | 允许提前停止的 always-valid 过程 |
| Multiple comparison | “家族错误” | 跑很多测试会抬高假阳性 |
| Bonferroni | “紧校正” | 把 α 除以测试数量 |
| Benjamini-Hochberg | “BH FDR” | 控制 false-discovery rate，不那么保守 |
| SRM | “切分坏了” | 样本比例不匹配；分配 bug |
| Statsig | “OpenAI 旗下” | 商业一体化平台，2025 年被收购 |
| GrowthBook | “那个 OSS 的” | MIT、warehouse-native 平台 |
| mSPRT | “sequential 概率比检验” | 经典的 sequential 过程 |

## Further Reading

- [GrowthBook — How to A/B Test AI](https://blog.growthbook.io/how-to-a-b-test-ai-a-practical-guide/)
- [Statsig — Beyond Prompts: Data-Driven LLM Optimization](https://www.statsig.com/blog/llm-optimization-online-experimentation)
- [Statsig vs GrowthBook comparison](https://www.statsig.com/perspectives/ab-testing-feature-flags-comparison-tools)
- [Deng et al. — CUPED](https://www.exp-platform.com/Documents/2013-02-CUPED-ImprovingSensitivityOfControlledExperiments.pdf)
- [Howard — Confidence Sequences](https://arxiv.org/abs/1810.08240)
