# 作为库的 Harness——Subagent 与 Session Store

> 一个你可以 import 的 harness：内置工具、用于上下文隔离的 subagent、hooks、W3C trace 传播、会话持久化。Claude Agent SDK 是参考示例——Claude Code harness 的库形态——而 Claude Managed Agents 是面向长时程异步工作的托管替代方案。

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 01 (Agent Loop), Phase 14 · 10 (Skill Libraries)
**Time:** ~75 minutes

## 学习目标

- 解释 Anthropic Client SDK（原始 API）与 Claude Agent SDK（harness 形态）之间的区别。
- 描述 subagent——并行化与上下文隔离——以及什么时候该用它们。
- 说出 Python SDK 的 session store 表面（`append`、`load`、`list_sessions`、`delete`、`list_subkeys`）以及 `--session-mirror` 的角色。
- 用标准库实现一个带内置工具、带隔离上下文的 subagent spawn、生命周期 hooks 和 session store 的 harness。

## 问题

一个原始 LLM API 只给你一次往返。一个生产智能体需要工具执行、MCP server、生命周期 hooks、subagent spawn、会话持久化、trace 传播。Claude Agent SDK 把这些形态作为一个库交付——正是 Claude Code 所用的那个 harness，暴露给自定义智能体。

## 概念

### Client SDK vs Agent SDK

- **Client SDK（`anthropic`）。** 原始 Messages API。循环、工具、状态都归你管。
- **Agent SDK（`claude-agent-sdk`）。** 内置工具执行、MCP 连接、hooks、subagent spawn、session store。作为库的 Claude Code 循环。

### 内置工具

SDK 开箱提供 10+ 个工具：文件读写、shell、grep、glob、网页抓取，还有更多。自定义工具通过标准 tool-schema 接口注册。

### Subagents

Anthropic 记录了两个目的：

1. **并行化。** 并发运行相互独立的工作。「为这 20 个模块分别找测试文件」就是 20 个并行的 subagent 任务。
2. **上下文隔离。** subagent 使用自己的上下文窗口；只有结果返回给 orchestrator。orchestrator 的预算被保住了。

Python SDK 近期新增：`list_subagents()`、`get_subagent_messages()`，用于读取 subagent 的转写。

### Session store

与 TypeScript 的协议对齐：

- `append(session_id, message)` —— 追加一轮。
- `load(session_id)` —— 恢复对话。
- `list_sessions()` —— 枚举。
- `delete(session_id)` —— 级联到 subagent 会话。
- `list_subkeys(session_id)` —— 列出 subagent 键。

`--session-mirror`（CLI 标志）在流式输出时把转写镜像到一个外部文件，便于调试。

### Hooks

你可以注册的生命周期 hooks：

- `PreToolUse`、`PostToolUse` —— 门控或审计工具调用。
- `SessionStart`、`SessionEnd` —— 装配与拆除。
- `UserPromptSubmit` —— 在模型看到用户输入之前对它做处理。
- `PreCompact` —— 在上下文压缩之前运行。
- `Stop` —— 智能体退出时清理。
- `Notification` —— 侧信道告警。

Hooks 是 pro-workflow（Phase 14 课程参考）及类似系统加入横切行为的方式。

### W3C trace context

调用方活跃的 OTel span 通过 W3C trace context 头传播进 CLI 子进程。整条多进程 trace 在你的后端里呈现为一条 trace。

### Claude Managed Agents

托管替代方案（beta 头 `managed-agents-2026-04-01`）。长时程异步工作、内置 prompt 缓存、内置压缩。用控制换取托管基础设施。

### 这个模式在哪里会出问题

- **Subagent 过度 spawn。** 为 100 个微小任务 spawn 100 个 subagent。开销占主导。改为批处理。
- **Hook 蔓延。** 每个团队都加 hooks；启动时间膨胀。每季度评审一次 hooks。
- **会话膨胀。** 会话不断累积；体积增长。用 `list_sessions` + 过期策略。

```figure
ae-subagent-isolation
```

## Build It

`code/main.py` 用标准库实现 SDK 的形态：

- `Tool`、`ToolRegistry`，带内置的 `read_file`、`write_file`、`list_dir`。
- `Subagent` —— 私有上下文、隔离运行、结果返回。
- `SessionStore` —— append、load、list、delete、list_subkeys。
- `Hooks` —— `pre_tool_use`、`post_tool_use`、`session_start`、`session_end`。
- 一个演示：主智能体并行 spawn 3 个 subagent（各自隔离）、聚合结果、持久化会话。

运行它：

```
python3 code/main.py
```

trace 展示 subagent 的上下文隔离（orchestrator 上下文大小保持有界）、hook 执行与会话持久化。

## Use It

- **Claude Agent SDK** 用于想要 Claude Code harness 形态的 Claude 优先产品。
- **Claude Managed Agents** 用于托管的长时程异步工作。
- **OpenAI Agents SDK**（第 16 课）用于 OpenAI 优先的对应物。
- **LangGraph + 自定义工具** 如果你想要图形状的状态机。

## Ship It

`outputs/skill-claude-agent-scaffold.md` 脚手架出一个 Claude Agent SDK 应用，带 subagent、hooks、session store、MCP server 挂接和 W3C trace 传播。

## 练习

1. 加一个 subagent spawner，把 20 个任务批成每组 5 个并行 subagent。对比每个任务一个的 orchestrator 上下文大小。
2. 实现一个 `PreToolUse` hook，对 `write_file` 调用做限流（每个会话每分钟 5 次）。追踪这个行为。
3. 接 `list_subkeys` 渲染一棵 subagent 树。深层嵌套长什么样？
4. 把玩具移植到真正的 `claude-agent-sdk` Python 包。工具注册会发生什么变化？
5. 读 Claude Managed Agents 文档。你什么时候会从自托管切换到托管？

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| Agent SDK | 「作为库的 Claude Code」 | harness 形态：工具、MCP、hooks、subagent、session store |
| Subagent | 「子智能体」 | 独立上下文、自己的预算；结果向上冒泡 |
| Session store | 「对话数据库」 | 持久化、加载、列出、删除轮次，带 subagent 级联 |
| Hook | 「生命周期回调」 | 工具前/后、会话、prompt 提交、压缩、停止 |
| W3C trace context | 「跨进程 trace」 | 父 span 传播进 CLI 子进程 |
| Managed Agents | 「托管 harness」 | Anthropic 托管的长时程异步工作 |
| `--session-mirror` | 「转写镜像」 | 在流式输出时把会话轮次写到一个外部文件 |
| MCP server | 「工具表面」 | 挂到智能体上的外部工具/资源来源 |

## 延伸阅读

- [Claude Agent SDK overview](https://platform.claude.com/docs/en/agent-sdk/overview) —— Claude Code 的库形态
- [Anthropic，Building agents with the Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk) —— 生产模式
- [Claude Managed Agents overview](https://platform.claude.com/docs/en/managed-agents/overview) —— 托管替代方案
- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) —— 对应物