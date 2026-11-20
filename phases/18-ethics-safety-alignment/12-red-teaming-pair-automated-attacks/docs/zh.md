# Red-Teaming：PAIR 与自动化攻击

> Chao、Robey、Dobriban、Hassani、Pappas、Wong（NeurIPS 2023，arXiv:2310.08419）。PAIR——Prompt Automatic Iterative Refinement——是权威的自动化黑盒 jailbreak。一个带红队 system prompt 的攻击者 LLM 迭代地为目标 LLM 提出 jailbreak，把尝试与响应累积在自己的对话历史中作为 in-context 反馈。PAIR 通常在 20 次查询内成功，比 GCG（Zou et al. 的 token 级梯度搜索）高效几个数量级，且无需白盒访问。PAIR 如今是 JailbreakBench（arXiv:2404.01318）和 HarmBench 中的标准基线，与 GCG、AutoDAN、TAP 和 Persuasive Adversarial Prompt 并列。

**Type:** Build
**Languages:** Python (stdlib, 针对玩具目标模型的 mock PAIR 循环)
**Prerequisites:** 第 18 阶段，第 01 课（instruction-following），第 14 阶段（agent engineering）
**Time:** ~75 分钟

## Learning Objectives

- 描述 PAIR 算法：攻击者 system prompt、迭代细化、in-context 反馈。
- 解释当目标是黑盒时，为什么 PAIR 严格比 GCG 更高效。
- 说出另外四个自动化攻击基线（GCG、AutoDAN、TAP、PAP），并各举一个区分性特征。
- 描述 JailbreakBench 和 HarmBench 的评估协议，以及在各自之下“attack success rate”意味着什么。

## 问题场景

红队过去是一项人工活动。少数专家测试者构造对抗 prompt 并记录哪些奏效。这无法扩展：attack success rate 需要统计样本，而目标是会随每一次模型发布而移动的移动靶。PAIR 把红队操作化为一个以黑盒为目标的优化问题。

## 核心概念

### PAIR 算法

输入：
- 目标 LLM T（我们正在攻击的模型）。
- 判断 LLM J（给一个响应是否是 jailbreak 打分）。
- 攻击者 LLM A（红队优化器）。
- 目标字符串 G：“以 [有害指令] 作出回应。”
- 预算 K（通常是 20 次查询）。

循环，对 k 从 1 到 K：
1. 向 A 提供目标 G 以及迄今的 (prompt, response) 对历史。
2. A 输出一个新的 prompt p_k。
3. 把 p_k 提交给 T；收到响应 r_k。
4. J 就目标给 (p_k, r_k) 打分。
5. 如果分数 >= 阈值，停止——找到 jailbreak。
6. 否则，把 (p_k, r_k) 追加到 A 的历史；继续。

经验结果（NeurIPS 2023）：对 GPT-3.5-turbo、Llama-2-7B-chat 的 attack success rate >50%；平均成功所需查询在 10-20 次区间。

### 为什么 PAIR 高效

GCG（Zou et al. 2023）通过梯度在对抗 token 后缀上搜索；它需要白盒模型访问，并产出不可读的后缀。PAIR 是黑盒的，产出可跨模型迁移的自然语言攻击。PAIR 的 in-context 反馈让攻击者从每一次被拒中学习；GCG 没有对应物（每次新的 token 更新都必须重新发现先前的进展）。

### 相关的自动化攻击

- **GCG（Zou et al. 2023，arXiv:2307.15043）。** 针对对抗后缀的 token 级梯度搜索。白盒、可迁移、产出不可读的字符串。
- **AutoDAN（Liu et al. 2023）。** 在 prompt 上进行进化搜索，由分层目标引导。
- **TAP（Mehrotra et al. 2024）。** 带剪枝的攻击树——把多个 PAIR 式 rollout 分支化。
- **PAP（Zeng et al. 2024）。** Persuasive Adversarial Prompts——把人类说服技巧编码为 prompt 模板。

### JailbreakBench 与 HarmBench

两者（2024）都将评估标准化：

- JailbreakBench（arXiv:2404.01318）。跨 10 个 OpenAI 政策类别的 100 种有害行为。以 attack success rate（ASR）作为主要指标。需要一个判断者（GPT-4-turbo、Llama Guard 或 StrongREJECT）。
- HarmBench（Mazeika et al. 2024）。跨 7 个类别的 510 种行为，含语义与功能性危害测试。比较 18 种攻击对 33 个模型。

ASR 通常在固定的查询预算下报告。比较攻击需要对齐预算；200 次查询下 90% 的 ASR 不能与 20 次查询下 85% 的 ASR 相比。

### 为什么它对 2026 年的部署很重要

如今每一家前沿实验室都会在发布前对生产模型运行 PAIR 和 TAP。ASR 轨迹会出现在模型卡（第 26 课）和安全论证附录（第 18 课）中。这种攻击并不新奇——它是标准基础设施。

### 这在本阶段脉络中的位置

第 12 课是自动化攻击的基础。第 13 课（many-shot jailbreaking）是一种互补的长度利用。第 14 课（ASCII 艺术 / 视觉）是一种编码攻击。第 15 课（indirect prompt injection）是 2026 年的生产攻击面。第 16 课涵盖对应的防御工具（Llama Guard、Garak、PyRIT）。

```figure
al-pair-loop
```

## Use It

`code/main.py` 构建一个玩具级的 PAIR 循环。目标是一个 mock 分类器，拒绝“明显的”有害 prompt（关键词过滤）。攻击者是一个基于规则的细化器，尝试改写、角色扮演框架和编码。判断者给响应打分。你会看到攻击者在约 5-15 次迭代内攻破关键词过滤器，而在语义过滤器上失败。

## Ship It

本课产出 `outputs/skill-attack-audit.md`。给定一份红队评估报告，它审计：运行了哪些攻击（PAIR、GCG、TAP、AutoDAN、PAP），每次调用各自的预算，使用哪个判断者，在哪个有害行为集上（JailbreakBench、HarmBench、内部）。

## Exercises

1. 运行 `code/main.py`。测量三种内置攻击策略的平均成功所需查询数。解释每种策略利用了目标防御的哪个假设。

2. 实现第四种攻击策略（例如翻译成另一种语言、base64 编码）。报告对关键词过滤目标和语义过滤目标的新平均成功查询数。

3. 阅读 Chao et al. 2023 图 5（PAIR 与 GCG 对比）。描述两个尽管 PAIR 有高效优势、仍更偏好 GCG 的场景。

4. JailbreakBench 报告针对固定目标集的 ASR。设计一个衡量攻击多样性（成功 prompt 的方差）的额外指标。解释为什么多样性对防御评估很重要。

5. TAP（Mehrotra 2024）以分支 + 剪枝扩展 PAIR。勾画一个对 `code/main.py` 的 TAP 式扩展，并描述算力成本与成功率之间的权衡。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| PAIR | “自动化 jailbreak” | Prompt Automatic Iterative Refinement；攻击者 LLM + 判断 LLM 的循环 |
| GCG | “梯度 jailbreak” | 针对对抗后缀的白盒 token 级梯度搜索 |
| Attack success rate (ASR) | “k 次查询下的破防率” | 主要指标；必须连同查询预算与判断者身份一起报告 |
| Judge LLM | “打分器” | 给一个响应是否满足有害目标打分的 LLM |
| JailbreakBench | “那套评估” | 带类别标签的标准化有害行为集 |
| HarmBench | “更广的那套 bench” | 510 种行为，功能 + 语义危害测试 |
| TAP | “攻击树” | 带分支 + 剪枝的 PAIR；更高算力下更高的 ASR |

## Further Reading

- [Chao et al. — Jailbreaking Black Box LLMs in Twenty Queries (arXiv:2310.08419)](https://arxiv.org/abs/2310.08419) — PAIR 论文，NeurIPS 2023
- [Zou et al. — Universal and Transferable Adversarial Attacks on Aligned LLMs (arXiv:2307.15043)](https://arxiv.org/abs/2307.15043) — GCG 论文
- [Chao et al. — JailbreakBench (arXiv:2404.01318)](https://arxiv.org/abs/2404.01318) — 标准化评估
- [Mazeika et al. — HarmBench (ICML 2024)](https://arxiv.org/abs/2402.04249) — 更广的评估
