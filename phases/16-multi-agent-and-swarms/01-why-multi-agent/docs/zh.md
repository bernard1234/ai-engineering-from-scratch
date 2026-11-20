# 为什么要用 multi-agent？

> 单个 agent 会撞上墙。聪明的做法不是做一个更大的 agent——而是做更多 agent。

**Type:** Learn
**Languages:** TypeScript
**Prerequisites:** 第 14 阶段（Agent Engineering）
**Time:** ~60 分钟

## Learning Objectives

- 识别单 agent 的天花板（context 溢出、专长混杂、串行瓶颈），并说明何时拆分成多个 agent 才是正确做法
- 比较各种编排模式（pipeline、并行 fan-out、supervisor、hierarchical），并为给定任务结构选择合适的一种
- 设计一个 multi-agent 系统，具备清晰的职责边界、共享状态和通信约定
- 分析 multi-agent 复杂度（延迟、成本、调试难度）与单 agent 简洁性之间的权衡

## 问题场景

你在第 14 阶段构建了一个单 agent。它能工作。它能读文件、运行命令、调用 API，并对结果进行推理。然后你把它指向一个真实的代码库：200 个文件、三种语言、依赖基础设施的测试，以及在写代码之前需要调研外部 API 的要求。

agent 卡住了。不是因为 LLM 笨，而是因为任务超出了单个 agent 循环能处理的范围。context window 被文件内容填满。agent 忘记了它在 40 次 tool call 之前读过什么。它试图同时扮演研究者、编码者和审查者，结果三样都做得很差。

这就是单 agent 的天花板。每当任务需要以下条件时，你就会撞上它：

- **上下文超过单个窗口的容量**——读取 50 个文件就会冲破 200k tokens
- **不同阶段需要不同的专长**——调研所需的 prompt 与代码生成不同
- **可以并行进行的工作**——既然能同时读三个文件，为什么还要串行读？

## 核心概念

### 单 agent 的天花板

单个 agent 就是一个循环、一个 context window、一个 system prompt。想象一下：

```
┌─────────────────────────────────────────┐
│            SINGLE AGENT                 │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │         Context Window            │  │
│  │                                   │  │
│  │  research notes                   │  │
│  │  + code files                     │  │
│  │  + test output                    │  │
│  │  + review feedback                │  │
│  │  + API docs                       │  │
│  │  + ...                            │  │
│  │                                   │  │
│  │  ██████████████████████ FULL ███  │  │
│  └───────────────────────────────────┘  │
│                                         │
│  One system prompt tries to cover       │
│  research + coding + review + testing   │
│                                         │
│  Result: mediocre at everything         │
└─────────────────────────────────────────┘
```

有三个地方会出问题：

1. **上下文饱和**——tool 结果不断堆积。到第 30 轮时，agent 已消耗 150k tokens 的文件内容、命令输出和先前推理。第 5 轮的关键细节丢失了。

2. **角色混淆**——让 system prompt 同时声明“你是研究者、编码者、审查者和测试者”，产出的 agent 只会半调研、半编码，审查永远做不完。

3. **串行瓶颈**——agent 先读文件 A，再读文件 B，然后读文件 C。三次串行 LLM 调用。三次串行 tool 执行。毫无并行。

### multi-agent 解法

拆分工作。给每个 agent 一个职责、一个 context window 和一份专门为该职责调优的 system prompt：

```
┌──────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                          │
│                                                          │
│  "Build a REST API for user management"                  │
│                                                          │
│         ┌──────────┬──────────┬──────────┐               │
│         │          │          │          │               │
│         ▼          ▼          ▼          ▼               │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│   │RESEARCHER│ │  CODER   │ │ REVIEWER │ │  TESTER  │  │
│   │          │ │          │ │          │ │          │  │
│   │ Reads    │ │ Writes   │ │ Checks   │ │ Runs     │  │
│   │ docs,    │ │ code     │ │ code     │ │ tests,   │  │
│   │ finds    │ │ based on │ │ quality, │ │ reports  │  │
│   │ patterns │ │ research │ │ finds    │ │ results  │  │
│   │          │ │ + spec   │ │ bugs     │ │          │  │
│   └─────┬────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │
│         │           │            │             │         │
│         └───────────┴────────────┴─────────────┘         │
│                          │                               │
│                     Merge results                        │
└──────────────────────────────────────────────────────────┘
```

每个 agent 都拥有：
- 一份聚焦的 system prompt（“你是代码审查者。你唯一的职责是找出 bug。”）
- 自己的 context window（不会被其他 agent 的工作污染）
- 清晰的输入/输出约定（接收调研笔记，输出代码）

### 真实的系统实践

**Claude Code subagents**——当 Claude Code 用 `Task` 派生子 agent 时，它会创建一个带限定任务的子 agent。父 agent 保持 context 干净。子 agent 做聚焦的工作并返回摘要。

**Devin**——运行一个 planner agent、一个 coder agent 和一个 browser agent。planner 把工作拆成步骤。coder 写代码。browser 调研文档。每个 agent 都有独立的 context。

**Multi-agent coding teams（SWE-bench）**——在 SWE-bench 上表现最好的系统使用一个读代码库的 researcher、一个设计修复方案的 planner，以及一个实现修复的 coder。单 agent 系统的得分更低。

**ChatGPT Deep Research**——并行派生多个搜索 agent，每个探索不同角度，然后综合结果。

### 光谱

multi-agent 不是非黑即白，而是一个光谱：

```
SIMPLE ──────────────────────────────────────────── COMPLEX

 Single        Sub-         Pipeline      Team         Swarm
 Agent         agents

 ┌───┐       ┌───┐        ┌───┐───┐    ┌───┐───┐    ┌─┐┌─┐┌─┐
 │ A │       │ A │        │ A │ B │    │ A │ B │    │ ││ ││ │
 └───┘       └─┬─┘        └───┘─┬─┘    └─┬─┘─┬─┘    └┬┘└┬┘└┬┘
               │                │        │   │       ┌┴──┴──┴┐
             ┌─┴─┐          ┌───┘───┐    │   │       │shared │
             │ a │          │ C │ D │  ┌─┴───┴─┐    │ state │
             └───┘          └───┘───┘  │  msg   │    └───────┘
                                       │  bus   │
 1 loop      Parent +      Stage by    │       │    N peers,
 1 context   child tasks   stage       └───────┘    emergent
                                       Explicit      behavior
                                       roles
```

**单 agent**——一个循环、一个 prompt。适合简单任务。

**Subagents**——父 agent 派生若干子 agent 处理聚焦的子任务。父 agent 维护计划，子 agent 回报结果。这正是 Claude Code 的做法。

**Pipeline**——agent 依次运行。agent A 的输出成为 agent B 的输入。适合分阶段工作流：research -> code -> review -> test。

**Team**——agent 并行运行，共享一条消息总线。每个 agent 有角色。由一个 orchestrator 协调。适合需要同时使用多种技能的任务。

**Swarm**——大量相同或近乎相同的 agent 共享状态。没有固定的 orchestrator。agent 从队列中领取工作。适合高吞吐的并行任务。

### 四种 multi-agent 模式

#### 模式 1：Pipeline

```
Input ──▶ Agent A ──▶ Agent B ──▶ Agent C ──▶ Output
          (research)  (code)      (review)
```

每个 agent 转换数据并向前传递。易于推演。任一阶段失败会阻塞后续所有阶段。

#### 模式 2：Fan-out / Fan-in

```
                ┌──▶ Agent A ──┐
                │              │
Input ──▶ Split ├──▶ Agent B ──├──▶ Merge ──▶ Output
                │              │
                └──▶ Agent C ──┘
```

把工作拆给并行的 agent，再合并结果。适合可分解为独立子任务的任务。

#### 模式 3：Orchestrator-Worker

```
                    ┌──────────┐
                    │  Orch.   │
                    └──┬───┬───┘
                  task │   │ task
                 ┌─────┘   └─────┐
                 ▼               ▼
           ┌──────────┐   ┌──────────┐
           │ Worker A │   │ Worker B │
           └──────────┘   └──────────┘
```

一个聪明的 orchestrator 决定做什么、委派给 worker，并综合结果。orchestrator 本身就是一个拥有派生 worker 工具的 agent。

#### 模式 4：Peer Swarm

```
         ┌───┐ ◄──── msg ────▶ ┌───┐
         │ A │                  │ B │
         └─┬─┘                  └─┬─┘
           │                      │
      msg  │    ┌───────────┐     │ msg
           └───▶│  Shared   │◄────┘
                │  State    │
           ┌───▶│  / Queue  │◄────┐
           │    └───────────┘     │
      msg  │                      │ msg
         ┌─┴─┐                  ┌─┴─┐
         │ C │ ◄──── msg ────▶ │ D │
         └───┘                  └───┘
```

没有中心 orchestrator。agent 之间点对点通信。决策从交互中涌现。更难调试，但可扩展到大量 agent。

### 何时不要用 multi-agent

multi-agent 会增加复杂度。agent 之间的每条消息都是潜在的失败点。调试从“读一段对话”变成“跨五个 agent 追踪消息”。

**以下情况保持单 agent：**
- 任务能放进一个 context window（工作数据低于约 100k tokens）
- 不需要为不同阶段使用不同的 system prompt
- 串行执行已经足够快
- 任务足够简单，拆分带来的开销大于价值

**复杂度成本：**
- 每个 agent 边界都是一次有损压缩：agent A 的完整 context 被概括成一条发给 agent B 的消息
- 协调逻辑（谁做什么、何时做、按什么顺序）本身就是 bug 的来源
- 延迟增加：N 个 agent 意味着至少 N 次串行 LLM 调用，若需要来回沟通则更多
- 成本成倍增长：每个 agent 都独立消耗 tokens

经验法则：如果任务少于 20 次 tool call 且能放进 100k tokens，就保持单 agent。

```figure
swarm-messages
```

## Build It

### 步骤 1：超载的单 agent

这是一个试图包办一切的 agent。它有一份庞大的 system prompt，以及一个同时装着调研、代码和审查的 context window：

```typescript
type AgentResult = {
  content: string;
  tokensUsed: number;
  toolCalls: number;
};

async function singleAgentApproach(task: string): Promise<AgentResult> {
  const systemPrompt = `You are a full-stack developer. You must:
1. Research the requirements
2. Write the code
3. Review the code for bugs
4. Write tests
Do ALL of these in a single conversation.`;

  const contextWindow: string[] = [];
  let totalTokens = 0;
  let totalToolCalls = 0;

  const research = await fakeLLMCall(systemPrompt, `Research: ${task}`);
  contextWindow.push(research.output);
  totalTokens += research.tokens;
  totalToolCalls += research.calls;

  const code = await fakeLLMCall(
    systemPrompt,
    `Given this research:\n${contextWindow.join("\n")}\n\nNow write code for: ${task}`
  );
  contextWindow.push(code.output);
  totalTokens += code.tokens;
  totalToolCalls += code.calls;

  const review = await fakeLLMCall(
    systemPrompt,
    `Given all previous context:\n${contextWindow.join("\n")}\n\nReview the code.`
  );
  contextWindow.push(review.output);
  totalTokens += review.tokens;
  totalToolCalls += review.calls;

  return {
    content: contextWindow.join("\n---\n"),
    tokensUsed: totalTokens,
    toolCalls: totalToolCalls,
  };
}
```

这种做法的问题：
- context window 随每个阶段膨胀。到了审查步骤，它同时包含调研笔记、代码和先前的推理。
- system prompt 是通用的，无法为每个阶段调优。
- 没有任何部分并行运行。

### 步骤 2：专家 agent

现在拆开。每个 agent 只负责一件事：

```typescript
type SpecialistAgent = {
  name: string;
  systemPrompt: string;
  run: (input: string) => Promise<AgentResult>;
};

function createSpecialist(name: string, systemPrompt: string): SpecialistAgent {
  return {
    name,
    systemPrompt,
    run: async (input: string) => {
      const result = await fakeLLMCall(systemPrompt, input);
      return {
        content: result.output,
        tokensUsed: result.tokens,
        toolCalls: result.calls,
      };
    },
  };
}

const researcher = createSpecialist(
  "researcher",
  "You are a technical researcher. Read documentation, find patterns, and summarize findings. Output only the facts needed for implementation."
);

const coder = createSpecialist(
  "coder",
  "You are a senior TypeScript developer. Given requirements and research notes, write clean, tested code. Nothing else."
);

const reviewer = createSpecialist(
  "reviewer",
  "You are a code reviewer. Find bugs, security issues, and logic errors. Be specific. Cite line numbers."
);
```

每个专家都有一份聚焦的 prompt。每个专家都得到干净的 context window，只包含它需要的输入。

### 步骤 3：通过消息协调

用显式的消息传递把专家们串起来：

```typescript
type AgentMessage = {
  from: string;
  to: string;
  content: string;
  timestamp: number;
};

async function multiAgentApproach(task: string): Promise<AgentResult> {
  const messages: AgentMessage[] = [];
  let totalTokens = 0;
  let totalToolCalls = 0;

  const researchResult = await researcher.run(task);
  messages.push({
    from: "researcher",
    to: "coder",
    content: researchResult.content,
    timestamp: Date.now(),
  });
  totalTokens += researchResult.tokensUsed;
  totalToolCalls += researchResult.toolCalls;

  const coderInput = messages
    .filter((m) => m.to === "coder")
    .map((m) => `[From ${m.from}]: ${m.content}`)
    .join("\n");

  const codeResult = await coder.run(coderInput);
  messages.push({
    from: "coder",
    to: "reviewer",
    content: codeResult.content,
    timestamp: Date.now(),
  });
  totalTokens += codeResult.tokensUsed;
  totalToolCalls += codeResult.toolCalls;

  const reviewerInput = messages
    .filter((m) => m.to === "reviewer")
    .map((m) => `[From ${m.from}]: ${m.content}`)
    .join("\n");

  const reviewResult = await reviewer.run(reviewerInput);
  messages.push({
    from: "reviewer",
    to: "orchestrator",
    content: reviewResult.content,
    timestamp: Date.now(),
  });
  totalTokens += reviewResult.tokensUsed;
  totalToolCalls += reviewResult.toolCalls;

  return {
    content: messages.map((m) => `[${m.from} -> ${m.to}]: ${m.content}`).join("\n\n"),
    tokensUsed: totalTokens,
    toolCalls: totalToolCalls,
  };
}
```

每个 agent 只收到发给自己的消息。没有 context 污染。researcher 读文档产生的 50k tokens 永远不会进入 reviewer 的 context。

### 步骤 4：对比

```typescript
async function compare() {
  const task = "Build a rate limiter middleware for an Express.js API";

  console.log("=== Single Agent ===");
  const single = await singleAgentApproach(task);
  console.log(`Tokens: ${single.tokensUsed}`);
  console.log(`Tool calls: ${single.toolCalls}`);

  console.log("\n=== Multi-Agent ===");
  const multi = await multiAgentApproach(task);
  console.log(`Tokens: ${multi.tokensUsed}`);
  console.log(`Tool calls: ${multi.toolCalls}`);
}
```

multi-agent 版本使用了更多总 tokens（三个 agent、三次独立的 LLM 调用），但每个 agent 的 context 保持干净。因为 system prompt 是专门化的，每个阶段的质量都提高了。

## Use It

本课产出一个可复用的 prompt，用于判断何时该采用 multi-agent。见 `outputs/prompt-multi-agent-decision.md`。

## Exercises

1. 增加第四个专家：一个 “tester” agent，它接收 coder 的代码和 reviewer 的审查反馈，然后编写测试
2. 修改 pipeline，让 reviewer 能把反馈发回给 coder 形成修订循环（最多 2 轮）
3. 把串行 pipeline 改成 fan-out：并行运行 researcher 和一个 “requirements analyzer” agent，然后先合并它们的输出再传给 coder

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|----------------------|
| Swarm | “AI agent 的蜂群思维” | 一组共享状态、没有固定 leader 的对等 agent。行为从局部交互中涌现。 |
| Orchestrator | “老板 agent” | 一个 agent，其工具集包含派生和管理其他 agent 的能力。它负责计划和委派，但可能不亲自完成实际工作。 |
| Coordinator | “交通警察” | 一个非 agent 组件（通常只是代码，不是 LLM），按规则在 agent 之间路由消息。 |
| Consensus | “agent 们达成一致” | 一种协议：多个 agent 在继续之前必须达成一致。用于需要裁决冲突输出的场景。 |
| Emergent behavior | “agent 们自己搞明白了” | 从 agent 交互中涌现、但从未被显式编程的系统级模式。可能有用，也可能有害。 |
| Fan-out / fan-in | “给 agent 用的 map-reduce” | 把任务拆分到并行的 agent（fan-out），再合并它们的结果（fan-in）。 |
| Message passing | “agent 之间互相说话” | agent 之间的通信机制：从一个 agent 发送到另一个 agent 的结构化数据，取代共享 context window。 |

## Further Reading

- [The Landscape of Emerging AI Agent Architectures](https://arxiv.org/abs/2409.02977)——multi-agent 模式综述
- [AutoGen: Enabling Next-Gen LLM Applications](https://arxiv.org/abs/2308.08155)——微软的 multi-agent 对话框架
- [Claude Code subagents documentation](https://docs.anthropic.com/en/docs/claude-code)——Claude Code 如何用 Task 委派
- [CrewAI documentation](https://docs.crewai.com/)——基于角色的 multi-agent 框架
