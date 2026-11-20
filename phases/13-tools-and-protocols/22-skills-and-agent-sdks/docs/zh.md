# Agent Skills：可移植契约与运行时边界

> Skill 不是起了更好文件名的长 prompt。它是一个可发现的包，包含 instructions、resources 和可执行 helpers，通过运行时契约进入 agent 的上下文。

**Type:** Build
**Languages:** Python（stdlib）
**Prerequisites:** 第 13 阶段，第 01 课（The Tool Interface）、第 13 阶段，第 05 课（Tool Schema Design）
**Time:** ~90 分钟

## Learning Objectives

- 定义 agent skill，并把它与 prompt、repository instructions、tool、hook、subagent 或 plugin 区分开。
- 阅读可移植的 `SKILL.md` 契约，并将其与运行时特有的扩展区分开。
- 把发现、选择、激活、资源加载、tool 使用和验证解释为彼此不同的生命周期阶段。
- 在运行时把 skill 放进 agent 的 catalog 之前，先校验 skill 包。
- 针对具体任务，在 skill、MCP tool、hook、subagent 或普通代码之间做选择。

## 十分钟首次成功

在冗长解释之前先做这件事。你会创建一个小 skill，把完整的 reviewer bundle 安装到真实的 agent host 中，调用它，验证结果，然后移除它。这用可观测的结果证明了整个生命周期。

### 真实 host 实验的前置检查

真实 host 检查点需要 Node.js、`npx`、Python 3、一个选定的支持 skill 的 host，以及在安装器中你选择的项目作用域或用户作用域的写权限。先验证本地命令：

```bash
node --version
npx --version
python3 --version
```

在安装前先决定你要用哪个 host 和哪个作用域。如果任一要求不可用，就在网站上阅读本课，或继续做下面的手工打包练习。那条回退路径能教会你契约，但无法证明 host 发现、调用、打包脚本执行或卸载行为。把这些观察标记为待定。

### 1. 从空工作目录开始

在任意存放学习工作的父目录中运行这些命令：

```bash
mkdir -p agent-skills-first-run
cd agent-skills-first-run
TARGET_ROOT="$(pwd -P)"
printf 'TARGET_ROOT=%s\n' "$TARGET_ROOT"
ls -A
```

最后一条命令应当没有任何输出。如果它打印了文件，换一个空目录，让 review 有清晰的边界。

为你的第一个 skill 创建目录：

```bash
mkdir -p my-first-skill
```

用以下内容创建 `my-first-skill/SKILL.md`：

```markdown
---
name: my-first-skill
description: Turn rough meeting notes into a compact decision record when the user asks to capture a technical decision.
---

# Decision record

Extract the decision, context, alternatives, owner, and next review date.
If the notes do not contain a decision, ask one clarifying question instead
of inventing one.
```

验证你在预期目录中创建了该文件：

```bash
test -f my-first-skill/SKILL.md
```

无输出且退出码为 0 表示文件存在。

### 2. 安装完整的 reviewer bundle

留在 `agent-skills-first-run` 中并运行：

```bash
npx skills add rohitg00/ai-engineering-from-scratch --skill skill-contract-reviewer --full-depth
```

选择你正在使用的 agent host 和作用域。安装器应当列出 `skill-contract-reviewer` 及其写入的目标位置。`--full-depth` 是必需的，因为本课的 skill 是一个嵌套 bundle，包含 references、一个 script 和一个 asset。

把 `SKILL_ROOT` 设为安装器报告的绝对目录。它必须是包含已安装 `SKILL.md` 的目录，而不是课程源码目录，也不是当前工作区：

```bash
# Replace the placeholder with the destination printed by the installer.
SKILL_ROOT="$(cd "/absolute/path/to/skill-contract-reviewer" && pwd -P)"
test -f "$SKILL_ROOT/SKILL.md"
printf 'SKILL_ROOT=%s\n' "$SKILL_ROOT"
```

如果 agent 会话已经打开，启动一个新会话，或使用该 host 的 skill 重新扫描命令。不要假设每个 host 都会热重载它的 catalog。

### 3. 显式调用它

在已安装的 agent 中，以 `agent-skills-first-run` 为工作目录，使用该 host 支持的语法：

| Host | 显式调用 |
|---|---|
| Codex | `skill-contract-reviewer`，或从 `/skills` 中选择，然后提供 review 请求 |
| Claude Code | `/skill-contract-reviewer`，后接 review 请求 |
| 可移植回退 | `Use skill-contract-reviewer to review the target package.` |

在请求中使用为 `SKILL_ROOT` 和 `TARGET_ROOT` 打印的绝对值。要求 host 在执行前展开它们，并展示精确解析后的命令，而不是依赖进程工作目录的命令：

```text
Use skill-contract-reviewer to review <TARGET_ROOT>/my-first-skill. The installed bundle root is <SKILL_ROOT>. Run python3 <SKILL_ROOT>/scripts/check_skill.py <TARGET_ROOT>/my-first-skill. Before running it, show the fully resolved argv. Return the validation report, selected primitives, and one sentence for each selection. Include the resolved script path, resolved target path, cwd, argv, and exit code as execution evidence.
```

解析后的命令应当形如下面这样，且不残留任何占位符：

```bash
python3 "/absolute/install/path/skill-contract-reviewer/scripts/check_skill.py" \
  "/absolute/workspace/path/agent-skills-first-run/my-first-skill"
```

成功的结果具备全部三个属性：

1. Host 能按名字找到 `skill-contract-reviewer`。
2. Reviewer 读取包契约并运行其打包的 validator。
3. 响应包含一份针对该样例没有结构错误的 validation report，以及有理有据的 primitive 选择。

执行证据还必须写明 script 路径、target 路径、cwd、精确的参数向量和退出码。一份流畅但没有这些字段的报告，并不能证明已安装的配套 script 确实运行过。

如果 host 报告 skill 不可用，验证安装目标位置，重新扫描或重启一次，然后重试显式请求。不要为了掩盖安装失败而改写 skill 的 description。

### 4. 探测隐式选择

开始一个新的 agent 轮次，在不点名该 skill 的情况下输入同一任务：

```text
Review <TARGET_ROOT>/my-first-skill as a reusable agent package and tell me whether its package contract is valid.
```

如果 host 会暴露被选中的 skills，记录它是否选择了 `skill-contract-reviewer`。如果 host 不暴露 routing，则把隐式选择标记为未验证。显式调用是可移植的回退方式。

### 5. 清理

只移除已安装的 reviewer bundle：

```bash
npx skills remove skill-contract-reviewer
```

选择与安装时相同的 host 和作用域。重新扫描或开启新会话后，显式请求 `skill-contract-reviewer` 应报告其不可用。保留 `my-first-skill` 供后续课程使用，或在完成本 track 后删除实验目录。

## 问题场景

假设你的团队有一套可靠的发布工作流。它查找已合并的变更、检查迁移说明、更新 changelog、运行打包命令，并产出一份 review 清单。

把这套工作流放进一个 prompt 里，粘贴容易，运营很难。这个 prompt 没有稳定的身份，没有发现规则，没有资源边界，没有可测试的包形态，也回答不了这些基本问题：谁可以调用它？模型应在何时选择它？它能运行哪些 script？哪些文件是可信的？上下文被压缩后还剩下什么？

相反的失误是把每一条可复用的指令都当成 skill。仓库约定、确定性自动化、外部工具、事件 hook 和委派 agent 解决的是不同问题。把它们全塞进 `SKILL.md`，得到的是一个看似可移植、实则依赖某个 host 未公开行为的目录。

第一项工程任务是分类。先决定这个工件是什么，再决定如何打包它。

## 核心概念

### Skill 编码过程性知识

Agent skill 是一个以 `SKILL.md` 为入口的目录。入口文件包含 YAML frontmatter，其后是 Markdown 指令。目录中还可以包含 references、scripts 和 assets。

```figure
skill-package-anatomy
```

可部署单元是目录，而不只是那个 Markdown 文件。复制来的 `SKILL.md` 如果缺失引用的文件，即使 frontmatter 能解析，也是一个损坏的包。

### 相邻的抽象

| 工件 | 主要职责 | 何时加载或运行 | 不应冒充什么 |
|---|---|---|---|
| Prompt | 塑造一次模型交互 | 由应用或用户包含 | 带资源的版本化包 |
| Repository instructions | 说明某个代码库的常驻规则 | 编码运行时进入该作用域时 | 可复用的任务工作流 |
| Agent skill | 提供可复用的过程性知识 | 显式或隐式激活时 | 硬性授权边界 |
| MCP tool | 暴露带类型的远程能力 | 模型或应用调用它时 | 详细的操作流程 |
| Hook | 在事件上运行确定性逻辑 | 声明的事件发生时 | 概率性的模型 routing |
| Subagent | 用独立的上下文和状态委派工作 | 编排器创建或调用它时 | 静态的指令包 |
| Plugin | 分发更大的运行时扩展 | host 安装或启用它时 | 可移植的 skill 契约本身 |
| Learned skill library | 存储从经验中发现的行为 | 策略检索此前的 program 或 trajectory | 基于标准的 `SKILL.md` 包 |

发布 skill 可以告诉 agent 如何检查一次发布。MCP server 可以暴露发布 registry。Hook 可以禁止直接 push。Subagent 可以独立审计候选版本。这些部件之所以能组合，是因为它们各自承担不同的职责。

### "skill" 一词指两个不同的概念

研究系统有时把学到的 program、成功的 trajectory 或环境特定的 policy 片段称为 skill。Agent 可以在探索过程中创建这些工件，按任务相似度检索它们，执行它们，并根据反馈修订这个库。Phase 14 · 10 会构建那种终身学习库。

本 mini-track 中的 Agent Skill 不同。它是一个作者编写的包，带有声明的文件系统契约、catalog 元数据、progressive disclosure、运行时中介的调用，以及 host 控制的 tools。它可以由 agent 生成或改进，但该格式并不要求"学习"。

| 维度 | Agent Skill 包 | Learned skill library |
|---|---|---|
| 主要单元 | `SKILL.md` 目录 | Program、policy、trajectory 或 memory 记录 |
| 创建 | 编写、生成或 curation | 通常从环境经验中发现 |
| 选择 | Catalog description 加运行时策略 | 基于任务状态的检索或 policy |
| 执行 | 模型遵循 instructions 并调用 host tools | 环境运行存储的行为或代码工件 |
| 可移植性 | 包契约可跨兼容 host | 往往绑定单一环境和动作空间 |
| 评估 | Routing、工件、安全性和 host 兼容性 | 奖励、成功率、迁移能力和库的增长 |

两种概念都在打包可复用的能力。它们不应仅仅因为同名就共享实现层面的主张。

### 可移植核心

Agent Skills 规范要求两个 frontmatter 字段：

```yaml
---
name: release-readiness
description: Inspect a release candidate when the user asks whether a version is ready to publish.
---
```

`name` 是稳定标识符。它必须满足规范的命名规则，并与父目录一致。`description` 既是文档也是 routing 元数据。它应当说明 skill 做什么、何时适用。

可移植的可选字段有：

| 字段 | 用途 | 可移植性说明 |
|---|---|---|
| `license` | 说明该包的条款 | 核心规范 |
| `compatibility` | 说明环境要求 | 核心规范 |
| `metadata` | 携带字符串值的扩展数据 | 核心规范 |
| `allowed-tools` | 建议预先批准的工具 | 实验性；host 支持不一 |

Markdown 正文承载操作指令。它应定义工作流、决策点、失败行为，以及指向配套资源的直接路径。

```markdown
# Release readiness

Use this workflow for a release candidate, not for ordinary development builds.

1. Read `references/release-policy.md`.
2. Run `python3 scripts/inspect_release.py --format json`.
3. Stop if the report contains a blocking failure.
4. Produce the checklist from `assets/release-checklist.md`.
5. Ask for approval before any publish or tag action.
```

### 运行时扩展是第二层

有些 host 接受额外的 frontmatter 或配套配置。这些字段可能有用，但并不会自动可移植。

| 行为 | 示例 host 扩展 | 可移植核心？ |
|---|---|---|:---:|
| 让 skill 对模型 routing 隐藏，同时保留用户直接调用 | `disable-model-invocation` | 否 |
| 让 skill 对用户命令菜单隐藏，同时允许模型 routing | `user-invocable` | 否 |
| 在命令菜单中显示参数帮助 | `argument-hint` | 否 |
| 在委派上下文中运行 skill | `context`、`agent` | 否 |
| 固定模型或推理设置 | `model`、`effort` | 否 |
| 注册生命周期自动化 | `hooks` | 否 |
| 在 Codex 中禁用隐式调用 | `agents/openai.yaml` policy | 否 |

把每个扩展当作一个 adapter。在没有它的情况下保持核心工作流仍然有效，记录回退方式，并测试消费它的 host。运行时有可能会忽略未知字段、拒绝它，或保留它但不实现相应行为。

### Frontmatter 是可执行的元数据

元数据会在 skill 正文被读取之前改变系统行为。

- 格式错误的 `name` 会让发现失败。
- 含糊的 `description` 会把错误的请求 route 过来。
- 仅供人类使用的标志可能把 skill 从模型的 catalog 中移除。
- tool 白名单会改变 host 是否请求权限。
- context 设置可能把执行移入独立的 agent 会话。

像审查配置代码一样审查 frontmatter。校验它、给它做版本化，并把它的行为纳入 eval。

### Skill 生命周期

```figure
skill-runtime-lifecycle
```

每一个箭头都是带有自身失败模式的边界。

1. **Discovery（发现）** 在配置的位置中找到可能的包。
2. **Validation（校验）** 在 catalog 发布前拒绝格式错误或不安全的包。
3. **Cataloging（编目）** 只暴露精简的 `name` 和 `description`，而不是整个包。
4. **Selection（选择）** 判断该 skill 是否相关。
5. **Activation（激活）** 把正文加载进模型可见的上下文。
6. **Disclosure（披露）** 仅当某个分支需要时才读取 references 或 assets。
7. **Execution（执行）** 在 host 的权限和隔离规则下使用 host tools。
8. **Verification（验证）** 独立于模型的自述来检查产出的工件。

把这些阶段混为一谈会导致错误的心智模型。被发现不等于已激活。已激活不等于有权做它描述的所有事。被允许的 tool 调用也不等于结果正确。

### Skill 与 tool 相互正交

MCP 回答的是："这个应用可以调用哪些能力，它们的 schema 是什么？"Skill 回答的是："agent 应当如何着手这一类任务？"

```figure
skill-tool-orthogonality
```

Skill 可以点名某个 tool，但实际的能力注册表归 host 所有。如果该 tool 不存在，skill 应当说明回退方式或明确失败。它绝不应暗示点名某个能力就等于创建了它。

### Skill 与仓库指令属于不同作用域

仓库指令描述你当前所处的环境：命令、约定、生成文件和边界。Skill 为可能跨多个仓库发生的任务提供可复用的流程。

当两者同时适用时，当前用户请求和仓库规则会约束该 skill。一个通用重构 skill 绝不能覆盖禁止编辑生成文件的仓库规则。

### Skill 之间不互相 import

一个 skill 可以指示 agent 调用另一个 skill，但这不是语言层面的 import。第二个 skill 仍要经过运行时发现、资格判定、激活、权限和上下文处理。

把跨 skill 依赖写成可观测的工作流边：

```markdown
After producing the candidate changelog, invoke the `release-risk-review` skill.
Pass the candidate path and require a blocking or non-blocking verdict.
If that skill is unavailable, stop and report the missing dependency.
```

这让依赖变得可测试，并给 host 一个执行策略的机会。

## Build It

`code/main.py` 实现了一个小型、面向标准的 validator 和一个工件选择器。它保持 stdlib-only，以便每条规则都清晰可见。

Validator 暴露：

- `parse_frontmatter(text)`，把元数据从正文中分离出来。
- `validate_skill_text(text, directory_name, allowed_runtime_extensions=())`，检查必填字段、命名、未知扩展、正文存在性和可移植上限。
- `ValidationIssue` 和 `SkillReport`，返回结构化的证据，而不是一个不透明的布尔值。
- `FrontmatterSyntaxError`，用于无法安全解释的输入。

Chooser 暴露 `TaskShape` 和 `select_primitives(task)`。它把任务需求映射到普通代码、repository instructions、skill、hook、subagent 或 MCP tool。

运行实验：

```bash
cd "$(git rev-parse --show-toplevel)"
cd phases/13-tools-and-protocols/22-skills-and-agent-sdks
python3 code/main.py
python3 -m unittest discover -s code/tests -v
```

此命令块需要本地 clone，且必须从该 clone 内任意位置启动，这样 `git rev-parse --show-toplevel` 才能解析出仓库根目录。

Demo 会为以下情况打印 JSON：一个有效的可移植 skill、一个 host 扩展过的 skill、一个无效的包，以及若干 task-shape 决策。检查 issue code。包 validator 应当解释如何修复工件，而不是替作者去猜。

### 校验顺序很重要

先校验成本低的结构事实，再处理更深入的内容规则：

```figure
skill-validation-order
```

这个顺序可以避免次要错误掩盖了第一个被破坏的不变量。

## Use It

在编写 skill 之前，先填好这张决策卡：

| 问题 | 如果是 | 可能的 primitive |
|---|---|---|
| 这是否需要跨多个步骤的可复用模型判断？ | 流程稳定但决策多变 | Skill |
| 这是否必须在事件每次触发时都发生？ | 漏掉一次执行都不可接受 | Hook 或应用代码 |
| 模型是否需要带类型输入的外部能力？ | 该操作存在于模型上下文之外 | Tool 或 MCP server |
| 这项工作是否需要独立的上下文、状态或归属？ | 独立 worker 返回有界结果 | Subagent |
| 这份指引是否只针对某一个仓库？ | 它描述本地的命令与约束 | Repository instructions |
| 一次交互是否足够？ | 不需要包生命周期 | Prompt |

很多生产工作流会同时用到不止一行。这张卡防止某个工件假装自己能提供所有属性。

## Ship It

本课在 `outputs/` 下产出 `skill-contract-reviewer` bundle。它包含：

- 一个可移植的 `SKILL.md`，用于审查拟议的 skill 包；
- 针对可移植契约和 primitive 选择的参考清单；
- 一个确定性的校验脚本；
- 覆盖 prompt、skill、tool、hook、普通代码和 subagent 的 task-shape fixture。

安装完整的 bundle，而不只是它的入口文件：

```bash
cd "$(git rev-parse --show-toplevel)"
python3 scripts/install_skills.py /tmp/aiefs-skills --phase 13 --type skill
```

课程安装器会报告每个已复制的 Phase 13 skill，并写入 `/tmp/aiefs-skills/manifest.json`。这个干净的目标位置用于检查包形态；上面的首次成功循环则在真实 host 中检查发现和调用。

后续课程会深化生命周期的每个阶段。Lesson 24 构建发现与 progressive disclosure。Lesson 25 构建调用策略与 routing。Lesson 26 把权限与沙箱隔离开。Lesson 27 把整个包变成一个经过评估的发布工件。

## Exercises

1. 用 `TaskShape` 对你自己团队的五个工作流进行分类。为你选择不止一个 primitive 的每一处辩护。
2. 添加边界测试，证明 500 字符的 `compatibility` 值通过，而 501 字符的值作为规范错误而失败。
3. 向 allowlist 添加一个运行时扩展。编写一个测试，证明同一个文件仍能与仅可移植的 skill 区分开。
4. 把一个 400 行的 prompt 拆分为 `SKILL.md`、一个 reference、一个 script 契约和一个输出模板。让每个文件只负责一类信息。
5. 为一个引用了不可用 MCP tool 的 skill 设计失败响应。不要悄悄替换成权限更宽的 tool。
6. 审查一个现有 skill，把每句话标注为 routing、procedure、policy、reference pointer 或 output contract。把不属于那里的内容移走。

## Key Terms

| 术语 | 人们怎么说 | 实际含义 |
|---|---|---|
| Agent skill | "保存下来的 prompt" | 一个可发现的目录，包含过程性指令和可选资源 |
| 可移植核心 | "每个运行时都共享的字段" | 由 Agent Skills 规范定义的契约 |
| 运行时扩展 | "额外的 frontmatter" | host 特有的配置，其行为需要兼容的 adapter |
| 激活 | "skill 跑起来了" | Skill 正文进入模型可见的上下文；执行可能稍后才发生 |
| Skill 依赖 | "import 另一个 skill" | 一条由运行时中介、带可用性和策略检查的调用边 |
| Tool 契约 | "一个函数 schema" | 某项能力的输入、输出、权限、副作用、错误和证据 |

## Further Reading

- [Agent Skills 规范](https://agentskills.io/specification)，了解可移植目录和 frontmatter 契约。
- [Agent Skills 最佳实践](https://agentskills.io/skill-creation/best-practices)，了解作用域、指令和资源组织。
- [OpenAI：构建 skills](https://learn.chatgpt.com/docs/build-skills)，了解当前 Codex 的发现与调用行为。
- [Claude Code skills](https://code.claude.com/docs/en/skills)，了解某个运行时的调用、参数、tool 和委派上下文扩展。
