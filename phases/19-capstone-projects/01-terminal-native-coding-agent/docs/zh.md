# Capstone 01 — 终端原生编码 agent

> 到 2026 年，编码 agent 的形态已经定型。TUI harness、有状态的计划、沙箱化的工具面、一个“计划—执行—观察—恢复”的循环。Claude Code、Cursor 3 和 OpenCode 从 50 英尺外看几乎一模一样。这个 capstone 要你端到端地构建一个——CLI 进、pull request 出——并在 SWE-bench Pro 上拿它与 mini-swe-agent 和 Live-SWE-agent 对比衡量。你会明白：难的部分不是模型调用，而是工具循环、sandbox，以及 50 轮运行的成本天花板。

**Type:** Capstone
**Languages:** TypeScript / Bun（harness）、Python（eval scripts）
**Prerequisites:** 第 11 阶段（LLM engineering）、第 13 阶段（tools and protocols）、第 14 阶段（agents）、第 15 阶段（autonomous systems）、第 17 阶段（infrastructure）
**Phases exercised:** P0 · P5 · P7 · P10 · P11 · P13 · P14 · P15 · P17 · P18
**Time:** 35 小时

## 问题场景

编码 agent 在 2026 年成了占主导的 AI 应用品类。Claude Code（Anthropic）、带 Composer 2 和 Agent Tabs 的 Cursor 3（Cursor）、Amp（Sourcegraph）、OpenCode（112k stars）、Factory Droids 和 Google Jules，交付的都是同一套架构的变体：一个终端 harness、一层带权限的工具面、一个 sandbox，以及围绕前沿模型构建的计划—执行—观察循环。前沿很窄——Live-SWE-agent 借助 Opus 4.5 在 SWE-bench Verified 上达到 79.2%——但工程技艺很宽。大多数失败模式不是模型出错，而是工具循环不稳定、context 被污染、token 成本失控，以及破坏性的文件系统操作。

你无法从外部推理这些 agent。你得亲手造一个，看着循环在第 47 轮崩溃——因为 ripgrep 返回了 8MB 匹配结果——然后重建截断层。这正是这个 capstone 的意义所在。

## 核心概念

harness 有四个表面。**Plan** 维护一个 TodoWrite 式的状态对象，由模型每轮重写。**Act** 派发工具调用（read、edit、run、search、git）。**Observe** 捕获 stdout / stderr / 退出码，截断后把摘要喂回去。**Recover** 处理工具错误，既不撑爆 context 窗口，也不无限循环。2026 年的形态还多了一样东西：**hooks**。`PreToolUse`、`PostToolUse`、`SessionStart`、`SessionEnd`、`UserPromptSubmit`、`Notification`、`Stop` 和 `PreCompact`——操作者可以注入策略、遥测和护栏的可配置扩展点。

sandbox 是 E2B 或 Daytona。每个任务都在一个全新的 devcontainer 里运行，挂载一个读写模式的 git worktree。harness 从不触碰宿主机文件系统。worktree 无论成功还是失败都会被销毁。成本控制在三层执行：每轮 token 上限、每会话美元预算、硬性轮数上限（通常是 50）。可观测性层是带 GenAI 语义约定的 OpenTelemetry span，发送到自托管的 Langfuse。

## 架构

```
  user CLI  ->  harness (Bun + Ink TUI)
                  |
                  v
           plan / act / observe loop  <--->  Claude Sonnet 4.7 / GPT-5.4-Codex / Gemini 3 Pro
                  |                          (via OpenRouter, model-agnostic)
                  v
           tool dispatcher (MCP StreamableHTTP client)
                  |
     +------------+------------+----------+
     v            v            v          v
  read/edit    ripgrep     tree-sitter   git/run
     |            |            |          |
     +------------+------------+----------+
                  |
                  v
           E2B / Daytona sandbox  (worktree isolated)
                  |
                  v
           hooks: Pre/Post, Session, Prompt, Compact
                  |
                  v
           OpenTelemetry -> Langfuse (spans, tokens, $)
                  |
                  v
           PR via GitHub app
```

## 技术栈

- Harness 运行时：Bun 1.2 + Ink 5（React-in-terminal）
- 模型接入：OpenRouter 统一 API，配 Claude Sonnet 4.7、GPT-5.4-Codex、Gemini 3 Pro、Opus 4.5（用于最难的任务）
- 工具传输：Model Context Protocol StreamableHTTP（MCP 2026 revision）
- Sandbox：E2B sandboxes（JS SDK）或 Daytona devcontainers
- 代码搜索：ripgrep 子进程，17 种语言的 tree-sitter parser（预编译）
- 隔离：每个任务 `git worktree add`，成功 / 失败后清理
- Eval harness：SWE-bench Pro（verified 子集）+ Terminal-Bench 2.0 + 你自己的 30 任务 holdout
- 可观测性：OpenTelemetry SDK 配 `gen_ai.*` semconv → 自托管 Langfuse
- PR 提交：GitHub App，细粒度 token，作用域限制在目标 repo

```figure
ce-agent-loop
```

## Build It

1. **TUI 与命令循环。** 用 Ink 搭起一个 Bun 工程。接受 `agent run <repo> "<task>"`。打印分栏视图：计划面板（上）、工具调用流（中）、token 预算（下）。加上 Ctrl-C 取消，退出前触发 `SessionEnd` hook。

2. **计划状态。** 定义一个带类型的 TodoWrite schema（pending / in_progress / done 条目，各带备注）。模型每轮以一次工具调用重写完整状态——不要让它增量修改。把计划持久化到 `.agent/state.json`，这样崩溃后可以恢复。

3. **工具面。** 定义六个工具：`read_file`、`edit_file`（带 diff 预览）、`ripgrep`、`tree_sitter_symbols`、`run_shell`（带超时）、`git`（status / diff / commit / push）。通过 MCP StreamableHTTP 暴露，让 harness 与传输方式解耦。每个工具都返回截断后的输出（每次调用上限 4k token）。

4. **Sandbox 包装。** 每个任务派生一个 E2B sandbox。`git worktree add -b agent/$TASK_ID` 拉一个新分支。所有工具调用都在 sandbox 内执行。宿主机文件系统不可达。

5. **Hooks。** 实现 2026 年的全部八种 hook 类型。至少接上四个用户自写的 hook：(a) `PreToolUse` 破坏性命令护栏，拦截 worktree 之外的 `rm -rf`；(b) `PostToolUse` token 计费；(c) `SessionStart` 预算初始化；(d) `Stop` 写出最终 trace bundle。

6. **Eval 循环。** 克隆 SWE-bench Pro Python 的 30 个 issue 子集。用你的 harness 逐个运行，并与 mini-swe-agent（最小基线）比较 pass@1、每任务轮数和每任务美元成本。把结果写入 `eval/results.jsonl`。

7. **成本控制。** 硬性截断：50 轮、200k context、每任务 $5。`PreCompact` hook 在 150k 标记处把较早的轮次总结成一个先验状态块，在不丢失计划的前提下为新观察腾出空间。

8. **PR 提交。** 成功时，最后一步是 `git push` 加一次 GitHub API 调用，在 body 中带上计划和 diff 摘要并开一个 PR。

## Use It

```
$ agent run ./my-repo "Fix the race condition in worker.rs"
[plan]  1 locate worker.rs and enumerate mutex uses
        2 identify shared state under contention
        3 propose fix, verify tests
[tool]  ripgrep mutex.*lock -t rust           (44 matches, truncated)
[tool]  read_file src/worker.rs 120..180
[tool]  edit_file src/worker.rs (+8 -3)
[tool]  run_shell cargo test worker::          (passed)
[plan]  1 done · 2 done · 3 done
[done]  PR opened: #482   turns=9   tokens=38k   cost=$0.41
```

## Ship It

交付物 skill 位于 `outputs/skill-terminal-coding-agent.md`。给定一个 repo 路径和一个任务描述，它在 sandbox 中跑完整的计划—执行—观察循环，返回一个 PR URL 加一个 trace bundle。这个 capstone 的评分标准：

| Weight | Criterion | How it is measured |
|:-:|---|---|
| 25 | 相对基线的 SWE-bench Pro pass@1 | 你的 harness 对比 mini-swe-agent，在 30 个匹配的 Python 任务上 |
| 20 | 架构清晰度 | Plan/act/observe 分离、hook 面、工具 schema——对照 Live-SWE-agent 的布局评审 |
| 20 | 安全性 | Sandbox 逃逸测试、权限提示、破坏性命令护栏通过红队测试 |
| 20 | 可观测性 | Trace 完整性（100% 的工具调用有 span）、逐轮 token 计费 |
| 15 | 开发者体验 | 冷启动 < 2s、崩溃恢复可续接计划、Ctrl-C 能干净地在工具执行中途取消 |
| **100** | | |

## Exercises

1. 把后端模型从 Claude Sonnet 4.7 换成在 vLLM 上服务的 Qwen3-Coder-30B。比较 pass@1 和每任务美元成本。报告开源模型在哪些地方表现更差。

2. 加一个 `reviewer` 子 agent，在提交 PR 前读 diff，并能请求进入修订循环。测量误报的 review 是否会把 SWE-bench 通过率压到单 agent 基线以下（提示：通常是）。

3. 压力测试 sandbox：写一个试图 `curl` 外部 URL 的任务，再写一个试图在 worktree 之外写文件的任务。确认两者都被 PreToolUse hook 拦截。记录这些尝试。

4. 用更小的模型（Haiku 4.5）实现 `PreCompact` 摘要。测量在 3 倍压缩下计划保真度损失多少。

5. 把 MCP StreamableHTTP 传输换成 stdio。对冷启动和每次调用延迟做 benchmark。为纯本地使用选出胜者。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Harness | “agent 循环” | 围绕模型的那层代码：派发工具、维护计划状态并强制预算 |
| Hook | “agent 事件监听器” | 由用户编写、在八个生命周期事件之一被 harness 执行的脚本 |
| Worktree | “git sandbox” | 位于独立路径的链接式 git checkout；可丢弃且不影响主克隆 |
| TodoWrite | “计划状态” | 模型每轮重写的 pending/in-progress/done 类型化列表 |
| StreamableHTTP | “MCP 传输” | 2026 年的 MCP 修订：长连接 HTTP 双向流；取代 SSE |
| Token ceiling | “context 预算” | 每轮或每会话对输入+输出 token 的上限；触发压缩或终止 |
| pass@1 | “单次尝试通过率” | SWE-bench 任务首次运行即解决（不重试、不偷看测试集）的比例 |

## Further Reading

- [Claude Code documentation](https://docs.anthropic.com/en/docs/claude-code) — Anthropic 的参考 harness
- [Cursor 3 changelog](https://cursor.com/changelog) — Agent Tabs 与 Composer 2 的产品说明
- [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) — 用于 SWE-bench harness 对比的最小基线
- [Live-SWE-agent](https://github.com/OpenAutoCoder/live-swe-agent) — 用 Opus 4.5 在 SWE-bench Verified 上达到 79.2%
- [OpenCode](https://opencode.ai) — 开源 harness，112k stars
- [SWE-bench Pro leaderboard](https://www.swebench.com) — 这个 capstone 瞄准的评测
- [Model Context Protocol 2026 roadmap](https://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/) — StreamableHTTP、能力元数据
- [OpenTelemetry GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) — 工具调用与 token 用量的 span schema
