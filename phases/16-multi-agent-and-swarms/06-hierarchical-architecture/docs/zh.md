# 分层架构及其失效模式

> 分层架构就是嵌套的 supervisor。管理者 agent 位于子管理者之上，子管理者之下是工作者。CrewAI 的 `Process.hierarchical` 是教科书式的版本：一个 `manager_llm` 动态地分派任务并校验输出。LangGraph 中的等价物是 `create_supervisor(create_supervisor(...))`。当任务本身就是一张真实的组织架构图时，这是最自然的模式。它同时也是最容易坍缩成管理者空转（managerial looping）的模式——管理者 agent 分派工作不当、误读子输出，或者无法达成共识。顺序式往往能胜过它。

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** 第 16 阶段，第 05 课（Supervisor Pattern）
**Time:** ~60 分钟

## 问题场景

一旦 supervisor 模式想通了，自然的下一步就是“如果工作者本身也是 supervisor 会怎样？”团队之下有子团队；公司之下有部门中的部门。分层架构正是对这种情况的镜像。

问题在于：LLM 管理者与人类管理者并不相同。人类管理者对下属知道什么有稳定的先验。LLM 管理者则每一轮都从上下文里的内容重新推理整个组织。上下文里一点点漂移，整棵树就会错误地分配工作。

## 核心概念

### 结构形态

```
                 Manager
                 ┌─────┐
                 └──┬──┘
           ┌────────┴────────┐
           ▼                 ▼
       Sub-Mgr A         Sub-Mgr B
       ┌─────┐           ┌─────┐
       └──┬──┘           └──┬──┘
         ┌┴──┬──┐          ┌┴──┐
         ▼   ▼  ▼          ▼   ▼
       W1  W2  W3         W4  W5
```

每个内部节点都负责规划、分派与综合。只有叶子节点真正干活。

### 它擅长的地方

- **组织映射清晰。** 如果真实任务本身就是按部门划分的（“法务审阅文档，财务审阅文档，工程审阅文档，最后由高管汇总”），那么层级关系就是显式的。
- **局部摘要。** 每个子管理者先综合自己团队的输出，再由顶层管理者查看。顶层管理者看到的是三份子管理者摘要，而不是十五份工作者输出。

### 它在哪儿会崩

2026 年的复盘分析反复发现三种失效模式：

1. **任务分配错误。** 管理者读取目标，凭空臆造出一套分解方案，然后把它分派给错误的子管理者。由于子管理者会顺从地处理自己拿到的东西，错误只会在顶层综合时才暴露——比人类本可发现它的位置隔了一层。
2. **输出误读。** 子管理者返回“无法验证主张 X”。顶层管理者却总结成“主张 X 未获确认”。含义在每一层都会漂移。
3. **共识循环。** 两个子管理者意见不一；顶层管理者让它们协调；它们把任务再往下分派；工作者重新运行；子管理者返回略有不同的答案；于是循环。CrewAI 的 `Process.hierarchical` 用步数上限来防范这种情况，但这个上限本身又成了一个超参数。

### 决定性问题

顺序式（线性流水线）对比分层式：你的任务是真的有相互独立的子团队，还是一条线性流程假扮成一棵树？如果是后者，用顺序式。如果是前者，用分层式，但要为明确的协调规则预留预算。

### 角色型框架中的实现

CrewAI 的 `Process.hierarchical` 在专家 crew 之上接入一个管理者 LLM。管理者会：

- 接收顶层任务，
- 把子任务分派给各个 crew，
- 评估 crew 的输出，
- 决定是接受、重新分派，还是迭代。

文档：https://docs.crewai.com/en/introduction（在 Core Concepts 下查找 “Hierarchical Process”）。

### 图型框架中的实现

LangGraph 使用嵌套的 `create_supervisor` 调用。内层 supervisor 拥有自己的图；外层 supervisor 把内层图当作一个不透明节点。就调试而言，这比 CrewAI 更干净（你可以分别单步调试每一张图），但更难表达对树的动态重塑。

参考：https://reference.langchain.com/python/langgraph-supervisor。

```figure
swarm-hierarchy-token
```

## Build It

`code/main.py` 运行一个 3 层的层级结构：

- 顶层管理者：把一个任务拆成“engineering”和“legal”两条分支，
- engineering 子管理者：拆成“frontend”和“backend”两个工作者，
- legal 子管理者：一个工作者。

演示对比了两条路径：一切顺利的路径（所有环节意见一致），以及一条**扰动路径**——在扰动路径中，顶层管理者在分解时把“legal”错标成“finance”，随后观察错误如何级联：子管理者顺从地去做财务工作，顶层综合者汇报财务发现，而原本的法务问题无人回答。

运行：

```
python3 code/main.py
```

输出会并列展示两条路径，清晰对照“被要求的是什么”与“实际交付的是什么”。

## Use It

`outputs/skill-hierarchy-fitness.md` 评估给定任务应当采用分层式、顺序式，还是扁平 supervisor。输入：任务描述、组织结构、协调预算。输出：模式建议，并列出需要防范的具体失效模式。

## Ship It

如果你要交付分层式系统：

- **把树的深度限制在 2 层。** 三层就已经会把大多数错误藏到可观测性之外。
- **明确的协调预算。** 设定顶层管理者必须做出最终决定前的最大轮数。通常是 2。
- **每次综合都带溯源。** 每个节点的摘要都必须标明它是由哪些叶子输出产生的。
- **对分解漂移告警。** 按步骤记录管理者的分解；与用户查询做差分。如果分解不再覆盖查询，就触发告警。

## Exercises

1. 运行 `code/main.py`，对比顺利路径与扰动路径。需要经过多少层管理者交接，顶层输出才会与用户的问题完全背离？
2. 增加第三层（top → sub → sub-sub → worker）。测量随着深度增加，扰动路径自我纠正与完全背离各占多少比例。
3. 在每个子管理者处实现一个“金丝雀”（canary）工作者，它总是被问及原封不动的原始用户问题。用金丝雀的答案来检测分解漂移。当金丝雀的答案与综合出的答案不一致时，管理者应当如何反应？
4. 阅读 CrewAI 的 `Process.hierarchical` 文档。找出 CrewAI 采用的一个具体防线（步数上限、manager_llm 约束），并说明它针对的是哪种失效模式。
5. 对比嵌套的 LangGraph supervisor 与 CrewAI 分层式。哪一种让协调循环的检测成本更低？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Hierarchical | “组织架构图模式” | 管理者之上还有管理者；只有叶子节点干活。 |
| Manager LLM | “老板” | 在内部节点上负责分解、分派与验证的 LLM。 |
| Decomposition drift | “老板跑偏了” | 顶层管理者的拆分不再覆盖原始问题。 |
| Reconciliation loop | “无休止的开会” | 子管理者意见不一；顶层重新分派；工作者重新运行；一直循环到预算耗尽。 |
| Depth-2 ceiling | “不要超过 2 层” | 经验性防线：3 层及以上会让可观测性崩溃。 |
| Canary question | “每一层都有基准真相” | 一个总是被问及原封不动原始查询的工作者，用来检测漂移。 |
| Provenance chain | “谁说了什么” | 从每次综合回溯到产生它的叶子输出。 |

## Further Reading

- [CrewAI introduction — Process.hierarchical](https://docs.crewai.com/en/introduction) — 教科书式的分层式实现，带一个管理者 LLM
- [LangGraph supervisor reference](https://reference.langchain.com/python/langgraph-supervisor) — 通过 `create_supervisor` 实现的嵌套 supervisor
- [Anthropic engineering — Research system](https://www.anthropic.com/engineering/multi-agent-research-system) — Anthropic 为何刻意选择扁平 supervisor 而非分层式
- [Cemri et al. — Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/abs/2503.13657) — MAST 分类法；关于协调失败的一节记录了分解漂移
