---
name: issue-to-pr
description: 构建一个异步的 GitHub issue-to-PR agent，在云端 sandbox 中运行、复现构建、验证测试，并在严格的按仓库预算内开出可直接评审的 PR。
version: 1.0.0
phase: 19
lesson: 16
tags: [capstone, async-agent, github, fargate, daytona, swe-bench, budget, safety]
---

给定一个带有 `@agent fix this` 标签 issue 的 GitHub 仓库，交付一个自托管的云端 agent，把每个打好标签的 issue 变成可直接评审的 PR，凭据限定作用域、成本有边界。

构建计划：

1. 带细粒度 token 的 GitHub App：issues 读写、PR 写、contents 读写、workflows 读。禁止 force-push。`main` 上的分支保护阻止直接写入。
2. Webhook 接收端（Lambda 或 Fly.io）过滤标签 / PR 评论事件并入队到 SQS。
3. Dispatcher 强制按仓库按天的金额与 PR 数量上限；为每个获准任务启动一个 ECS Fargate 任务。
4. 环境推断：从仓库内容检测语言 + 包管理器 + 运行时。缺失时即时合成 Dockerfile。
5. 每个任务一个 Daytona 或 E2B sandbox。把仓库克隆进全新的 `git worktree` 与 agent 分支。
6. Agent 循环（在 Claude Opus 4.7 或 GPT-5.4-Codex 上运行 mini-swe-agent 或 SWE-agent v2）。工具：ripgrep、tree-sitter repo-map、read_file、edit_file、run_tests、git。上限：20 美元、30 轮、30 分钟。
7. 验证：在 sandbox 内跑完整 CI；通过 jacoco / coverage.py 计算覆盖率变化；变化 < -2% 时打 `needs-review` 标签；CI 红灯则中止。
8. 通过 GitHub API 开 PR，附理由说明、diff 摘要、trace URL、成本、轮次。
9. 可观测性：每个 PR 一个 Langfuse trace；日志做密钥清洗；按仓库的预算仪表盘。
10. 在 30 个预设的内部 issue 上评测；在一个三道 issue 的共享子集上对比 Cursor Background Agents 与 AWS Remote SWE Agents。

评估标准：

| 权重 | 评分标准 | 衡量方式 |
|:-:|---|---|
| 25 | 30 个 issue 上的通过率 | 端到端成功（CI 绿灯 + 覆盖率达标） |
| 20 | PR 质量 | diff 大小、覆盖率变化、风格一致性 |
| 20 | 每个已解决 issue 的成本与延迟 | 每个 PR 的金额与实际耗时 |
| 20 | 安全性 | 限定作用域的 token、按仓库预算、禁止 force-push、凭据卫生 |
| 15 | 运维体验 | 理由评论、重试入口、@ 提及追问 |

硬性淘汰项：

- 任何能够 force-push 的 agent。硬性排除。
- 跳过预算检查的 dispatcher。失控循环是典型故障。
- 未在 sandbox 内通过完整 CI 就开出的 PR。
- 含有未脱敏 token 或 PII 的 trace 归档。

拒绝规则：

- 拒绝在 `main` 上没有分支保护的情况下安装。
- 拒绝在没有按仓库日预算（金额与 PR 数量）的情况下运行。
- 拒绝自动重试失败的运行；所有重试都必须由人工重新打标签。

交付物：一个仓库，包含 GitHub App、webhook 接收端、dispatcher + 预算账本、Fargate 任务定义、sandbox 生命周期管理、mini-swe-agent 循环、30 个 issue 的评测运行、与 Cursor Background Agents 和 AWS Remote SWE Agents 的并排对比，以及一份说明文档，点名前三大构建推断失败，以及分别降低它们的 Dockerfile 合成改动。
