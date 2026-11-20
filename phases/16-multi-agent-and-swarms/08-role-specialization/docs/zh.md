# 角色专业化——Planner、Critic、Executor、Verifier

> 2026 年最常见的一种多智能体分解：一个 agent 规划，一个执行，一个批判或校验。MetaGPT（arXiv:2308.00352）把它形式化为编码进角色 prompt 的 SOP——Product Manager、Architect、Project Manager、Engineer、QA Engineer——遵循 `Code = SOP(Team)`。ChatDev（arXiv:2307.07924）把 designer、programmer、reviewer、tester 串成一条“聊天链”，并配有“沟通式去幻觉”（communicative dehallucination，agent 会显式索取缺失的细节）。校验者是承重角色：Cemri 等人（MAST，arXiv:2503.13657）表明，每一种多智能体失效都可追溯到缺失或失效的校验。PwC 报告称，在 CrewAI 中采用结构化校验循环带来了 7 倍准确率提升（10% → 70%）。

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** 第 16 阶段，第 04 课（Primitive Model）、第 05 课（Supervisor）
**Time:** ~60 分钟

## 问题场景

通用型多智能体系统产出通用型的输出。三个程序员在一个 group chat 里写出三段风味相同、都平庸的代码。你可以加更多 agent、加更多轮次，仍然跨不过质量门槛。

解法不是更多 agent——而是*不同*的 agent。指派各不相同的角色。给批判者一些规划者没有的工具。给校验者一套客观的测试。这样系统内部就有了分歧，也有基于事实的纠错，而不只是并行地猜。

## 核心概念

### 四个经典角色

**Planner。** 读取目标，产出步骤列表或一份规格说明。工具：知识检索、文档。输出：结构化的计划。

**Executor。** 一次读取一个计划步骤，产出工件。工具：真正干活的工具（代码编译器、shell、API 客户端）。输出：工件。

**Critic。** 对照规划者的意图来阅读执行者的输出。工具：对工件的只读访问、静态分析。输出：接受/拒绝，并给出理由。

**Verifier。** 读取工件并运行确定性检查。工具：测试运行器、类型检查器、schema 校验器。输出：通过/失败，并给出证据。

Critic 是主观的、带判断的，通常由 LLM 担任。Verifier 是客观的、确定性的，通常由代码担任。它们不是同一个角色。

### MetaGPT 的 SOP 模式

MetaGPT（arXiv:2308.00352）把软件工程的 SOP 编码成角色 prompt：

- **Product Manager** 撰写 PRD。
- **Architect** 产出系统设计。
- **Project Manager** 拆分任务。
- **Engineer** 实现。
- **QA Engineer** 运行测试。

每个角色都有严格的输入/输出 schema。角色 prompt 说明这个角色*是什么*，以及它*必须产出*什么。`Code = SOP(Team)` 这一表述的含义是——确定性的 SOP 把一支 LLM 团队变成一条可预测的流水线。

### ChatDev 的沟通式去幻觉

ChatDev 增加了一个关键动作：当执行者需要一个计划里没有的具体细节时，它会在继续之前显式地向 designer 询问。这避免了 LLM 的经典失效——凭空编造出一个看似合理的细节。

实现方式：角色 prompt 中写明“当你需要未被提供的具体信息时，在产出输出之前按名字向相关角色询问。”

### 为什么校验者最重要

Cemri 等人（MAST）追踪了 1642 次多智能体执行失败。21.3% 是校验缺口——系统交付了一个没人检查过的答案。其余 79% 也往往可以追溯到“有一次检查静默失败，或者根本没运行”。校验是承重角色。

PwC 报告称（CrewAI 部署，2025），加入一个结构化校验循环把准确率从 10% 提升到 70%。一个角色带来 7 倍提升。

### Critic 对比 Verifier

- Critic 是一个 LLM 在审查工件的质量。主观。可能被看似合理的文字骗过。
- Verifier 是一个运行在工件上的确定性程序。客观。给出带证据的通过/失败。

两者都用。Critic 能抓到 Verifier 说不清的口味问题。Verifier 能抓到 Critic 看不见的 bug，因为这些 bug 只在运行时才显现。

### 反模式

你系统里每个角色都是 LLM，每个角色的输出都是“我看挺好”。这是经典的 MAST 失效模式。至少要有一个 Verifier，其通过/失败由代码而非 LLM 决定。

### 框架映射

- **CrewAI** —— `Agent(role, goal, backstory)` 就是教科书式的专业化接口。
- **LangGraph** —— 节点可以拥有专门的 prompt；边来强制流水线。
- **AutoGen** —— 在 GroupChat 中使用名字只有一个词的、角色专属的 ConversableAgent。
- **OpenAI Agents SDK** —— 在角色专业化的 Agent 之间用 handoff 工具。

```figure
swarm-roles
```

## Build It

`code/main.py` 实现了一条 4 个角色的流水线，用来构建一个简单的 Python 函数：

- **Planner** 产出一份规格。
- **Executor** 生成一段代码字符串。
- **Critic**（模拟 LLM）标出明显的问题。
- **Verifier** 在沙箱（`exec`）里用测试用例运行生成的代码。

演示运行两次：一次是执行者产出正确代码（Critic 与 Verifier 都通过），一次是执行者产出偏离规格的代码（Critic 因为代码看似合理而漏掉 bug，Verifier 因为测试失败而抓到它）。

运行：

```
python3 code/main.py
```

## Use It

`outputs/skill-role-designer.md` 接收一个任务，产出角色名册（3-5 个角色）、每个角色的输入/输出 schema，以及 Verifier 检查。在把 agent 接入框架之前先用它。

## Ship It

检查清单：

- **至少一个确定性校验器。** 绝不要全 LLM。
- **每个角色有显式 I/O schema。** 规划者返回一份规格，而不是一段散文；执行者读取那个 schema。
- **沟通式去幻觉。** 执行者缺信息时必须询问规划者；绝不要臆造。
- **Critic/Verifier 的顺序。** 先运行 Critic（便宜，抓设计问题），再运行 Verifier（慢，抓 bug）。
- **循环预算。** 升级到人工之前，最多 2 轮 Critic-Executor 修订。

## Exercises

1. 运行 `code/main.py`，观察 Verifier 如何抓到 Critic 漏掉的 bug。加一项静态分析检查（统计 `return` 出现的次数）作为额外的 Verifier。它抓到了运行时测试漏掉的什么？
2. 增加第 5 个角色：“需求分析师”，把用户的愿望翻译成规划者可直接使用的规格。应当有哪些沟通式去幻觉的请求向上流向它？
3. 阅读 MetaGPT 第 3 节（“Agents”）。列出 MetaGPT 五个角色各自的输入/输出 schema。
4. 阅读 ChatDev 的聊天链图（arXiv:2307.07924 图 3）。找出沟通式去幻觉在何处打破了一个否则会无限进行的循环。
5. PwC 的 7 倍准确率提升来自校验循环。假设三个加校验器也不会有帮助的任务——在这些任务上，对正确性的确定性检查要么不可能，要么成本高得离谱。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Role specialization | “不同的 agent，不同的活” | 为 planner/executor/critic/verifier 角色分别调校的、各不相同的系统 prompt。 |
| SOP pattern | “编码好的标准作业流程” | MetaGPT 的框架：每个角色有严格的 I/O schema，把团队变成流水线。 |
| Communicative dehallucination | “先问再编” | ChatDev 模式：缺失细节时执行者去问规划者，而不是编一个。 |
| Critic | “LLM 审稿人” | 主观、带判断的审查者。抓口味问题。可能被看似合理的文字骗过。 |
| Verifier | “确定性检查” | 基于代码的通过/失败。测试运行器、类型检查器、schema 校验器。骗不过。 |
| Verification gap | “没人检查” | 占 MAST 失效的 21.3%。答案在缺少本可抓到 bug 的检查的情况下被交付。 |
| Revision loop | “审查者打回” | Critic 拒绝会触发执行者带反馈重跑。需要预算。 |
| All-LLM anti-pattern | “我看挺好” | 每个角色都是 LLM，没有确定性检查。经典的 MAST 失效。 |

## Further Reading

- [Hong et al. — MetaGPT: Meta Programming for Multi-Agent Collaboration](https://arxiv.org/abs/2308.00352) — 把 SOP 作为角色 prompt 的参考论文
- [Qian et al. — Communicative Agents for Software Development (ChatDev)](https://arxiv.org/abs/2307.07924) — 聊天链 + 沟通式去幻觉
- [Cemri et al. — Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/abs/2503.13657) — MAST 分类法；校验缺口占失效的 21.3%
- [CrewAI docs — Agent roles](https://docs.crewai.com/en/introduction) — 生产级的角色规格接口
