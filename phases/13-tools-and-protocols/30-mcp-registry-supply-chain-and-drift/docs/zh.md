# MCP Registry 供应链：准入、漂移与回滚

> 一条 registry 记录告诉你的只是发布者声明了什么。生产环境中的准入要证明你取到了什么、观察到了什么、批准了什么，以及你能安全恢复什么。

**Type:** Build
**Languages:** Python
**Prerequisites:** 第 13 阶段，第 17 课（网关与注册中心）、第 18 课（生产环境认证）
**Time:** ~90 分钟

## Learning Objectives

- 把 Registry 发布、包 provenance、运行时发现和本地审批区分开。
- 在不信任记录内部自报名称的前提下验证一个 MCP 服务端命名空间。
- 钉住不可变的发布、执行源、provenance 与实时描述符证据。
- 在准入之后检测 registry 状态变化与运行时 drift。
- 把路由回滚到此前已准入的版本，同时不重写历史。
- 维护一个可防篡改的准入账本，解释每一次决策。

## 问题场景

你在一个 registry 里找到 `com.example/inventory`。它的描述看起来正确。它的包存在。服务端会响应 `server/discover`。

这并不是一个事实，而是一条来自不同权威的事实链：

1. 一个通过了某命名空间认证的发布者提交了一条记录。
2. 一个包 registry 提供了一个具有特定身份和摘要的工件。
3. 一个运行中的端点报告了协议版本、capabilities、tools 以及诊断用的 server 信息。
4. 你的组织决定这个确切的组合是被允许的。

把这些事实压缩成“它在 registry 里，所以可信”，就会形成供应链盲区。一次有效的发布仍可能被弃用。如果不钉住摘要，一个包标签可能指向意料之外的工件。服务端可能在评审之后新增一个破坏性工具。回滚可能悄悄选中一个从未被准入过的版本。

解决方法是设置一个准入控制器，在每条边界上都保留证据。

## Registry 是索引，不是你的审批系统

官方 MCP Registry 存储服务端元数据。它的 `server.json` 记录会声明一个服务端版本，并声明一个或多个包或远程端点。发布规则增加了命名空间认证、包所有权检查、受限 registry 规则，以及一个范围很窄的发布者元数据位置。

这些控制回答的是发布问题。你的生产策略仍然要回答部署问题：

| 边界 | 问题 | 证据负责人 |
|---|---|---|
| Namespace | 该发布者是否有权使用这个名字？ | Registry 认证，加上你已验证的命名空间输入 |
| Record | 发布者为这个版本声明了什么？ | 不可变的 `server.json` 摘要 |
| Execution source | 最终执行的是哪个包或远程端点？ | 声明的 source 字段、验证过的所有权结果、传输方式，以及可信摘要 |
| Runtime | 端点现在暴露了什么？ | `server/discover` 与 tool 描述符 |
| Admission | 你的策略是否批准了这个确切的集合？ | 本地 pin 与账本条目 |
| Operations | 它是否仍然安全，什么可以替代它？ | 漂移检查、状态同步、健康检查与回滚路由 |

Registry 的 schema 版本与 MCP 协议版本是相互独立的。一条记录可能使用已发布的 `2025-12-11` server schema，而线上服务端支持 MCP `2026-07-28`。永远不要从其中一个推断另一个。

```figure
mcp-registry-admission
```

## 在一个准入决策中的七项控制

### 1. 命名空间验证

官方 Registry 名称使用经过认证的命名空间。一个已验证的域名可以映射为一个反向域名前缀。例如，对 `example.com` 的控制权可以确立 `com.example/*`。

不要接受字符串前缀检查：

```python
server_name.startswith("com.example")
```

这也会接受 `com.exampleevil/tool`。请在 `/` 处切分名称，要求 slug 非空，并精确比较命名空间片段。更重要的是，从认证结果把已验证的命名空间传入准入流程。不要从不受信任的记录中推导出信任。

GitHub 支撑的命名空间与域名支撑的命名空间使用不同的认证路径。请把任一路径归一化成同一个准入输入：那个精确的已验证命名空间字符串。

### 2. Provenance 关联

对于包记录，声明与取回的工件必须在显式字段上关联：

- package registry 类型
- package 标识符
- package 版本
- 验证过的所有权结果
- 下载工件的摘要

还要校验声明的 package 传输方式。只有远程端点的记录同样是有效的，不能因为没有包就予以拒绝。对于远程源，要把声明的 URL 和传输类型，与独立验证过的端点所有权、以及可信连接或部署证据的摘要关联起来。

本课代码同时支持两种 source 类型，并把所选 source 与 Registry source、服务端名称、Registry 版本、记录摘要和证据摘要一起哈希。所得的 provenance 摘要是指向完整证据集的一个紧凑指针。它不是保留证据的替代品。

永远不要接受仅由你正试图验证的工件所提供的摘要。要在可信的取回边界计算它，或者从一个你已校验其验证结果的包服务处接收它。

### 3. 钉住决策，而不只是版本

Registry 版本是唯一的发布标识符。已发布的元数据不可变。记录一旦变化就必须使用新版本。推荐使用语义化版本，但 Registry 并不强制要求，也不接受版本区间。

这意味着 `^1.4` 不是准入 pin，“latest”也不是。一个有用的 pin 包含：

```json
{
  "server": "com.example/inventory",
  "version": "1.0.0",
  "recordDigest": "...",
  "source": {"kind": "package", "registryType": "pypi"},
  "sourceDigest": "...",
  "toolsetDigest": "...",
  "provenanceDigest": "...",
  "registryStatus": "active"
}
```

钉住多层内容让你能够识别出是哪条边界发生了变化。同一个 Registry 版本下记录摘要发生变化，是 Registry 完整性故障。同一个 package 坐标或远程部署下 source 摘要发生变化，是执行源完整性故障。toolset 摘要发生变化则是运行时 drift。

### 4. 实时漂移检测

准入应当观察真正会接收流量的那个服务端。调用 `server/discover`，通过你信任的路径列出或以其他方式获取已暴露的 tool 描述符，并验证：

- `2026-07-28` 出现在 `supportedVersions` 中
- 本地所需的全部 capabilities 都存在
- 每个 tool 描述符都有必需的身份与 schema 表面
- 在后续检查中，归一化后的描述符摘要与已准入 pin 一致

可选结果 `_meta["io.modelcontextprotocol/serverInfo"]` 的值是自报的展示、日志与调试上下文。把它记为诊断证据，但永远不要用它来确立命名空间、包所有权、端点所有权、准入或任何其他安全决策。位于 `_meta` 之外的直接 `serverInfo` 别名不是契约字段，不应被提升为诊断证据。

只归一化那些顺序没有含义的字段。示例在哈希之前按稳定名称对 tool 列表排序，因此无害的列表顺序变化不会造成 drift。它不会丢弃描述符字段。新增 tool、变更 schema、变更描述或新增注解都会改变 pin。

示例把格式错误的描述符以及任何描述符摘要变化都视为 drift，隔离该 pin，移除其活跃路由，并禁止该版本作为回滚目标。生产策略可以仅通过一次新的评审来允许编辑性变更，因为描述会影响模型的 tool 选择。“表面性”的元数据也可能改变 agent 行为。

### 5. Registry 状态是实时状态

Registry API 会在每条 server 记录旁边附加一个响应级的 `_meta` 对象。Registry 管理的字段位于 `_meta["io.modelcontextprotocol.registry/official"]` 之下。请把响应的 `_meta` 对象传给准入流程，并读取 `_meta["io.modelcontextprotocol.registry/official"].status`。直接读取 `_meta.status` 不是官方的 wire 形状。不要把响应元数据与发布记录自身的 `_meta` 混淆。状态可以是：

- `active`：默认返回，可以进入本地准入
- `deprecated`：仍可发现并带有警告，但不再是一个安全的自动选择
- `deleted`：默认隐藏，但其历史记录仍可通过 deleted 或增量视图获取

在准入之后同步状态。如果某个 active 版本变为 deprecated 或 deleted，就隔离它的 pin，并停止把新工作路由给它。保留证据。从默认列表中删除并不等于允许你抹掉审计轨迹。

发布者提供的自定义元数据在发布记录中只能位于 `_meta.io.modelcontextprotocol.registry/publisher-provided` 之下。Registry 管理的响应元数据是另一回事。不要让发布者设置它自己的官方状态。

### 6. 回滚意味着路由恢复

不可变的发布在回滚过程中不会被编辑。回滚选择一个此前已准入、当前仍合格的 pin，并改变活跃路由。

一个安全的目标必须：

1. 拥有完整的准入记录。
2. 在你的策略下仍处于 active 的 Registry 状态。
3. 未被运行时或安全证据隔离。
4. 仍能解析到所钉住的包与实时描述符集合。
5. 通过当前的健康检查。

示例聚焦于前三个条件。真正的 reconciler 应当在激活之前重新拉取包并重新检查实时端点。

### 7. 追加式准入账本

准入数据库说明当前是什么处于活跃状态。账本则解释原因。

每条示例条目包含序号、时间、事件、服务端、版本、结果、原因、证据、上一条目哈希及其自身哈希。修改某个较早的结果，会破坏该条目以及之后每一环的验证。

这是可防篡改（tamper-evident），而不是神奇地防篡改（tamper-proof）。请把周期性的账本头部锚定到独立的信任域，例如签名的发布元数据或一次写入存储。限制谁可以追加。把授权 token、包凭据、tool 参数和私有端点数据排除在证据之外。

## Build It

可运行的控制器位于 `code/main.py`。它只使用 Python 标准库。

从有限演示开始：

```bash
cd phases/13-tools-and-protocols/30-mcp-registry-supply-chain-and-drift
python3 code/main.py
```

该演示执行五个操作：

1. 准入 `1.0.0`，其命名空间、包 provenance、协议、capabilities 与 tools 均匹配。
2. 准入 `1.1.0` 并让它成为活跃版本。
3. 在运行时观察到一个意料之外的 delete 工具。
4. 观察到 `1.1.0` 的 Registry 状态变为 `deprecated`。
5. 把路由恢复到仍被准入的 `1.0.0` pin。

预期的输出形状：

```json
{
  "admitted": [true, true],
  "driftAllowed": false,
  "rollbackAllowed": true,
  "activeVersion": "1.0.0",
  "ledgerValid": true
}
```

按以下顺序阅读实现：

1. `namespace_for_domain()` 与 `namespace_matches()` 确立精确的命名权威。
2. `digest()` 与 `normalized_tools()` 生成确定性证据。
3. `RegistryAdmissionController.admit()` 关联发布、provenance、运行时与策略。
4. `check_live()` 把新的观察与 pin 比较。
5. `observe_registry_status()` 隔离 Registry 状态发生变化的版本。
6. `rollback()` 只激活此前已准入且仍然合格的目标。
7. `AdmissionLedger.verify()` 检测对已记录历史的改动。

## Use It

把控制器放在发现与路由之间：

```text
Registry sync -> artifact verifier -> live discovery -> admission controller -> route table
                                               |                 |
                                               v                 v
                                          evidence store    admission ledger
```

为这些职责使用相互独立的身份。Registry 同步 worker 需要对元数据的读取权限。工件验证器需要包取回权限。路由 reconciler 需要激活已批准 pin 的权限。它们都不需要全部凭据。

让发布状态显式化。“Approved”表示证据通过了策略。“Active”表示当前路由选择了它。“Quarantined”表示它不能接收新工作。“Superseded”表示另一个已准入版本处于活跃状态。不要用一个布尔值编码这四种含义。

在把服务端暴露到 `tools/list` 之前先运行准入。否则客户端可能在发布与策略评估之间的空档里发现某个工具。

## 交互实验

你会一次观察一条边界失败。

### 实验 A：命名空间冲突

在 code 目录中打开一个 Python shell：

```bash
cd phases/13-tools-and-protocols/30-mcp-registry-supply-chain-and-drift/code
python3 -q
```

然后运行：

```python
from main import namespace_matches
namespace_matches("com.example/inventory", "com.example")
namespace_matches("com.exampleevil/inventory", "com.example")
```

第一个结果为 `True`；第二个为 `False`。在本地把精确比较替换为 `startswith`，观察第二个名称为何越过了边界。继续之前先恢复精确比较。

### 实验 B：描述符漂移

```python
from main import *
times = iter(f"2026-08-21T12:00:{n:02d}+00:00" for n in range(10))
c = RegistryAdmissionController(clock=lambda: next(times))
meta = {OFFICIAL_META_KEY: {"status": "active"}}
c.admit(sample_record("1.0.0"), meta, "com.example", evidence_for("1.0.0"), sample_live("1.0.0"))
c.check_live("com.example/inventory", "1.0.0", sample_live("1.0.0", True))
```

检查原因与路由状态。包和 Registry 记录都没有变化。运行时 tool 表面变了，所以控制器隔离并停用了该 pin。这就是为什么供应链控制必须在安装之后持续进行。

### 实验 C：状态与回滚

准入 `1.1.0`，把它标记为 deprecated，然后尝试两个回滚目标：

```python
c.admit(sample_record("1.1.0"), meta, "com.example", evidence_for("1.1.0"), sample_live("1.1.0"))
c.observe_registry_status("com.example/inventory", "1.1.0", "deprecated")
c.rollback("com.example/inventory", "1.1.0", "unsafe retry")
c.rollback("com.example/inventory", "1.0.0", "restore known release")
c.ledger.verify()
```

被隔离的目标被拒绝。较早的 active pin 被接受。账本仍然有效。

## 练习实验

为控制器扩展一个双人审批门。

要求：

- 把审批存储为签名的证据引用，而不是 pin 中可变的名称。
- 对于包含 `destructiveHint: true` 工具的工具集，要求两个不同的评审者身份。
- 拒绝重复的评审者身份。
- 当审批不完整时，在账本中保留最初的准入尝试。
- 为零个、一个、重复和两个不同审批添加测试。
- 不要记录签名、凭据或完整的私有 tool 参数。

成功的标准是：在两位身份都批准了确切的记录、包和 toolset 摘要之前，破坏性工具无法变为活跃。

## 交付工件

本课交付 `outputs/skill-mcp-registry-admission.md`。在评审一个新的 Registry 版本或排查 drift 时，把它当作一份扁平、可复用的 runbook。它定义了输入、拒绝规则、证据包、状态协调和回滚证明，且不依赖示例中的类名。

## 验证清单

运行演示与确定性测试套件：

```bash
cd phases/13-tools-and-protocols/30-mcp-registry-supply-chain-and-drift
python3 code/main.py
python3 -m unittest discover -s code/tests -v
```

验证应当证明：

- 精确的命名空间边界会拒绝相似前缀
- 只有官方的、带命名空间的 Registry 状态才能让一个版本合格
- 未验证或不匹配的包与远程证据会被拒绝
- 发布者元数据无法冒充 Registry 管理的元数据
- tool 顺序被归一化，但不会隐藏描述符变化
- 格式错误的包与 tool 结构会被安全拒绝
- `serverInfo` 始终只是诊断信息，绝不提供准入权威
- 描述符 drift 会隔离、停用并阻止回滚到该 pin
- 状态变化会隔离活跃 pin
- 回滚无法选择被隔离或未知的版本
- 账本篡改会被检测到

## 生产失败模式

| 故障 | 发生原因 | 必需的响应 |
|---|---|---|
| 名称看起来有效，但命名空间从未被认证 | 策略信任了记录文本 | 在可信命名空间验证器给出精确前缀之前拒绝 |
| 同一包坐标返回了新的字节 | 上游可变或分发过程被入侵 | 停止激活，保留两份摘要，调查取回边界 |
| “Latest” 未经评审就发生变化 | 浮动选择逃出了 pin 的约束 | 只解析确切的已准入版本与摘要 |
| 审批之后出现新工具 | 运行时 drift 或不同的部署 | 隔离该路由并抓取一份新的描述符观察 |
| 被弃用的版本仍在活跃 | 状态同步缺失或延迟 | 按计划并在激活之前协调状态 |
| 已删除记录从默认同步中消失 | 客户端只请求了 active 记录 | 使用增量或 deleted-aware 协调，并保留本地历史 |
| 回滚目标从未被准入 | 路由控制与审批状态脱节 | 拒绝回滚，并为该目标跑一次新的准入 |
| 攻击者重写所有条目后，账本在本地仍能验证 | 哈希链没有外部锚 | 把已签名的账本头部发布到独立的信任域 |
| 证据中包含 bearer token 或 tool 参数 | 日志复制了完整请求 | 在收集时脱敏，只存储最小必要证明 |

## 运营准则

发布回答的是“这个身份能否发布这个名字？”。准入回答的是“我们是否会执行这个确切的工件并暴露这个确切的行为？”。把这两个决策分开，钉住每一次关联，并让回滚依据证据而不是记忆来做出选择。

## Further Reading

- [官方 Registry 的 server.json 要求](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/official-registry-requirements.md)
- [官方 Registry OpenAPI 契约](https://registry.modelcontextprotocol.io/openapi.yaml)
- [MCP 2026-07-28 服务端发现](https://modelcontextprotocol.io/specification/2026-07-28/server/discover)
