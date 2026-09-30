# 编排模式：Supervisor、Swarm、Hierarchical

> 四种编排模式在 2026 年的各框架中反复出现：supervisor-worker、swarm / peer-to-peer、hierarchical、debate。Anthropic 的指引：「关键是构建适合你需求的系统。」从简单开始；只有当单个智能体加五种工作流模式不够用时，才添加拓扑。

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 12 (Workflow Patterns), Phase 14 · 25 (Multi-Agent Debate)
**Time:** ~60 minutes

## 学习目标

- 说出四种反复出现的编排模式，以及各自适合的场景。
- 描述 2026 年 LangChain 的推荐：基于工具调用的监督 vs 监督库。
- 解释 Anthropic 的「构建正确的系统」规则，以及它如何约束拓扑选择。
- 在标准库中针对一个共享的脚本化 LLM 实现全部四种模式。

## 问题

团队在自己真正需要之前就伸手去拿「多智能体」。四种模式在各框架中反复出现；一旦你能叫出它们的名字，你就能选对那个——或者干脆跳过拓扑。

## 概念

### Supervisor-worker

- 一个中央路由 LLM 把任务派发给专家智能体。
- 它决定：循环回自身、handoff 给专家，或终止。
- 专家之间不互相通信；所有路由都经过 supervisor。

框架：LangGraph `create_supervisor`、Anthropic orchestrator-workers、CrewAI Hierarchical Process。

**2026 年 LangChain 的推荐：** 通过直接工具调用来做监督，而不是 `create_supervisor`。这带来更精细的上下文工程控制——你精确地决定每个专家看到什么。

### Swarm / peer-to-peer

- 智能体通过共享工具面直接 handoff。
- 没有中央路由。
- 比 supervisor 延迟更低（跳数更少）。
- 更难推理（没有单一控制点）。

框架：LangGraph swarm 拓扑、OpenAI Agents SDK handoffs（当所有智能体都可以 handoff 给其他所有智能体时）。

### Hierarchical

- supervisor 管理 sub-supervisor，sub-supervisor 管理 worker。
- 在 LangGraph 中实现为嵌套子图；在 CrewAI 中实现为嵌套 crew。
- 能以运营复杂度为代价扩展到大规模智能体群体。

何时需要它：当单个 supervisor 的上下文预算无法容纳所有专家的描述时。

### Debate

- 并行提议者 + 迭代交叉批判（第 25 课）。
- 不算真正的编排——更像验证——但在各框架中作为拓扑选择出现。

### Autonomous crews vs deterministic flows

CrewAI 把两种部署模式形式化了：

- **Flow** 用于确定性的、事件驱动的自动化（生产环境的推荐起点）。
- **Crew** 用于自主的、基于角色的协作。

这与上述四种模式正交，但映射到拓扑：Flow 通常是 supervisor 或 hierarchical；Crew 通常是带 LLM 路由器的 supervisor。

### Anthropic 的指引

「在 LLM 领域，成功不是构建最复杂的系统，而是构建适合你需求的系统。」

决策顺序：

1. 单个智能体 + workflow patterns（第 12 课）——从这里开始。
2. Supervisor-worker——当你有 2-4 个专家时。
3. Swarm——当延迟比推理清晰度更重要时。
4. Hierarchical——只有当 supervisor 的上下文预算失效时才用。
5. Debate——当准确率比成本更重要时。

### 这个模式在哪里会出问题

- **拓扑优先思维。** 「我们需要多智能体」——却还没弄清多智能体要解决什么问题。
- **swarm 中来回弹跳的 handoff。** A -> B -> A -> B。使用跳数计数器。
- **虚假层级。** 因为「企业级」而搞三层；实际只有两个团队。坍缩掉。

```figure
orchestration-pattern
```

## Build It

`code/main.py` 在标准库中针对一个脚本化 LLM 实现全部四种模式：

- `Supervisor`——中央路由。
- `Swarm`——带直接 handoff 的 peer-to-peer。
- `Hierarchical`——supervisor 的 supervisor。
- `Debate`——并行提议者 + 批判。

每种模式处理同一个三意图任务（退款 / 缺陷 / 销售）。轨迹形态各不相同。

运行它：

```
python3 code/main.py
```

输出：每种模式的轨迹 + 操作计数。Supervisor 最干净；swarm 最短；hierarchical 最深；debate 最贵。

## Use It

- **LangGraph** 用于 supervisor 和 hierarchical（嵌套子图）。
- **OpenAI Agents SDK** 用于 handoffs-as-tools（supervisor 形态）。
- **CrewAI Flow** 用于生产确定性场景。
- **Custom** 用于 debate，或当你需要精确控制时。

## Ship It

`outputs/skill-orchestration-picker.md` 挑选一个拓扑并实现它。

## 练习

1. 通过移除路由把 supervisor-worker 转成 swarm。什么会坏？什么会变好？
2. 给 swarm 加一个跳数计数器：在 3 次 handoff 后拒绝。它能抓住 A->B->A 的弹跳吗？
3. 为一个有 12 个专家的领域构建两级 hierarchical 系统。不做嵌套的话，上下文预算在哪里会失效？
4. 在一个生产形态的工作负载上剖析这四种模式。每种模式在哪个指标上胜出（延迟、成本、准确率、可调试性）？
5. 阅读 Anthropic 的《Building Effective Agents》文章。把你每条生产流程映射到四种之一。有不干净的吗？

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| Supervisor-worker | 「路由器 + 专家」 | 中央 LLM 派发给专家；专家之间不互相通信 |
| Swarm | 「Peer-to-peer」 | 通过共享工具直接 handoff；没有中央路由 |
| Hierarchical | 「supervisor 的 supervisor」 | 面向大规模群体的嵌套子图 |
| Debate | 「提议者 + 批判」 | 并行提议者、交叉批判（第 25 课） |
| Tool-call-based supervision | 「不用库的 supervisor」 | 把 supervisor 实现为直接工具调用以获得上下文控制 |
| Crew | 「自主团队」 | CrewAI 基于角色的协作模式 |
| Flow | 「确定性工作流」 | CrewAI 事件驱动的生产模式 |

## 延伸阅读

- [Anthropic，Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)——五种模式 + agent vs workflow
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)——supervisor、swarm、hierarchical
- [CrewAI docs](https://docs.crewai.com/en/introduction)——Crew vs Flow
- [Du 等人，Society of Minds（arXiv:2305.14325）](https://arxiv.org/abs/2305.14325)——debate 模式