---
name: workbench-pack
description: 生成一个项目调优的即插即用 agent workbench pack——规则针对团队历史打磨，scope glob 匹配 repo，rubric 维度扩展一条领域特定的条目。
version: 1.0.0
phase: 14
lesson: 42
tags: [capstone, workbench-pack, installer, schemas, drop-in]
---

给定一个 repo、团队的故障历史，以及在它里面运行的 agent 产品，产出一个调优过的 agent-workbench-pack 和一个安装器。

产出：

1. 匹配规范布局的 `agent-workbench-pack/` 目录：AGENTS.md、docs/、schemas/、scripts/、bin/、README.md、VERSION。
2. 一个 `bin/install.sh`，在没有 `--force` 时拒绝覆盖已有 pack，并把 `.workbench-version` 写进目标 repo。
3. 项目调优版的 `agent-rules.md`（每个类别至少一条规则，源自团队最近六次故障）、`reviewer-rubric.md`（带第六个领域维度），以及 `scope_contract.schema.json`（带项目特定的 glob）。
4. 一个 `lint_pack.py` 脚本，当脚本与 schema 之间、或 VERSION 与 schema 的 `schema_version` 之间出现漂移时就失败。
5. 可选的 CI 集成，在 demo 分支上安装 pack，并针对一个已知良好的 task 运行 verification gate。

硬性拒绝：

- 包含项目特定 task 的 pack。task 归属于目标 repo 的 board。
- 绑定单一厂商 SDK 的 pack。只允许框架无关；SDK 接线是目标 repo 的事。
- 改动 state 文件的安装器。安装器是只动 surface 的幂等操作；state 属于 agent 和人类。
- 没有对应检查函数的规则。口号式的规则属于入职材料，不属于 pack。

拒绝规则：

- 如果故障历史为空，拒绝交付调优过的 `agent-rules.md`。使用规范默认值，并把这个缺口摆出来。
- 如果目标 repo 的 CI 与本次安装不兼容（没有 `.github/workflows/`，也没有等价物），拒绝可选的 CI 步骤并记录手动路径。
- 如果团队使用 pack 的私有 fork，拒绝编写公开安装器。私有安装器携带私有不变量。

输出结构：

```
agent-workbench-pack/
├── AGENTS.md
├── docs/
├── schemas/
├── scripts/
├── bin/install.sh
├── lint_pack.py
├── VERSION
└── README.md
```

以「接下来读什么」结尾，指向：

- 第 41 课，了解这个 pack 所改进的前后对比基准。
- 第 30 课（Eval-Driven Agent Development），了解消费 pack 的 verdict 的 eval 循环。
- [SkillKit](https://github.com/rohitg00/skillkit)，了解把 pack 分发到 32 个 AI agent。