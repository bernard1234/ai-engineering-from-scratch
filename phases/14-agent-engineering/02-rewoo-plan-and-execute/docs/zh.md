# ReWOO 与 Plan-and-Execute：解耦式规划

> ReAct 把思考与行动交织在一条流里。ReWOO 把它们分开：先做一份大计划，再执行。token 减少 5 倍，HotpotQA 上准确率 +4 分，而且你可以把 planner 蒸馏成一个 7B 模型。Plan-and-Execute 将它泛化；Plan-and-Act 把它扩展到网页导航。

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 01 (Agent Loop)
**Time:** ~60 minutes

## 学习目标

- 解释为什么 ReWOO 的 Planner / Worker / Solver 分工相比 ReAct 的交织循环能节省 token 并提升鲁棒性。
- 用纯标准库实现一个计划 DAG、一个按依赖排序的执行器，以及一个把 worker 输出组合起来的 solver。
- 用 2026 年「五种工作流模式」的框架（Anthropic），判断一个任务应当按「先计划后执行」还是交织式 ReAct 来跑。
- 识别出 Plan-and-Act 的合成计划数据在何时对长时程的网页或移动任务不可或缺。

## 问题

ReAct 的交织式 thought-action-observation 循环简单且灵活，但每一次工具调用都必须携带完整的先前上下文——包括之前的每一次思考。token 用量随深度呈二次增长。更糟的是：当某个工具在循环中途失败时，模型必须从错误观察中重新推导出整份计划。

ReWOO（Xu 等人，arXiv:2305.18323，2023 年 5 月）注意到了这一点，并做了一个赌注：一次性把整件事计划好，并行抓取证据，最后组合答案。一次 LLM 调用做计划，N 次工具调用抓证据（可以并行），一次 LLM 调用求解。代价是灵活性降低（计划是静态的），换来的是好得多的 token 效率和更清晰的失败模式。

## 概念

### 三个角色

```
Planner:  user_question -> [plan_dag]
Workers:  [plan_dag]     -> [evidence]        (tool calls, possibly parallel)
Solver:   user_question, plan_dag, evidence -> final_answer
```

Planner 产出一个 DAG。每个节点指名一个工具、它的参数，以及它依赖哪些更早的节点（引用形如 `#E1`、`#E2`）。Workers 按拓扑序执行节点。Solver 把所有东西缝合起来。

### 为什么 token 减少 5 倍

ReAct 的提示词长度随步数线性增长。到第 10 步时，提示词里已经包含思考 1 加行动 1 加观察 1 加思考 2 加行动 2 加观察 2，依此类推。每个中间步骤还冗余地带上了最初的提示词。

ReWOO 只付一次 planner 提示词（大）、N 个小的 worker 提示词（每个只有工具调用，没有链条），和一次 solver 提示词。论文在 HotpotQA 上测得 token 减少约 5 倍，同时绝对准确率还 +4 分。

### 为什么它更鲁棒

如果 worker 3 在 ReAct 中失败，循环必须在流程中途从错误里推理出来。在 ReWOO 中，worker 3 返回一条错误字符串；solver 结合原始计划在上下文中看到它，就能优雅地降级。失败定位是按节点、而非按步。

### Planner 蒸馏

论文的第二个结果：因为 planner 看不到观察，你可以用 175B 教师的 planner 输出来微调一个 7B 模型。小模型负责规划；推理时不再需要大模型。这如今已是标配——许多 2026 年的生产智能体用一个小 planner 加一个大 executor，或反过来。

### Plan-and-Execute（2023）

LangChain 团队 2023 年 8 月的帖子把 ReWOO 泛化成了一个模式名：Plan-and-Execute。前置的 planner 产出一个步骤列表，executor 跑每一步，一个可选的 replanner 可以在观察结果后修订计划。这比 ReWOO 更接近 ReAct（replanner 把观察带回了规划），但保留了 token 的节省。

### Plan-and-Act（Erdogan 等人，arXiv:2503.09572，ICML 2025）

Plan-and-Act 把这个模式扩展到了长时程的网页和移动智能体。关键贡献是合成计划数据：一个带标签的轨迹生成器产出「计划显式存在」的训练数据。用它来微调 planner 模型，让它们在 WebArena 类任务上跑过 30–50 步仍保持连贯——而单条 ReAct 轨迹在此会失去连贯性。

### 该选哪个

| 模式 | 适用场景 |
|---------|------|
| ReAct | 短任务、未知环境、需要响应式异常处理 |
| ReWOO | 工具已知的结构化任务、对 token 敏感、证据可并行 |
| Plan-and-Execute | 类似 ReWOO，但在部分执行后可重新规划 |
| Plan-and-Act | 长时程（>30 步）、网页/移动/computer-use |
| Tree of Thoughts | 值得为搜索付出代价（第 4 课） |

Anthropic 2024 年 12 月的指引：从最简单的开始。如果任务只是「一次工具调用加一个总结」，就不要搭 ReWOO。如果任务是 40 步的研究任务，就不要只用 ReAct。

```figure
rewoo-plan
```

## Build It

`code/main.py` 实现了一个玩具 ReWOO：

- `Planner` —— 一个脚本化策略，从提示词产出一个计划 DAG。
- `Worker` —— 通过注册表派发每个节点的工具调用。
- `Solver` —— 脚本化组合，读取证据并产出最终答案。
- 依赖解析 —— 形如 `#E1` 的引用被替换为更早的 worker 输出。

这个 demo 用一个两步计划回答「法国的首都的人口是多少，四舍五入到百万？」：(1) 查首都，(2) 查人口，然后求解。

运行它：

```
python3 code/main.py
```

trace 先展示完整计划，再展示 worker 结果，最后是 solver 组合。把 token 计数（我们打印一个粗略的字符数）与 ReAct 式交织运行对比——在这类结构化任务上 ReWOO 胜出。

## Use It

LangGraph 把 Plan-and-Execute 作为一个配方发布（ReAct 用 `create_react_agent`，plan-execute 用自定义图）。CrewAI 的 Flows 直接编码了这个模式：你预先定义任务，Flow DAG 来执行它们。Plan-and-Act 的合成数据方法仍主要是研究性质；运行时模式（显式计划 DAG）通过 LangGraph 和 CrewAI Flows 在生产中落地。

## Ship It

`outputs/skill-rewoo-planner.md` 在给定工具目录的情况下，从用户请求生成一个 ReWOO 计划 DAG。它在交给执行器之前校验计划（无环、每个引用都可解析、每个工具都存在）。

## 练习

1. 为相互独立的计划节点并行化 worker 执行。在一个有 2 个并行组的 6 节点 DAG 上，这能给你带来什么？
2. 加一个在任一 worker 返回错误时触发的 replanner 节点。把 ReWOO 变成 Plan-and-Execute 的最小改动是什么？
3. 用一个小模型（7B 级）替换 `Planner`，把 `Solver` 留在前沿模型上。比较端到端质量——这个分工在哪里会失败？
4. 读 ReWOO 论文关于 planner 蒸馏的第 4 节。概念性地复现 175B -> 7B 的结果：你需要什么训练数据，如何给计划质量打分？
5. 把玩具移植到 Plan-and-Act 的轨迹形状：计划是一个序列，而非 DAG。哪些权衡会改变？

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| ReWOO | 「无观察推理」 | 先计划，再并行抓证据，最后求解——规划提示词中没有观察 |
| Plan-and-Execute | 「LangChain 的 plan-execute 模式」 | 带一个可选执行后 replanner 节点的 ReWOO |
| Plan-and-Act | 「扩展的 plan-execute」 | 显式 planner/executor 分工 + 面向长时程任务的合成计划训练数据 |
| Evidence reference | 「#E1, #E2, ...」 | 计划节点占位符，派发时替换为先前的 worker 输出 |
| Planner distillation | 「小 planner、大 executor」 | 在大教师的 planner 轨迹上微调一个小模型 |
| Token efficiency | 「更少的往返」 | 论文中 HotpotQA 上比 ReAct 少 5 倍 token |
| DAG executor | 「拓扑派发器」 | 按依赖顺序运行计划节点；每一层内并行 |

## 延伸阅读

- [Xu 等人，ReWOO: Decoupling Reasoning from Observations（arXiv:2305.18323）](https://arxiv.org/abs/2305.18323)——经典原论文
- [Erdogan 等人，Plan-and-Act（arXiv:2503.09572）](https://arxiv.org/abs/2503.09572)——带合成计划的规模化 planner-executor
- [LangGraph Plan-and-Execute 教程](https://docs.langchain.com/oss/python/langgraph/overview)——框架配方
- [Anthropic，Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)——选最有效的简单模式