# 显式作用域与无状态 Elicitation

> Roots 在 MCP 2026-07-28 中已弃用，而且它从来就不是安全沙箱。把作用域放进可见的工具参数或资源 URI 中，在 server 上对它授权，当某个工具确实需要用户输入时使用 MRTR。用户看到的是决策，模型看到的是句柄，而任何 server 实例都能处理这次重试。

**Type:** Build
**Languages:** Python
**Prerequisites:** 第 13 阶段，第 07 课（MCP server）、第 13 阶段，第 11 课（无状态 MRTR）
**Time:** ~60 分钟

## Learning Objectives

- 用显式的工作区参数、资源 URI 或 server 配置替换已弃用的 Roots。
- 把作用域提示与授权、路径包含（path containment）和操作系统沙箱区分开。
- 通过 MRTR 的 `input_required` 结果交付 form 模式的 `elicitation/create`。
- 在逐请求的客户端能力中宣告 elicitation 支持，并拒绝不受支持的模式。
- 把 `accept`、`decline` 和 `cancel` 作为三种不同的结果来校验。
- 把破坏性确认绑定到已认证的 principal、原始参数、候选集和过期时间。

## 两个看起来相似的问题

一个笔记工具收到这样的请求："删除那份旧的 TPS 报告。"

server 必须回答两个不同的问题。

1. 这次操作可以触碰哪个工作区？
2. 三份匹配的笔记中，用户指的是哪一份？

第一个是作用域与授权。第二个是交互式的消歧。把两者混在一起会导致危险的设计，例如把客户端提供的文件夹当作"调用方可以删除其中一切内容"的证据。

## Roots 只是迁移面

较早的 MCP 版本允许 client 宣告 Roots，并在列表变化时通知 server。Roots 只是信息性指导。它们不约束 server 进程能读取什么，不授权调用方，也不创建操作系统沙箱。

MCP 2026-07-28 为新设计弃用 `roots/list` 和 `notifications/roots/list_changed`。优先使用以下显式替代方案之一：

- 当作用域随每次调用变化时，使用 `workspaceUri` 或 `directory` 工具参数。
- 当操作本身已指向某个资源时，使用资源 URI。
- 当一个部署只拥有一个固定工作区时，使用 server 配置。
- 当代码必须在技术上无法逃逸时，使用进程沙箱或受囚禁的文件系统。

如果某个既有的 2026-07-28 集成在弃用窗口期内仍然需要 `roots/list`，server 应把它内嵌到 MRTR 的 `inputRequests` 中。它不得发送实时的反向请求。那只是迁移适配器；新的处理器应当接受显式作用域。

模型能看见并重复显式句柄。隐藏的传输会话作用域更难检查、重放、审计和路由。

### 三层规则

显式 URI 本身仍然不构成授权。三层都要落实：

1. **授权：** 这个已认证的 principal 是否被允许使用这个工作区？
2. **包含（Containment）：** 归一化后的目标 URI 是否仍位于已授权的工作区边界之内？
3. **沙箱：** 操作系统能否阻止已被攻陷的 server 无论如何都逃逸出去？

可运行的 server 维护一份已授权工作区 URI 的允许列表，归一化百分号编码的路径，检查真实的路径分量边界，并在删除前立刻再次检查包含关系。

朴素的字符串前缀检查是错的：

```text
allowed:   file:///work/notes
attacker:  file:///work/notes-evil/secret.md
traversal: file:///work/notes/%2e%2e/private.md
```

两条恶意路径都以误导性的字符串开头。先归一化，再比较路径分量。生产环境的文件系统 server 还必须防御符号链接竞态和平台特有的路径语义。

## Elicitation 仍然存在，但交付方式变了

Elicitation 是当前的客户端特性，用于在 `tools/call`、`prompts/get` 或 `resources/read` 期间收集用户输入。方法名仍然是 `elicitation/create`。变化的是 wire 流程的方向。

2026-07-28 的 server 不发送反向的 JSON-RPC 请求。它返回一个 `InputRequiredResult`：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "resultType": "input_required",
    "inputRequests": {
      "delete_choice": {
        "method": "elicitation/create",
        "params": {
          "mode": "form",
          "message": "Choose one matching note and confirm deletion.",
          "requestedSchema": {
            "type": "object",
            "properties": {
              "note_id": {
                "type": "string",
                "enum": ["note-3", "note-7", "note-14"]
              },
              "confirm": {"type": "boolean"}
            },
            "required": ["note_id", "confirm"]
          }
        }
      }
    },
    "requestState": "integrity-protected-delete-state"
  }
}
```

宿主渲染这个表单。用户可以选择接受、明确拒绝或直接关闭。随后 client 用一个新的 id 重试原来的 `tools/call`：

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "notes_delete",
    "arguments": {
      "workspaceUri": "file:///Users/alice/Documents/Notes",
      "title": "TPS report"
    },
    "inputResponses": {
      "delete_choice": {
        "action": "accept",
        "content": {"note_id": "note-14", "confirm": true}
      }
    },
    "requestState": "integrity-protected-delete-state",
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {
        "elicitation": {"form": {}}
      }
    }
  }
}
```

两次调用之间没有协议会话。server 校验回显的 state，按期望的 schema 校验响应，检查所选笔记是否在签名的候选集之内，重新授权工作区，重新检查包含关系，然后执行删除。

## 能力协商是逐请求的

支持 form 模式 elicitation 的 client 这样宣告：

```json
{
  "io.modelcontextprotocol/clientCapabilities": {
    "elicitation": {"form": {}}
  }
}
```

为兼容起见，空的 elicitation 能力 `"elicitation": {}` 仍等同于仅支持 form。显式的 `"elicitation": {"form": {}}` 同样支持 form 模式。仅声明 URL 的 `"elicitation": {"url": {}}` 则不支持。即使更早的请求宣告过，server 也不得内嵌当前请求能力中不存在的模式。

每个请求还携带 `io.modelcontextprotocol/protocolVersion`。版本缺失或不是字符串返回 `-32602`。字符串不受支持返回 `-32022`，并给出精确的 `supported` 与 `requested` 数据。缺少 elicitation 支持或仅支持 URL 时返回 `-32021`，并把 `data.requiredCapabilities` 置为 `{"elicitation":{"form":{}}}`。

没有 JSON-RPC `id` 的信封是 notification。处理它，但不发出 JSON-RPC 成功或错误响应。在 Streamable HTTP 上，被接受的 notification 收到不带 body 的 `202 Accepted`。

应当包含 `clientInfo` 用于诊断，但它是自报的，不能用于识别用户以做授权。

server 实现 `server/discover`，返回 `supportedVersions`、capabilities、`ttlMs` 和 `cacheScope`，并带上 `resultType: "complete"`。它在这次现代设计中不宣告 Roots。由于宣告了 tools，它还必须实现强制的 `tools/list`。该结果返回确定性的 `notes_delete` 描述符、合法的对象 `inputSchema`、server 身份元数据和公开缓存提示。

## Form 模式

Form 模式使用一种为可用对话框而设计的受限 JSON Schema。根是对象，其属性是扁平的基本类型字段或受支持的 enum 数组。深层嵌套的对象和通用文档 schema 不适合放进确认对话框。

Form 模式适用于：

- 在多个候选中选择一个；
- 确认一项破坏性操作；
- 收集非敏感的偏好设置；
- 采集少量必须由用户（而非模型）决定的值。

不要用 form 模式收集密码、API key、access token 或支付凭据。这些机密会流经 MCP client，可能进入日志或模型上下文。

server 会再次校验返回的内容。客户端的表单校验改善 UX，但不产生信任。

## URL 模式

URL 模式发送一个安全网页 URL，用于带外交互：

```json
{
  "method": "elicitation/create",
  "params": {
    "mode": "url",
    "message": "Connect the report service to continue.",
    "url": "https://mcp.example.com/connect/report-service"
  }
}
```

当敏感信息必须直接进入由 server 控制的网页流程（例如第三方授权）时使用它。client 展示完整的目标地址，并在打开前获得同意。它不得预取该 URL。

`accept` 响应意味着用户同意打开该 URL。它并不证明外部流程已完成。在重试时，server 检查自己的状态，或完成流程，或再返回一个 `input_required` 结果。

URL elicitation 不是 MCP client 与 MCP server 之间授权的替代品。它用于 MCP server 需要代表用户执行的外部交互。server 必须把浏览器用户绑定到发起该 MCP 操作的同一个已认证 principal。

## 响应分支

把这些动作当作产品决策，而不是别名：

| 动作 | 含义 | 安全的 server 行为 |
|--------|---------|----------------------|
| `accept` | 用户提交了这次交互 | 校验内容并继续 |
| `decline` | 用户明确拒绝 | 返回完整的、非错误的拒绝结果 |
| `cancel` | 用户关闭了对话框或无法完成 | 安全停止，并允许稍后重试 |

绝不要把缺失内容解读为同意。绝不要把 decline 变成重复提示的循环。

## 保护破坏性 MRTR 状态

候选列表不能只存在于 prompt 或未签名的 Base64 值中。客户端控制它回传的一切。

本课签署一份 state 载荷，包含：

- 已认证的 principal；
- 发起请求的方法；
- `workspaceUri` 与 `title` 的摘要；
- 表单中展示的允许的 note id；
- 操作阶段；
- 较短的过期时间。

在变更之前，server 还会检查实时的 note 记录。这能捕获删除竞态，以及表单展示后目标被移出工作区的情况。

对于一次性的、涉及财务或不可逆的操作，仅靠 HMAC 不能阻止有效 state 在过期前被重放。要在由每个处理器实例共享的重放存储中，将 nonce 存储并恰好消费一次。本课注入一个有界、按 TTL 修剪的存储，并在执行内存删除期间持有其原子占用。生产数据库应把 nonce 占用与变更放在同一个事务或等价的按条件写边界内。

先校验交互，再占用 nonce。格式错误的响应或 `cancel` 不执行任何变更，state 保持可重试直到过期。显式的 `decline` 是终止性的，因此本课会消费 nonce 但不删除任何内容。

```figure
t3-roots-boundary
```

## Build It

`code/main.py` 演示了一个现代的 `notes_delete` 工具：

- `tools/list` 返回确定性的、可缓存的描述符，带必需的 workspace 和 title schema。
- 作用域是一个显式的 `workspaceUri` 参数。
- server 配置把该工作区授权给本课的 principal。
- URI 归一化拒绝前缀混淆和编码遍历。
- 每一次破坏性删除都要求 form 模式 elicitation。
- elicitation 在 `resultType: "input_required"` 内部传递。
- 签名的 `requestState` 绑定精确的候选列表和原始参数。
- 注入的重放存储会跨 server 实例拒绝同一个已接受或已拒绝的 state。
- 重试使用新的请求 id，并返回 `resultType: "complete"`。

数据存储放在内存中，便于检查协议行为。换成数据库后安全规则完全相同。

## Use It

从仓库根目录：

```bash
cd phases/13-tools-and-protocols/12-mcp-roots-and-elicitation/code
python3 main.py
python3 -m unittest discover tests -v
```

预期检查点：

- discovery 宣告 tools，但不宣告 Roots。
- 工具发现返回 `notes_delete`，带 `resultType`、server 身份和缓存提示。
- 请求 id `1` 在 `inputRequests.delete_choice` 中返回表单。
- 请求 id `2` 回显签名的 state 并完成删除。
- 前缀路径和编码遍历路径都无法通过包含检查。
- 改动 title 后无法复用原来的确认 state。
- decline 之后笔记保持原样。
- 共享 note 与重放状态的两个 server 对象无法都执行同一次确认。
- 空的与显式的 form 声明都能工作，而仅支持 URL 时返回精确的 `-32021` form 要求。
- 版本不受支持的失败使用精确的 `-32022` 数据形状。
- 没有 id 的 notification 不产生任何 JSON-RPC 响应。

## Ship It

`outputs/skill-elicitation-form-designer.md` 设计显式作用域、授权检查、MRTR 表单、响应分支和状态绑定。它会拒绝把已弃用的 Roots 当作沙箱，也拒绝通过 form 模式收集机密。

## Exercises

1. 把内存重放存储替换为 SQLite。用一个事务完成 nonce 占用与笔记删除，然后证明两个进程无法都提交成功。
2. 增加 `url` 能力协商和一个带外的设置流程。把第三方凭据挡在 `inputResponses` 之外。
3. 把内存中的笔记映射替换为临时 SQLite 数据库。在变更事务内部重新检查授权和包含关系。
4. 为真实的文件系统实现增加符号链接策略。解释为什么仅靠 URI 的词法包含无法阻止 symlink 逃逸。
5. 设计一个 2025-11-25 适配器，把现代 MRTR 处理器的输出映射到旧的由 server 发起的 elicitation。让它与当前处理器隔离。

## Key Terms

| 术语 | 在 2026-07-28 中的含义 |
|------|------------------------|
| Roots | 已弃用的信息性工作区提示，既不是授权也不是沙箱 |
| Explicit scope | 请求参数中可见的工作区、目录或资源句柄 |
| Containment | 归一化的路径分量检查，把目标限制在边界内 |
| Elicitation | 在 MCP 操作期间获取用户输入的客户端特性 |
| Form mode | 使用受限扁平 schema 的带内结构化用户输入 |
| URL mode | 面向敏感或外部工作流的带外交互 |
| MRTR | 无状态的 input-required 结果加上一次新的重试 |
| `requestState` | 由 client 原样回显、由 server 做完整性校验的不透明状态 |
| Decline | 用户明确的拒绝 |
| Cancel | 未获批准的关闭或不完整交互 |

## 旧版兼容

对于固定在 2025-11-25 的对端，`roots/list`、`notifications/roots/list_changed` 以及实时的由 server 发起的 `elicitation/create` 可能仍然存在。把该适配器标记为 legacy。不要让旧的 Root 列表绕过 server 授权，也不要把协议会话假设带进现代处理器。

## Further Reading

- [MCP 2026-07-28 Elicitation](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation)
- [MCP 2026-07-28 多次往返请求（MRTR）](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)
- [MCP 2026-07-28 Roots 弃用说明](https://modelcontextprotocol.io/specification/2026-07-28/client/roots)
- [MCP 2026-07-28 server 发现](https://modelcontextprotocol.io/specification/2026-07-28/server/discover)
