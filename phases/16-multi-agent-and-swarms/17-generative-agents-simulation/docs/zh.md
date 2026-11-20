# Generative Agents 与涌现式模拟

> Park 等人 2023 年的工作（UIST '23，arXiv:2304.03442）用 25 个 agent 的沙盒 **Smallville** 承载了一套三部分架构：**memory stream**（自然语言日志）、**reflection**（agent 针对自身 stream 生成的高层综合），以及 **plan**（日级行为，再往下是子计划）。标志性的结果是情人节派对的涌现：一个 agent 被种下“想举办情人节派对”的目标，无需进一步脚本化，就产生了邀请并在人群中扩散、协调了日期，派对真的办成了——而最初的 24 个 agent 对它一无所知。消融实验表明，三个组件对可信度都是必需的。已记录在案的失效是空间规范错误（走进已关门的商店，共用单人卫生间）。这是 2026 年 agent 模拟与多智能体社会评估的参考架构。

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** 第 16 阶段，第 04 课（Primitive Model）、第 13 课（Shared Memory）
**Time:** ~75 分钟

## 问题场景

大多数多智能体系统都是紧密脚本化的团队：planner 规划、coder 编码、reviewer 审查。这对定义明确的任务有效。但它捕捉不到当 agent 拥有记忆、优先级和一个开放世界时所涌现出的、非脚本化的行为。研究、社会模拟，以及日益增多的游戏 AI，都需要后一种。

Smallville 架构就是这方面的基准。在 Park 2023 之前，最好的 agent 模拟也只是浅层的脚本跟随者；在此之后，这个模式成了开放世界中 generative agents 的默认做法。如果你在 2026 年构建 agent 模拟，那么你要么在使用 Smallville 的三个组件，要么就得明确论证为何不用。

## 核心概念

### 三个组件

**Memory stream。** 一份只追加、记录观察、动作、反思与计划的日志。每条记录都有时间戳、类型、一段描述（自然语言），以及派生元数据：**recency**、**importance**（由 agent 自评 1-10）、**relevance**（与当前查询的余弦相似度）。

```
[2026-02-14 09:12:03] observation: Isabella Rodriguez asked me if I like jazz
[2026-02-14 09:14:22] reflection:   I enjoy long conversations about music
[2026-02-14 10:05:00] plan:         Attend Isabella's Valentine's Day party tonight
```

记忆检索综合这三个分数：`score = w_recency * e^(-decay * age) + w_importance * importance + w_relevance * cos_sim`。得分最高的 k 条记录进入当前 prompt。

**Reflection。** agent 会定期地（每 N 条记忆，或遇到重要事件时）从近期记忆中生成高阶综合。反思记录会回到 stream 中，并像任何其他记忆一样可被检索。agent 正是这样积累“理解”的——这是该架构中相当于长期信念的东西。

**Plan。** 自顶向下的分解。首先是一份粗线条的日级计划（“去上班，和 Klaus 吃晚饭”）。然后是小时级计划。再然后是动作级计划。计划是可修订的：当某条观察与计划矛盾时，agent 会重新规划受影响的那一段。

### 为什么三者都重要（消融）

Park 等人做了消融实验，分别去掉观察、反思和计划。每一次消融都会损害可信度：

- 没有**观察**，agent 会漏掉上下文，并依据过时的信念行事。
- 没有**反思**，agent 无法形成高阶信念；交互停留在浅层。
- 没有**计划**，行为变成反应性的噪声；目标消散。

人类评分者给出的可信度分数在三者齐备时最高；去掉任意一个都会带来可度量的退步。

### 情人节派对的涌现

一个 agent，Isabella Rodriguez，被种下目标“想在 2 月 14 日下午 5 点在 Hobbs Cafe 举办情人节派对”。其余 24 个 agent 都没有这样的种子。在模拟的若干天里：

1. Isabella 的计划中包含邀请他人。
2. 每一份邀请都会成为某位邻居 memory stream 中的一条观察。
3. 该邻居的反思会生成信念：“Isabella 正在办派对。”
4. 该邻居的计划纳入“2 月 14 日参加派对”。
5. 邻居又告诉其他邻居。邀请在没有中心协调的情况下扩散开来。
6. 2 月 14 日下午 5 点，若干 agent 汇聚到 Hobbs Cafe。

这是技术意义上的涌现：系统级行为（一场派对）从局部交互（双向邀请 + 个体规划）中产生，而没有中心 orchestrator。

### 已记录在案的失效模式

Park 等人明确记录了：

- **空间规范错误。** agent 会走进已经关门的商店。agent 会试图共用同一个单人卫生间。agent 会在并非用于进食的房间里吃东西。模型无法仅凭环境推断出社会-物理规范。
- **记忆溢出。** 长时间的模拟运行会让记忆检索成本增长。实用补救：定期做记忆压缩（摘要并剪枝），以及对低重要性记录施加衰减。
- **反思幻觉。** 反思可能编造出 memory stream 中并不存在的关系。缓解：在反思 prompt 中包含来源记忆的 id，并在检索时加以核对。

这些是与生产相关的失效模式：任何 2026 年的 agent 模拟都会继承它们。

### 三组件的实现规则

1. **记忆只追加。** 绝不修改记忆记录。更正写成新的记录。
2. **重要性评分很便宜。** 在写入时调用 LLM 打出 1-10 的重要性评分。缓存这个分数。
3. **检索是排序，不是过滤。** 按综合得分取前 k 条；不要用硬性过滤（那会丢失上下文）。
4. **反思定期运行。** 当未处理记忆的重要性总和超过阈值（例如 150）时触发。
5. **计划可修订。** 当新的观察与计划矛盾时，只重新生成受影响的那一段，而不是整份计划。

### Smallville 之外的 generative agents

2024-2026 年的后续文献扩展了这一架构：

- **面向政策 / 市场研究的多智能体社会模拟。** 类 Smallville 的人群模拟用户对功能的反应。比 A/B 测试更快；准确性尚有争议。
- **游戏中的 NPC AI。** 采用 Smallville agent 的 RPG 会产生涌现的故事情节，而不是脚本化的任务。
- **generative-agent 评估 benchmark。** 衡量指标不再是任务准确率，而是长时间运行下的可信度 + 行为连贯性。

这套架构是参照物。各种扩展会替换组件（用向量库做记忆、检索增强的反思、神经符号计划），但都保留三部分结构。

### 这对多智能体工程意味着什么

Smallville 是一个概念验证：只要组件对了，多智能体涌现的成本很低。这套架构如今已在开源模型上被复现（更小的 LLM 在可信度上只是平缓下降，而非骤降）。任何需要**涌现式社会行为**的生产系统都采用这种形态。任何需要**紧凑任务执行**的系统，则采用本阶段前文的 supervisor / 角色 / 原语模式。

```figure
a5-memory-reflection
```

## Build It

`code/main.py` 用标准库 Python、以脚本化的 agent 策略（不含真正的 LLM）实现了这三个组件。演示在缩略规模上复现情人节派对的涌现：

- `MemoryStream`——只追加的日志，带 recency/importance/relevance 检索。
- `reflect(stream)`——对近期高重要性记忆的脚本化反思。
- `plan(agent_state)`——基于当前信念的日级与小时级计划。
- 场景：5 个 agent。Agent 1 起始于“下午 5 点办派对”。在模拟的 tick 推进中，邀请扩散，agent 汇聚。

运行：

```
python3 code/main.py
```

预期输出：逐 tick 的轨迹。到最后一个 tick 时，5 个 agent 中至少有 3 个在计划里出现了派对，并且它们汇聚在派对地点。单个种子在没有任何 orchestrator 的情况下产生了协调一致的到场。

## Use It

`outputs/skill-simulation-designer.md` 设计一个 generative-agent 模拟：agent 数量、记忆 schema、反思节奏、计划视野，以及评估指标。

## Ship It

生产级模拟的规则：

- **记忆就是数据库。** 规模化时选一个真正的存储（向量库、Postgres）。内存版标准库实现只用于原型。
- **记录检索轨迹。** 对每一个动作，记录驱动它的前 k 条记忆。这就是你的调试能力之所在。
- **为每个 agent 预算 token。** 每个 agent 每个 tick 的 retrieve + reflect + plan 是 O(k) 次 LLM 调用。N 个 agent × T 个 tick × 每 tick 调用数，足以让你的预算相形见绌。
- **定期压缩记忆。** 对低重要性记录做摘要并剪枝。保留策略是一项设计决策，而不是细节。
- 显式地**检测空间 / 社会规范违规**。这套架构并不会学到它们。

## Exercises

1. 运行 `code/main.py`。确认有 3 个以上 agent 汇聚到派对。把 agent 增加到 10 个——涌现还会发生吗？
2. 去掉反思步骤。行为看起来如何？对应到 Park 2023 的消融发现。
3. 引入一个竞争性的种子目标（“Klaus 想在下午 5 点做一场研究报告”）。agent 会分裂，还是一个目标占主导？由什么决定？
4. 增加空间约束：Hobbs Cafe 最多容纳 4 个 agent。模拟是优雅地处理溢出，还是撞上“单人卫生间”的失效模式？
5. 阅读 Park 等人（arXiv:2304.03442）第 6 节（涌现行为实验）。找出一个你的缩略版无法复现的行为。你需要增强架构中的哪个组件？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Memory stream | “agent 的日记” | 记录观察、动作、反思、计划的只追加日志。 |
| Recency | “这条记忆有多新” | 按时间年龄的指数衰减得分。 |
| Importance | “agent 多在意” | 写入时自评 1-10。会缓存。 |
| Relevance | “与当前查询有多相关” | 余弦相似度（基于 embedding）。 |
| Reflection | “高阶信念” | 从近期记忆生成的综合，重新作为一条新记忆摄入。 |
| Plan | “日/小时/动作的分解” | 自顶向下的计划树。观察矛盾时可修订。 |
| Smallville | “Park 2023 的沙盒” | 产生了情人节涌现的 25 个 agent 的模拟。 |
| Believability | “质量指标” | 人类评分者对行为是否像一个可信 agent 的评分。 |

## Further Reading

- [Park et al. — Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442) — 参考架构
- [UIST '23 paper page](https://dl.acm.org/doi/10.1145/3586183.3606763) — 发表会议
- [Smallville code release](https://github.com/joonspk-research/generative_agents) — 参考 Python 实现
- [Hayes-Roth 1985 — A Blackboard Architecture for Control](https://www.sciencedirect.com/science/article/abs/pii/0004370285900639) — 结构化记忆 agent 的前身工作
