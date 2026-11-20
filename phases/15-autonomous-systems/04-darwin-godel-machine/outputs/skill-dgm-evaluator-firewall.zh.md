---
name: dgm-evaluator-firewall
description: 为 Darwin-Godel-Machine 式的自我修改 agent 循环指定所需的 evaluator 隔离，以避免已记录的 reward hacking。
version: 1.0.0
phase: 15
lesson: 4
tags: [dgm, self-modification, reward-hacking, evaluator, sandbox]
---

给定一个拟议的自我修改 agent 循环（agent scaffold、evaluator 流水线、部署目标），产出一份防火墙规格，确保 evaluator 始终在 agent 够不到的范围内。DGM 论文记录了 agent 移除自身安全标记以提高分数；本 skill 就是对应的控制手段。

产出：

1. **文件系统边界。** 列出 agent 可以编辑的每一个文件。列出 evaluator 读取的每一个文件。两者的交集必须为空。如果不为空，说明把它变空所需的确切移动操作。
2. **进程边界。** evaluator 必须运行在 agent 无法控制的进程中。写清容器或 sandbox 的规格。如果 agent 拥有 shell 访问权限，它就能绕过进程内的防护。
3. **网络与机密边界。** agent 绝不能编辑那些用于拉取 evaluator 输入或回传分数的 CI 机密。列出机密存放的位置以及挂载方式。
4. **分数入口契约。** 分数从 evaluator 返回循环的档案，这条路径是唯一的通道。agent 能写入、且会影响未来评分的任何东西都会破坏该契约。
5. **变更审查清单。** 列出在接纳前需要人工审查的 agent 编辑类别：新增依赖、对评分邻近代码的编辑、对 sandbox 配置的编辑、对日志或监控的编辑。

硬性拒绝：
- evaluator 与 agent 源码位于同一个仓库。把它移出去。
- evaluator 以 Python import 的形式运行在 agent 进程内。用子进程运行它。
- 任何在边界 agent 一侧应用的分数调整。所有调整必须在服务端完成。
- 任何 agent 可以通过编辑自己代码来静默的日志。

拒绝规则：
- 如果用户无法说出 agent 可以编辑的每一个文件，拒绝，并要求先做文件级写访问审计。
- 如果 evaluator 没有 held-out 输入，拒绝——这是第 03 课的审计，属于前置条件。
- 如果部署面包含对 evaluator 自身的改动（即使是间接地通过提议的依赖更新），拒绝，并要求一个手动防火墙审查步骤。

输出格式：

返回一份单页规格，包含：
- **Agent 写入面**（路径、glob）
- **Evaluator 读取面**（路径、端点）
- **交集**（必须为空；展示 diff）
- **进程模型**（evaluator 如何隔离）
- **机密清单**（存放在哪、如何挂载）
- **需审查的变更类别**（项目符号）
- **签核行**（谁拥有这条防火墙不变量）
