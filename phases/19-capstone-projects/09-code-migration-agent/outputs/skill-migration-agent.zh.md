---
name: migration-agent
description: 构建一个仓库级代码迁移 agent，把确定性 recipe 与 agent fallback 循环结合起来，通过 MigrationBench，并发布一份失败分类法。
version: 1.0.0
phase: 19
lesson: 09
tags: [capstone, code-migration, openrewrite, libcst, migrationbench, agent, sandbox]
---

给定一个 Java 8 或 Python 2 仓库，产出一个迁移后的分支（迁到 Java 17 或 Python 3.12），测试套件全绿且覆盖率回退最小。在 50 仓库的 MigrationBench 子集上评估。

构建计划：

1. 确定性 pass：OpenRewrite（Java）或 libcst（Python）先执行机械化重写。作为一个 "recipe" commit 提交，diff 干净。
2. Daytona sandbox：预装目标运行时；按分支构建；源码只读挂载。
3. Agent 循环：LangGraph 或 OpenAI Agents SDK，跑在 Claude Opus 4.7 + GPT-5.4-Codex 之上。工具：`run_build`、`read_file`、`edit_file`、`run_test`、`git_diff`。对失败分类（dep、syntax、test、build-tool），施加针对性修复，重跑。
4. 预算上限：30 分钟、$8、20 轮。任一超限即中止，并以当前 diff 归档在 `budget_exhausted` 下。
5. 测试 + 覆盖率闸门：先 build 绿，再 tests 绿；覆盖率下降不得超过 2%。
6. 开 PR，包含 recipe commit + agent commit + 总结评论。
7. 失败分类法：每仓库从 `{dep_upgrade_required, build_tool_drift, custom_annotation, test_flake, syntax_edge_case, budget_exhausted, coverage_regression}` 打标签。
8. 在 MigrationBench 上跑 50 仓库；发布按类的通过率、单仓库成本与覆盖率保持度；与纯确定性基线对比。

评估评分表：

| 权重 | 标准 | 衡量方式 |
|:-:|---|---|
| 25 | MigrationBench 通过率 | 50 仓库子集的 pass@1 |
| 20 | 测试覆盖率保持 | 相对基线分支的平均覆盖率变化 |
| 20 | 每个迁移仓库的成本 | 通过运行的平均 $/repo |
| 20 | Agent / 确定性工具集成 | 由 OpenRewrite 与 agent 分别处理的修复占比 |
| 15 | 失败分析写作 | 分类法完整度与示例 |

硬性驳回：

- 跳过确定性 pass 的流水线。OpenRewrite 处理机械的 70-80%，比任何 agent 更便宜也更可靠。
- 覆盖率回退超过 2% 仍按通过处理。
- 把机械改动与 agent 改动塞进一个 commit 的 PR。必须分开。
- 报告通过率，却不提供同样 50 仓库上配对的纯确定性基线。

拒绝规则：

- 拒绝把迁移分支 force-push 覆盖基线。永远是新建分支 + PR。
- 拒绝为 CI 在 sandbox 中尚未转绿的 PR 开单。
- 拒绝在未获明确修改许可的公司仓库上运行。

产出：一个仓库，包含两层迁移流水线、50 仓库的 MigrationBench 运行日志、失败分类法看板、配对的纯确定性基线运行，以及一篇关于三类最常见失败类别和能消除每一类的 recipe 改动的写作。
