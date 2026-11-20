---
name: elicitation-form-designer
description: 为面向 MCP 2026-07-28 的操作设计显式资源作用域与无状态 elicitation，包含授权、安全表单和签名的重试状态。
version: 2.0.0
phase: 13
lesson: 12
tags: [mcp, elicitation, mrtr, scope, authorization]
---

为一个面向协议版本 `2026-07-28` 的 MCP 操作设计用户输入环节。

产出：

1. 作用域契约。把工作区、目录或资源 URI 放进可见的工具参数或 server 配置中。写明哪些已认证的 principal 可以使用它。
2. 边界检查。定义 URI 归一化、路径分量包含、符号链接策略和操作系统沙箱。
3. 触发条件。指明究竟哪一处歧义、确认或外部交互需要用户输入。
4. Discovery 与能力门禁。从 `server/discover` 返回精确的 `supportedVersions`、capabilities、`ttlMs` 和 `cacheScope`。如果宣告了 tools，就要包含强制的确定性 `tools/list` 描述符，带合法的对象 `inputSchema`、server 身份元数据和缓存提示。把 `elicitation: {}` 和显式的 `elicitation.form` 都视为支持 form。对缺失或仅 URL 的支持用 `-32021` 和 `data.requiredCapabilities.elicitation.form` 拒绝；对版本不受支持用 `-32022` 并给出精确的 `supported` 和 `requested` 数据。
5. MRTR 结果。返回 `resultType: "input_required"`，带一个稳定的 `inputRequests` 键和 `elicitation/create` 请求。
6. 交互设计。对于 form 模式，给出朴素的消息和受限的扁平 schema。对于 URL 模式，展示 HTTPS 目标地址和带外完成规则。
7. 重试契约。要求新的 JSON-RPC id、原始方法与参数、当前 `inputResponses`、逐请求的 `_meta`，以及精确回显的 `requestState`。
   没有 id 的 notification 永远不会收到 JSON-RPC 结果或错误；被接受的 Streamable HTTP notification 收到不带 body 的 `202`。
8. 分支处理。把 `accept`、`decline` 和 `cancel` 映射到各自不同的安全结果。
9. 状态保护。把 HMAC 或认证加密绑定到已认证的 principal、原始参数摘要、候选集、操作阶段、过期时间和一次性 nonce。在由每个处理器实例共享的有界、按 TTL 修剪的重放存储中原子地消费 nonce。
10. 最终再校验。在变更前立刻重新检查授权、实时记录状态和包含关系。

硬性拒绝：

- 把已弃用的 Roots 当作授权、包含或沙箱。
- 在新的 2026-07-28 设计中使用 `roots/list` 或 `notifications/roots/list_changed`。
- 发送反向的 `elicitation/create` 请求，而不是通过 MRTR 返回它。
- 在 form 模式中收集密码、API key、access token 或支付凭据。
- 发送当前逐请求能力中不存在的 elicitation 模式。
- 把 `clientInfo` 当作已认证的用户身份。
- 在校验过的接受和最终授权检查之前执行破坏性操作。
- 承载候选集或与权限相关数据的未签名 `requestState`。

拒绝规则：

- 在用户明确 decline 之后拒绝重复提示。
- 对于 server 无需用户介入即可推导或校验的值，拒绝发起 elicitation。
- 拒绝包含凭据、用户机密或预认证 bearer 值的 URL。
- 拒绝使用隐藏协议会话状态、`initialize` 或 `Mcp-Session-Id` 的请求。

输出一份单页设计，包含作用域、授权、包含、交互模式、schema 或 URL、MRTR wire 形状、state 字段、响应分支、重放策略和最终再校验清单。
