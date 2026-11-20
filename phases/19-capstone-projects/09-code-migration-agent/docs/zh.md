# Capstone 09 — 代码迁移 Agent（仓库级语言 / 运行时升级）

> Amazon 的 MigrationBench（Java 8 到 17）与 Google 的 App Engine Py2 到 Py3 迁移器设定了 2026 年的门槛。Moderne 的 OpenRewrite 大规模执行确定性 AST 重写。Grit 用 codemod 风格 DSL 解决同一问题。生产模式把两者结合：一个负责安全重写的确定性基底，加一个处理模糊情形、按分支构建的 sandbox 和一套在 PR 打开前变绿的测试 harness 的 agent 层。本 capstone 要求迁移 50 个真实仓库，并发布通过率与失败分类法。

**Type:** Capstone
**Languages:** Python（agent）、Java / Python（目标）、TypeScript（看板）
**Prerequisites:** 第 5 阶段（NLP）、第 7 阶段（transformers）、第 11 阶段（LLM engineering）、第 13 阶段（tools）、第 14 阶段（agents）、第 15 阶段（autonomous）、第 17 阶段（infrastructure）
**Phases exercised:** P5 · P7 · P11 · P13 · P14 · P15 · P17
**Time:** 30 小时

## 问题场景

大规模代码迁移是 2026 年编码 agent 最干净的生产应用之一。地面真值显而易见（迁移后测试套件是否通过？），回报真实（一次 Java-8 机群迁移是人力规模的项目），benchmark 公开（MigrationBench 50 仓库子集）。Moderne 的 OpenRewrite 负责确定性那一侧。agent 层负责 OpenRewrite recipe 做不到的一切：模糊重写、构建系统漂移、长尾语法、传递依赖断裂。

你会构建一个 agent，接收一个 Java 8 仓库（或 Python 2 仓库），产出 CI 变绿的迁移分支。你会测量通过率、测试覆盖率保持、单仓库成本，并构建失败分类法。与纯确定性 baseline 的并排对比会告诉你 agent 的价值究竟在哪里。

## 核心概念

流水线分两层。**确定性基底**（Java 用 OpenRewrite，Python 用 libcst）安全地执行大部分机械重写：import、方法签名、空安全修改、try-with-resources、废弃 API 替换。它快，并产出可审计的 diff。**agent 层**（在 Claude Opus 4.7 与 GPT-5.4-Codex 之上用 OpenAI Agents SDK 或 LangGraph）处理 recipe 做不到的情形：构建文件升级（Maven/Gradle/pyproject）、传递依赖冲突、测试抖动、自定义注解。

每个仓库获得一个预装目标运行时的 Daytona sandbox。agent 迭代：运行构建、对失败分类、应用修复、重跑。硬性限制：每仓库 30 分钟、$8、20 个 agent turn。若全部测试通过且覆盖率差值不为负，分支就开 PR。否则该仓库连同证据被归入某个失败类。

失败分类法就是交付物。跨 50 个仓库，什么坏了？传递依赖？自定义注解？构建工具版本？与迁移无关的测试抖动？每个类得到一个计数和一个范例 diff。未来的 recipe 作者可以瞄准前三类。

## 架构

```
target repo
      |
      v
OpenRewrite / libcst deterministic recipes
   (safe, fast, auditable, ~70-80% of fixes)
      |
      v
Daytona sandbox per branch
      |
      v
agent loop (Claude Opus 4.7 / GPT-5.4-Codex):
   - run build -> capture failures
   - classify failures (build, test, lint)
   - apply fix (patch or retry recipe)
   - rerun
   - budget: 30 min, $8, 20 turns
      |
      v
test + coverage delta gate
      |
      v (passed)
open PR
      |
      v (failed)
file under failure class + attach repro
```

## 技术栈

- 确定性基底：OpenRewrite（Java）或 libcst（Python）
- Agent：在 Claude Opus 4.7 + GPT-5.4-Codex 之上用 OpenAI Agents SDK 或 LangGraph
- Sandbox：按分支的 Daytona devcontainer，预装目标运行时（Java 17 / Python 3.12）
- 构建系统：Maven、Gradle、uv（Python）
- Benchmark：Amazon MigrationBench 50 仓库子集（Java 8 到 17）、Google App Engine Py2 到 Py3 仓库
- 测试 harness：并行 runner，覆盖率经 Jacoco（Java）或 coverage.py（Python）
- 可观测性：Langfuse + 每仓库的 trace 包，含每个 diff chunk
- 看板：失败分类法看板，含逐类计数与范例 diff

```figure
ce-migration-funnel
```

## Build It

1. **Recipe 遍历。** 先跑 OpenRewrite（Java）或 libcst（Python）recipe。抓住 70-80% 属于机械性的迁移。作为“recipe”commit 提交。

2. **构建试跑。** Daytona sandbox：安装目标运行时，运行构建。若绿，跳到测试。若红，交给 agent。

3. **Agent 循环。** LangGraph 带工具：`run_build`、`read_file`、`edit_file`、`run_test`、`git_diff`。agent 对失败分类（dep、syntax、test、build-tool）并应用针对性修复。重跑。

4. **预算上限。** 每仓库 30 分钟墙钟、$8 成本、20 个 agent turn。任何越界都中止，并连同当前 diff 归入“budget_exhausted”。

5. **测试 + 覆盖率关卡。** 构建变绿后，运行测试套件。与 base 仓库比较覆盖率。若覆盖率下降超过 2%，归入“coverage_regression”。

6. **开 PR。** 成功时，推送分支，带上 diff 以及哪些 recipe 生效、哪些 commit 由 agent 撰写的摘要开 PR。

7. **失败分类法。** 对每个失败仓库，打上类别标签：`dep_upgrade_required`、`build_tool_drift`、`custom_annotation`、`test_flake`、`syntax_edge_case`、`budget_exhausted`。构建一个看板。

8. **50 仓库运行。** 在整个 MigrationBench 子集上执行。报告逐类通过率、单仓库成本、覆盖率保持，以及与纯确定性 baseline 的对比。

## Use It

```
$ migrate legacy-java-service --target java17
[recipe]   27 rewrites applied (JUnit 4->5, HashMap initializer, try-with-resources)
[build]    FAIL: cannot find symbol sun.misc.BASE64Encoder
[agent]    turn 1 classify: removed_jdk_api
[agent]    turn 2 apply: sun.misc.BASE64Encoder -> java.util.Base64
[build]    OK
[tests]    412/412 passing; coverage 84.1% -> 84.3%
[pr]       opened #1841  cost=$3.20  turns=4
```

## Ship It

`outputs/skill-migration-agent.md` 是交付物。给定一个仓库，它先执行确定性 recipe，再跑 agent 循环，产出一个变绿的迁移分支，或把该仓库归入某个分类法类别。

| 权重 | 标准 | 如何衡量 |
|:-:|---|---|
| 25 | MigrationBench 通过率 | 50 仓库子集 pass@1 |
| 20 | 测试覆盖率保持 | 相对 base 的平均覆盖率差值 |
| 20 | 单仓库迁移成本 | 通过运行上的 $/仓库 |
| 20 | Agent / 确定性工具集成 | OpenRewrite 处理 vs agent 撰写的修复比例 |
| 15 | 失败分析总结 | 带范例的分类法完整度 |
| **100** | | |

## Exercises

1. 只用 OpenRewrite（无 agent）跑迁移流水线。把通过率与完整流水线比较。找出仅靠 agent 才形成差异的案例。

2. 实现一个“lint-clean”检查：迁移后运行风格 linter（Java 用 spotless，Python 用 ruff）。若出现新的 lint 错误则让 PR 失败。测量“覆盖率保持但风格回退”的比率。

3. 加一个“最小 diff”优化器：agent 的分支通过测试后，用第二遍裁剪不必要的改动。报告 diff 体积缩减。

4. 扩展到第三种迁移：Node 18 到 Node 22。复用 sandbox 封装；把 recipe 层换成自定义 codemod。

5. 测量 time-to-first-green-build（TTFGB）作为 UX 指标。目标：p50 低于 10 分钟。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Deterministic substrate | “recipe 引擎” | OpenRewrite / libcst：带安全保证的声明式 AST 重写 |
| Codemod | “改代码的程序” | 机械地改变源代码的重写规则 |
| Build drift | “工具版本偏斜” | 大版本之间 Maven / Gradle / uv 行为的细微变化 |
| Failure class | “分类桶” | 仓库未迁移的标注原因：dep、syntax、test、build-tool、budget |
| Coverage delta | “覆盖率保持” | 从 base 到迁移分支的测试覆盖率 % 变化 |
| Agent turn | “工具调用轮” | agent 循环中的一次 plan -> act -> observe 循环 |
| Budget exhaustion | “撞到天花板” | 仓库耗尽了 30 分钟 / $8 / 20 turn 的限制仍未通过 |

## Further Reading

- [Amazon MigrationBench](https://aws.amazon.com/blogs/devops/amazon-introduces-two-benchmark-datasets-for-evaluating-ai-agents-ability-on-code-migration/) — 2026 年的权威 benchmark
- [Moderne.io OpenRewrite 平台](https://www.moderne.io) — 确定性基底参考
- [OpenRewrite 文档](https://docs.openrewrite.org) — recipe 编写
- [Grit.io](https://www.grit.io) — 另一种 codemod DSL
- [OpenAI sandboxed migration cookbook](https://developers.openai.com/cookbook/examples/agents_sdk/sandboxed-code-migration/sandboxed_code_migration_agent) — Agents SDK 参考
- [Google App Engine Py2 到 Py3 迁移器](https://cloud.google.com/appengine) — 另一种迁移 benchmark
- [libcst](https://github.com/Instagram/LibCST) — Python 确定性基底
- [Daytona sandbox](https://daytona.io) — 参考的按分支 sandbox
