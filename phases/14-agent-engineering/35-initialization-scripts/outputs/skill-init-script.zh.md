---
name: init-script
description: 访谈项目并产出一个带五个 probe 的确定性 init_agent.py，外加一个在任何 probe 失败时就拒绝启动 agent 的 CI workflow。
version: 1.0.0
phase: 14
lesson: 35
tags: [init, probes, ci, workbench, fail-loud]
---

给定一个 repo、agent 产品及其依赖面，产出项目专属的 init script 和 CI 接线。

产出：

1. `tools/init_agent.py`，带这些 probe：runtime 版本、列出的依赖、测试命令可解析性、必需环境变量、state 文件新鲜度。
2. 在脚本旁记录的 `init_report.json` schema。每个 probe 返回 `(name, status: pass|warn|fail, detail)`。
3. `.github/workflows/agent-init.yml`（或等价物），运行脚本并在任何 fail 级 probe 上阻止 agent job。
4. 一个 agent runtime 可在每个 session 开始前调用的 `pre-task` hook 脚本。
5. `docs/init.md` 里的文档，列出每个 probe、其严重度以及如何修复一次失败。

硬性拒绝：

- 没有超时却访问网络的 probe。Init 必须快且离线安全。
- 需要 LLM 调用的 probe。Init 是确定性管道。
- 被包装层吞掉的非零退出码。大声失败才是重点。
- 无幂等地触及 state 的 probe。连续两次运行必须产生除时间戳外相同的 report。

拒绝规则：

- 如果项目没有测试命令，拒绝交付脚本。改为把这个缺口加进 workbench audit。
- 如果环境变量列表含脚本会打印的 secret，拒绝并强制脱敏。init report 绝不该携带 secret。
- 如果某 probe 在 dry run 中超过三秒，交付前把这个计时发现摆在明面上。冗长 probe 让 init 变成仪式。

输出结构：

```
<repo>/
├── tools/
│   ├── init_agent.py
│   └── pre_task.sh
├── docs/
│   └── init.md
└── .github/
    └── workflows/
        └── agent-init.yml
```

结尾附上「接下来读什么」，指向：

- Lesson 36，使用 init report 的 `repo_paths` 的每任务 scope contract。
- Lesson 37，消费已解析测试命令的 runtime feedback loop。
- Lesson 38，依赖 probe 通过的 verification gate。