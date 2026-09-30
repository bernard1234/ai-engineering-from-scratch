---
name: claude-agent-scaffold
description: 搭建一个 Claude Agent SDK 应用，包含 subagent、生命周期 hook、session 存储、MCP server 挂接以及 W3C trace 传播。
version: 1.0.0
phase: 14
lesson: 17
tags: [claude-agent-sdk, subagents, hooks, session-store, mcp]
---

给定一个产品领域及一组 MCP server，搭建一个 Claude Agent SDK 应用。

产出：

1. 一个主 agent 定义，含 instructions、内置工具访问（read_file、write_file、shell、grep、glob、web fetch）以及自定义函数工具。
2. 用于并行化和上下文隔离的 subagent spawner。当 orchestrator 会耗尽自身上下文预算时使用。
3. 注册的生命周期 hook：用于审计的 PreToolUse + PostToolUse、用于初始化的 SessionStart、用于清理的 SessionEnd、用于规则执行的 UserPromptSubmit（参见 pro-workflow 模式）。
4. Session 存储（默认 SQLite），并接入 `list_subkeys` 以渲染 subagent 树。
5. 用于外部工具/资源面的 MCP server 挂接。
6. W3C trace context 传播，使来自调用方的 OTel span 能够贯穿 CLI 继续传递。

硬拒绝：

- 为单个工具任务 spawn 一个 subagent。Subagent 用于并行化或上下文隔离；不是用于“一次 read_file 调用”。
- 带同步昂贵工作的 Hook。Hook 应在微秒到毫秒量级。长工作应放进 subagent。
- 没有级联删除策略的 Session 存储。孤立的 subagent session 会膨胀存储。

拒绝规则：

- 如果产品需要长时程异步工作（数小时到数天），拒绝对自托管的 SDK，改走 Claude Managed Agents。
- 如果用户要求对共享位置做 `--session-mirror`，拒绝。Session 记录携带 PII；应镜像到按用户加密的存储。
- 如果 agent 依赖不带工具使用的原始 LLM streaming 来提供 UX，拒绝 Agent SDK，直接推荐 Client SDK。

输出：`agent.py`、`tools.py`、`hooks.py`、`session.py`、`README.md`，说明 subagent 策略、hook 注册表、session 后端、MCP 挂接及 OTel 接入。结尾的“接下来读什么”指向：语音 handoff 看第 22 课、OTel span 归属看第 23 课、若产品需要生产运行时形态则看第 18 课。