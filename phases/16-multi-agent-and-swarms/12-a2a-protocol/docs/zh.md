# A2A —— Agent-to-Agent 协议

> Google 于 2025 年 4 月发布 A2A；到 2026 年 4 月，规范位于 https://a2a-protocol.org/latest/specification/，并有 150+ 家组织支持。A2A 是 MCP（第 13 课）的水平互补：MCP 是垂直的（agent ↔ tools），A2A 是点对点的（agent ↔ agent）。它定义了 Agent Card（发现）、带 artifact 的 task（text、structured data、video）、不透明的 task 生命周期以及 auth。生产系统日益把 MCP 与 A2A 搭配使用。Google Cloud 在 2025-2026 年间把 A2A 支持加入了 Vertex AI Agent Builder。

**Type:** Learn + Build
**Languages:** Python（stdlib，`http.server`，`json`）
**Prerequisites:** 第 16 阶段，第 04 课（Primitive Model）
**Time:** ~75 分钟

## 问题场景

你的 agent 需要调用另一个系统上的另一个 agent。怎么做？你可以暴露一个 HTTP endpoint、定义一套定制的 JSON schema，然后指望对方也讲这套。于是每一对 agent 都变成一次自定义集成。

A2A 就是这种调用的通用 wire protocol。标准化的发现、标准化的 task 模型、标准化的 transport、标准化的 artifact。它像 HTTP+REST，只不过把 agent 当作一等公民。

## 核心概念

### 四个要素

**Agent Card。** 位于 `/.well-known/agent.json` 的一份 JSON 文档，描述该 agent：name、skills、endpoints、支持的模态、auth 要求。发现的过程就是读取这张 card。

```
GET https://agent.example.com/.well-known/agent.json
→ {
    "name": "code-review-agent",
    "skills": ["review-python", "review-typescript"],
    "endpoints": {
      "tasks": "https://agent.example.com/tasks"
    },
    "auth": {"type": "bearer"},
    "modalities": ["text", "structured"]
  }
```

**Task。** 工作单元。一个异步、有状态的对象，带生命周期：`submitted → working → completed / failed / canceled`。客户端发送一个 task，然后轮询或订阅更新。

**Artifact。** task 产出的结果类型。text、结构化 JSON、image、video、audio。artifact 是带类型的，因此不同模态都是一等公民。

**不透明生命周期。** A2A 不规定远端 agent *如何* 解决 task。客户端只看到状态转换和 artifact；实现方可以自由使用任何框架。

### MCP 与 A2A 的分工

- **MCP**（第 13 课）：agent ↔ tool。agent 通过 JSON-RPC 对 tool server 读写。默认无状态。
- **A2A**：agent ↔ agent。点对点协议；双方都是带自身推理的 agent。

生产级 multi-agent 系统两者都用。一个 A2A 对等方会在自己那侧调用 MCP tool。这种分工让两类关注点保持干净。

### 发现流程

```
Client                     Agent server
  ├──GET /.well-known/agent.json──>
  <──Agent Card JSON─────────────
  ├──POST /tasks {skill, input}──>
  <──201 task_id, state=submitted
  ├──GET /tasks/{id}──────────────>
  <──state=working, 42% done──────
  ├──GET /tasks/{id}──────────────>
  <──state=completed, artifacts──
```

或者用流式：订阅 `/tasks/{id}/events` 的 SSE 以获取推送更新。

### 认证

A2A 支持三种常见模式：

- **Bearer token** —— OAuth2 或不透明 token。
- **mTLS** —— 双向 TLS；组织之间相互证明身份。
- **签名请求** —— 对 payload 做 HMAC。

认证方式在 Agent Card 中声明；客户端发现后照此遵守。

### 到 2026 年 4 月的 150+ 家组织

企业采用推动了 A2A 的规模。要点是：A2A 成为企业 agent 系统跨越信任边界的方式。Google Cloud 发布了 Vertex AI Agent Builder 的 A2A 支持；Microsoft Agent Framework 支持它；多数主流框架（LangGraph、CrewAI、AutoGen）都提供 A2A 适配器。

### A2A 占优的场景

- **跨组织调用。** A 公司的 agent 调用 B 公司的 agent。没有 A2A，每一对都是一份定制契约。
- **异构框架。** LangGraph agent 调用 CrewAI agent，再调用自定义 Python agent。A2A 把这一切归一化。
- **带类型的 artifact。** video 结果、结构化 JSON、audio —— 全都是一等公民。
- **长时间运行的任务。** 不透明生命周期 + 轮询让持续数小时的任务变得简单直接。

### A2A 吃力的场景

- **对延迟敏感的微调用。** A2A 的生命周期是异步的。亚毫秒级的 agent 对 agent 调用不适合；改用直接 RPC。
- **紧耦合的进程内 agent。** 如果两个 agent 运行在同一个 Python 进程里，A2A 的 HTTP 往返就太夸张了。
- **小团队。** 规范带来的开销是真实的；仅内部使用的 agent 可能不需要这种正式度。

### A2A 与 ACP、ANP、NLIP

2024-2026 年间出现了若干相关规范：

- **ACP**（IBM/Linux Foundation）—— A2A 的前身，范围更窄。
- **ANP**（Agent Network Protocol）—— 侧重对等发现，去中心化优先。
- **NLIP**（Ecma Natural Language Interaction Protocol，2025 年 12 月标准化）—— 自然语言内容类型。

截至 2026 年 4 月，A2A 是采用最广的点对点协议。对比参见 arXiv:2505.02279（Liu 等，“A Survey of Agent Interoperability Protocols”）。

```figure
sw-agent-card-discovery
```

## Build It

`code/main.py` 使用 `http.server` 和 JSON 实现一个最小化的 A2A server 与 client。server 会：

- 暴露 `/.well-known/agent.json`，
- 接受 `POST /tasks`，
- 管理 task 状态，
- 在 `GET /tasks/{id}` 时返回 artifact。

client 会：

- 获取 Agent Card，
- 提交一个 task，
- 轮询直到完成，
- 读取 artifact。

运行：

```
python3 code/main.py
```

脚本在后台线程中启动 server，然后让 client 针对它运行。你会看到完整流程：发现、提交、轮询、artifact。

## Use It

`outputs/skill-a2a-integrator.md` 设计一次 A2A 集成：Agent Card 内容、task schema、认证选择、流式还是轮询。

## Ship It

检查清单：

- **锁定规范版本。** A2A 仍在演进；Agent Card 应声明协议版本。
- **幂等的 task 创建。** 重复提交（网络重试）应只产生一个 task。
- **Artifact schema。** 声明 agent 返回的形状；消费方应做校验。
- **限流 + 认证。** A2A 是面向公网的；套用标准 Web 安全。
- **失败 task 的死信处理。** 长期观察模式，找出反复出现的故障类型。

## Exercises

1. 运行 `code/main.py`。确认 client 发现了 server，并收到了正确的 artifact。
2. 给 server 添加第二个 skill（例如“summarize”）。更新 Agent Card。写一个根据 task 类型挑选 skill 的 client。
3. 实现一个 SSE 流式 endpoint：`/tasks/{id}/events`，用于发出状态变化。client 需要做出什么不同的处理？
4. 阅读 A2A 规范（https://a2a-protocol.org/latest/specification/）。找出规范强制要求、而这个演示未实现的三件事。
5. 把 A2A（Agent Card 发现）与 MCP（通过 `listTools` 在 server 侧列出能力）做比较。自描述 agent 与能力探测之间的权衡是什么？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| A2A | “agent 对 agent” | 让 agent 跨系统调用其他 agent 的点对点协议。Google，2025 年。 |
| Agent Card | “agent 的名片” | 位于 `/.well-known/agent.json` 的 JSON，描述 skill、endpoint、auth。 |
| Task | “工作单元” | 带生命周期的异步有状态对象；完成时产出 artifact。 |
| Artifact | “结果” | 带类型的输出：text、结构化 JSON、image、video、audio。一等公民的媒体。 |
| 不透明生命周期 | “怎么解是 agent 自己的事” | 客户端看到状态转换；server 可自由选择框架/工具。 |
| Discovery | “找到那个 agent” | `GET /.well-known/agent.json` 返回 card。 |
| MCP vs A2A | “tool 对 peer” | MCP：垂直的 agent ↔ tool。A2A：水平的 agent ↔ agent。 |
| ACP / ANP / NLIP | “兄弟协议” | 相邻的规范；A2A 是 2026 年采用最广的。 |

## Further Reading

- [A2A 规范](https://a2a-protocol.org/latest/specification/) —— 权威规范
- [Google Developers Blog —— A2A 发布公告](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/) —— 2025 年 4 月的发布文章
- [A2A GitHub 仓库](https://github.com/a2aproject/A2A) —— 参考实现与 SDK
- [Liu 等 —— A Survey of Agent Interoperability Protocols](https://arxiv.org/html/2505.02279v1) —— MCP、ACP、A2A、ANP 对比
