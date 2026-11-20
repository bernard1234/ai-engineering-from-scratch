# MCP Conformance 工程：版本化、证据与运营

> 一个服务端不会因为它的正常路径通过某个 SDK 跑通就算 conformant。Conformance 存在于 wire 上、版本边界处、穿过中间层时，以及在回滚过程中。

**Type:** Build
**Languages:** Python
**Prerequisites:** 第 13 阶段，第 09 课（传输）、第 17 课（网关）、第 30 课（Registry 准入）
**Time:** ~100 分钟

## Learning Objectives

- 把规范性 MCP 规则转成黄金与负向的 wire transcript。
- 让严格的 `2026-07-28` 行为与有界的旧版回退保持分离。
- 区分增量的未知字段与无效的未知 `resultType`。
- 把原始 JSON-RPC 证据与 SDK 归一化视图进行比较。
- 通过一个真实的代理边界证明头与 body 的完整性。
- 用脱敏后的 transcript、健康与回滚证据为发布设门禁。

## 问题场景

你的客户端通过一个 SDK 调用 `tools/list` 并拿到 tools。集成测试通过了。

这个结果留下了若干重要问题没有回答：

- 该请求是否携带了现代式的按请求协议元数据？
- `MCP-Protocol-Version`、`Mcp-Method` 和 `Mcp-Name` 是否与 JSON-RPC body 匹配？
- 响应在 wire 上是否包含有效的 `resultType`，还是由 SDK 合成了一个？
- 客户端会不会保留一个未来新增的增量字段？
- 一个已被识别的现代错误会不会意外触发旧版握手？
- 代理是否保留源站状态与 JSON-RPC 错误？
- 通知序列化器是否发出了被禁止的响应？
- 运营团队能否在不存储密钥的情况下证明某个发布为何被提升或回滚？

Conformance 是一组可观察的不变量。构建一个 harness，在生产流量不得不自己去发现这些问题之前就把它们捕获下来。

```figure
mcp-conformance-operations
```

## 从版本纪元开始

MCP `2026-07-28` 使用自包含的按请求元数据。一个现代请求携带 `params._meta.io.modelcontextprotocol/protocolVersion` 与 `params._meta.io.modelcontextprotocol/clientCapabilities`。确切的、带命名空间的键很重要；裸的 `protocolVersion` 或 `clientCapabilities` 别名都是格式错误的。当 HTTP 边界存在镜像路由头时，它们的值必须与 JSON-RPC body 一致。现代的成功结果携带 `resultType`。

直到 `2025-11-25` 的版本使用更早的初始化纪元。只有在客户端选择了那个更早的纪元之后，不带 `resultType` 的旧版结果才会被解释为完整。

不要创建一个同时接受两种形状的宽松校验器。使用两个分支：

| 分支 | 入口证据 | 缺失 `resultType` | 初始化 |
|---|---|---|---|
| Modern | 成功的 `server/discover` 或已被识别的现代响应 | 无效 | 不是默认路径 |
| Legacy | 配置的 allowlist，加上在一次结论不明的现代探测之后得到的有效旧版 `initialize` 结果 | 解释为完整 | 该纪元要求 |

这种分离可以防止一个格式错误的现代对端因为放宽校验而得到奖赏。

### 严格模式

严格模式要求现代行为的证明。一次成功的 `server/discover` 证明现代分支。一个已被识别的现代 JSON-RPC 错误也能证明它。修正请求，或者停止。永远不要因为服务端返回了 `-32020`、`-32021` 或 `-32022` 就降级。

### 回退模式

回退模式执行一次有界的现代探测。超时、空回复、连接关闭或无法识别的响应都属于结论不明。它并不能证明对端是旧版。只有被显式配置或列入兼容 allowlist 的端点，才可以随后接收一次有界的旧版探测，而且客户端只有在校验了该探测的 `initialize` 结果与协商出的旧版修订之后，才选择旧版分支。

回退不是“在任何错误之后都试试旧版”。一个已被识别的现代错误包含有用的修正信息。在它之后降级，可能掩盖头不匹配、缺少 capability 声明或不受支持的版本。

这可以防止攻击者、故障或过滤代理通过丢弃现代响应来强制降级。要把端点策略、结论不明的现代观察、确切的正向旧版证据以及所选纪元一起记录下来。

在每份 transcript 旁边记录所选纪元。缺少这个事实，一个缺失字段可能在一次测试运行中看起来可接受，在另一次中却是无效的。

## 构建 transcript 语料库

一个 transcript 夹具记录的是跨过边界的内容，而不仅仅是 SDK 调用：

```json
{
  "name": "golden-modern-list",
  "era": "modern",
  "headers": {
    "MCP-Protocol-Version": "2026-07-28",
    "Mcp-Method": "tools/list"
  },
  "request": {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {
      "_meta": {
        "io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientCapabilities": {}
      }
    }
  },
  "responseStatus": 200,
  "responseBody": {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
      "resultType": "complete",
      "tools": []
    }
  }
}
```

保留两类夹具。

### 黄金 transcript

黄金 transcript 证明被接受的行为：

- 元数据和 HTTP 头匹配的现代发现请求或方法请求
- 带必需字段的完整结果
- 当该方法可以请求更多输入时出现的 `input_required` 结果
- 只有在相应 capability 已被声明之后才出现的扩展结果
- 不带 `resultType` 的旧版结果，但只在所选旧版纪元中
- 通知处理，且不产生 JSON-RPC 响应

黄金 transcript 追求精确，而不是规模。让易变的 ID 与时间戳保持确定性，或在比较前归一化。

### 负向 transcript

负向 transcript 证明拒绝行为：

- 头与 body 不匹配
- 缺少按请求的 capabilities
- 已匹配但不受支持的协议版本
- 缺少现代 `resultType`
- 未知或未被声明的 `resultType`
- 响应 `jsonrpc` 不为 `2.0`，或 ID 在值或 JSON 类型上不同
- 同时包含 `result` 与 `error`，或两者都不包含的响应
- 缺少整数 `code` 与字符串 `message` 的错误
- 一个已知协议错误被映射到错误的 HTTP 状态
- 对通知发出响应
- 格式错误的 JSON-RPC 信封
- 代理把协议错误压平

对于每个负向用例，都要断言拒绝边界与稳定的错误码。“调用失败了”太弱。一个由代理生成的 500 与一个源站的 `-32020` 都可能看起来像失败，却向运营者讲述了完全不同的故事。

头不匹配夹具必须包含服务端真实的 HTTP 400 JSON-RPC 响应，其请求 ID 匹配且错误码为 `-32020`。只要本地校验器观察到 `HeaderMismatch`，就自动强制执行这一点；不要把响应校验做成一个可选的夹具标志。一个 HTTP 500 且没有 body 的用例，即使本地拒绝码正确，也应判为失败。一个在自己请求校验器抛出异常后就停下的 harness，只测了它自己，没有测服务端的 wire 行为。

官方 MCP conformance 项目作为外部套件和版本化参考很有用。同时也要保留本地的 transcript。它们捕获了你的代理、SDK、认证、扩展和发布路径，这些是通用套件不可能知道的。

## HTTP 头值必须与 RPC body 匹配

在现代 Streamable HTTP 中，中间层可以用镜像头来做路由或执行策略。JSON-RPC body 仍然是协议的真相来源。不匹配是完整性故障，而不是选择某个值的提示。

按以下顺序校验：

1. 解析并校验 JSON-RPC 信封与元数据类型。
2. 把 `MCP-Protocol-Version` 与 `params._meta.io.modelcontextprotocol/protocolVersion` 比较。
3. 把 `Mcp-Method` 与 `method` 比较。
4. 当该方法带有路由名称时，把 `Mcp-Name` 与 body 中对应的值比较。
5. 在建立相等关系之后，再判断已匹配的版本与 capability 集合是否受支持。

这个顺序把不匹配 `-32020` 与不受支持的版本 `-32022` 区分开。它也阻止网关按头里的名称授权，而源站却执行 body 里的另一个名称。

HTTP 字段名大小写不敏感，而它们的值仍然大小写敏感。在查找之前先归一化头名称，并拒绝相互冲突的重复项。对于不安全的、非 ASCII 的、或带前导/尾随空白的 `Mcp-Name`，要先解码确切的 `=?base64?{Base64EncodedValue}?=` UTF-8 sentinel，再与 body 比较。对不完整的 sentinel、无效的 Base64、无效的 UTF-8，或原始的不安全值，一律以 `-32020` 拒绝。即使 body 包含相同字符，原始的周边空白也是无效的，因为该值在传输之前就需要 sentinel 编码。

中间层可能在一个请求到达 MCP 服务端之前就拒绝格式错误的 HTTP，因此它的失败可能是一个没有 JSON-RPC 的 HTTP 错误。要捕获拒绝是来自中间层还是源站。源站 MCP 服务端在处理一个有效 JSON-RPC 请求时，应当使用协议错误契约。

## 未知字段不等于未知结果

前向兼容需要两条不同的规则。

### 增量未知字段

结果对象与 `_meta` 映射可以新增字段。校验器应当根据自身角色保留或忽略增量字段，除非该字段违反了某个保留契约。示例把完整的原始结果保留在证据中，并在一个已知结果旁边接受 `futureHint`。

如果你是透明代理，保留未知字段通常比剥离它更安全。如果你是应用客户端，忽略它可以是有效的。你的差分测试仍应揭示 SDK 省略了它，从而使该行为是有意为之。

### 未知的 `resultType`

`resultType` 是一个判别符。现代核心结果使用 `complete` 或 `input_required`。扩展只有在相应 capability 已被声明时才能新增另一个值。例如 Tasks 扩展可以在那个已协商的 capability 上下文中新增 `task`。

未知或未被声明的判别符不能被安全地当作完整。客户端并不知道自己将丢弃什么样的生命周期。要拒绝它。

因此，同一份原始响应可以同时包含一个可接受的未知字段和一个不可接受的未知结果类型。两种情形都要测试。

判别符只是第一层。在它之后再校验方法特定的载荷。一个完整的 `tools/list` 结果需要一个 `tools` 数组，其描述符要有唯一且非空的名称、有用的描述，以及对象根的 `inputSchema` 值。一个 `task` 结果只有在具备 Tasks capability 的合格 `tools/call` 上才有效，并且要求 `taskId`、已知状态、创建与更新时间戳、`ttlMs`，以及一个有效的可选轮询间隔。一个完整的 `completion/complete` 结果要求一个 `completion` 对象，其中字符串值不超过 100 个，可选的 `total` 为非负整数且不小于返回值的数量，另有一个可选的布尔 `hasMore`。一个拼写正确的 `resultType` 并不能让格式错误的载荷变得 conformant。

## 通知不变量

JSON-RPC 通知没有 `id`。接收方不得发送 JSON-RPC 成功或错误响应。

对于一个被接受的 HTTP 通知形状，harness 期望 HTTP `202` 且 body 为空。MCP `2026-07-28` 在 Streamable HTTP 上不定义任何核心的客户端到服务端通知。示例只用一个带命名空间的课程扩展通知来测试单向序列化器不变量。不要把它呈现为一个新的核心方法。

要测试序列化器，而不只是 handler。一个 handler 可能返回 `None`，而中间件却把它包装成一个 JSON 成功对象。捕获最终的出口字节。

## 增加 SDK 差分

SDK 常常把 wire 对象转成方便的语言类型。这很有用，但一个归一化对象无法证明实际收到了什么。

对于每个高风险夹具，都要捕获：

1. SDK 解码之前的原始状态、头与响应 body。
2. SDK 归一化后的返回值或异常。
3. 所选纪元的预期语义投影。
4. SDK 提升、合成、剥离或改变的字段。

示例在比较应用载荷时，允许 SDK 仅移除已知的 wire 记账字段，例如 `resultType`、`_meta`、`ttlMs` 和 `cacheScope`。它会报告被丢弃的 `futureHint`，因为那个未知的语义字段消失了。

不要假定每一处差异都是 SDK 缺陷。重点在于让这次变换可见。要明确你的组件是应用端点（可以忽略增量字段），还是透明中间层（应当保留它）。

对你交付的每个 SDK 和版本都运行这个差分。如果两个 SDK 对同一份 transcript 的归一化方式不同，发布策略应当说明哪种行为是可接受的，而不是事后挑选最方便的输出。

## 采集代理证据

大多数生产 MCP 故障发生在不止一个进程之间。记录三个视图：

| 视图 | 最小证据 |
|---|---|
| Ingress | 请求头、JSON-RPC body、content type、已认证路由、接收时间 |
| Origin | 转发头与 body 摘要、源站状态、响应头与 body |
| Egress | 客户端可见的状态、头、body 与发送时间 |

示例检测两种常见的变换：

- 源站的 HTTP 400 或 404 JSON-RPC 错误变成了通用的代理 500
- 出口 JSON-RPC body 与源站 body 不同

为 content type、`Accept`、压缩、请求作用域 SSE、缓存头和 trace 关联添加部署特定的断言。在策略允许时，捕获 TLS 终止的两侧。永远不要仅仅为了证明路径就记录凭据。

## 在证据离开内存之前脱敏

脱敏是 conformance 运营的一部分，而不是事后的清理工作。要在序列化、哈希、日志、测试工件或失败上传之前就应用它。

示例会先对键名做大小写折叠并移除分隔符再匹配，然后递归替换以下键下的值：`Authorization`、`Cookie`、`Set-Cookie`、`X-Api-Key`、`accessToken`、`clientSecret`、`registrationAccessToken`、`token`、`password`、`secret` 和 `api_key`。规范化形式与拒绝名单必须使用同一种形态，这样 camelCase、连字符、下划线和点号变体就无法彼此绕过策略。生产采集器应当补充方法特定的参数策略，因为像 `query` 这样无害的键也可能包含个人或受监管数据。

对脱敏后的证据包做哈希。只有在某项具体调查需要时，才把原始捕获保存在一个受批准的短生命周期系统中。摘要证明是哪个脱敏包驱动了决策；它不会泄露被移除的值。

## 让健康检查与回滚成为门禁的一部分

协议 conformance 是必要条件，但不足以支撑发布。一个 conformant 的候选版本仍然可能超时、泄漏内存，或压垮某个依赖。

在 rollout 之前定义一个健康窗口：

- 最小样本数
- 最大错误率
- 最大延迟百分位数
- 饱和度或资源限制
- 观察时长
- 与已准入基线的比较

同样要在 rollout 之前定义回滚证据：

- 确切的先前版本
- 准入证据摘要
- SHA-256 工件与描述符 pin
- 当前 Registry 状态
- 当前健康结果
- 路由恢复步骤
- 来自可信 release-controller 身份、针对上述确切字段的 attestation

要求该回滚目标在提升之前就被验证且健康，而不只是在候选版本失败之后。一次没有可用恢复路径的成功发布不是生产就绪的。

如果候选版本失败，而回滚目标缺少这些证据，就暂停流量，而不是猜测。“回滚到原来那个”不是一种运营控制。

不要把就绪性简化为真值检查，例如非空版本、`healthy: "yes"`，或一个任意的证据字符串。示例要求确切的类型、一个 active 状态、三个 SHA-256 摘要、一个可信签名者，以及一个针对完整回滚载荷的有效 HMAC-SHA-256 attestation。它的确定性演示密钥是一个非密钥夹具。在生产环境的发布边界上，要注入受保护的密钥、KMS 验证结果，或公钥 attestation 验证器。

发布门禁还会拒绝空的 transcript、SDK 差分或代理证据。每个来源都必须携带有效的证据摘要。一个绿色的健康窗口无法填补一条从未被观察过的边界。

## Build It

运行标准库 harness：

```bash
cd phases/13-tools-and-protocols/31-mcp-conformance-versioning-and-operations
python3 code/main.py
```

演示恰好运行十五个黄金与负向 transcript，其中包括有效与格式错误的 completion 结果，把原始结果与 SDK 视图进行比较，检查一个把源站错误压平的代理，评估健康状态，对回滚证据做认证，并选择那个目标。

预期的输出形状：

```json
{
  "transcriptsPassed": 15,
  "transcriptsTotal": 15,
  "sdkDroppedFields": ["futureHint"],
  "proxyIssues": [
    "proxy collapsed a protocol error into HTTP 500",
    "proxy changed the origin JSON-RPC body"
  ],
  "releaseAction": "rollback",
  "evidenceDigest": "..."
}
```

按以下顺序阅读 `code/main.py`：

1. `validate_request()` 执行纪元特定的请求与头规则。
2. `validate_result()` 区分缺失的旧版判别符、有效的现代值、扩展与未知值。
3. `select_era()` 实现严格与有界回退策略。
4. `run_transcript()` 评估黄金与负向夹具。
5. `compare_sdk_view()` 暴露归一化差异。
6. `inspect_proxy()` 比较 ingress、origin 与 egress 证据。
7. `redact()` 在证据哈希之前移除明显的密钥。
8. `rollback_evidence_ready()` 校验确切的 pin 字段与可信发布 attestation。
9. `ReleaseGate.evaluate()` 关联非空的 conformance、SDK、代理、健康与回滚证据。

## Use It

在四个时点运行这个 harness：

1. 每次实现变更时，用进程内测试适配器运行。
2. 针对构建出的客户端与服务端二进制，通过真实传输运行。
3. 在预发环境中穿过已部署的代理或网关运行。
4. 在 canary rollout 期间配合实时健康与回滚证据运行。

在各层之间保持相同的稳定用例名。`negative-header-body-mismatch` 在单元、端到端、代理和 canary 报告中应当表示同一个不变量。证据摘要会因为边界变化而不同；要求不应变化。

把夹具 schema 存在版本控制中。把脱敏后的运行证据存在发布系统中。只在事件访问控制之下存储短生命周期的原始捕获。

## 交互实验

### 实验 A：证明纪元边界

从 `code` 目录打开 Python：

```bash
cd phases/13-tools-and-protocols/31-mcp-conformance-versioning-and-operations/code
python3 -q
```

运行：

```python
from main import *
validate_result({"tools": []}, "legacy")
validate_result({"tools": []}, "modern")
```

旧版调用会推断为 `complete`。现代调用会抛出 `ProtocolViolation`。现在测试回退：

```python
select_era({"kind": "timeout"}, "fallback")
select_era(
    {"kind": "timeout"},
    "fallback",
    legacy_allowed=True,
    legacy_evidence={"kind": "initialize_success", "protocolVersion": LEGACY_VERSION},
)
select_era({"kind": "jsonrpc_error", "code": -32021}, "fallback")
```

第一次超时会 fail closed，因为沉默不是旧版证据。第二次调用选择旧版，仅因为配置允许，且观察到了有效的旧版初始化结果。那个已被识别的缺少 capability 错误证明了现代分支。

### 实验 B：增量字段与判别符

```python
validate_result({"resultType": "complete", "tools": [], "futureHint": True}, "modern")
validate_result({"resultType": "future_mode", "tools": []}, "modern")
```

第一个结果保留 `futureHint`。第二个被拒绝，因为生命周期判别符未知。

### 实验 C：检查一次 SDK 变换

```python
compare_sdk_view(
    {"resultType": "complete", "tools": [], "futureHint": {"mode": "new"}},
    {"tools": []},
)
```

判断你的组件可以忽略 `futureHint`，还是必须转发它。把这个选择写进发布策略。不要静默抹掉这个差分。

### 实验 D：修复代理

修改演示交换，使出口保留源站状态与 body。再次运行 `python3 main.py`。代理问题应当消失，但 SDK 差分仍会阻止提升。然后在 SDK 视图中加入 `futureHint`，观察当每个证据来源都通过时，动作变为 `promote`。

## 练习实验

把请求作用域的 SSE transcript 加入 harness。

要求：

- 捕获响应状态、content type、有序的 SSE 事件以及流终止。
- 证明每个 JSON-RPC 事件都有有效的、纪元特定的结果或错误。
- 为在转发之前缓冲整条流的代理添加一个负向用例。
- 为某个 SSE 事件的 JSON-RPC id 与请求不同添加一个负向用例。
- 在写入证据之前对事件数据脱敏。
- 在健康窗口中加入流时长、首事件延迟和事件数量。
- 让发布门禁在流失败时只选择一个有证据的回滚目标。

成功的标准是：同一个用例既直接运行，也通过代理运行，并产出一份报告指出究竟是哪条边界改变了行为。

## 交付工件

本课交付 `outputs/skill-mcp-conformance-release-gate.md`。用它把服务端、客户端、网关或 SDK 的变更转成一份版本化的 conformance 矩阵与发布决策。该工件要求原始 wire 证据、负向用例、显式的纪元选择、SDK 差分、代理证明、脱敏、健康阈值和回滚证据。

## 验证清单

运行演示与确定性测试套件：

```bash
cd phases/13-tools-and-protocols/31-mcp-conformance-versioning-and-operations
python3 code/main.py
python3 -m unittest discover -s code/tests -v
```

验证应当证明：

- 每个纳入的黄金与负向 transcript 都达到预期结果
- 现代请求要求确切的带命名空间元数据键
- HTTP 头名称按大小写不敏感匹配，且被编码的 `Mcp-Name` 值被精确解码
- 头与 body 不匹配会返回现代不匹配错误码
- 响应版本、ID、result 或 error 的排他性、错误形状与 HTTP 映射都被校验
- 方法特定的 tool-list、task 与 completion 载荷要求被强制执行
- 每一个观察到的 `HeaderMismatch` 都要求一个真实的 HTTP 400 JSON-RPC `-32020` 响应
- 原始 `Mcp-Name` 空白被拒绝，而精确的 sentinel 编码空白可以往返
- 缺失的 `resultType` 只在所选旧版纪元中有效
- 增量字段能通过原始校验，而未知结果类型会失败
- 扩展结果类型要求其已声明的 capability
- 已被识别的现代错误永远不会触发旧版回退
- 通知不产生任何 JSON-RPC 响应
- SDK 移除记账字段与丢失语义字段被区分对待
- 代理错误压平会被检测到，凭据会在 camelCase 与分隔符变体之间被递归脱敏
- 提升要求非空的 transcript、SDK、代理与健康的运营证据
- 提升与回滚都要求一个经过认证、已钉住、active 且健康的回滚目标

## 生产失败模式

| 故障 | 弱的测试会报告什么 | harness 必须证明什么 |
|---|---|---|
| SDK 合成了一个缺失的判别符 | “tools/list 通过了” | 原始现代结果缺少 `resultType`，因此无效 |
| 客户端在 `-32021` 之后降级 | “旧版重试成功了” | 已被识别的现代错误禁止回退 |
| 未知结果类型被当作完整 | “响应解析成功” | 未被声明的生命周期判别符被拒绝 |
| 代理授权一个工具，源站执行另一个 | “请求到达了服务端” | `Mcp-Name` 在每一跳都等于 body 中的路由名称 |
| harness 在读取服务端响应之前就抛出异常 | “头不匹配测试通过了” | HTTP 400 与 JSON-RPC `-32020` 响应被抓取并校验 |
| 代理把源站 400 变成通用 500 | “上游错误” | 源站与出口的状态和 JSON-RPC body 都被保留 |
| 通知中间件发出 `{result: null}` | “handler 返回了 none” | 最终出口 body 为空，且不存在 JSON-RPC 响应 |
| SDK 剥掉了一个增量字段 | “类型化对象匹配” | 原始视图与归一化视图显示确切的被丢弃字段 |
| 失败工件泄露了一个 bearer token | “debug 包已上传” | 脱敏发生在哈希、日志或上传之前 |
| 凭据键的书写风格绕过了脱敏 | “拒绝名单包含 api_key” | camelCase 与分隔符变体共用一个规范化的拒绝名单形态 |
| canary 没有样本但看起来健康 | “零错误” | 最小样本数被强制执行 |
| 回滚选择了未知构建 | “先前部署已恢复” | 目标版本、准入摘要、pin、状态与健康都存在 |

## 运营准则

测试你发送的字节、每个中间层转发的字节、每个 SDK 暴露的语义，以及运营人员在压力下将要依赖的证据。兼容性是一个显式分支。回滚是一个有证据支撑的发布动作。两者都不应是宽松解析器的意外副作用。

## Further Reading

- [MCP 2026-07-28 基础协议](https://modelcontextprotocol.io/specification/2026-07-28/basic)
- [MCP 版本协商](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning)
- [MCP Streamable HTTP 传输](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
- [官方 MCP conformance 项目](https://github.com/modelcontextprotocol/conformance)
