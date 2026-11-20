---
name: terminal-coding-agent
description: 针对 SWE-bench Pro 构建并评估一个终端原生的编码 agent，成本有界、工具沙箱化，并覆盖 2026 年完整的 hook 面。
version: 1.0.0
phase: 19
lesson: 01
tags: [capstone, coding-agent, claude-code, swe-bench, mcp, hooks, sandbox]
---

给定一个目标仓库和一句自然语言任务，构建一个会制定计划、在 sandbox 中执行、并开出 pull request 的 harness。在 30 任务的 SWE-bench Pro 子集上追平或超过 mini-swe-agent 基线，同时保持在每任务 $5 的预算之内。

构建计划：

1. 搭起一个 Bun + Ink 的 TUI harness，包含计划面板、工具调用流，以及实时的 token/美元预算。
2. 通过 Model Context Protocol StreamableHTTP 定义六个工具（read_file、edit_file、ripgrep、tree_sitter_symbols、run_shell、git）。每次调用最多返回 4k token。
3. 每次工具调用都在 E2B 或 Daytona sandbox 内、一个全新的 `git worktree add` 分支上运行。绝不触碰宿主机文件系统。
4. 接上 2026 年的全部八个 hook 事件：SessionStart、SessionEnd、PreToolUse、PostToolUse、UserPromptSubmit、Notification、Stop、PreCompact。至少交付四个用户自写的 hook（破坏性命令护栏、token 计费、OTel span 发射器、trace bundle 写入器）。
5. 强制三份预算：50 轮、200k token、$5。PreCompact 在 150k 时触发并总结较早的轮次。
6. 向自托管的 Langfuse 发送带 GenAI 语义约定的 OpenTelemetry span。
7. 成功时推送分支并开一个 PR，正文中附上计划和 trace bundle。
8. 在 30 个 issue 的 SWE-bench Pro Python 子集上对比 mini-swe-agent 评测，记录每任务的 pass@1、轮数、token 和美元成本。

Assessment rubric:

| Weight | Criterion | Measurement |
|:-:|---|---|
| 25 | SWE-bench Pro pass@1 | 匹配的 30 任务子集对比 mini-swe-agent 基线 |
| 20 | 架构清晰度 | Plan/act/observe 分离、hook 面、工具 schema 的可读性 |
| 20 | 安全性 | Sandbox 逃逸红队 + 破坏性命令护栏审计 |
| 20 | 可观测性 | 100% 的工具调用有 span，逐轮 token 计费 |
| 15 | 开发者体验 | 冷启动低于 2s、崩溃恢复、Ctrl-C 取消语义 |

Hard rejects:

- 在宿主机文件系统上（而非 sandbox 内）调用 git 的 harness。
- 任何能在 worktree 之外写入、或在没有显式白名单 hook 的情况下 curl 外部 URL 的 agent。
- 未在同一 30 个 issue 上跑匹配基线就报告的 eval 数字。
- 依赖重试之间 `git reset --hard` 的“通过率”声明；SWE-bench Pro 是 pass@1。

Refusal rules:

- 任何配置下都拒绝直接推送到 main。只允许 PR 分支。
- 拒绝禁用破坏性命令护栏。这是评分标准中的硬性要求。
- 拒绝在没有预算上限的情况下运行。开放式运行会污染 eval 对比。

Output：一个 repo，包含 harness、固定的 30 任务 SWE-bench Pro eval harness 及与之匹配的 mini-swe-agent 基线运行、至少 5 次完整运行的 OpenTelemetry trace 归档，以及一篇说明哪些任务你的 harness 能解而基线不能、反之亦然。最后附一节，讲你观察到的三大失败模式以及分别修复它们的 hook 改动。
