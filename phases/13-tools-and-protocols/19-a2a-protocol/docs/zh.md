# A2A —— Agent-to-Agent 协议

> MCP 是 agent 对 tool。A2A（Agent2Agent）是 agent 对 agent——一种开放协议，让构建在不同框架上的不透明 agent 能够协作。它于 2025 年 4 月由 Google 发布，2025 年 6 月捐赠给 Linux Foundation，2026 年 4 月达到 v1.0，拥有 150+ 支持者，包括 AWS、Cisco、Microsoft、Salesforce、SAP 和 ServiceNow。它吸收了 IBM 的 ACP，并增加了 AP2 支付扩展。本课讲解 Agent Card、Task 生命周期以及两种 transport 绑定。

**Type:** Build
**Languages:** Python（stdlib，Agent Card + Task harness）
**Prerequisites:** 第 13 阶段，第 06 课（MCP fundamentals）、第 13 阶段，第 08 课（MCP client）
**Time:** ~75 分钟

## Learning Objectives

- 区分 agent 对 tool（MCP）与 agent 对 agent（A2A）两类用例。
- 在 `/.well-known/agent.json` 发布带有 skills 与 endpoint metadata 的 Agent Card。
- 走完 Task 生命周期（submitted → working → input-required → completed / failed / canceled / rejected）。
- 使用带 Parts（text、file、data）的 Messages，以及作为输出的 Artifacts。

## 问题场景

一个客服 agent 需要把报告撰写委托给专门的 writer agent。在 A2A 出现之前的选择：

- 自定义 REST API。可行，但每一对搭档都是一次性工程。
- 共享代码库。要求两个 agent 运行在同一框架上。
- MCP。不合适：MCP 用于调用 tool，而不是让两个 agent 在保留各自不透明内部推理的前提下协作。

A2A 填补了这个空白。它把交互建模为一个 agent 向另一个 agent 发送 Task，带有生命周期、messages 和 artifacts。被调用 agent 的内部状态保持不透明——调用方只看到 task 状态转换和最终输出。

A2A 是“让跨框架的 agent 彼此对话”的协议。它不取代 MCP；两者互补。

## 核心概念

### Agent Card

每个符合 A2A 的 agent 都在 `/.well-known/agent.json` 发布一张 card：

```json
{
  "schemaVersion": "1.0",
  "name": "research-agent",
  "description": "Summarizes academic papers and drafts citations.",
  "url": "https://research.example.com/a2a",
  "version": "1.2.0",
  "skills": [
    {
      "id": "summarize_paper",
      "name": "Summarize a paper",
      "description": "Read a paper PDF and produce a 3-paragraph summary.",
      "inputModes": ["text", "file"],
      "outputModes": ["text", "artifact"]
    }
  ],
  "capabilities": {"streaming": true, "pushNotifications": true}
}
```

发现基于 URL：拉取 card，获知 A2A endpoint 的 URL，枚举 skills。

### 签名的 Agent Cards（AP2）

AP2 扩展（2025 年 9 月）为 Agent Card 增加了密码学签名。发布者用自己的 JWT 签署 card，消费方验证。这可以防止冒充。

### Task 生命周期

```
submitted -> working -> completed | failed | canceled | rejected
             -> input_required -> working (loop via message)
```

client 通过 `tasks/send` 发起。被调用 agent 在多个状态间转换；client 通过 SSE 订阅状态更新，或进行轮询。

### Messages 与 Parts

一条 message 携带一个或多个 Part：

- `text` —— 纯内容。
- `file` —— 带 mimeType 的 base64 blob。
- `data` —— 有类型的 JSON 载荷（供被调用 agent 使用的结构化输入）。

示例：

```json
{
  "role": "user",
  "parts": [
    {"type": "text", "text": "Summarize this paper."},
    {"type": "file", "file": {"name": "paper.pdf", "mimeType": "application/pdf", "bytes": "..."}},
    {"type": "data", "data": {"targetLength": "3 paragraphs"}}
  ]
}
```

### Artifacts

输出是 Artifact，而不是原始字符串。Artifact 是具名且有类型的输出：

```json
{
  "name": "summary",
  "parts": [{"type": "text", "text": "..."}],
  "mimeType": "text/markdown"
}
```

Artifact 可以按块流式传输，由调用方累积。

### 两种 transport 绑定

1. **基于 HTTP 的 JSON-RPC。** `/a2a` endpoint，用 POST 发送请求，可选 SSE 流式。默认绑定。
2. **gRPC。** 适用于 gRPC 是原生技术的企业环境。

两种绑定携带相同的逻辑消息形态。

### 不透明性保持

一个关键设计原则：被调用 agent 的内部状态是不透明的。调用方看到 task 状态和 artifacts。被调用 agent 的思维链、它的 tool 调用、它的子 agent 委托——全都不可见。这与 MCP 不同，MCP 中的 tool 调用是透明的。

理由：A2A 让竞争方能够在隐藏内部实现的情况下协作。A2A 可以是“调用这个客服 agent”，而调用方无需了解该 agent 如何实现这项服务。

### 时间线

- **2025-04-09。** Google 宣布 A2A。
- **2025-06-23。** 捐赠给 Linux Foundation。
- **2025-08。** 吸收 IBM 的 ACP。
- **2025-09。** AP2 扩展（Agent Payments）发布。
- **2026-04。** v1.0 发布，拥有 150+ 支持组织。

### 与 MCP 的关系

| 维度 | MCP | A2A |
|-----------|-----|-----|
| 用例 | Agent 对 tool | Agent 对 agent |
| 透明度 | 透明的 tool 调用 | 不透明的内部推理 |
| 典型调用方 | Agent 运行时 | 另一个 agent |
| 状态 | tool 调用结果 | 带生命周期的 task |
| 授权 | OAuth 2.1（Phase 13 · 16） | 签名的 Agent Cards（AP2） |
| 传输 | Stdio / Streamable HTTP | 基于 HTTP 的 JSON-RPC / gRPC |

想调用某个具体 tool 时用 MCP。想将整个 task 委托给另一个 agent 时用 A2A。许多生产系统两者都用：agent 用 MCP 作为 tool 层，用 A2A 作为协作层。

```figure
a2a-task-lifecycle
```

## Use It

`code/main.py` 实现了一个最小 A2A harness：research agent 发布其 card，writer agent 收到一个 `tasks/send`，其中 parts 包含一个 PDF 和一条文本指令，经过 working → input_required → working → completed 的状态转换，并返回一个 text artifact。全部使用 stdlib；使用内存 transport 以聚焦消息形态。

值得关注的点：

- Agent Card 的 JSON 形态。
- Task id 的分配与状态转换。
- 带混合类型 parts 的 Messages。
- task 进行中出现的 input-required 分支。
- 完成时返回 Artifact。

## Ship It

本课产出 `outputs/skill-a2a-agent-spec.md`。给定一个应能被其他 agent 调用的新 agent，该 skill 产出 Agent Card JSON、skills schema 和 endpoint 蓝图。

## Exercises

1. 运行 `code/main.py`。跟踪完整的 Task 生命周期，包括被调用 agent 请求澄清的 input-required 暂停。

2. 添加签名 Agent Card。对 card 的规范 JSON 使用 HMAC 签名。编写验证器，确认它在 card 被篡改时失败。

3. 实现 task 流式传输：writer agent 通过 SSE 发出三个增量 artifact 块，调用方将它们累积起来。

4. 设计一个包装 MCP server 的 A2A agent。把每个 MCP tool 映射为一个 A2A skill。注意权衡——失去了哪些不透明性？

5. 阅读 A2A v1.0 发布公告，找出截至 2026 年 4 月还没有任何框架实现的那一个特性。（提示：它与多跳 task 委托有关。）

## Key Terms

| 术语 | 常见说法 | 实际含义 |
|------|----------------|------------------------|
| A2A | “Agent 对 Agent 协议” | 面向不透明 agent 协作的开放协议 |
| Agent Card | “`.well-known/agent.json`” | 描述 agent 的 skills 与 endpoint 的已发布 metadata |
| Skill | “可调用单元” | agent 支持的一项具名操作（类比 MCP tool） |
| Task | “委托单元” | 带生命周期和最终 artifact 的工作项 |
| Message | “task 输入” | 携带 Parts（text、file、data） |
| Part | “有类型的分片” | message 中 `text` / `file` / `data` 元素 |
| Artifact | “task 输出” | 完成时返回的具名、有类型输出 |
| AP2 | “Agent Payments Protocol” | 用于信任与支付的签名 Agent Cards 扩展 |
| Opacity | “黑盒协作” | 被调用 agent 的内部对调用方隐藏 |
| Input-required | “task 暂停” | agent 需要更多信息时的生命周期状态 |

## Further Reading

- [a2a-protocol.org](https://a2a-protocol.org/latest/) —— A2A 规范正文
- [a2aproject/A2A — GitHub](https://github.com/a2aproject/A2A) —— 参考实现与 SDK
- [Linux Foundation — A2A 发布新闻稿](https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents) —— 2025 年 6 月的治理转移
- [Google Cloud — A2A 协议升级](https://cloud.google.com/blog/products/ai-machine-learning/agent2agent-protocol-is-getting-an-upgrade) —— 路线图与合作伙伴势头
- [Google Dev — A2A 1.0 里程碑](https://discuss.google.dev/t/the-a2a-1-0-milestone-ensuring-and-testing-backward-compatibility/352258) —— v1.0 发布说明与向后兼容指引
