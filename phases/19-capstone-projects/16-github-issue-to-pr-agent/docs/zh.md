# Capstone 16 — GitHub Issue-to-PR 自主 Agent

> 打个标签就拿到 PR——这是 2026 年自主编码 agent 的产品形态：在云端 sandbox 里运行 agent，验证测试通过，然后贴出一份带理由说明、可直接评审的 PR。AWS Remote SWE Agents、Cursor Background Agents、OpenAI Codex cloud 和 Google Jules 都提供了这一能力。难的部分在于自动复现仓库的构建环境、防止凭据泄漏、按仓库强制预算，以及确保 agent 无法 force-push。本 capstone 构建自托管版本，并在成本与通过率上同托管方案做对比。

**Type:** Capstone
**Languages:** Python（agent）、TypeScript（GitHub App）、YAML（Actions）
**Prerequisites:** 第 11 阶段（LLM engineering）、第 13 阶段（tools）、第 14 阶段（agents）、第 15 阶段（autonomous）、第 17 阶段（infrastructure）
**Phases exercised:** P11 · P13 · P14 · P15 · P17
**Time:** 30 小时

## 问题场景

异步云端编码 agent 是与交互式编码 agent（capstone 01）不同的产品品类。它的 UX 就是一个 GitHub 标签。你给某个 issue 打上 `@agent fix this`，一个 worker 在云端 sandbox 中启动，克隆仓库、运行测试、修改文件、验证，然后开一个 PR，正文里带上 agent 的理由说明。没有交互循环，也没有终端。AWS Remote SWE Agents、Cursor Background Agents、OpenAI Codex cloud、Google Jules 和 Factory Droids 都收敛到了这一形态。

工程挑战很具体：环境复现（agent 必须在没有缓存开发镜像的情况下从头构建仓库）、不稳定的测试（必须重跑或隔离）、凭据作用域（一个具备最小细粒度权限的 GitHub App）、按仓库按天限额，以及禁止 force-push 的策略。本 capstone 衡量通过率、成本与安全性，并与托管方案对比。

## 核心概念

触发器是 GitHub webhook（issue 标签或 PR 评论）。一个 dispatcher 把任务入队到 ECS Fargate 或 Lambda。worker 把仓库拉进 Daytona 或 E2B sandbox，其中的 Dockerfile 由仓库推断而来（语言、框架）。agent 针对 Claude Opus 4.7 或 GPT-5.4-Codex 运行 mini-swe-agent 或 SWE-agent v2 循环。它反复迭代：读代码、提出修复、应用 patch、运行测试。

验证是闸门步骤。开 PR 之前，完整的 CI 必须在 sandbox 内通过。覆盖率变化会被计算；如果下降超过阈值，PR 仍会打开，但会打上 `needs-review` 标签。agent 把理由说明作为 PR 描述发布，并附一个 `@agent` 讨论线程，评审者可以 ping 它追问。

安全性通过两个不同的 GitHub 表面来划定：App 提供带 `workflows: read` 以及狭窄的仓库 contents/PR 范围的短期 installation token；分支保护（而非 app 权限）强制执行“不得直接写入 `main`”与“不得 force-push”——app 永远不被加入放行名单。对 `.github/workflows` 的路径级只读访问并不是 GitHub App 的真实原语，因此 agent 的文件编辑白名单必须在 worker 层强制执行。每仓库每天的预算是上限，在 dispatcher 层执行（例如每个仓库每天最多 5 个 PR，每个 PR 20 美元）。

## 架构

```
GitHub issue labeled `@agent fix` or PR comment
            |
            v
    GitHub App webhook -> AWS Lambda dispatcher
            |
            v
    ECS Fargate task (or GitHub Actions self-hosted runner)
       - pull repo
       - infer Dockerfile (language, package manager)
       - Daytona / E2B sandbox with target runtime
       - clone -> git worktree -> agent branch
            |
            v
    mini-swe-agent / SWE-agent v2 loop
       Claude Opus 4.7 or GPT-5.4-Codex
       tools: ripgrep, tree-sitter, read/edit, run_tests, git
            |
            v
    verify CI passes in-sandbox + coverage delta check
            |
            v (verified)
    git push + open PR via GitHub App
       PR body = rationale + diff summary + trace URL
       label: needs-review
            |
            v
    operator reviews; can @-mention agent for follow-ups
```

## 技术栈

- 触发：带细粒度 token 的 GitHub App；webhook 接收端经由 Lambda 或 Fly.io
- Worker：ECS Fargate 任务（或 GitHub Actions 自托管 runner）
- Sandbox：每个任务一个 Daytona devcontainer 或 E2B sandbox
- Agent 循环：mini-swe-agent 基线，或基于 Claude Opus 4.7 / GPT-5.4-Codex 的 SWE-agent v2
- 检索：tree-sitter repo-map + ripgrep
- 验证：在 sandbox 内跑完整 CI + 覆盖率变化闸门
- 可观测性：Langfuse，每个 PR 归档 trace，并从 PR 正文链接过去
- 预算：按仓库的每日金额上限；每个仓库每天的 PR 数量上限

```figure
cf-issue-to-pr
```

## Build It

1. **GitHub App。** 细粒度 installation token：issues 读写、pull_requests 写、contents 读写、workflows 读。分支保护（唯一能做这件事的表面）强制执行“不得直接推送到 `main`”与“不得 force-push”；app 不在放行名单中。由于 GitHub App 权限并非路径级，worker 对拟定 diff 做白名单检查，强制执行“不得写入 `.github/workflows`”。

2. **Webhook 接收端。** Lambda 函数接收 issue 标签 / PR 评论 webhook。按标签 `@agent fix this` 过滤。入队到 SQS。

3. **Dispatcher。** 从 SQS 取任务。强制按仓库按天预算。为每个任务启动一个 ECS Fargate 任务，带上仓库 URL、issue 正文和一个全新的 Daytona sandbox。

4. **环境推断。** 检测语言（Python、Node、Go、Rust）与包管理器（uv、pnpm、go mod、cargo）。若 Dockerfile 不存在，则即时生成一个。

5. **Agent 循环。** 用 Claude Opus 4.7 驱动 mini-swe-agent 或 SWE-agent v2。工具：ripgrep、tree-sitter repo-map、read_file、edit_file、run_tests、git。硬性限制：20 美元成本、30 分钟实际耗时、30 个 agent 轮次。

6. **验证。** 循环结束后，在 sandbox 内运行完整测试套件。通过 jacoco / coverage.py 计算覆盖率变化。若 CI 红灯：中止，不开 PR。若覆盖率下降超过 2%：开 PR 但打上 `needs-review` 标签。

7. **发布 PR。** 推送 agent 分支。通过 GitHub API 开 PR，包含：标题、理由说明、diff 摘要、trace URL、成本、轮次。

8. **凭据卫生。** worker 以短期的 GitHub App installation token 运行。归档前对日志做密钥清洗。

9. **评测。** 30 个难度不等的内部预设 issue。测量通过率、PR 质量（diff 大小、风格、覆盖率）、成本、延迟。在同一批 issue 上与 Cursor Background Agents、AWS Remote SWE Agents 对比。

## Use It

```
# on github.com
  - user labels issue #842 with `@agent fix this`
  - PR #1903 appears 14 minutes later
  - body:
    > Fixed NPE in widget.dedupe() caused by null comparator entry.
    > Added regression test widget_test.go::TestDedupeNullComparator.
    > Coverage delta: +0.12%
    > Turns: 7  Cost: $1.80  Trace: langfuse:...
    > Label: needs-review
```

## Ship It

`outputs/skill-issue-to-pr.md` 是交付物：一个 GitHub App 加异步云 worker，把打好标签的 issue 变成可直接评审的 PR，成本有边界、凭据有作用域。

| 权重 | 评分标准 | 衡量方式 |
|:-:|---|---|
| 25 | 30 个 issue 上的通过率 | 端到端成功（CI 绿灯 + 覆盖率达标） |
| 20 | PR 质量 | diff 大小、覆盖率变化、风格一致性 |
| 20 | 每个已解决 issue 的成本与延迟 | 每个 PR 的金额与实际耗时 |
| 20 | 安全性 | 限定作用域的 token、按仓库预算、禁止 force-push、凭据卫生 |
| 15 | 运维体验 | 理由评论、重试入口、@ 提及追问 |
| **100** | | |

## Exercises

1. 增加“修复不稳定测试”模式：标签 `@agent stabilize-flake TestX` 会在 sandbox 内把该测试跑 50 次，并提出一个使其稳定的最小改动。

2. 在三个共享 issue 上对比 Cursor Background Agents 的成本。报告各工具在何处占优。

3. 实现预算仪表盘：按仓库按天成本、按用户成本。对异常发出告警。

4. 构建“试运行”模式：不跑 CI 就开草稿 PR，让评审者低成本地审视方案。

5. 加入保留策略：超过 7 天未合并的 PR 分支自动删除。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| GitHub App | "Scoped bot identity" | 具备细粒度权限 + 短期 installation token 的 App |
| Async cloud agent | "Background agent" | 在云端 sandbox 而非终端中运行的非交互式 worker |
| Environment inference | "Dockerfile synthesis" | 检测语言 + 包管理器，缺失时生成 Dockerfile |
| Verification | "CI-in-sandbox" | 开 PR 之前先在 worker 内运行完整测试套件 |
| Coverage delta | "Coverage preservation" | 从基线到 agent 分支的测试覆盖率百分比变化 |
| Per-repo budget | "Daily ceiling" | 在 dispatcher 层强制执行的金额与 PR 数量上限 |
| Rationale | "PR body explanation" | agent 对改了什么、为什么改的说明；PR 正文必需 |

## Further Reading

- [AWS Remote SWE Agents](https://github.com/aws-samples/remote-swe-agents) —— 标准异步云端 agent 参考
- [SWE-agent](https://github.com/SWE-agent/SWE-agent) —— CLI 参考
- [Cursor Background Agents](https://docs.cursor.com/background-agent) —— 商业替代方案
- [OpenAI Codex (cloud)](https://openai.com/codex) —— 托管竞品
- [Google Jules](https://jules.google) —— Google 的托管版本
- [Factory Droids](https://www.factory.ai) —— 另一商业参考
- [GitHub App documentation](https://docs.github.com/en/apps) —— 作用域化的 bot 身份
- [Daytona cloud sandboxes](https://daytona.io) —— 参考 sandbox
