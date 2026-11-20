# Negotiation 与 Bargaining

> agent 就资源、价格、任务分配和条款进行谈判。2026 年的基准集已经很清晰：NegotiationArena（arXiv:2402.05863）表明 LLM 可以通过人格操纵（"desperation"）把收益提升约 20%；"Measuring Bargaining Abilities"（arXiv:2402.15813）表明买方比卖方更难，且规模没有帮助 —— 他们的 **OG-Narrator**（确定性报价生成器 + LLM 叙述者）把成交率从 26.67% 提升到 88.88%；Large-Scale Autonomous Negotiation Competition（arXiv:2503.06416）跑了约 18 万次谈判，发现**隐藏 chain-of-thought** 的 agent 通过把推理藏起来不向对手展示而获胜；Bhattacharya 等人 2025 年在 Harvard Negotiation Project 指标上的排名是：Llama-3 最有效、Claude-3 最具攻击性、GPT-4 最公平。本课实现 Contract Net Protocol（FIPA 的前身，第 02 课），接线一个 LLM 风格的买方/卖方，运行一个 OG-Narrator 风格的分解，并度量成交率如何随每个结构性选择变化。

**Type:** Learn + Build
**Languages:** Python（stdlib）
**Prerequisites:** 第 16 阶段，第 02 课（FIPA-ACL Heritage）、第 09 课（Parallel Swarm Networks）
**Time:** ~75 分钟

## 问题场景

两个 agent 需要就一个价格达成一致。若只给它们纯语言 prompt 自行发挥，2024-2026 年的 LLM 达成交易的比例低得惊人（在 arXiv:2402.15813 的紧参数化议价中约为 27%）。规模解决不了这个问题：GPT-4 在结构上并不比 GPT-3.5 更擅长 bargaining；它更擅长 bargaining 的*语言*。

根本问题在于 LLM 把两件事混为一谈 —— 决定报价与叙述报价。OG-Narrator 把二者分开：一个确定性的报价生成器计算数值动作；LLM 只负责叙述。成交率跃升到约 89%。

这呼应了一个经典的多 agent 结论：把机制与通信层解耦就能取胜。Contract Net Protocol（FIPA，1996；Smith，1980）是参考性的任务市场机制。把一个 LLM 接入叙述槽位，你就得到一个现代的、由 LLM 驱动的任务市场。

## 核心概念

### 一段话讲清 Contract Net

Smith 1980 年的 Contract Net Protocol：一个 **manager** 广播一个 **call for proposals (cfp)**；**bidder** 用含其报价的 **propose** 消息响应；manager 选出一个赢家，向赢家发送 **accept-proposal**，向输家发送 **reject-proposal**。赢家执行工作。可选消息：**refuse**（bidder 拒绝提案）。FIPA 把它编为 `fipa-contract-net` 交互协议。

### OG-Narrator 为何胜出

"Measuring Bargaining Abilities of Language Models"（arXiv:2402.15813）观察到：

- LLM 常常违反议价规则（以荒谬的价格报价、无视对方的 ZOPA）。
- 它们的锚定很差（接受糟糕的首次报价；以象征性而非策略性的金额还价）。
- 单靠规模解决不了这些。更大的模型生成更可信的语言，但策略性错误相似。

OG-Narrator 的分解：

```
           ┌──────────────────┐        ┌──────────────────┐
  state  → │ offer generator  │ price → │  LLM narrator    │ → message
           │  (deterministic) │        │  (writes the     │
           │                  │        │   human-style    │
           └──────────────────┘        │   accompaniment) │
                                       └──────────────────┘
```

报价生成器是一个经典谈判策略：Rubinstein bargaining 模型、Zeuthen 策略，或简单的价格针锋相对。LLM 负责叙述。消息包含确定性价格与自然语言的包装。

成交率跃升因为：
- 价格保持在议价区间内。
- 锚点是策略性的，而非情绪化的。
- LLM 做它擅长的事：写作。

### NegotiationArena 的发现

arXiv:2402.05863 提供了权威基准。核心发现：

- LLM 可以通过采用人格（"I am desperate to sell this by Friday"）把收益提升约 20% —— 人格操纵是一种真实战术。
- 公平/合作的 agent 会被对抗性的 agent 剥削；防御需要显式的反向姿态。
- 对称配对在约 40% 的基准场景中收敛到不平等的结局。

这不是"LLM 是不好的谈判者"。而是"LLM 谈判得太像人类，包括那些可被剥削的部分"。

### Chain-of-thought 隐藏

Large-Scale Autonomous Negotiation Competition（arXiv:2503.06416）在众多 LLM 策略间跑了约 18 万次谈判。赢家把自己的推理对对手隐藏：

- 若一个 agent 把"我最多只出到 $75；我的保留价是 $70"写进公开可见的 scratchpad，对手就会读到它。
- 赢家私下计算策略；输出通道只包含报价与必需的最少叙述。

这是 2026 年对经典博弈论（Aumann 1976 论理性与信息）的呼应：暴露你的私人估值会损失收益。LLM 对此没有直觉，会愉快地把自己的保留价敲进推理轨迹里，而这些轨迹对对手变得可见。

工程要点：把 private-scratchpad context 与 public-message context 分开。这不是可选项。

### Bhattacharya 等人 2025 —— 模型排名

在 Harvard Negotiation Project 指标上（principled negotiation、BATNA 尊重、利益互惠）：

- **Llama-3** 在达成交易上最有效（成交率 + 收益）。
- **Claude-3** 是最具攻击性的谈判者（高锚点、迟让步）。
- **GPT-4** 是最公平的（跨配对收益方差最小）。

这是 2025 年的快照。重点不在于 2026 年 4 月哪个模型胜出 —— 而在于不同底座模型有持久的谈判风格。异构集成（第 15 课）把它作为一种多样性来源纳入。

### 通过 Contract Net + LLM 做任务分配

Contract Net 在 LLM multi-agent 中的现代复用：

1. Manager agent 把任务分解为单元。
2. 向 worker agent 广播带任务描述的 `cfp`。
3. 每个 worker 返回一个报价：`(price, eta, confidence)`，其中 price 可以是 token、算力单元或美元。
4. Manager 选出赢家（根据任务，单个或多个）并授予。
5. 被拒绝的 worker 可以自由竞标其他任务。

这能良好扩展到 100 个以上 worker，因为协调是广播-响应式的，而非同步聊天。生产中使用：Microsoft Agent Framework 的编排模式、一些 LangGraph 实现。

### LLM-Stakeholders Interactive Negotiation

NeurIPS 2024（https://proceedings.neurips.cc/paper_files/paper/2024/file/984dd3db213db2d1454a163b65b84d08-Paper-Datasets_and_Benchmarks_Track.pdf）引入了带**秘密分数**与**最低接受阈值**的多方可评分博弈。每个利益相关方都有私有效用；LLM 必须从消息中推断它们。这是把两方 bargaining 推广到 N 方联盟形成。对具有异构 worker 能力的生产任务市场很有意义。

### 叙述与机制之分的规则

在 2024-2026 年所有谈判基准中，一致的工程规则是：

> 让 LLM 叙述。不要让 LLM 计算报价。

若报价需要是一个数值（价格、ETA、数量），就从谈判状态确定性地生成它，再让 LLM 产生包装。若报价需要是一种提案结构（任务分解、角色分配），就让 LLM 起草它，但在发送前要针对 schema 做校验并做约束检查。

```figure
a5-og-narrator
```

## Build It

`code/main.py` 实现：

- `ContractNetManager`、`ContractNetTask`、`Bid` —— manager + bidder，广播 cfp，收集提案，授予。
- `og_narrator_bargain(state, rng)` —— OG-Narrator 买方：确定性 Zeuthen 式地向中点让步。
- `seller_response(state, rng)` —— 确定性卖方还价策略（两种风格的结构性 ground truth）。
- `naive_llm_bargain(state, rng)` —— 模拟一个全 LLM 的谈判者：以高方差挑选价格，常常落在 ZOPA 之外。
- 度量：在 1000 次试验上的成交率，每次试验采样新的保留价。

运行：

```
python3 code/main.py
```

预期输出：naive-LLM 成交率约 65-75%；OG-Narrator 成交率约 85-95%；15-25 个百分点的差距就是把报价生成与叙述分解开来的结构性优势。外加一个带三个 bidder 与一个任务的 Contract Net 任务市场分配示例。

## Use It

`outputs/skill-bargainer-designer.md` 设计一个 bargaining 协议：谁生成报价（确定性还是 LLM）、谁叙述、私有 scratchpad 如何与公开消息分离、以及如何监控成交率。

## Ship It

生产 bargaining 检查清单：

- **分离 scratchpad。** 私有状态绝不进入对手的 context。这一点不容妥协。
- **确定性报价生成。** 价格、数量、ETA：计算，不要 prompt。
- **校验所有入站报价**是否符合 schema。在协议边界处拒绝超出 ZOPA 的报价。
- **限制轮数。** 最多 3-5 轮；陷入僵局时升级给调解者。
- **持续度量成交率与收益方差。** 成交率下降是一个征兆 —— 往往是 prompt 漂移或对手侧攻击。
- **记录所有被拒绝的提案**及其确定性理由。对 Contract Net manager 而言，落败的 bidder 需要理解原因。

## Exercises

1. 运行 `code/main.py`。确认 OG-Narrator 在成交率上胜过 naive-LLM。高出多少？
2. 实现**基于人格的收益提升**（arXiv:2402.05863）—— 买方只在叙述中采用"desperate to buy this week"人格，报价生成器不变。成交率或收益会变吗？
3. 实现 chain-of-thought **隐藏**：维护一个不传给对手的私有 scratchpad 字符串。若你不小心泄露了它（通过交换通道来模拟）会发生什么？
4. 把 Contract Net 扩展为带保留价的 N-bidder 拍卖。当所有出价都超过保留价时，manager 如何在最低价与最高质量之间抉择？你选哪条授予规则，为什么？
5. 阅读 Bhattacharya 等人 2025 关于 Harvard Negotiation Project 指标的工作。实现两个不同风格的谈判者（攻击型 vs 公平型）。度量在对称与非对称配对下的收益方差。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Contract Net | "Task market" | Smith 1980，FIPA 1996。cfp + propose + accept/reject。权威的任务市场。 |
| ZOPA | "Zone of possible agreement" | 买方最高价与卖方最低价的重叠区。区间外的报价无法成交。 |
| BATNA | "Best alternative to a negotiated agreement" | 若这笔交易失败的退路。它设定你的保留价。 |
| OG-Narrator | "Offer generator + narrator" | 分解：确定性报价，LLM 叙述。 |
| Zeuthen strategy | "Risk-minimizing concession" | 经典的报价生成器，基于风险上限来让步。 |
| Rubinstein bargaining | "Alternating-offer equilibrium" | 无限期、带折扣的 bargaining 的博弈论模型。 |
| CoT concealment | "Hide your reasoning" | arXiv:2503.06416 中的赢家用私有 scratchpad；公开通道只显示报价。 |
| Persona manipulation | "Emotional posturing" | arXiv:2402.05863：通过绝望/紧迫人格获得约 20% 的收益提升。 |

## Further Reading

- [NegotiationArena](https://arxiv.org/abs/2402.05863) —— 该基准；人格操纵与剥削的发现
- [Measuring Bargaining Abilities of Language Models](https://arxiv.org/abs/2402.15813) —— OG-Narrator 以及买方比卖方更难的结果
- [Large-Scale Autonomous Negotiation Competition](https://arxiv.org/abs/2503.06416) —— 约 18 万次谈判；chain-of-thought 隐藏获胜
- [LLM-Stakeholders Interactive Negotiation (NeurIPS 2024)](https://proceedings.neurips.cc/paper_files/paper/2024/file/984dd3db213db2d1454a163b65b84d08-Paper-Datasets_and_Benchmarks_Track.pdf) —— 带秘密效用的多方可评分博弈
- [Smith 1980 — The Contract Net Protocol](https://ieeexplore.ieee.org/document/1675516) —— 经典机制，IEEE Transactions on Computers
