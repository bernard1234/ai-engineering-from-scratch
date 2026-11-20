# Agent 经济、Token 激励、声誉

> 长时程自主 agent（METR 的 1 小时到 8 小时工作曲线）需要经济代理能力。新兴的 **5 层堆栈** 是：**DePIN**（物理算力）→ **Identity**（W3C DID + 声誉资本）→ **Cognition**（RAG + MCP）→ **Settlement**（账户抽象）→ **Governance**（Agentic DAO）。生产级的 agent 激励网络包括 **Bittensor**（TAO 子网奖励任务专属模型）、**Fetch.ai / ASI Alliance**（ASI-1 Mini LLM + FET token）和 **Gonka**（基于 transformer 的 PoW，把算力重新分配到有产出的 AI 任务上）。学术工作：AAMAS 2025 的去中心化 LaMAS 使用 **Shapley 值信用归因**来公平奖励有贡献的 agent；Google Research 的“Mechanism design for large language models”提出在单调聚合下的 **token 拍卖**，采用第二价格支付。本课构建一个最小的 agent 市场，把 Shapley 值信用归因应用到一条 multi-agent 流水线，并运行一次第二价格 token 拍卖，让博弈论的机制落地。

**Type:** Learn
**Languages:** Python (stdlib)
**Prerequisites:** 第 16 阶段，第 16 课（Negotiation and Bargaining）、第 09 课（Parallel Swarm Networks）
**Time:** ~75 分钟

## 问题场景

当 agent 共同创造价值、却需要分别获得奖励时，multi-agent 系统就变得复杂。经典机制 —— 平均分配、最后贡献者全拿 —— 要么不公平，要么可被操纵。基于联盟的 Shapley 值奖励在构造上是公平的，但计算代价高昂。2025-2026 年的文献推动了实用的近似方法：Shapley 采样、单调聚合拍卖，以及从已确认贡献中累积的链上声誉。

在信用归因之外，这个领域已转向真正的经济 agent：Bittensor TAO 奖励挖矿算力用于微调子网专属模型，Fetch.ai/ASI 用 FET token 奖励 ASI-1 Mini LLM 的使用，Gonka 把 transformer 的工作量证明重新分配到有产出的 AI 任务上。自主交易的 agent 今天已经存在；问题在于如何对齐激励。

本课把 agent 经济视为一个特定问题族 —— 信用归因、机制设计、声誉 —— 并用最少的数学把每一个搭起来，让思想扎根。

## 核心概念

### 5 层 agent 经济堆栈

1. **DePIN（物理算力）。** 出租 GPU、存储、带宽的去中心化基础设施。Bittensor 子网、Render Network、Akash。并非 agent 专属；agent 使用它。
2. **Identity。** W3C 去中心化标识符（DID）为每个 agent 提供一个独立于任何平台的持久 ID。声誉累积到 DID 上。Agent Network Protocol（ANP）以 DID 作为发现层。
3. **Cognition。** agent 的推理循环：LLM + RAG + MCP。这正是其他阶段所构建的内容。
4. **Settlement。** 账户抽象（ERC-4337）让 agent 无需持有 ETH 就能用自身余额支付 gas。agent 可以付费购买服务、彼此付费，或为算力付费。
5. **Governance。** Agentic DAO：人类 *与* agent 共同对协议变更投票的治理结构，投票权与声誉挂钩。

并非每个生产系统都会用满五层。Bittensor 用到 1、2，部分用到 3、部分用到 4，完全不用 5。OpenAI 的 agent 除 3 之外都不用。这个堆栈是一张参考地图，而不是硬性要求。

### Bittensor、Fetch.ai、Gonka —— 实际运行着什么

**Bittensor（TAO）。** 子网是专门化的任务（语言建模、图像生成、预测）。矿工提交模型输出。验证者对它们排序；按 stake 加权的评分分配 TAO 奖励。每个子网有自己的评估。经济启示：为任务专属的输出质量付费，而不是为消耗的算力付费。

**Fetch.ai / ASI Alliance。** ASI-1 Mini LLM 运行在 Fetch.ai 的网络上；用户用 FET token 支付推理费用。这里“agent 即对等者”的叙事更强：Fetch 上的一个 agent 可以调用另一个来完成一项任务，并用 FET 付款。

**Gonka。** Transformer 工作量证明：“工作”就是 transformer 的前向传播。矿工通过运行已知正确输出（来自训练数据）的推理任务来获利。用有产出的算力型 PoW，而非基于哈希的 PoW。

截至 2026 年 4 月，这三者都是生产级。收益分配方式各不相同。Bittensor 奖励相对于子网验证者的质量；Fetch 奖励由付费用户衡量的效用；Gonka 奖励可验证的推理工作。

### Shapley 值信用归因

三个 agent 协作完成一项任务。输出得分为 0.8。谁贡献了多少？

Shapley 值：满足四条公理（有效性、对称性、线性性、零贡献者）的唯一信用分配。对 agent `i`：

```
shapley(i) = (1/N!) * sum over all orderings O of (v(S_i_O ∪ {i}) - v(S_i_O))
```

其中 `S_i_O` 是在排列 `O` 中位于 `i` 之前的 agent 集合。实践中：枚举所有排列，记录每个 agent 在每个排列中的边际贡献，再取平均。

当 N=3 个 agent 时，共有 6 种排列。当 N=10 时，有 360 万种 —— 所以实践中你会采样排列，而不是枚举。

### 用于聚合的第二价格拍卖

Google Research（“Mechanism design for large language models”）提出用第二价格 token 拍卖来聚合 LLM 输出。设定：N 个 agent 各提出一个补全；每个 agent 对被选中都有一个私有估值。拍卖者挑选价值最高的提案，并支付 *第二高* 的价值。在单调聚合下（价值取决于选中哪个提案，而非有多少个参与竞价），该机制是诚实的 —— agent 会报出真实价值。

这对 LLM 系统为何重要：你可以把补全任务外包给多个定价不同的 agent；拍卖会选出最优者并公平支付，而 agent 没有虚报的动机。

### 声誉资本

绑定 DID 的声誉分数从已确认的贡献中累积。一个简单的更新规则：

```
rep(i, t+1) = alpha * rep(i, t) + (1 - alpha) * contribution_quality(i, t)
```

其中衰减因子 `alpha` 接近 1。声誉：

- 读取成本低，可用于路由决策（“把困难任务发给高声誉 agent”）。
- 伪造成本高（随时间累积，绑定 DID）。
- 可以被罚没：未通过验证的贡献会被扣减。

### AAMAS 2025 去中心化 LaMAS

LaMAS 方案（AAMAS 2025）结合了：DID 身份、Shapley 值信用归因，以及一个简单的拍卖机制。核心主张：把信用归因步骤去中心化，能使系统可审计、且免于单点操纵。

### 经济学在哪里失灵

- **价格 oracle 操纵。** 如果信用函数可以被操纵，agent 就会去操纵它。每个机制都需要对抗测试。
- **Sybil 攻击。** 一个运营者拉起 N 个假 agent 来虚增自己的贡献。DID 只能减缓、不能阻止；伪造声誉的成本是缓解手段。
- **验证成本。** 信用归因的公平程度不超过验证者的公平程度。如果验证很便宜（小 LLM），它可能被操纵；如果很贵（人工小组），系统就无法扩展。
- **监管悬顶。** agent 经济与金融监管相交。截至 2026 年，Bittensor、Fetch 和 Gonka 在某些司法辖区都处于法律灰色地带。

### 何时 agent 经济才有意义

- **由异构运营者组成的开放网络。** 没有单一团队控制所有 agent。
- **可验证的输出。** 没有验证，信用归因只是猜测。
- **长时程工作流。** 一次性任务无法从声誉累积中获益。
- **代币化支付在你的司法辖区合法可行。**

在封闭的企业系统中，经济学让位于更简单的分配（管理者指派工作，指标是内部的）。经济学文献主要适用于开放网络。

```figure
swarm-auction
```

## Build It

`code/main.py` 实现了：

- `shapley(value_fn, agents)` —— 对小规模 N 通过枚举做精确的 Shapley 计算。
- `second_price_auction(bids)` —— 诚实机制；赢家支付第二高价。
- `Reputation` —— 带指数衰减和罚没的 DID 绑定声誉。
- 演示 1：三个 agent 协作，精确 Shapley 归因信用。
- 演示 2：五个 agent 竞价争一个任务槽位；第二价格拍卖选出赢家和支付额。
- 演示 3：100 轮任务分配给声誉各异的 agent；按声誉加权的路由胜过随机路由。

运行：

```
python3 code/main.py
```

预期输出：每个 agent 的 Shapley 值；拍卖结果显示真实报价的均衡；按声誉加权的路由在预热后相比随机路由取得 10-20% 的质量增益。

## Use It

`outputs/skill-economy-designer.md` 设计一个最小的 agent 经济：身份层的选择、信用归因机制、支付机制、声誉规则。

## Ship It

在 2026 年运营一个 agent 经济：

- **从声誉开始，而不是 token。** 声誉实现成本低，且单独就有价值；token 会增加法律和经济上的复杂度。
- **先验证再奖励。** 绝不要在没有独立验证步骤的情况下分配信用。自报质量会招来 Sybil 操纵。
- **用 Shapley 采样，而非精确 Shapley。** 采样 100-1000 个排列；精确枚举无法扩展。
- **给衰减因子设上限、给声誉设下限。** 无界的衰减会抹掉正当贡献者；衰减太慢则会奖励过时的高声誉 agent。
- **以对抗方式审计机制。** 在开放网络之前先跑红队场景。每个机制都有一套博弈论；你要抢在攻击者之前找到漏洞。

## Exercises

1. 运行 `code/main.py`。确认 Shapley 值之和等于总价值（有效性公理）。改变价值函数；Shapley 分配是否朝预期的方向改变？
2. 实现 Shapley *采样*（对 K 个排列做 Monte Carlo）。K 如何影响近似精度？与 N=4 时的精确值比较。
3. 在拍卖前实现一个结盟步骤：agent 可以合并成团队、作为一个单元竞价。会形成哪些联盟？结果是否比各自竞价更符合帕累托改进？
4. 阅读 Google Research 的机制设计文章。找出一个一旦被违反就会破坏诚实性的假设。在 LLM 场景中，这种失效模式看起来是什么样？
5. 阅读 AAMAS 2025 的去中心化 LaMAS 论文。在一个合成任务上对 10 个 agent 实现他们的 Shapley 步骤。精确计算要花多久？用 100 次抽样能逼近到什么程度？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| DePIN | “去中心化物理基础设施” | 以 token 激励的算力/存储/带宽。Bittensor、Akash、Render。 |
| DID | “去中心化标识符” | 便携 ID 的 W3C 规范。agent 声誉绑定到 DID，而不是某个平台。 |
| ERC-4337 | “账户抽象” | 能赞助 gas 的合约账户，使 agent 支付成为可能。 |
| Shapley value | “公平信用归因” | 满足有效性、对称性、线性性、零贡献者的唯一分配。 |
| Second-price auction | “Vickrey 拍卖” | 诚实机制：赢家支付第二高报价。兼容单调聚合。 |
| Reputation capital | “累积质量分” | 来自已确认贡献、绑定 DID 的分数；随时间衰减。 |
| Agentic DAO | “agent + 人类共同治理” | 把 agent 投票者视为一等公民的 DAO，投票权与声誉挂钩。 |
| TAO / FET / GPU credits | “token 面额” | Bittensor 的 TAO、Fetch.ai 的 FET，以及各种 DePIN token。 |

## Further Reading

- [The Agent Economy](https://arxiv.org/abs/2602.14219) —— 2026 年 5 层 agent 经济堆栈综述
- [Google Research — Mechanism design for large language models](https://research.google/blog/mechanism-design-for-large-language-models/) —— 单调聚合下的 token 拍卖
- [AAMAS 2025 — decentralized LaMAS](https://www.ifaamas.org/Proceedings/aamas2025/pdfs/p2896.pdf) —— Shapley 值信用归因
- [Bittensor TAO documentation](https://docs.bittensor.com/) —— 子网结构与奖励分配
- [Fetch.ai / ASI Alliance](https://fetch.ai/) —— ASI-1 Mini LLM 与 FET token
- [W3C Decentralized Identifiers (DIDs) spec](https://www.w3.org/TR/did-core/) —— 身份基础
