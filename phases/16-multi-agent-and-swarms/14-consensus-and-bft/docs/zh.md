# 面向 Agent 的 Consensus 与 Byzantine Fault Tolerance

> 经典分布式系统的 BFT 遇上随机性的 LLM。2025-2026 年出现了三个研究方向：**CP-WBFT**（arXiv:2511.10400）用 confidence probe 为每一票加权；**DecentLLMs**（arXiv:2507.14928）去掉 leader，采用并行 worker 提案与几何中位数聚合；**WBFT**（arXiv:2505.05103）把加权投票与 Hierarchical Structure Clustering 结合起来，将节点划分为 Core 与 Edge。来自 "Can AI Agents Agree?"（arXiv:2603.01213）的诚实实证结果是：即便在标量上达成一致，在今天也很脆弱 —— 单个欺骗性 agent 就能劫持一个 Mixture-of-Agents。BFT 是必要的，但不充分。本课构建一个最小 BFT 协议，注入三种 agent 特有的攻击（byzantine 谎言、谄媚式从众、相关错误单一栽培），并度量每种 consensus 变体如何应对。

**Type:** Learn + Build
**Languages:** Python（stdlib）
**Prerequisites:** 第 16 阶段，第 07 课（Society of Mind and Debate）、第 13 课（Shared Memory）
**Time:** ~75 分钟

## 问题场景

你有 N 个 LLM agent，各自给出一个答案。它们意见不一。多数投票选错了，因为其中两个 agent 是相关的（同一底座模型、同一训练数据、同一失败模式）。第三个 agent 恰好以一种新奇的方式出错 —— 于是多数只是一个虚假的多数。

现在加入一个欺骗性 agent：它故意撒谎。或者一个谄媚的 agent：谁最后发言它就同意谁。在经典 BFT 中，假设拜占庭（Byzantine）节点占一个比例 `f < n/3`，且行为任意。2026 年的现实是：LLM 节点即便诚实也是随机性的，跨模型相关，并且会受彼此输出的影响。你不能把它们当作独立的伯努利投票者。

经典 BFT（PBFT，1999）并不错误 —— 而是不完整。它能处理任意的比特翻转。它处理不了"三个诚实 agent 因为共享训练数据而共享同一个幻觉"。本课从 PBFT 的基础出发，叠加三种 2025-2026 年的适配。

## 核心概念

### 经典 BFT 提供了什么

Practical Byzantine Fault Tolerance（Castro & Liskov，OSDI 1999）可容忍 `f < n/3` 个拜占庭节点。该协议有三个阶段（pre-prepare、prepare、commit）和两个原语（签名消息、quorum 证书）。在 `n >= 3f + 1` 个诚实或恶意节点间就单个值达成一致。

其保证很强，但假设：

1. **故障相互独立。** 拜占庭节点不会协同。
2. **诚实节点真的诚实。** 诚实输出的正确性不是问题；协议只对齐分歧。
3. **问题有 ground truth。** 对一个错误事实的 consensus 依然是 consensus。

LLM agent 违反了全部三条。运行同一底座模型的两个 agent 共享故障。一个"诚实"的 LLM 仍会幻觉。而在模糊问题上，"真相"就是 agent 决定的东西 —— 没有外部 oracle。

### 三种 LLM 特有的攻击

**Byzantine 谎言。** 一个 agent 故意输出错误答案。若 `f < n/3`，经典 BFT 能处理。

**谄媚式从众。** 一个 agent 在投票前读取他人的答案，并与最后发言者对齐。这不是恶意，但与最响亮的声音相关。经典 BFT 无法阻止，因为该 agent 通过了每一项签名检查。

**相关错误单一栽培。** 三个 agent 共享一个底座模型。它们幻觉出同一个错误答案。多数就是错的。经典 BFT 帮不上忙，因为三者"诚实地"达成了一致。

### 2025-2026 年的应对

**CP-WBFT**（arXiv:2511.10400）—— Confidence-Probed Weighted BFT。每个投票者为其答案附带一个 confidence probe（一个自报概率，或一个独立校准模型的预测）。投票权重随置信度缩放。报告称在完全图上带来 +85.71% 的 BFT 提升。缓解对象：谄媚式从众（从众的 agent 对其主动表达的立场往往置信度较低）。

**DecentLLMs**（arXiv:2507.14928）—— 无 leader。worker agent 并行提案，evaluator agent 为提案打分，最终答案是打分位置的几何中位数。在 `f < n/2` 时稳健。缓解对象：Byzantine 谎言与相关错误（几何中位数对离群值稳健，会向密集簇靠拢，而不是向有模型偏置的均值靠拢）。

**WBFT**（arXiv:2505.05103）—— 带 Hierarchical Structure Clustering 的加权 BFT。投票权重由回答质量加一个从历史中学到的信任分来分配。将 agent 聚成 Core 与 Edge；Core agent 必须先达成 consensus，Edge agent 跟随。缓解对象：可扩展性（Core consensus 小而快），并部分缓解单一栽培（可以通过 Core 的选取来保证多样性）。

### 实证："Can AI Agents Agree?"（arXiv:2603.01213）

该论文在多个前沿模型间度量标量一致性（LLM agent 就单个数值达成一致）。其发现令人不安：

- 即便没有对手，LLM agent 在许多 benchmark 的标量问题上分歧率超过 30%。
- 一个采取欺骗性人格的单个 agent，就能把 Mixture-of-Agents 的 consensus 从诚实基线拉偏 40 多个百分点。
- 分歧率与模型多样性相关 —— 异构集成比同构集成分歧更多（好：错误不相关），但漂移也更慢（坏：达成一致的时间更长）。

要点：BFT 给你对齐输出的机制，但它并不告诉你对齐后的输出是否正确。要与验证（第 16 阶段，第 08 课角色专门化）、多样性（第 16 阶段，第 15 课 debate 变体）以及 evaluator agent（第 16 阶段，第 24 课 benchmark）配合使用。

### 核心协议，精简版

面向 LLM agent 的最小 BFT 轮：

```
1. task arrives; each agent i produces answer a_i
2. each agent attaches confidence probe c_i in [0, 1]
3. aggregator collects (a_i, c_i) from all n agents
4. aggregator groups by semantic cluster (equivalent answers)
5. aggregator computes weight for each cluster C:
     w(C) = sum_{i in C} c_i
6. winner = cluster with max weight, if max > threshold * sum(c_i)
   else: retry or escalate
7. minority clusters logged with provenance for post-hoc audit
```

语义聚类这一步是 LLM 特有的变化。两个答案"the study reports 4.2%"与"4.2% improvement"属于同一簇。朴素的字符串相等检查会漏掉这一点。在生产中，使用一个廉价的 embedding 模型或显式的规范化。

### 阈值调优

`threshold` 参数决定何时接受、何时重试。太低：你会接受弱多数。太高：你永远接受不了任何结果。经验范围：`n=5-7` 个 agent 时为 0.5-0.67，`n` 更小时更高。低于阈值时，升级给人类或另一个 agent 集成。

### Consensus 帮不上忙的地方

- **模糊问题。** 若问题没有 ground truth，consensus 就是一种意见。就称之为意见。
- **复合问题。**"写代码并解释它" —— 是两个答案。对每一个独立投票。
- **对抗性多轮。** 若 agent 能观察前几轮并模仿（Du 2023 debate），它们就会不顾真相地开始彼此附和。要限制轮数（通常 2-3 轮）。

```figure
swarm-consensus-wave
```

## Build It

`code/main.py` 实现：

- `AgentVoter` —— 一个带（answer, confidence）的脚本化策略。
- `MajorityVote` —— 经典相对多数。
- `CPWBFT` —— 带语义聚类的置信度加权投票。
- `DecentLLMs` —— 对打分提案做几何中位数聚合。
- `Scenario` —— 在三种攻击模式下运行每个聚合器。

实现的攻击模式：

1. `byzantine`：一个 agent 以高置信度撒谎。
2. `sycophancy`：一个 agent 复制它看到的第一个答案，配以匹配的置信度。
3. `monoculture`：三个 agent 共享一个错误答案（相关错误），置信度中等。

运行：

```
python3 code/main.py
```

预期输出：一张 (attack, aggregator) -> final answer 的表，并高亮正确答案。相对多数在单一栽培场景下失败。CPWBFT 的置信度加权缓解谄媚。当单一栽培少于半数时，DecentLLMs 的几何中位数会向诚实簇靠拢。

## Use It

`outputs/skill-consensus-designer.md` 为一个多 agent 集成设计 consensus 协议：聚类方法、加权、阈值，以及低于阈值轮次的升级策略。

## Ship It

在发布任何 consensus 机制之前：

- **至少用上面三种模式做攻击测试。** 你的协议应当可预测地失败，而不是悄无声息地失败。
- **记录每个少数簇**及其 provenance。少数簇是你对相关错误的预警系统。
- **强制有界轮数。** 不要"一直辩论到达成一致" —— 那会奖励谄媚。
- **把一致性与正确性分开。** Consensus 输出进入 verifier；verifier 独立于该集成。
- **监控一致率。** 急剧上升意味着从众偏置；急剧下降意味着模型漂移。

## Exercises

1. 运行 `code/main.py`。确认相对多数在单一栽培攻击下失败，但当单一栽培的置信度低于 0.7 时，CPWBFT 能部分缓解它。
2. 加入第四种攻击模式：**沉默弃权** —— 一个 agent 拒绝回答（"I don't know"）。每个聚合器应如何处理弃权？实现你的选择。
3. 把语义聚类从字符串规范化换成 embedding 相似度（使用任意开源 embedding 模型）。谄媚攻击会怎样变化？
4. 阅读 CP-WBFT（arXiv:2511.10400）。实现 confidence-probe 校准步骤（一个独立的校准模型检查每个 agent 自报的置信度）。度量在单一栽培场景下的准确率增益。
5. 阅读 "Can AI Agents Agree?"（arXiv:2603.01213）。复现一个简化的标量一致性实验：三个 agent、一个标量问题、欺骗性人格 prompt。CPWBFT 或 DecentLLMs 能抓住它吗？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| BFT | "Byzantine fault tolerance" | Castro-Liskov 1999 协议，在 `f < n/3` 个任意故障下达成 consensus。 |
| Byzantine | "Any bad behavior" | 一个可以撒谎、丢消息、静默失败的节点 —— 除安全崩溃外的任何行为。 |
| Confidence probe | "How sure are you?" | 附加到一票上的、自报或由校准器预测的概率。 |
| Semantic clustering | "Same answer, different words" | 在计票前把等价答案归为一组。 |
| Geometric median | "Robust center" | 使得到样本点距离之和最小的点。与均值不同，它对离群值稳健。 |
| Monoculture | "Same model, same failures" | agent 共享训练数据或底座模型时产生的相关错误。 |
| Sycophantic conformity | "Agreeing with the loud voice" | 一个 agent 的投票偏向最先/最响亮发言者。 |
| Core/Edge | "Hierarchical BFT" | WBFT 的划分：先由小规模的 Core 达成 consensus，Edge 节点跟随。限制了延迟。 |

## Further Reading

- [Castro & Liskov — Practical Byzantine Fault Tolerance (OSDI 1999)](https://pmg.csail.mit.edu/papers/osdi99.pdf) —— 基础
- [CP-WBFT — Confidence-Probe Weighted BFT](https://arxiv.org/abs/2511.10400) —— 按置信度加权投票
- [DecentLLMs — leaderless multi-agent consensus](https://arxiv.org/abs/2507.14928) —— 几何中位数聚合
- [WBFT — Weighted BFT with Hierarchical Structure Clustering](https://arxiv.org/abs/2505.05103) —— Core/Edge 划分以限制延迟
- [Can AI Agents Agree?](https://arxiv.org/abs/2603.01213) —— 标量一致性的脆弱性与欺骗性人格攻击
