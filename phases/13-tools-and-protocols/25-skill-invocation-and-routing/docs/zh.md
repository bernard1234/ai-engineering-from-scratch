# Skill 调用与路由

> 调用（invocation）先是一次授权决策，然后才是一次相关性决策。好的描述帮助模型做选择；好的策略决定这个选择是否被允许。

**Type:** Build
**Languages:** Python（stdlib）
**Prerequisites:** 第 13 阶段，第 24 课（技能发现与渐进式披露）
**Time:** ~105 分钟

## Learning Objectives

- 区分显式用户调用、隐式模型调用、应用调用和技能对技能调用。
- 把人类可见性和模型资格建模为两个独立的策略维度。
- 编写带有正向触发条件和近似误触（near-miss）边界说明的路由描述。
- 在 trace 和测试中把 eligibility、selection、activation、argument binding 与 execution 分离开。
- 适配特定运行时（runtime-specific）的调用字段，但不要把它们当成可移植的 frontmatter 呈现。

## 问题场景

你安装了一个 `database-migration` skill。用户可以按名字运行它，但模型也会看到它的描述，于是当有人问一个泛泛的数据库问题时就会选中它。结果这个 skill 为一个只需要解释的任务提出了 schema 变更。

你加了 `user-invocable: false`，期望阻止人们手动运行它。但在另一个运行时里，这个字段被忽略了。你又加了 `disable-model-invocation: true`，期望这个 skill 彻底消失。而在认得它的那个运行时里，用户仍然可以显式调用它。

字段名本身没有错，错的是心智模型。"用户能看到它""模型能选中它""应用能预加载它""它能执行内部的工具"是相互独立的事实。一个名叫 `invocable` 的布尔值无法表达这些。

路由还有第二种失败模式。如果描述含糊，多个 skill 都会显得可能适用。如果描述塞满关键词，不相关的任务也会触发它们。catalog 是一个概率性接口：要紧凑到装得下，也要具体到能路由。

## 核心概念

### 有五个通道可以启动这个生命周期

| 发起方 | 调用形态 | 典型用途 | 主要风险 |
|---|---|---|---|
| 人类用户 | 在 UI 或 prompt 中点名某个 skill | 有意识的工作流选择 | 用户以为拥有宿主并未授予的可用性或权限 |
| 模型或自主 agent | 根据任务上下文从 catalog 中选中一个条目 | 自动化的专家流程 | 误报路由（false-positive routing） |
| 应用 | 通过运行时（runtime）代码激活或预加载某个 skill | 固定的产品工作流 | 对单一宿主产生隐藏耦合 |
| 另一个 skill 或 subagent | 作为工作流依赖请求某个确切的 skill | 组合（composition） | 循环、缺失依赖或上下文污染 |
| 评测 harness | 在固定场景下激活某个确切的 skill | 可重复的度量 | 在测试 skill 的同时意外绕过了被测的生产策略 |

可移植的 Agent Skills 规范定义的是包本身。它并没有统一标准化的斜杠命令 UI、隐式路由开关、应用 API 或 subagent 生命周期。

### 调用的五个阶段

```figure
skill-invocation-stages
```

请精确使用这些词：

- **Eligible** 表示策略允许该发起方请求这个 skill。
- **Selected** 表示用户点名了它，或者某个 router 判定它相关。
- **Activated** 表示它的指令进入了工作上下文。
- **Executing** 表示 agent 在这些指令之下开始了模型或工具工作。
- **Completed** 表示输出通过了独立的成功检查。

只记录 `skill_used=true` 的 trace，会掩盖失败发生在哪个边界上。

### 人类调用与模型调用构成一个 2x2 矩阵

| 人类可调用 | 模型可调用 | 模式 | 合适的例子 |
|:---:|:---:|---|---|
| 是 | 是 | 共享（Shared） | 代码解释、测试规划、文档评审 |
| 是 | 否 | 仅人类（Human-only） | 发布准备、账单导出、破坏性清理计划 |
| 否 | 是 | 仅模型（Model-only） | 内部风格指南、领域参考、自动支持流程 |
| 否 | 否 | 禁用或仅应用（Disabled or application-only） | 分阶段上线、已弃用的包、程序化预加载 |

这个矩阵是策略模型，而不是标准 YAML。

某个当前宿主用 `disable-model-invocation: true` 表示"仅人类"这一行，用 `user-invocable: false` 表示"仅模型"这一行。默认两者都是。另一个宿主用 `agents/openai.yaml` 中的 `allow_implicit_invocation: false`，在保留显式调用的同时禁用隐式选择。这些是运行时适配器。未知宿主可能会忽略它们。

令人困惑的细节很重要：`user-invocable: false` 并不意味着"模型不能用它"。在定义它的宿主里，它只是移除了用户直接调用的能力。`disable-model-invocation: true` 并不意味着"这个 skill 被禁用了"。它移除了模型发起的选中，同时保留用户的显式访问。

### 显式调用以身份为先

显式调用直接给出身份：

```text
/release-readiness v2.4.0
```

或者：

```text
release-readiness check v2.4.0 without publishing
```

当前 Codex 的接口记录了用 `/skills` 进行选择，以及在请求中用纯 skill 名称进行显式调用。Claude Code 记录了 `/skill-name` 和宿主特有的参数展开。确切的语法、菜单可见性、引号规则和变量展开规则都属于宿主。

显式请求同样要通过策略。点名某个 skill 不应绕过缺失的权限、工作区约束、审批门（approval gate）或运行时隔离。

### 隐式调用以描述为先

对于隐式路由，模型最初看到的是 catalog 元数据，而不是完整的正文。因此 description 就是这个 skill 的路由接口。

弱：

```yaml
description: Helps with releases.
```

过宽：

```yaml
description: Use for release, version, package, build, deploy, publish, tag, changelog, GitHub, CI, or software tasks.
```

有界：

```yaml
description: Inspect an already prepared release candidate and produce a readiness report. Use when the user asks whether a version, tag, package, or image is ready to publish; do not use for ordinary build failures or feature development.
```

有界版本包含：

1. **能力（Capability）：** 检查一个已准备好的候选。
2. **输出（Output）：** readiness report。
3. **正向边界（Positive boundary）：** 询问某个发布产物是否已就绪。
4. **负向边界（Negative boundary）：** 普通构建和开发不在范围内。

当两个相近的 skill 共享词汇时，负向边界很有用。但它们不能替代 near-miss 评测。

### 路由是带弃权选项的分类

对某个 skill `s` 和请求 `x`，设想一个 router 分数：

```text
score(s, x) = capability_match + trigger_match + context_match - exclusion_match - ambiguity_penalty
```

精确的打分可能是一个 LLM 判断，而不是算术运算。工程原则依然成立：选中结果应当同时越过阈值并压过竞争 skill。证据薄弱时，弃权（abstain）。

```figure
skill-routing-abstention
```

对于高影响力 skill，即使描述很强，隐式路由也可能不合适。当误报的代价超过自动选择的便利时，请使用"仅人类"策略。

### Eligibility 必须先于排序

不要对所有已发现的 skill 打分、挑出得分最高的那个、然后再去检查那一个 skill 的策略。被阻止的最高匹配会错误地阻止一个合格的、得分较低的候选被考虑。

隐式路由请使用这个顺序：

1. 根据发起方主体和生效的宿主适配器，过滤已发现的 skill。
2. 只对合格的候选打分。
3. 如果最强匹配通过了阈值和歧义规则，就选中它。
4. 当没有候选合格、或没有合格候选的分数足够强时，弃权。

假设 `incident-triage` 得分 `0.80`，但它的宿主扩展禁用了模型调用。`incident-review` 得分 `0.55`，且允许模型调用。router 应当把 `incident-review` 当作最合格的候选来评估。它不应该选中 `incident-triage`、拒绝它、然后停下。

这个顺序也让策略的变更不会改变相关性分数的含义。Eligibility 定义了选择集，相关性只在这个集内排序。

### 路由评测需要 near miss

正例证明召回（recall）：

```json
{"prompt":"Is version 2.4.0 ready to publish?","expected":"release-readiness"}
```

明确的负例证明基本的精确率（precision）：

```json
{"prompt":"Explain rotary position embeddings.","expected":null}
```

Near miss 暴露边界质量：

```json
{"prompt":"Why did today's package build fail?","expected":"build-diagnostics"}
```

这个 near miss 与发布 skill 共享 `package` 和 `build`，却属于别处。一个只由明显正例和不相关负例组成的路由集，会高估质量。

### 参数有三种表示

一个调用参数会跨越若干边界：

```figure
skill-argument-boundaries
```

在每个边界上，保留意图，但不要把文本当作代码。

- 宿主解析器决定命令语法和引号规则。
- skill 按照宿主规则接收绑定后的文本或变量。
- 指令校验必填值和默认值。
- 工具调用把值转换成带类型的 schema 并重新校验。

不要把原始参数插值（interpolate）进 shell 命令。优先使用以参数向量（argument vector）调用的脚本，或带类型的 MCP 工具。

### 应用调用是显式编排

产品可以在工作流已经知道任务类型时激活某个 skill。例如，一个 pull request 评审服务可以在用户点击"Review"之后预加载 `pull-request-risk-review`。

这消除了路由的不确定性，但也产生了对运行时 API 的依赖。把这个适配器放在可移植正文之外：

```figure
skill-host-adapter
```

当另一个兼容的客户端打开这个 skill 时，它应当仍然可理解。

### 技能对技能调用是一条类工具边

假设 `release-readiness` 在依赖文件发生变化时请求 `security-change-review`。

调用方应当提供：

- 目标 skill 的身份；
- 有界的任务和产物路径；
- 预期的响应契约；
- 调用的理由；
- 不可用时的回落方案；
- 最大深度或循环规则。

```json
{
  "target_skill": "security-change-review",
  "task": "Review dependency changes in the candidate diff",
  "inputs": ["artifacts/release.diff"],
  "expected": "risk-report.json",
  "max_depth": 2
}
```

第二个 skill 不会被盲目粘贴进第一个。由宿主决定如何激活它，以及它是共享上下文、在 fork 中运行，还是通过工具结果返回。

### 上下文生命周期由宿主决定

激活之后，skill 正文可能留在对话中、在压缩（compaction）时被摘要，或者在委托的上下文中运行。工具许可可能只持续一个回合，而指令却持续更久。subagent 可能拿到这个 skill，但没有父级的完整历史。

不要编写依赖隐式生命周期假设的 skill。把持久输出放进文件或带类型的状态里，让重入（re-entry）安全，并说明中断后必须重新加载什么。

```markdown
On resume, read `artifacts/release-readiness.json` if it exists.
Revalidate the candidate commit before continuing.
Do not repeat an external write whose idempotency key is already recorded.
```

## Build It

`code/main.py` 把策略和路由实现为相互独立的适配器。

模型包含：

- `Actor`，用于 human、model、autonomous agent、application、skill 和 harness 这些调用方；
- `SkillMetadata`，用于路由身份；
- `InvocationPolicy`，用于人类/模型矩阵；
- `InvocationRequest` 和 `InvocationDecision`，用于可追溯的输入和结果；
- `CorePolicyAdapter`，用于不依赖宿主扩展的可移植行为；
- `ExtensionPolicyAdapter`，用于已识别的运行时字段；
- `build_invocation_matrix(policy)`，用于生成 2x2 视图；
- `route_request(skills, request, adapter)`，用于在相关性排序、选择和拒绝之前做 eligibility 过滤。

运行它：

```bash
cd phases/13-tools-and-protocols/25-skill-invocation-and-routing
python3 code/main.py
python3 -m unittest discover -s code/tests -v
```

demo 会打印一个矩阵，以及针对显式人类、隐式模型、自主 agent、应用、skill 组合和 harness 各通道的决策。它的扩展适配器结果展示了：一个被阻止的最高词法匹配，会在一个合格备选被排序之前被移除。它还包含按精确名称的 allowlist。整个过程不需要模型 API。这个确定性 router 的存在是为了让策略边界可以被检视，而不是宣称词法匹配能够复现生产环境的模型路由。

### 为什么核心适配器和扩展适配器要分开

如果一个解析器给每个观察到的 frontmatter 字段都赋予含义，它就是在悄悄把运行时约定升格成一个假标准。分开的适配器迫使调用方明确指出当前生效的是哪个宿主的语义。

`CorePolicyAdapter` 只使用应用提供的策略。`ExtensionPolicyAdapter` 识别一组显式的宿主字段，并记录是哪个字段改变了决策。

## Use It

在发布一个 skill 之前，先写一份调用契约（invocation contract）：

```yaml
actors:
  human: allow
  model: deny
  application: allow
  skill: deny
explicit_name: release-readiness
arguments:
  candidate: required
  publish: fixed_false
ambiguity: ask_user
missing_dependency: stop
context:
  durable_state: artifacts/release-readiness.json
  max_composition_depth: 2
```

这份契约是给适配器和测试用的设计文档。除非某个标准明确采纳它，否则它不是可移植的 `SKILL.md` frontmatter。

## Ship It

本课产出一个 `skill-invocation-router` bundle。它包含一份调用模型参考、一个示例宿主策略，以及一个不执行任何操作的 CLI：该 CLI 评估一个 human、model、autonomous-agent、application、skill-composition 或 harness 请求，并返回带有 channel、adapter、score 和 reason 的 JSON 决策。

这个单请求 CLI 是一个策略探针，而不是完整的触发评测。请使用第 27 课中带标签的正例与 near-miss 设计，来计算混淆计数、精确率、召回率和重复运行的稳定性。

## Exercises

1. 把人类/模型矩阵的四行全部创建出来，并为每一行写一个合理的用例。
2. 给 `CorePolicyAdapter` 加上"仅应用"激活。证明 human 和 model 调用方仍然被拒绝。
3. 为一个部署 skill 写十条 near miss。每条 prompt 都必须与这个 skill 共享词汇，却属于一个不同的工作流。
4. 在最高的两个路由分数之间加一个歧义余量（ambiguity margin）。当余量太小时返回 `ask`。
5. 给技能对技能的请求加上最大组合深度，并检测一个双 skill 的循环。
6. 让同一套带标签的数据分别通过核心适配器和扩展适配器。解释每一个发生变化的决策。

## Key Terms

| 术语 | 人们怎么说 | 它实际指什么 |
|---|---|---|
| Explicit invocation | "斜杠命令" | 某个发起方直接给出 skill 身份，并受策略约束 |
| Implicit invocation | "模型自己选" | router 根据任务上下文从合格的 catalog 元数据中选择 |
| User-invocable | "人类能用它" | 宿主特有的菜单或直接调用属性，不是核心字段 |
| Model-invocable | "agent 能用它" | 在宿主策略下隐式模型选择的资格 |
| Invocation adapter | "frontmatter 解析器" | 把某个宿主的字段和 API 映射成一份已声明的策略模型的代码 |
| Near miss | "hard negative" | 一个不触发、但与 skill 的预期输入相似的请求 |
| Abstention | "没有选中 skill" | 证据缺失或含糊时，一个刻意给出的路由结果 |

## Further Reading

- [Optimizing skill descriptions](https://agentskills.io/skill-creation/optimizing-descriptions) 讲解正向触发条件、具体程度和评测。
- [Evaluating skills](https://agentskills.io/skill-creation/evaluating-skills) 讲解触发评测和输出评测的设计。
- [OpenAI: Build skills](https://learn.chatgpt.com/docs/build-skills) 讲解当前 Codex 的显式调用和隐式调用控制。
- [Claude Code skills](https://code.claude.com/docs/en/skills) 讲解某个宿主的 `user-invocable`、`disable-model-invocation`、参数和委托上下文。
