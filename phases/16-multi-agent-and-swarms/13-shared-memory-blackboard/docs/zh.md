# Shared Memory 与 Blackboard 模式

> 2026 年的 multi-agent 系统里并存两种做法：**message pool**（每个人都看到所有人的 message，如 AutoGen GroupChat 或 MetaGPT）与**带订阅的 blackboard**（agent 订阅相关事件，如 Context-Aware MCP 或 Matrix 框架）。两者都是 multi-agent 系统中唯一的有状态部分 —— 也就是说，两者都是有趣的 bug 藏身之处。典型的故障模式是 **memory poisoning**：一个 agent 幻觉出一个“事实”，其他 agent 把它当作已验证内容，于是准确率逐步衰减，这种衰减比直接崩溃难调试得多。本课用标准库构建这两种结构，注入一次投毒攻击，并展示三种在生产中真正有效的缓解手段。

**Type:** Learn + Build
**Languages:** Python（stdlib，`threading`）
**Prerequisites:** 第 16 阶段，第 04 课（Primitive Model）、第 09 课（Parallel Swarm Networks）
**Time:** ~75 分钟

## 问题场景

multi-agent 系统需要一个让 agent 共享事实的地方。最字面的选项是“把所有东西都放进 message 传递” —— 但这只是带着额外拷贝重新发明了 shared state。另一个是“给每个人一份全局日志” —— 但全局日志会无界增长，而且很轻易就被投毒。第三种是“为每个 agent 投影一个视图” —— 可扩展，但 schema 负担重。

当其中一个 agent 产生幻觉并把幻觉写入 shared state 时，每个读到该状态的下游 agent 都会把幻觉当成事实。等人类察觉时，推理链已经深入五步，而根因是写下的第三条 message。调试 multi-agent 的准确率衰减比调试崩溃更难。

这就是 memory poisoning。它是 MAST 分类法（Cemri 等，arXiv:2503.13657）中记录第二多的故障族，而且是结构性的：任何缺少 provenance 和不可写验证器的 shared-memory 设计，最终都会显现它。

## 核心概念

### 两种主要拓扑

**全量 message pool。** 每个 agent 读取每一条 message。AutoGen GroupChat 和 MetaGPT 就用这个。简单、透明、可检查，但超过约 10 个 agent 就无法扩展，因为每个 agent 的 context 会被其他 agent 的产出填满。

```
agent-A ──write──▶ ┌────────────────┐ ◀──read── agent-D
                   │ message pool   │
agent-B ──write──▶ │                │ ◀──read── agent-E
                   │ (global log)   │
agent-C ──write──▶ └────────────────┘ ◀──read── agent-F
```

**带订阅的 blackboard。** agent 声明对 topic 的兴趣；底层只路由相关的 message。CA-MCP（arXiv:2601.11595）和去中心化的 Matrix 框架（arXiv:2511.21686）使用这个。扩展性更好，但需要预先设计 schema，订阅才有意义。

```
                   ┌─ topic: prices ──┐
agent-A ──pub────▶ │                  │ ──▶ agent-D (subscribed)
                   ├─ topic: orders ──┤
agent-B ──pub────▶ │                  │ ──▶ agent-E (subscribed)
                   ├─ topic: alerts ──┤
agent-C ──pub────▶ │                  │ ──▶ agent-F (subscribed)
                   └──────────────────┘
```

### 各自适用的场景

- **Full pool** 在 agent 数量少（< 10）、异构、且对话时程较短时占优。当每个人都看到一切时，推理谁说了什么变得很简单。
- **Blackboard** 在 agent 众多、角色同构但实例数量庞大（swarm）、且对话长期运行时占优。路由可以节省 token 成本和 context 污染。

生产系统常常混用：顶部是一个小的 full pool（规划层），下面是 blackboard（worker 层）。

### 一个场景里的 memory poisoning

三个 agent 共同完成一个研究任务。Agent A 是检索 agent。Agent B 是摘要 agent。Agent C 是分析 agent。

1. A 抓取一个页面，并向 shared state 写入一条 message：“研究报告显示准确率提升了 42%。”
2. 抓到的页面实际上写的是“提升了 4.2%”。A 幻觉出了一个小数点。
3. B 读取 shared state 后写道：“报告了 42% 的大幅准确率提升（来源：A）。”
4. C 读取 shared state 后写道：“建议采纳 —— 42% 的提升是颠覆性的。”
5. 最终报告引用了一个从未存在过的 42% 数字。

没有 agent 崩溃。没有测试失败。系统“正常工作了”。幻觉通过 shared state，从一个 agent 的 context 跨进了每个下游 agent 的推理。

### 为什么这是结构性的

没有 shared state 时，agent A 的幻觉留在 A 的 context 里。下游 agent 会重新抓取或重新推导，可能抓住这个错误。而用朴素的 shared state，A 的 context 变成了所有人的 context，幻觉被洗成了事实。

问题不在于 shared state 本身 —— 而在于**缺少 provenance、缺少独立验证器**的 shared state。三种缓解手段针对这一点：

1. **在每次写入时标注 provenance。** shared state 中的每条记录都记下是谁写的、何时写的、在什么 prompt 下写的，以及（如适用）agent 引用了什么来源。下游 agent 带着与 provenance 挂钩的怀疑来阅读。
2. **为写入做版本化；把它们视为 append-only。** 更正是取代旧条目的新条目，而不是原地更新。审计轨迹得以保留。
3. **至少保留一个无法写入 shared state 的 agent。** 一个只读的验证器 agent 抽样检查条目、重新抓取来源，并标记不一致之处。由于它无法写入 pool，它也就不会被 pool 投毒。

### Blackboard 的渊源（Hayes-Roth，1985）

blackboard 模式比 LLM agent 早了四十年。Hayes-Roth（1985，“A Blackboard Architecture for Control”）描述了专门的 Knowledge Source：它们观察一块全局 blackboard，贡献部分解，并触发其他 source。2026 年的 blackboard（CA-MCP、Matrix）是同一模式，只是把 LLM agent 当作 Knowledge Source，把 JSON blob 当作部分解。旧文献已经记录了写竞争、机会式控制和一致性问题的解决方案，而现代系统正重新发现它们。

### 投影与全量视图

纯粹的 blackboard 给每个订阅者相同的投影（按 topic 划定范围）。更激进的设计是 **per-agent projection**：每个 agent 得到按自身角色定制的视图。LangGraph 的 state reducer 是 2026 年的典型实现 —— reducer 函数把全局状态折叠成角色专属的切片。

per-agent projection 扩展性更好，但需要 schema。没有 schema，你就得在每个 agent 的 prompt 里重新搭一套临时投影。

### 写竞争的模式

多个 agent 同时写入是一个并发问题，而不只是 LLM 问题。三种模式有效：

- **串行写入者（单生产者）。** 所有写入经过一个协调 agent 串行化。简单，但是瓶颈。
- **带版本号的乐观并发。** 每条记录有版本号；写入者在版本不匹配时失败并重试。经典的数据库技术。
- **Topic 分区。** 不同 agent 拥有不同 topic。没有跨 topic 的竞争。需要设计好分区边界。

多数 2026 年的框架默认使用串行写入者，因为 LLM 调用足够慢，竞争很少见，瓶颈也不会造成明显伤害。

### 不可写的验证器

最关键的缓解手段是只读验证器。实现规则：

- 验证器与团队共享状态（读取 blackboard 或 pool）。
- 验证器对 shared state 没有写句柄 —— 只能写一个独立的验证通道。
- 验证器独立抓取写入中被引用的来源。标记出不一致。
- 验证器自身的输出被路由给人类或一个独立的决策 agent，绝不回灌到 pool 里。

没有这种隔离，验证器的输出就会成为 pool 中的新条目，这意味着被投毒的 pool 会污染验证器，而验证器又会污染它自己的验证结论。

```figure
swarm-blackboard
```

## Build It

`code/main.py` 用 stdlib Python 实现两种拓扑，外加一个玩具级的投毒攻击和三种缓解手段。

- `MessagePool` —— 线程安全、支持完整读出的 append-only 日志。
- `Blackboard` —— 按 topic 键控的 pub/sub，支持 per-agent 订阅。
- `ProvenanceEntry` —— 每次写入记录 (writer, timestamp, prompt_hash, source_uri)。
- `PoisoningScenario` —— 运行一个三 agent 研究任务，其中 agent A 幻觉出一个小数点。打印最终报告。
- `Verifier` —— 一个只读 agent，重新抓取来源并标记不一致。在验证器存在的情况下运行同一场景。

运行：

```
python3 code/main.py
```

预期输出：
- 第 1 次运行（无验证器）：幻觉出来的 42% 传播到最终报告。
- 第 2 次运行（有验证器）：验证器标记出不一致，pool 被标记为“flagged”，最终报告包含一处撤回。

## Use It

`outputs/skill-memory-auditor.md` 是一个 skill，用来审计任意 multi-agent 系统的 shared-memory 设计在 provenance、版本化和验证器隔离方面的表现。在生产之前，把它跑在新的 multi-agent 架构上。

## Ship It

对任何 shared-memory 设计：

- 在每次写入时记录 provenance：`(writer, timestamp, prompt_hash, tool_calls_cited, source_uri)`。
- 让日志保持 append-only。更正是引用被取代条目的新条目。
- 至少部署一个拥有独立来源访问权限的只读验证器 agent。
- 把验证器的输出路由到独立通道，而不是回灌到共享 pool。
- 记录 supersession 写入所占的比例 —— 比例上升是幻觉模式出现的早期证据。

## Exercises

1. 运行 `code/main.py`。确认第 1 次运行传播了幻觉，第 2 次运行抓住了它。
2. 添加第二个幻觉：agent B 编造一个数据集大小。验证器应在没有针对任一幻觉手工调优的情况下把两者都抓住。
3. 把 full pool 换成带 topic 分区的 blackboard（`prices`、`summaries`、`analyses`）。topic 分区让哪些投毒场景更难实施，又对哪些场景没有帮助？
4. 阅读 Hayes-Roth（1985，“A Blackboard Architecture for Control”）。找出论文中两个本课未讨论、而 2026 年系统会受益的控制模式。
5. 阅读 CA-MCP（arXiv:2601.11595）。把它的 Shared Context Store 映射到 `code/main.py` 中的 MessagePool 或 Blackboard 类。CA-MCP 在其之上增加了哪些原语？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Message pool | “共享聊天记录” | 每个 agent 都读取的 append-only 日志。完全透明，扩展性差。 |
| Blackboard | “共享工作区” | 按 topic 键控的 pub/sub。agent 订阅相关 topic。扩展得更远。 |
| Provenance | “谁写了什么” | 每次写入上的元数据：写入者、时间戳、prompt、来源。 |
| Memory poisoning | “幻觉扩散” | 一个 agent 的错误进入 shared state，下游 agent 把它当作事实。 |
| Append-only | “不做原地更新” | 更正是取代旧条目的新条目。保留审计轨迹。 |
| 不可写验证器 | “独立审计员” | 只读 agent，重新抓取来源并标记不一致。 |
| Projection | “有作用域的视图” | 由全局状态计算出的 per-agent 视图。LangGraph reducer 是典型案例。 |
| Knowledge Source | “专家 agent” | Hayes-Roth 1985 年对 blackboard 参与者的称呼。 |

## Further Reading

- [Cemri 等 —— Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/abs/2503.13657) —— MAST 分类法；memory poisoning 是协调故障的一个子族
- [CA-MCP —— Context-Aware Multi-Server MCP](https://arxiv.org/abs/2601.11595) —— 为协同的 MCP server 提供 Shared Context Store
- [Matrix —— 去中心化 multi-agent 框架](https://arxiv.org/abs/2511.21686) —— 基于 message 队列、没有中心编排者的 blackboard
- [LangGraph state 与 reducer](https://docs.langchain.com/oss/python/langgraph/workflows-agents) —— 生产环境中的 per-agent projection 模式
- [Anthropic —— How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) —— 来自一次生产部署的 provenance 与验证笔记
