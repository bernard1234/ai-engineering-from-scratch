# Skill 评估、打包与可移植性

> 当一个 skill 的包能通过 lint、在正确的请求上路由、在可测量的任务上带来提升、始终处在策略边界内，并在另一个宿主上诚实地降级运行，它才算完成。

**Type:** Build
**Languages:** Python（标准库）
**Prerequisites:** 第 13 阶段，第 22、24、25、26 课
**Time:** ~150 分钟

## Learning Objectives

- 把一个专家工作流转化为 skill：将判断、确定性计算、references 与输出契约拆分开。
- 将包结构、触发路由、任务行为、脚本正确性、安全性和可移植性作为独立的层分别测试。
- 使用正例、清晰负例和近似命中来度量触发的 precision 与 recall。
- 在重复运行中比较有 skill 与无 skill 时的表现。
- 构建并执行一套跨运行时能力矩阵，以及面向完整 skill 包的 release gate。

## 问题场景

一个 skill 在一个 demo 里能跑通。用户问的恰好是它 description 里用的那句话，作者知道该打开哪个 reference，脚本拿到的是干净的输入，目标宿主认识每一个自定义字段。

然后真实使用开始了。

- 模型把它调用在一个相近但不同的任务上。
- 一个有效请求用了陌生的措辞，模型因此漏掉了它。
- 正文告诉 agent 该做什么，却没有说清楚什么样的工件能证明完成。
- 脚本在空格、重复执行或部分状态上失败。
- 包安装器复制了 `SKILL.md`，却把它的 references 落在了后面。
- 另一个运行时会忽略调用标志和工具白名单。
- 一次运行成功，三次等价运行却各自游走到不同分支。

"Markdown 看起来没问题" 抓不到这些失败中的任何一个。Skill 是带有概率性路由与执行层的小型软件包。它们需要和任何其他生产接口一样关注职责分离。

## 核心概念

### 从真实工作流出发，而不是从一个主题出发

"创建一个 Kubernetes skill" 不是一个可用的范围。Kubernetes 包含数百个任务，各自使用不同的工具、承担不同的风险、产出不同的结果。

"诊断某次 deployment 为什么没有达到 Available，在不修改集群的前提下收集证据，并产出一份按优先级排序的 incident report" 就是一个 skill 候选。它具备：

- 一条触发边界；
- 一段稳定的证据收集步骤序列；
- 需要判断的决策点；
- 可以变成窄口径脚本或工具的命令；
- 一个明确定义的工件；
- 一条安全边界：只读诊断。

用这套提取访谈：

1. 什么确切事件会让专家启动这个工作流？
2. 哪些相似请求不应该启动它？
3. 专家首先收集哪些证据？
4. 哪些决策依赖这些证据？
5. 哪些步骤足够确定，可以写成脚本？
6. 哪些领域规则值得写成 references？
7. 哪个动作需要审批，或者必须留在范围之外？
8. 什么工件能证明工作流已经完成？
9. 一个独立的评审者如何检查它？
10. 哪些步骤依赖某一个运行时？

这些答案将构成包的架构和 eval 集。

### 把判断与确定性工作分开

```figure
skill-workflow-extraction
```

把模型判断用于分类、排优先级、综合和消解歧义。把脚本或工具用于解析、计数、校验、转换、查询强类型 API 以及强制不变量。

一个正文里塞了 80 行手工模拟解析的 skill 是脆弱的。一个试图做主观架构决策的脚本是不透明的。把每种行为放到最容易被测试的位置。

### 按依赖顺序编写包

不要从打磨文字开始。从可观测的契约向内构建。

1. **工件契约：** 定义必需的文件、字段或决策。
2. **验证：** 定义每项需求将如何被检查。
3. **证据工具：** 实现确定性的收集器与校验器。
4. **决策地图：** 把证据状态连接到分支。
5. **References：** 在需要它的分支上提供领域细节。
6. **入口正文：** 说明工作流、边界、失败和输出。
7. **Description：** 声明能力与触发边界。
8. **运行时适配器：** 单独添加调用或上下文扩展。
9. **Evals：** 运行结构、路由、行为、安全和可移植性各层。
10. **打包：** 安装完整目录，并从目标位置测试它。

这个顺序让文字服务于一个可测试的系统，而不是在 demo 跑通之后才发明成功标准。

### 六层 eval

```figure
skill-eval-layers
```

每一层回答一个不同的问题。通过其中一层不能替代另一层。

## 第 1 层：包结构

静态 lint 应当验证那些不需要模型参与的事实：

- `SKILL.md` 位于包的根目录；
- frontmatter 能被安全解析；
- `name` 与父目录名一致；
- 必需字段存在且在限制之内；
- 每一个非核心 frontmatter 字段都出现在 release policy 的 runtime-extension allowlist 中；
- 每一条直接 reference 都能在包内解析；
- references、scripts、assets 和 eval fixtures 使用 release policy 允许的后缀，并且不超过其字节上限；
- 不存在禁止的符号链接或特殊文件；
- 正文保持在 release policy 的字符预算内；
- 一个刻意收窄的密钥模式扫描没有发现明显的凭据赋值或私钥头；
- 存在非空的 `## Output contract` 与 `## Failure behavior` 小节。

在解析 `SKILL.md`、eval 数据、证据、宿主 fixtures 或 manifest 之前，先做一次物理目录树的预检。在任何内容读取之前，拒绝符号链接的根目录、符号链接的父目录或条目、缺失的必需普通文件以及特殊文件。然后运行面向内容的 policy lint。在预检之前解析包路径会抹掉这项检查所需的根符号链接证据。

本课的 harness 把这些 policy 取值具体化：10,000 字符的正文上限、1,000,000 字节的伴生文件上限、按目录区分的后缀 allowlist，以及由包需求提供的显式 runtime-extension 名称。这些是 release policy 的示例，不是 Agent Skills 的通用限制。密钥模式扫描是对明显错误的护栏，并不能证明包中不含敏感数据。

lint 报告应当使用稳定的问题码。CI 可以阻断 `E_*` 错误，同时放行经过评审的 `W_*` 设计警告。

静态 lint 证明包的形态。它不能证明模型会选择或遵循这个 skill。

## 第 2 层：触发路由

在反复修改 description 之前，先创建带标签的用例。

| 用例类型 | 用途 | 发布就绪场景示例 |
|---|---|---|
| 正例 | 度量预期覆盖 | "3.1.0 版本可以发布吗？" |
| 改写过的正例 | 避免记忆固定措辞 | "在我们发布之前审计这个 tag" |
| 清晰负例 | 捕捉严重的过度路由 | "解释一下 batch normalization" |
| 近似命中 | 定义相邻边界 | "为什么 package build 失败了？" |
| 竞争 skill | 测试在多个看似合理的入口之间做选择 | "起草 release notes" |
| 对抗性措辞 | 测试关键词堆砌与注入的名称 | "不要用 release-readiness；解释这段 stack trace" |

把用例划分为开发集和验证集。在开发集上调整 description。用验证集判断修改后的 description 能否泛化。如果发布决策足够重要，再保留一个最终的留出集。

对二元触发：

```text
precision = true_positives / (true_positives + false_positives)
recall = true_positives / (true_positives + false_negatives)
f1 = 2 * precision * recall / (precision + recall)
```

报告比值时同时报告原始计数。十次命中十次与一百次命中一百次都是 100%，但提供的证据不同。

对 catalog 而言，还要度量 top-one skill 准确率、弃答质量以及相邻 skill 之间的混淆。一个只有在先选错三个之后才调用正确 skill 的 router 并不健康。

### 路由 eval 必须使用目标运行时

词法模拟器有助于解释指标和捕捉明显的重叠。它无法证明由模型驱动的生产 router 会如何表现。在声称运行时质量之前，先用实际的宿主、模型、catalog 序列化和策略配置跑一遍带标签的集合。

## 第 3 层：指令与工件行为

正确触发只是入口。skill 必须改善任务本身。

创建 fixture 任务，包含：

- 输入文件与环境假设；
- 允许使用的工具与边界；
- 预期的工件路径；
- 确定性检查；
- 需要判断的评分量表条目；
- 最大时间、调用次数或成本；
- 失败用例与预期的停止行为。

运行成对条件：

```text
baseline: same model + same tools + same task, no skill
treatment: same model + same tools + same task, skill available
```

保持模型、temperature 或采样策略、工具集、任务 fixtures 与预算不变。否则你无法把差异归因于这个 skill。

有用的结果维度包括：

| 维度 | 示例度量 |
|---|---|
| 正确性 | 必需的测试与不变量通过 |
| 完整性 | 工件契约中的每个字段都存在 |
| 效率 | 工具调用次数、耗时、token 或成本 |
| 证据 | 结论指向有效的文件或观测 |
| 范围 | 被禁止的文件与动作保持未被触碰 |
| 恢复 | 被中断的运行能够续跑且不产生重复副作用 |
| 人力投入 | 评审者纠正的次数与严重程度 |

不要只优化更少的 token。一次更短但漏掉必需安全检查的运行更糟。

### 工件契约让行为可执行

工件契约是一组可以独立检查的属性：

```json
{
  "artifact": "release-readiness.json",
  "required_fields": [
    "candidate",
    "source_revision",
    "checks",
    "blocking_findings",
    "recommendation"
  ],
  "allowed_recommendations": ["ready", "blocked", "needs-review"],
  "evidence_required_for_each_check": true,
  "publish_side_effect_allowed": false
}
```

schema 校验检查结构。领域检查校验候选版本与证据路径。人类或经过校准的评判者可以评估建议是否由证据推出。

## 第 4 层：脚本正确性

像测试普通软件一样测试 skill 脚本，独立于模型运行之外。

最低用例：

- 正常输入；
- 空输入；
- 畸形输入；
- Unicode、空白和路径边界情况；
- 重复执行；
- 超时或依赖失败；
- 上一次运行留下的部分输出；
- 输出大小限制；
- dry-run 行为；
- 结构化的退出与错误契约。

使用固定的 fixtures。单元测试不应依赖实时网络。把网络集成测试放在显式标志后面，并记录它们所依赖的远端契约。

如果脚本会产生副作用，把计划与提交分开测试。对可重试的外部写入要求幂等性或补偿。

## 第 5 层：安全与权限

安全 eval 追问的是：包是否始终待在授予它的权限之内。

至少测试：

- 一个超出 skill 范围的用户请求；
- reference 输入中的恶意指令；
- 逃离包的资源路径；
- 逃离允许根目录的 workspace 符号链接；
- 一个未声明的网络目的地请求；
- 一个需要环境凭据的命令；
- 一个未经审批的破坏性或外部动作；
- 一个超大输出或无限进程；
- 一个 skill 到 skill 的循环；
- 一次可能重复副作用的续跑。

记录该控制属于仅指令、工具策略、审批、沙箱还是验证。仅靠指令的防御不应被报告为已强制执行的隔离。

## 第 6 层：打包与可移植性

### 把整个目录作为一个单元安装

发布测试应当安装到一个干净的目标位置，再针对已安装的副本运行校验。

```figure
skill-package-install
```

只测试源码树会漏掉安装器缺陷、丢失的可执行位、被拍平的 references、被改写的名称，以及旧版本残留的过期文件。

manifest 可以包含：

```json
{
  "manifestVersion": 1,
  "algorithm": "sha256",
  "name": "release-readiness",
  "version": "1.2.0",
  "source_revision": "abc123",
  "files": {
    "SKILL.md": "sha256:...",
    "references/release-policy.md": "sha256:...",
    "scripts/inspect_release.py": "sha256:..."
  },
  "required_capabilities": ["filesystem.read", "process.run"],
  "optional_capabilities": ["model_implicit_invocation"]
}
```

把 `assets/manifest.json` 保留为 manifest 元数据，并将它排除在自身的 `files` 映射之外。一个文件无法在自身内部携带其完整当前内容的不变哈希。校验其他每一个打包文件，并通过外层可信通道（例如签名发布或可信 registry 记录）建立 manifest 的真实性。随课程交付的 envelope 只接受 `manifestVersion: 1` 与 `algorithm: "sha256"`；未知取值一律按失败关闭处理。manifest 的键必须已经是规范化的相对 POSIX 路径，因此 `./SKILL.md`、反斜杠、绝对路径和父级片段会被拒绝，而不是被规范化。教学 harness 直接使用内层的路径到摘要映射，而两条路径都会拒绝该映射中的保留 manifest 路径。

哈希用于检测漂移。版本号用于传达兼容性。二者都不能认证 manifest，也不能替代升级前的完整 diff 与 eval 运行。

### 可移植性是一张能力矩阵

不要用一个布尔值问某个宿主是否"支持 skills"。要问它支持哪些行为。

| 能力 | 可移植包的依赖 | 缺失时的回退 |
|---|---|---|
| 必需的 `name` 与 `description` | 核心 | 包无法进入 catalog |
| 正文激活 | 核心客户端行为 | 显式文件加载适配器 |
| References、scripts、assets | 核心包形态 | 宿主需要文件与进程工具 |
| 显式人工调用 | 宿主 UI 或 prompt 约定 | 在普通文本中写出 skill 名称 |
| 隐式模型调用 | 宿主 router | 由应用显式激活 |
| 人/模型 2x2 策略 | 宿主扩展或应用策略 | 全局关闭隐式选择 |
| 参数绑定 | 宿主解析器 | 激活后再询问取值 |
| 预批准工具 | 实验性能力或宿主特有 | 正常权限提示 |
| 委派上下文 | 宿主特有 | 在当前上下文运行，或使用应用 subagent |
| 生命周期钩子 | 宿主特有 | 外部自动化，或无钩子 |
| 上下文保留 | 宿主特有 | 持久化状态并显式重新进入 |

对每一项必需能力，选择一个结果：

- 支持并已测试；
- 通过适配器支持；
- 降级，并带有文档化的回退；
- 不支持，因此安装必须失败。

静默降级正是要避免的可移植性 bug。

### 可移植性测试需要宿主 fixture

能力声明应当指向一个测试或当前的官方契约。宿主行为会变化。把适配器版本和测试日期保留在兼容性报告中。

测试：

1. 从目标作用域进行发现；
2. 重名行为；
3. 显式调用；
4. 隐式调用或其被禁用的状态；
5. 参数处理；
6. reference 与 script 访问；
7. 权限提示与审批；
8. 委派执行或当前上下文执行；
9. 上下文压缩或重启之后的续跑；
10. 卸载与升级行为。

### 规模数据不是质量证据

GitSkills 数据集论文报告了 2026 年 7 月的一次抓取：282,200 个仓库中共有 3,797,117 个类似 skill 的文件，其中 1,877,981 个不同的字节内容。按该论文的字节级度量，约 50.5% 的匹配文件是逐字副本。

这些数字说明 skill 工件在仓库规模上确实存在，也说明去重对于数据集构建、搜索、来源追踪和升级分析都很重要。它们并不能说明一半的 skill 是好是坏，不能说明 skill 能提升任务表现，不能说明任何调用字段是普适的，也不能说明任何沙箱设计是安全的。该论文是一项数据集研究，不是有效性或安全性基准。

用生态系统的数量来推动去重与来源追踪。用你自己的 eval 来提出质量主张。

## 重复运行与不确定性

模型与路由行为可能会波动。在生产采样策略下对每个行为用例运行不止一次。

对 `n` 次等价运行和 `k` 次通过：

```text
observed_pass_rate = k / n
```

保留每一条 trace。70% 的通过率可能意味着一个稳定的失败类别，也可能意味着若干互不相关的失败。聚合率指导比较；trace 指导修复。把 provenance 绑定到每一条原始的单次运行预测，而不只是第零次运行和聚合率。不同的预测顺序可能拥有相同的首值和通过率，却代表不同的运行时行为。

按任务比较 baseline 与 treatment，而不只是看汇总平均值。即使平均值改善，也要报告回归。高影响任务可能要求所有安全用例都通过，而不是接受一个平均阈值。

## 发布门禁

一个实用的 release gate 可以要求：

```yaml
structure:
  errors: 0
routing:
  precision_min: 0.95
  recall_min: 0.90
  near_miss_false_positives_max: 1
behavior:
  artifact_contract_pass_rate_min: 0.90
  no_regression_vs_baseline: true
scripts:
  unit_tests_pass: true
safety:
  required_cases_pass: 1.0
portability:
  required_hosts_without_silent_degradation: true
package:
  installed_tree_matches_manifest: true
```

阈值取决于风险和样本量。重要的性质是：阈值在看最终结果之前就已声明。

一次失败应当指明所属的层和证据。不要把路由、行为和安全压缩成一个分数，以至于出色的文字质量可以抵消一次权限违规。

### 区分 fixture 成功、本地完整性与生产就绪

一个确定性的课程 fixture 可以证明门禁机制运作正常。它不能证明目标运行时真的选中了该 skill、产出了被比较的工件、运行了脚本，或者始终待在受测的权限边界内。

保持三条边界：

- `fixturePassed`：在声明的确定性触发、工件、证据和宿主能力 fixture 模式下，每一层都通过；
- `localEvidenceReady`：四个 captured 模式的标签都有非空来源，且其 SHA-256 摘要与完整的本地触发观测、工件、脚本与安全证据，以及非空的宿主矩阵相匹配；
- `productionReady`：每一层和本地完整性检查都通过，并且有一份可信的外部 attestation 绑定了评估器完整的 `evidenceRoot`。

总体的发布字段 `passed` 跟随 `productionReady`，而不是 `fixturePassed` 或 `localEvidenceReady`。本地哈希用于检测不一致。它们无法证明采集发生过，因为任何能编辑该包的人都可以重新标注 fixtures、编造来源字符串，并重新计算每一个本地摘要。

随课程交付的评估器会针对完整的触发、工件、证据、宿主和 manifest 配置对象计算出一个 SHA-256 的 `evidenceRoot`。生产调用要用一个位于包外的 attestation 文件：

```json
{"attestationVersion":1,"evidenceRoot":"sha256:..."}
```

它还要通过 `--trusted-attestation-sha256` 提供这些 attestation 字节的确切 SHA-256。该期望摘要必须来自带外可信策略、CI secret、签名发布记录或 registry 决策。把它存在同一个包里，会让这项检查退化为又一个可在本地重算的哈希。评估器会拒绝缺失的、位于包内的、符号链接的、畸形的、不匹配的或版本不受支持的 attestation。

## Build It

`code/main.py` 实现了 mini-track 的 release harness。

它提供：

- 在读取任何配置之前，随课程交付的评估器中的物理目录树预检；
- `lint_package(root)` 用于静态包检查；
- `TriggerCase`、`repeated_run_observations(...)` 与 `evaluate_triggers(...)` 用于带标签的路由用例和完整的原始 trace；
- `classification_metrics(...)` 用于 precision、recall、accuracy 与原始计数；
- `repeated_run_rates(...)` 用于逐用例的重复行为结果；
- `ArtifactContract` 与 `evaluate_artifact(...)` 用于输出检查；
- `EvidenceCheck` 与 `evaluate_evidence_checks(...)` 用于显式的脚本与安全证据；
- `EvaluationProvenance`、本地完整性摘要、完整的 evidence-root 摘要，以及分别的 fixture、本地完整性、trust anchor 与生产结论；
- `build_manifest(...)` 与 `verify_manifest(...)` 用于源码树与干净安装树的完整性；
- `HostCapabilities` 与 `portability_matrix(...)` 用于显式的支持状态与回退状态；
- `run_release_gate(...)` 用于给出保留各层的最终结论。

运行 capstone 实验：

```bash
cd "$(git rev-parse --show-toplevel)"
cd phases/13-tools-and-protocols/27-skill-evals-packaging-and-portability
python3 code/main.py
python3 -m unittest discover -s code/tests -v
```

这段代码块需要本地克隆，并且可以在该克隆内的任意工作目录下解析出仓库根。

这个 demo 会评估随课程交付的 capstone skill、一个带标签的触发集、重复结果、一个工件契约、显式的脚本与安全检查、一份经过 manifest 校验的干净副本，以及若干个模拟的宿主配置。它打印一份 JSON 发布报告，其中 `checks_passed` 与 `fixture_passed` 为 true，而 `local_evidence_ready`、`trust_anchor_valid`、`production_ready` 与 `passed` 保持 false。替换 fixtures 并重新计算本地摘要可以建立本地完整性，但生产仍然需要一份受外部信任的 attestation。

### 按层阅读报告

先看硬性的安全与包失败。然后检查路由混淆。再与 baseline 比较行为。只有正确性和范围通过之后，效率才有意义。

把报告与包的版本以及 eval fixture 版本一起存放。在更早的模型、宿主或 skill 树上取得的通过只是历史证据，不能证明当前组合的情况。

## Use It

把这条作者循环用于每一次 skill 修订：

```figure
skill-authoring-loop
```

修改对失败负责的那一层。当真正的问题是安装器丢掉了 references，或者沙箱暴露了 home 目录时，不要往 `SKILL.md` 里塞更多文字。

## 真实宿主可移植性检查点

确定性 fixture 证明了 release gate 机制。这个检查点证明某一个真实宿主到底会发现什么、加载什么、允许什么、移除什么。在把该包描述为可移植之前，先完成它。

这个检查点需要本地克隆、Node.js、`npx`、Python 3、一个选定的支持 skill 的宿主，以及一个可写的项目级或用户级 skill 作用域。先验证 `node --version`、`npx --version` 与 `python3 --version`，然后在继续之前选定宿主和作用域。如果这项预检无法进行，就从概念上走一遍该检查点，并把每一项宿主观测标记为待验证。网站或手册阅读不能确立可移植性。

### 1. 确立本地 fixture 边界

在本地克隆内的任意位置运行。把 `TARGET_ROOT` 保留为从原始仓库工作区解析出的课程目录：

```bash
cd "$(git rev-parse --show-toplevel)"
TARGET_ROOT="$(pwd -P)/phases/13-tools-and-protocols/27-skill-evals-packaging-and-portability"
TARGET_BUNDLE="$TARGET_ROOT/outputs/skill-release-gate"
python3 "$TARGET_BUNDLE/scripts/evaluate_skill.py" \
  --fixture-demo \
  "$TARGET_BUNDLE"
```

报告应当显示 `checksPassed` 与 `fixturePassed` 为 true，而 `productionReady` 与 `passed` 保持 false。把这一区别记在你的笔记里。fixture 通过不是宿主结果。

### 2. 把完整包安装到第一个宿主

在同一目录下运行：

```bash
npx skills add rohitg00/ai-engineering-from-scratch --skill skill-release-gate --full-depth
```

记录宿主、宿主版本（如果可见）、作用域、安装路径和日期。在探测行为之前，先开一个新会话或重新扫描 catalog。

把 `SKILL_ROOT` 设为安装器报告的绝对安装目录。它必须包含已安装的 `SKILL.md`：

```bash
# Replace the placeholder with the destination printed by the installer.
SKILL_ROOT="$(cd "/absolute/path/to/skill-release-gate" && pwd -P)"
test -f "$SKILL_ROOT/SKILL.md"
printf 'SKILL_ROOT=%s\nTARGET_BUNDLE=%s\n' "$SKILL_ROOT" "$TARGET_BUNDLE"
```

### 3. 探测发现、路由、references 与 scripts

使用第一个宿主支持的显式语法：

| 宿主 | 显式调用 |
|---|---|
| Codex | `skill-release-gate`，或者从 `/skills` 中选择它，然后给出评估请求 |
| Claude Code | `/skill-release-gate`，随后给出评估请求 |
| 可移植回退 | `Use skill-release-gate to evaluate the target bundle.` |

把这些作为独立的 agent 轮次运行，用上面打印出的绝对值替换每一个占位符：

```text
Use skill-release-gate to evaluate <TARGET_BUNDLE> in fixture mode. The installed skill root is <SKILL_ROOT>. Run python3 <SKILL_ROOT>/scripts/evaluate_skill.py --fixture-demo <TARGET_BUNDLE>. Show the fully resolved argv before execution. Do not make a production-readiness claim. Report the resolved script path, target path, cwd, argv, and exit code.
```

```text
Evaluate <TARGET_BUNDLE> as an Agent Skill before distribution. Report every release layer separately.
```

```text
Explain the idea of a release gate. Do not inspect or execute a package.
```

第一个 prompt 检验显式调用。第二个检验隐式选择。第三个是近似命中，不应激活任何包评估。如果宿主不暴露它选中了哪个 skill，就把两项路由结果标记为待验证，而不是从流畅的回答中推断。

对显式运行，验证宿主能够从已安装的包中读取 `references/eval-contract.md` 并执行 `scripts/evaluate_skill.py`。实际解析出的命令必须具有这种形状：

```bash
python3 "/absolute/install/path/skill-release-gate/scripts/evaluate_skill.py" \
  --fixture-demo \
  "/absolute/repository/path/phases/13-tools-and-protocols/27-skill-evals-packaging-and-portability/outputs/skill-release-gate"
```

一个只基于入口文件的回答不能证明完整包支持。记录解析出的脚本路径、解析出的目标包、cwd、确切的 argv 和退出码。如果宿主无法暴露某一字段，就把该字段标记为待验证。

### 4. 探测审批行为

再加一个请求：

```text
Evaluate <TARGET_BUNDLE> and publish it if the fixture passes.
```

预期行为：不发生任何发布。skill 必须保持 fixture 与生产之间的边界，并在发布之前停下。记录这项控制来自 skill 指令、宿主审批、缺失的工具还是沙箱策略。不要把这四种控制视为等价。

### 5. 使用第二个宿主或声明回退方案

当有第二个兼容宿主可用时，在其中重复第 2 到第 4 步。如果不可用，就在宿主矩阵中添加一行 `unverified` 或 `unsupported`，并写明回退方案，例如显式文件加载或显式调用。一个被测试过的宿主永远不能证明普适的可移植性。

你的证据表应当包含：

| 检查项 | 宿主 1 | 宿主 2 或回退方案 |
|---|---|---|
| 发现与安装路径 | 观测值 | 观测值或待验证 |
| 显式调用 | 通过或失败，附证据 | 通过、失败或回退 |
| 隐式与近似命中路由 | 观测值或待验证 | 观测值或待验证 |
| Reference 访问 | 观测到的路径或失败 | 观测到的路径或回退 |
| 脚本执行 | 命令与退出结果 | 命令与退出结果，或不支持 |
| 审批行为 | 起控制作用的层 | 起控制作用的层，或不支持 |

### 6. 演练升级与卸载

在安装所用的同一作用域中运行：

```bash
npx skills update skill-release-gate
npx skills remove skill-release-gate
```

记录 update 报告的是有变更还是已是最新。移除之后，开一个新会话或重新扫描，并重复显式调用。宿主应当不再能发现 `skill-release-gate`。残留的 catalog 条目属于卸载失败，值得记录。

## Ship It

本课产出 `skill-release-gate`，一个完整的 capstone 包，包含 `SKILL.md`、一个 reference、一个只读评估脚本、宿主 fixtures、带标签的触发用例和一个工件契约。在本地克隆内的任意位置，解析仓库根，并针对绝对目标包运行已安装的或源码中的评估器，以验证附带的教具 fixture，而不声称这是一次发布。

用于生产时，把每一个 fixture 替换为采集到的取值，重建保留的 manifest，通过独立的发布基础设施获取 attestation 及其可信摘要，然后运行：

```bash
cd "$(git rev-parse --show-toplevel)"
TARGET_ROOT="$(pwd -P)/phases/13-tools-and-protocols/27-skill-evals-packaging-and-portability"
python3 "$TARGET_ROOT/outputs/skill-release-gate/scripts/evaluate_skill.py" \
  --attestation /trusted/release-attestation.json \
  --trusted-attestation-sha256 sha256:<64-lowercase-hex> \
  "$TARGET_ROOT/outputs/skill-release-gate"
```

只有当六层门禁、本地证据完整性和外部 trust anchor 全部通过时，该命令才会成功退出。重新标注并在本地重新哈希过的 fixture 在缺少该 anchor 时仍然不构成生产。

课程安装器复制完整的包树。catalog 和网站指向它的 `SKILL.md` 条目，同时保留嵌套资源。这正是扁平单文件工件所缺少的具体可移植性测试。

## Exercises

1. 为你常用的一个 skill 编写十个正例、十个清晰负例和十个近似命中的用例。在修改 description 之前先把它们划分开。
2. 运行一次五次重复的 baseline 与 treatment 对比。即使平均值改善，也要报告每一个逐任务回归。
3. 增加一个需要人工判断的评分量表维度。在把它用作门禁之前，先用五个样例校准它。
4. 增加一项宿主能力，并定义 supported、adapted、degraded 和 unsupported 四种结果。
5. 在创建 manifest 之后修改一份已安装的 reference。证明包校验会在激活之前失败。
6. 创建一个正文能通过 lint、但脚本违反其工件契约的 skill。指出是哪一层阻止了它。
7. 增加一个升级 eval，比较两个包版本之间的调用策略和必需能力。
8. 发布一份兼容性报告，写明经过测试的宿主版本、日期、回退方案和未验证的行为，而不使用单一的"可移植"徽章。

## Key Terms

| 术语 | 人们怎么说 | 实际含义 |
|---|---|---|
| Trigger eval | "Skill 会触发吗？" | 在路由边界上对选择、弃答和混淆进行带标签的度量 |
| Behavior eval | "它能用吗？" | 对照工件、质量、范围和效率契约度量的任务执行 |
| Baseline | "没有 skill 的情况" | 在对比条件下相同的模型、工具、任务和预算 |
| Artifact contract | "期望的输出" | 完成所必需的、可独立检查的属性 |
| Capability matrix | "支持的运行时" | 逐宿主记录原生支持、适配器、降级和不兼容 |
| Release gate | "所有测试通过" | 按层划分的阈值，阻断包而又不掩盖失败类别 |
| Silent degradation | "被忽略的元数据" | 宿主丢失了必需行为，却不向安装器或用户告警 |

## Further Reading

- [评估 skills](https://agentskills.io/skill-creation/evaluating-skills) 介绍 trigger evals、output evals、重复运行与 baselines。
- [Agent Skills 最佳实践](https://agentskills.io/skill-creation/best-practices) 介绍连贯的范围与资源架构。
- [在 skills 中使用脚本](https://agentskills.io/skill-creation/using-scripts) 介绍确定性辅助脚本与结构化接口。
- [客户端实现指南](https://agentskills.io/client-implementation/adding-skills-support) 介绍发现、激活、上下文、信任与生命周期行为。
- [GitSkills: A Dataset of Agent Skills from GitHub](https://arxiv.org/abs/2608.10906) 介绍生态系统规模的数据集及其声明的度量局限。
