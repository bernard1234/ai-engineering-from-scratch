# Skill 发现与 Progressive Disclosure

> Skill 在正文加载之前就已经产生价值。它的 name 和 description 在 catalog 中争得一席之地；更深的文件只有在任务真正到达它们时才挣得上下文。

**Type:** Build
**Languages:** Python（stdlib）
**Prerequisites:** 第 13 阶段，第 22 课（Agent Skills：可移植契约与运行时边界）
**Time:** ~105 分钟

## Learning Objectives

- 构建一条文件系统发现流水线，把作用域、校验、冲突策略和 catalog 发布分开。
- 解释三个披露层级：catalog 元数据、激活后的指令、任务特定的资源。
- 设计 references，使 agent 能直接到达所需细节，而不必加载整个包。
- 把 catalog 空间预算与激活 skill 的上下文预算分开计算。
- 当 skill 读取自己的资源时，拒绝路径穿越和符号链接逃逸。

## 问题场景

你的 agent 装了 200 个 skill。在会话开始时加载每一个 `SKILL.md`、reference 文件、script 和模板，会让当前任务淹没在无关的流程里。什么都不加载，又迫使用户记住精确的文件系统路径。

常见的折中是 catalog：向模型展示每个合格 skill 的紧凑身份和 routing description，等选中后再加载完整正文。这带来两个新的工程问题。

第一，发现不只是递归文件搜索。Skill 可以存在于项目、用户、管理员、plugin 或内置作用域。两个包可以同名。一个符号链接可以指向可信根目录之外。一个格式错误的包可能占用 catalog 空间，或变得无法调用。

第二，progressive disclosure 也可能变成 progressive confusion。如果 `SKILL.md` 说"阅读相关指南"，而包里有十二份指南，模型只能瞎猜。如果每份指南又指向另外三个文件，加载就变成无界的图遍历。

好的运行时会做到发现确定性、披露有意图。

## 核心概念

### 发现是一条编译器流水线

把文件系统当作 source input。不要把原始路径直接发布给模型。

```figure
skill-discovery-pipeline
```

每个阶段都应产出结构化数据和结构化的失败。一份发现日志应当回答：

- 搜索了哪些根目录？
- 找到了哪些候选？
- 哪些候选被拒绝，为什么？
- 哪个包赢得了冲突？
- 哪些 catalog 条目因预算而被缩短或省略？

没有这些证据，"模型没用我的 skill"几乎无法诊断。

### 作用域是运行时策略

可移植规范定义的是 skill 包，而不是一条通用的安装路径或优先级顺序。由 host 决定在哪里搜索。

一个通用运行时可能使用这些作用域：

| 作用域 | 示例根目录 | 预期归属 |
|---|---|---|
| Workspace | `<repo>/.agents/skills/` | 项目维护者 |
| User | `<user-data>/skills/` | 单个开发者 |
| Administrator | `<system>/skills/` | 机器或组织策略 |
| Plugin | 一个签名的 plugin bundle | Plugin 发布者和安装者 |
| Built-in | 运行时包 | 运行时厂商 |

截至 2026 年 8 月，Codex 文档说明项目发现从 `$CWD/.agents/skills` 开始，沿祖先目录直到仓库根，再加用户、管理员和内置位置。它支持符号链接的 skill 目录。重名可能同时出现，而不是被合并。这些是 Codex 的行为，不是 `SKILL.md` 的要求；编写 adapter 时请核对当前的 [Codex skill 文档](https://learn.chatgpt.com/docs/build-skills)。

绝不要从目录名去臆造优先级。把它声明为策略并加以测试。本课实验为每个 `Scope` 使用显式整数 rank，使同一组候选总能得到相同的解析结果。

### 冲突需要 `name` 之外的身份

两个都叫 `release-readiness` 的包可以是合理的。一个可能是 workspace 覆盖，一个是用户默认。因此一个 catalog 条目至少需要：

```json
{
  "name": "release-readiness",
  "description": "Inspect a release candidate for this repository.",
  "scope": "workspace",
  "source": "/repo/.agents/skills/release-readiness",
  "selected": true
}
```

常见的冲突策略包括：

| 策略 | 好处 | 风险 |
|---|---|---|
| 保留每个候选 | 什么都不隐藏 | 模型看到含糊的名字 |
| 最高优先级作用域胜出 | 调用简单 | 本地包可能遮蔽可信包 |
| 拒绝重复项 | 没有静默遮蔽 | 合理的覆盖也会失效 |
| 按来源限定名字 | 身份明确 | 面向用户的名字变长 |

为 host 选定一种策略。即使被拒绝或被遮蔽的候选不在模型 catalog 中，也要在诊断信息中保留它们。

### 三个披露层级

Agent Skills 规范描述了分阶段加载。关键在于每个层级有不同用途。

```figure
skill-disclosure-levels
```

#### 第 1 层：catalog 元数据

模型需要足够的信息把该 skill 与邻居区分开。规范估计每个 catalog 条目约 100 token，但实际的序列化和分词由 host 决定。

有用的 description 有两个子句：

```yaml
description: Validate a release candidate and produce a readiness report. Use when the user asks whether a version, tag, or package is ready to publish.
```

第一个子句说明能力。第二个子句说明触发边界。Lesson 25 会用正例和近似误例 prompt 来评估这个边界。

#### 第 2 层：激活后的指令

激活之后，正文应当同时充当地图和流程。规范建议把 `SKILL.md` 保持在 500 行以内。这是一个设计信号，而不是要填满的目标。

正文应当包含：

- 任务边界；
- 默认工作流；
- 分支条件；
- 指向更深文件的直接引用；
- tool 和 script 契约；
- 失败与停止行为；
- 预期输出及其验证方式。

不要仅仅为了让入口文件变短，就把核心工作流挪进 reference。激活必须给模型足够的上下文来正确开始。

#### 第 3 层：配套资源

References 提供文字或数据。Scripts 提供确定性计算。Assets 被复制、填充或转换成交付物，而不是当作指令来读。

| 目录 | 模型会读吗？ | 模型会执行吗？ | 典型内容 |
|---|:---:|:---:|---|
| `references/` | 需要时会读 | 不会 | schema、policy、领域指南 |
| `scripts/` | 可能会查看 | 通过被允许的 tool | validator、converter、collector |
| `assets/` | 仅在有帮助时 | 不会 | 模板、fixture、图片、起始文件 |

这些名字是约定，不是魔法能力。Host 仍然需要文件访问权和执行 tool。

### 分支特定的 reference 优于主题堆砌

把入口文件写成一张决策地图：

```markdown
## Choose the path

- For a Python package, read `references/python-release.md`.
- For a container image, read `references/container-release.md`.
- For a documentation-only release, read `references/docs-release.md`.
- If the release combines artifact types, read only the guides for those artifacts.
```

这给每个 reference 一个可观测的加载条件。"更多内容请阅读 `references/`"则没有。

保持 reference 图足够浅。官方指引建议从 `SKILL.md` 直接链接，并避免深链。一跳让可达性可测试，也降低了某个必需约束永远不会进入上下文的概率。

```figure
skill-reference-map
```

### Catalog 预算与激活上下文是不同的预算

设 `c_i` 为技能 `i` 的序列化 catalog 成本，`B_c` 为 catalog 预算，`b_j` 为激活正文成本，`r_k` 为实际加载的资源。

```text
catalog_cost = sum(c_i for every published skill)
active_cost = sum(b_j for every activated skill) + sum(r_k for every disclosed resource)
```

降低一个预算不会自动降低另一个。短 description 可以节省 catalog 空间，但一个被激活的 900 行正文仍会压垮任务。把正文拆成 references，只有在运行时和指令确实避免加载无关分支时，才会降低激活成本。

当上下文窗口大小已知时，Codex 目前把初始 skill 列表预算设为上下文窗口的 2%。8,000 字符这一数值只在窗口大小未知时作为回退使用；它不是与 2% 规则叠加的第二个上限。当 catalog 超出适用预算时，description 可能被缩短或省略。把这些数字当作当前 Codex 的策略，而不是 Agent Skills 标准的属性。

### 资源路径是一条信任边界

Skill 只应读取自己包内的文件。字面的字符串前缀检查还不够：

```text
references/../../../../.ssh/config
references/external-link -> /private/company-secrets
```

用文件系统语义解析包根目录和候选路径，拒绝绝对路径输入，并验证解析后的候选仍位于解析后的根目录之下。在发现之前先决定是否允许符号链接。如果允许，每次都检查解析后的目标。

```figure
skill-resource-containment
```

路径包含并不等于内容可信。一个有效的包内 reference 仍可能包含恶意指令。Lesson 26 处理这种威胁。

### 加载必须可观测

记录披露事件，但不要记录密钥：

```json
{
  "event": "skill.resource.loaded",
  "skill": "release-readiness",
  "resource": "references/python-release.md",
  "reason": "candidate contains pyproject.toml",
  "bytes": 2840
}
```

reason 把一个上下文选择变成可审查的证据。它还能帮助识别那些导致 agent "以防万一"加载每个文件的指令。

## Build It

`code/main.py` 构建了一个确定性的发现与披露引擎。

发现表面包括：

- `Scope`，用于来源和优先级元数据；
- `SkillCandidate`，表示一个未经校验的文件系统候选；
- `discover_scope(scope)`，枚举直接子级 skill 目录；
- `resolve_collisions(candidates, precedence)`，应用一种已声明的策略；
- `CatalogEntry` 和 `build_catalog(...)`，发布有界的元数据；
- `CatalogBudget`，对序列化条目计账，而不会假装字符等于通用 token。

披露表面包括：

- `load_skill_body(entry, ...)`，用于第 2 层激活；
- `validate_reference(skill_dir, reference)`，用于路径包含检查；
- `load_reference(...)`，用于有界的第 3 层读取。

运行实验：

```bash
cd "$(git rev-parse --show-toplevel)"
cd phases/13-tools-and-protocols/24-skill-discovery-and-progressive-disclosure
python3 code/main.py
python3 -m unittest discover -s code/tests -v
```

此代码块需要本地 clone，并会从 clone 内任意工作目录解析出仓库根。

Demo 会创建临时的项目和用户作用域，插入一个冲突，在刻意很小的预算下构建 catalog，激活一个 skill，并尝试一次有效的 reference 读取和一次穿越逃逸。不会安装任何永久文件。

### 为什么发现是浅层的

`discover_scope` 检查直接子目录中是否有 `SKILL.md`。它不会递归地把每个嵌套的 `SKILL.md` 都当作独立包。这保持了包边界，避免意外发布已安装 skill 内部的示例或 fixture。

### 为什么实验不解析任意 YAML

该实验只支持其 catalog 所需的标量 frontmatter。生产运行时应使用安全的 YAML 解析器，并设置显式 schema、大小限制和禁用的自定义对象构造。"Stdlib-only"是教学约束，不是悄悄发明一套残缺 YAML 方言的许可。

## Use It

把这份清单应用到任何发现 adapter：

1. 列出每个已配置的根目录，以及谁可以写入它。
2. 声明是否允许符号链接的包。
3. 校验包名、目录名、必需元数据和入口正文大小。
4. 在内部身份中保留来源和作用域。
5. 声明并测试重名行为。
6. 测量实际发送给模型的精确序列化 catalog。
7. 记录正文或资源为何被加载。
8. 让资源读取保持在解析后的包根目录之内。
9. 当被引用的文件缺失时明确失败。
10. 当安装或策略变化时重建 catalog。

## Ship It

本课产出 `skill-catalog-builder` bundle。它扫描显式排序的根目录，拒绝符号链接的入口文件和名字与目录不匹配的包，解析跨作用域冲突，拒绝同优先级的重复项，并把选中的元数据装进声明的条目数、description 长度和序列化字符预算。

它的 JSON 报告包含选中的条目、被遮蔽的候选、被省略的条目、校验错误、优先级和预算使用情况。正文和 reference 加载仍是独立的运行时操作，因此 catalog builder 不会执行脚本，也不会把整个包放进上下文。

## Exercises

1. 添加一个 plugin 作用域，并把它放在 user 与 built-in 优先级之间。用测试证明冲突结果。
2. 把冲突策略从最高优先级改为限定名字。在 catalog 中保留两个条目。
3. 给 `load_reference` 添加字节大小限制。测试一个恰好等于限制的文件和一个超出 1 字节的文件。
4. 创建两个听起来几乎一样的 description。重写它们，使触发边界不重叠。
5. 添加一个 manifest，包含每个 reference 和 script 的哈希。在加载资源前检测其是否被修改。
6. 给 demo 加入 instrumentation，分别报告第 1 层、第 2 层和第 3 层的字节数。

## Key Terms

| 术语 | 人们怎么说 | 实际含义 |
|---|---|---|
| Skill 发现 | "找到每个 SKILL.md" | 搜索配置的作用域、校验包、附加来源信息并应用策略 |
| Skill catalog | "已安装 skill 的列表" | 面向模型、用于 routing 的紧凑元数据，覆盖合格包 |
| 冲突策略 | "哪个重复项赢" | 针对来自不同来源的同名候选所声明的规则 |
| Progressive disclosure | "懒加载" | 从 catalog 到正文再到分支特定资源的分阶段上下文准入 |
| Reference 图 | "skill 链接的文件" | 可达的资源结构及其加载条件 |
| 路径包含 | "别跑出文件夹" | 验证解析后的资源目标仍位于解析后的包根内 |

## Further Reading

- [Agent Skills specification](https://agentskills.io/specification)，了解包形态和 progressive disclosure 层级。
- [Optimizing skill descriptions](https://agentskills.io/skill-creation/optimizing-descriptions)，了解 catalog routing 元数据。
- [Agent Skills best practices](https://agentskills.io/skill-creation/best-practices)，了解直接引用和入口文件大小。
- [OpenAI: Build skills](https://learn.chatgpt.com/docs/build-skills)，了解当前 Codex 的发现作用域与 catalog 限制。
