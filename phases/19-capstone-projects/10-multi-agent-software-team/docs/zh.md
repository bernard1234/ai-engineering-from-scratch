# Capstone 10 — 多智能体软件工程团队

> 2026 年多智能体工程团队的形态已经收敛：architect 做规划，N 个 coder 在并行 worktree 里干活，reviewer 把关，tester 验证。SWE-AF 的工厂架构、MetaGPT 的基于角色的提示、AutoGen 0.4 的类型化 actor 图、Cognition 的 Devin，以及 Factory 的 Droids，都各自独立地落到了这个形态上。并行 worktree 把 wall-clock 时间转换成 throughput。共享状态与交接协议成为失效面。这个 capstone 要求你搭出这支团队，在 SWE-bench Pro 上评测，并报告哪些交接会断、断得多频繁。

**Type:** Capstone
**Languages:** Python / TypeScript（agents）、Shell（worktree 脚本）
**Prerequisites:** 第 11 阶段（LLM engineering）、第 13 阶段（tools）、第 14 阶段（agents）、第 15 阶段（autonomous）、第 16 阶段（multi-agent）、第 17 阶段（infrastructure）
**Phases exercised:** P11 · P13 · P14 · P15 · P16 · P17
**Time:** 40 小时

## 问题场景

单 Agent 的编码 harness 在大任务上会撞到天花板。这不是因为某个 Agent 本身弱，而是因为 200k token 的 context 既装不下架构方案，也装不下四份并行的代码库切片、reviewer 的评论以及测试输出。多 Agent 工厂把问题拆开：architect 负责方案，coders 在并行 worktree 中各管实现，reviewer 把关，tester 验证。SWE-AF 的 “factory” 架构、MetaGPT 的角色、AutoGen 的类型化 actor 图——这三种说法描述的是同一种形态。

失效面在于交接（handoff）。architect 规划出 coders 无法实现的东西。coders 产出互相冲突的 diff。reviewer 批准了一个幻觉式的修复。tester 与仍在写代码的 coder 抢跑。你要搭出这样一支团队，在 50 个 SWE-bench Pro issue 上运行，追踪每一次交接，并发布复盘报告。

## 核心概念

角色就是带类型的 agent。**Architect**（Claude Opus 4.7）阅读 issue、撰写方案，并把它拆成带显式接口的子任务。**Coders**（Claude Sonnet 4.7，N 个并行实例，每个都在一个 `git worktree` + Daytona sandbox 中）独立实现子任务。**Reviewer**（GPT-5.4）阅读合并后的 diff，要么批准，要么提出具体的修改要求。**Tester**（Gemini 2.5 Pro）在隔离环境中运行测试套件，并带产物报告通过/失败。

通信通过一块共享的任务板（file-backed 或 Redis）进行。每个角色只消费自己有权处理的任务。交接是 A2A 协议类型化的消息。协调的关切点包括：合并冲突解决（协调者角色或自动三方合并）、共享状态同步（coders 一旦开工，方案即冻结；重新规划是独立事件），以及 reviewer 的把关（reviewer 不能批准自己的改动或自己提出的改动）。

token 放大是隐藏成本。每一道角色边界都会加上总结 prompt 与交接 context。一次 40 轮的单 Agent 运行，放到四个角色下会变成总共 160 轮。评分标准特意把 token 效率相对单 Agent 基线纳入权重，因为问题不是“多 Agent 能不能跑通”，而是“它按美元算是否划算”。

## 架构

```
GitHub issue URL
      |
      v
Architect (Opus 4.7)
   reads issue, produces plan with subtasks + interfaces
      |
      v
Task board (file / Redis)
      |
   +-- subtask 1 ---+-- subtask 2 ---+-- subtask 3 ---+-- subtask 4 ---+
   v                v                v                v                v
Coder A          Coder B          Coder C          Coder D          (4 parallel)
 (Sonnet)         (Sonnet)         (Sonnet)         (Sonnet)
 worktree A       worktree B       worktree C       worktree D
 Daytona          Daytona          Daytona          Daytona
      |                |                |                |
      +--------+-------+-------+--------+
               v
           merge coordinator  (three-way merge + conflict resolution)
               |
               v
           Reviewer (GPT-5.4)
               |
               v
           Tester  (Gemini 2.5 Pro)  -> passes? -> open PR
                                     -> fails?  -> route back to coder
```

## 技术栈

- 编排：LangGraph，采用共享状态 + 每个 agent 的子图
- 消息传递：A2A 协议（Google 2025），用于 agent 间的类型化消息
- 模型：Opus 4.7（architect）、Sonnet 4.7（coders）、GPT-5.4（reviewer）、Gemini 2.5 Pro（tester）
- Worktree 隔离：每个 coder 一个 `git worktree add` + Daytona sandbox
- 合并协调器：自研三方合并 + LLM 介入的冲突解决
- 评测：SWE-bench Pro（50 个 issue）、SWE-AF 场景，单元测试用 HumanEval++
- 可观测性：Langfuse，带角色标记的 span，按 agent 记账 token
- 部署：K8s，每个角色一个独立 Deployment + 基于积压的 HPA

```figure
ce-team-handoff
```

## Build It

1. **任务板。** file-backed JSONL，承载类型化消息：`plan_request`、`subtask`、`diff_ready`、`review_needed`、`test_needed`、`approved`、`rejected`、`replan_needed`。agent 按 tag 订阅。

2. **Architect。** 读取 GitHub issue，用要求显式子任务接口（涉及的文件、公开函数、测试影响）的方案模板运行 Opus 4.7。发出一个带子任务 DAG 的 `plan_request`。

3. **Coders。** N 个并行 worker，各自从任务板领取一个子任务。每个都拉起一个新的 `git worktree add` 分支，外加一个 Daytona sandbox。实现该子任务。发出带 patch + 测试增量的 `diff_ready`。

4. **合并协调器。** 在所有 coder 完成后，把 N 个分支三方合并到一个 staging 分支。仅当存在文件级重叠时，才使用 LLM 介入的冲突解决。

5. **Reviewer。** GPT-5.4 阅读合并后的 diff。不能批准自己撰写的 diff。发出 `approved`（no-op）或带具体修改要求的 `review_feedback`，并路由回相关的 coder。

6. **Tester。** Gemini 2.5 Pro 在干净的 sandbox 中运行测试套件。捕获产物。发出 `test_passed` 或带 stacktrace 的 `test_failed`。失败的测试回到负责该失败子任务的 coder。

7. **交接记账。** 每条跨角色边界的消息在 Langfuse 中生成一个 span，记录 payload 大小与所用模型。计算每个子任务的 token 放大系数（coder_tokens + reviewer_tokens + tester_tokens + architect_share / coder_tokens）。

8. **评测。** 在 50 个 SWE-bench Pro issue 上运行。用 pass@1 与“每个已解决 issue 的美元成本”对比单 Agent 基线（单个 worktree 中的一个 Sonnet 4.7）。

9. **复盘。** 对每个失败的 issue，找出断掉的那次交接（方案太模糊、合并冲突、reviewer 误批、tester flake）。产出一张交接失败直方图。

## Use It

```
$ team run --issue https://github.com/acme/widget/issues/842
[architect] plan: 4 subtasks (parser, cache, api, migration)
[board]     dispatched to 4 coders in parallel worktrees
[coder-A]   subtask parser  -> 42 lines, tests pass locally
[coder-B]   subtask cache   -> 88 lines, tests pass locally
[coder-C]   subtask api     -> 31 lines, tests pass locally
[coder-D]   subtask migration -> 19 lines, tests pass locally
[merge]     3-way merge: 0 conflicts
[reviewer]  comments on cache (thread pool sizing); routed to coder-B
[coder-B]   revision: 92 lines; submits
[reviewer]  approved
[tester]    all 412 tests pass
[pr]        opened #3382   4 coders, 1 revision, $4.90, 18m
```

## Ship It

`outputs/skill-multi-agent-team.md` 是交付物。给定一个 issue URL 与并行度，这支团队产出一个可合并的 PR，并附带按角色分列的 token 记账。

| 权重 | 标准 | 衡量方式 |
|:-:|---|---|
| 25 | SWE-bench Pro pass@1 | 对齐的 50 个 issue 子集上的 pass@1 |
| 20 | 并行加速 | wall-clock 相对单 Agent 基线 |
| 20 | 评审质量 | 注入缺陷探针上的误批率 |
| 20 | token 效率 | 每个已解决 issue 的总 token 相对单 Agent |
| 15 | 协调工程 | 合并冲突解决、交接失败直方图 |
| **100** | | |

## Exercises

1. 在运行中途往某个 diff 里注入一个明显的 bug（在主逻辑前多加一个 `return None`）。测量 reviewer 的误批率。调整 reviewer 的 prompt，直到误批率低于 5%。

2. 缩减到两个 coder（architect + coder + reviewer + tester，coder 顺序跑两个子任务）。对比 wall-clock 与通过率。

3. 用单写者约束替换合并协调器（子任务只触碰互不相交的文件集）。测量 architect 的规划负担。

4. 把 reviewer 从 GPT-5.4 换成 Claude Opus 4.7。测量误批率与 token 成本差。

5. 增加第五个角色：documenter（Haiku 4.5）。在评审之后，它产出一条 changelog 记录。衡量文档质量是否值回多花的 token。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Parallel worktree | “隔离分支” | `git worktree add` 为每个 coder 生成一棵全新的工作树 |
| Task board | “共享消息总线” | 存储类型化消息的文件或 Redis，agent 按需订阅 |
| Handoff | “角色边界” | 任何从一个角色的 context 跨越到另一个角色的消息 |
| Token amplification | “多 Agent 开销” | 同一任务中跨所有角色的总 token / 单 Agent token |
| A2A protocol | “Agent 之间对话” | Google 2025 年发布的 agent 间类型化消息规范 |
| Merge coordinator | “集成者” | 执行三方合并并调解冲突的组件 |
| False approval | “reviewer 幻觉” | reviewer 批准了一个已知带 bug 的 diff |

## Further Reading

- [SWE-AF 工厂架构](https://github.com/Agent-Field/SWE-AF) — 2026 年多 Agent 工厂的参考实现
- [MetaGPT](https://github.com/FoundationAgents/MetaGPT) — 基于角色的多 Agent 框架
- [AutoGen v0.4](https://github.com/microsoft/autogen) — 微软的类型化 actor 框架
- [Cognition AI (Devin)](https://cognition.ai) — 参考产品
- [Factory Droids](https://www.factory.ai) — 另一个参考产品
- [Google A2A 协议](https://a2a-protocol.org/latest/) — agent 间消息传递规范
- [git worktree 文档](https://git-scm.com/docs/git-worktree) — 隔离的底层机制
- [SWE-bench Pro](https://www.swebench.com) — 评测目标
