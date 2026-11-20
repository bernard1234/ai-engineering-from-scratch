# Group Chat 与发言者选择

> 共享会话式编排把 N 个 agent 放进同一个会话；由一个选择器函数（LLM、轮转或自定义）决定下一个谁发言。这是涌现式多智能体会话的原型——agent 并不知道自己在静态图中的角色，它们只是对共享池做出反应。AutoGen GroupChat 与 AG2 GroupChat 是参考实现：AutoGen v0.2 的 GroupChat 语义被保留在 AG2 分叉中；AutoGen v0.4 把它重写为事件驱动的 actor 模型。微软在 2026 年 2 月把 AutoGen 转入维护模式，并将它与 Semantic Kernel 合并成 Microsoft Agent Framework（2026 年 2 月 RC）。GroupChat 原语在 AG2 和 Microsoft Agent Framework 中都保留了下来——学一次，到处可用。

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** 第 16 阶段，第 04 课（Primitive Model）
**Time:** ~60 分钟

## 问题场景

当工作流已知时，静态图（LangGraph）非常好用。真实对话不是静态的：有时是程序员问审查者，有时是问研究员，有时是问写作者。把每一种可能的交接都硬编码，会造成边的爆炸。你想要的是*对共享池做出反应的 agent*，并由某个函数决定下一个谁说话。

这正是 AutoGen GroupChat 所做的事。

## 核心概念

### 结构形态

```
              ┌─── shared pool ────┐
              │   m1  m2  m3  ...  │
              └─────────┬──────────┘
                        │ (everyone reads all)
      ┌───────┬─────────┼─────────┬───────┐
      ▼       ▼         ▼         ▼       ▼
    Agent A  Agent B  Agent C  Agent D  Selector
                                           │
                                           ▼
                                  "next speaker = C"
```

每个 agent 都能看到每一条消息。每一轮都会调用一个选择器函数来挑选下一个发言者。

### 三种选择器风格

**轮转（Round-robin）。** 固定循环。确定性。随 N 线性扩展，但忽略上下文——即使话题是法务审查，程序员也会轮到发言。

**LLM 选择（LLM-selected）。** 调用一次 LLM，读取近期的池子并返回最合适的下一个发言者。能感知上下文但慢：每一轮都增加一次 LLM 调用。AutoGen 的默认方式。

**自定义（Custom）。** 一个 Python 函数，逻辑随你写。典型做法：LLM 选择加兜底规则（例如“程序员的下一轮总是交给校验者”）。

### ConversableAgent API

```
agent = ConversableAgent(
    name="coder",
    system_message="You write Python.",
    llm_config={...},
)
chat = GroupChat(agents=[coder, reviewer, tester], messages=[])
manager = GroupChatManager(groupchat=chat, llm_config={...})
```

`GroupChatManager` 持有选择器。当一个 agent 完成一轮，管理者调用选择器，选择器返回下一个 agent。循环一直持续到某个终止条件。

### 终止

三种常见模式：

- **最大轮数。** 对总轮数设硬上限。
- **“TERMINATE” token。** agent 可以发出一个哨兵消息；管理者一旦看到它就停止。
- **目标达成检查。** 每一轮运行一个轻量校验器，完成后停止会话。

### 谱系：分叉与合并

2025 年初，微软开始围绕事件驱动的 actor 模型对 AutoGen（v0.4）进行大规模重写。社区把 AutoGen v0.2 的 GroupChat 语义分叉为 AG2，保留了早期采用者已经集成过的 API。

2026 年 2 月，微软宣布 AutoGen 将进入维护模式，事件驱动的 actor 模型并入 **Microsoft Agent Framework**（2026 年 2 月 RC，现已与 Semantic Kernel 合并）。GroupChat 的概念在两条线上都保留下来；实现细节不同。AG2 是兼容 v0.2 代码的首选上游。

### GroupChat 适合什么

- **涌现式会话。** 你不想预先接好每一个可能的下一位发言者。
- **混合角色的任务。** 程序员问研究员，研究员问档案管理员，档案管理员又问回程序员。流程不是 DAG。
- **探索式解题。** 想的是“头脑风暴会”，而不是“装配线”。

### 它在哪儿会失效

- **严格确定性。** LLM 选择器可能不稳定。同样的 prompt，不同的运行，不同的下一位发言者。
- **谄媚级联。** agent 都顺从发言最自信的那个。要显式地反向提示。
- **上下文膨胀。** 每个 agent 都读每一条消息；10 轮之后上下文就很庞大。用投影（第 15 课）来限定视野。
- **热门发言者。** 某个 agent 因为选择器偏爱它的专长而主导会话。把发言均衡作为选择器的一项特性。

### Group chat 对比 supervisor

相同的原语，不同的默认值：

- Supervisor：一个 agent 规划，其他 agent 执行。选择器就是“问规划者接下来做什么”。
- Group chat：所有 agent 都是同侪；选择器是一个作用于共享池的函数。

两者都使用第 04 课的四个原语。Group chat 默认采用 LLM 选择的编排和全池共享状态。

```figure
swarm-speaker
```

## Build It

`code/main.py` 用标准库从零实现一个 GroupChat。三个 agent（coder、reviewer、manager）、轮转与 LLM 选择两种变体，以及基于 `TERMINATE` token 的终止。

演示会打印会话记录，以及两种变体下选择器的决策轨迹。

运行：

```
python3 code/main.py
```

## Use It

`outputs/skill-groupchat-selector.md` 为给定任务配置 GroupChat 选择器——轮转、LLM 选择还是自定义，以及使用哪些选择器输入（近期消息、agent 专长、轮次计数）。

## Ship It

检查清单：

- **最大轮数上限。** 永远要有。典型任务 10-20。
- **发言均衡指标。** 跟踪每个 agent 的轮次；当不均衡超过阈值时告警。
- **终止 token。** `TERMINATE` 或一个专用校验者 agent。
- **投影或限定范围记忆。** 约 10 条消息之后，考虑给每个 agent 只提供一个限定范围的视野，以防上下文膨胀。
- **选择器日志。** 对 LLM 选择的变体，既要记录选择器的输入，也要记录它的选择。否则调试不可能。

## Exercises

1. 运行 `code/main.py`。对比轮转与 LLM 选择下的会话。各自是哪个 agent 主导？
2. 在选择器里加一条“每 agent 最大发言次数”规则。它如何影响会话记录？
3. 实现一个目标达成终止：当 reviewer 返回 “approved” 时停止。它在触及轮数上限之前多久触发一次？
4. 阅读 AutoGen 稳定版文档中关于 GroupChat 的内容（https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/design-patterns/group-chat.html）。找出 `GroupChatManager` 使用的默认选择器。
5. 阅读 AG2 仓库（https://github.com/ag2ai/ag2），把它的 v0.2 GroupChat 与 v0.4 事件驱动版本做对比。v0.4 增加了哪个具体属性（吞吐、容错、可组合性）？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| GroupChat | “agent 在一个聊天室” | 共享消息池 + 选择器函数。AutoGen / AG2 原语。 |
| Speaker selection | “下一个谁说话” | 挑选下一个 agent 的函数。轮转、LLM 选择或自定义。 |
| GroupChatManager | “会议主持” | 持有选择器并循环推进轮次的 AutoGen 组件。 |
| ConversableAgent | “基础 agent” | AutoGen 基类；一个能收发消息的 agent。 |
| Termination token | “那个‘停’字” | 结束会话的哨兵字符串（通常是 `TERMINATE`）。 |
| Hot speaker | “一个 agent 主导” | 选择器不断挑选同一个 agent 的失效模式。 |
| Context bloat | “池子无界膨胀” | 每个 agent 都读此前每条消息；上下文随轮次增长。 |
| Projection | “限定视野” | 对共享池的角色专属视图，用来防止上下文膨胀。 |

## Further Reading

- [AutoGen group chat docs](https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/design-patterns/group-chat.html) — 参考实现
- [AG2 repo](https://github.com/ag2ai/ag2) — 社区接续的 AutoGen v0.2
- [Microsoft Agent Framework docs](https://learn.microsoft.com/en-us/agent-framework/) — 合并后的继任者，2026 年 2 月 RC
- [AutoGen v0.4 release notes](https://microsoft.github.io/autogen/stable/) — 事件驱动 actor 模型重写的细节
