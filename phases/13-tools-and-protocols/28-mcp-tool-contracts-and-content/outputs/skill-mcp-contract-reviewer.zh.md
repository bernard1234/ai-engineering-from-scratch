---
name: mcp-contract-reviewer
description: 在把工具暴露给模型之前，评审 MCP 工具描述符、结果、分页、completion 以及参数 header 策略。
version: 1.0.0
phase: 13
lesson: 28
tags: [mcp, tools, json-schema, pagination, completion, security]
---

对照协议版本 `2026-07-28` 评审所提供的 MCP 工具面。

如果缺少以下输入，请索取：

1. 完整的 `tools/list` 描述符分页，包含每一个 `nextCursor` 字段。
2. 每个工具至少一个成功结果和一个失败结果。
3. Streamable HTTP 的参数 header 映射（如使用）。
4. Completion references、调用方类别以及示例建议。
5. 可能改变可见工具集的授权上下文。

产出一份包含以下小节的简洁报告。

## 描述符准入

对每个工具：

- 校验名称非空且稳定；
- 要求 `inputSchema` 为 object；
- 识别 JSON Schema 方言，省略时默认为 2020-12；
- 在存在时校验 `outputSchema`；
- 把注解列为不可信的提示，而非策略；
- 返回 `ADMIT`、`REJECT` 或 `CONDITIONAL`，并给出一个精确理由。

拒绝一个畸形描述符，同时不要拒绝其他无关的有效工具。

## 结果契约

对每一个完整结果，包括带 `isError: true` 的结果：

- 要求 `resultType: complete`；
- 按类型校验每一个内容块；
- 把 `structuredContent` 视为任意 JSON 值，而非仅限 object；
- 存在 `outputSchema` 时，要求 `structuredContent` 存在且符合该 schema；
- 对结构化结果要求一个兼容性 text 块；
- 区分 resource link 与 embedded resource；
- 说明大小与媒体类型限制。

把畸形请求归类为 JSON-RPC 错误。把可处理的执行失败归类为带 `isError: true` 的完整结果，同时不得绕过已发布的输出契约。

## 参数 header

对每一个 `x-mcp-header`：

- 要求合法且非空的 HTTP field-name token；
- 要求在不区分大小写的情况下唯一；
- 要求类型为 string、integer 或 boolean；
- 遍历整个输入 schema，包括嵌套 properties、组合子、array items，以及被 `$ref` 使用的定义；
- 只允许该注解出现在 `inputSchema.properties` 的直接成员上，并拒绝在别处或在 `outputSchema` 中发现的每一个注解；
- 拒绝 `number`，以及超出 `-9007199254740991` 到 `9007199254740991` 的整数值；
- 按部署策略拒绝凭据、token、secret、password、authorization 以及 PII 字段；
- 只有当取值是非空的可见 ASCII 且不以 `=?base64?` 开头时，才按纯文本传输；
- 否则精确发出 `=?base64?{Base64UTF8}?=`，不裁剪也不规范化原始取值；
- 对 Unicode、空、空白、控制、CR 或 LF、带填充以及看起来像哨兵的字符串进行编码，并把布尔值渲染为小写文本；
- 在 HTTP 边界上解码已识别的 `Mcp-Param-*` 取值，不区分大小写地比较 header 名称，并把解码后的取值与 JSON body 精确比较；把缺失、重复、意外、畸形或不匹配的副本以 HTTP `400` 加 JSON-RPC `-32020` 拒绝；
- 记录最终的 header 名称与拒绝类别，绝不记录参数取值或编码后的载荷。

## 分页

追踪每一次列表请求。只要 `nextCursor` 存在且非 null 就继续，包括它是空字符串的情况。绝不解码、修改、自增、排序或从游标推导含义。报告重复工具、缺失的页以及不稳定的顺序。

## completion

对每一个 prompt 或资源 reference：

- 校验 reference 与参数；
- 通过调用方的授权过滤建议；
- 把结果上限设为 100 个取值；
- 定义客户端防抖与服务器速率限制；
- 测试隐藏的租户、资源和环境名称不会泄露。

## 验证矩阵

至少返回以下检查：

| 检查项 | Fixture | 预期结果 |
|------|---------|-----------------|
| 非 object 的结构化输出 | 合法的 array、标量或 null schema | 符合时接受 |
| 输出不匹配 | JSON 类型错误或缺少属性 | 在模型使用之前拒绝 |
| 错误输出不匹配 | `isError: true` 且结构化内容缺失或无效 | 在模型使用之前拒绝 |
| 空游标 | `nextCursor: ""` | 后续请求发送该确切游标 |
| 不安全 header | token 或非法字段名 | 描述符被拒绝 |
| 嵌套 header 注解 | `oneOf`、`items`、嵌套对象或 `$ref` 定义 | 在全树准入期间拒绝描述符 |
| 编码 header 取值 | Unicode、换行、填充或看起来像哨兵的文本 | 精确的 base64 UTF-8 哨兵能还原原始取值 |
| 整数 header 取值 | 两个安全边界，以及各自越界的一个取值 | 安全边界通过；不安全取值被拒绝 |
| Header 与 body 一致 | 大小写变体、缺失副本、解码后不匹配 | 大小写变体通过；缺失或不匹配返回 HTTP 400 与 JSON-RPC -32020 |
| 混合内容 | text、media、link、embedded resource | 每个块被独立校验 |
| Completion 隔离 | 低权限调用方 | 不返回特权建议 |
| 错误分层 | 未知工具与业务失败 | JSON-RPC 错误与 `isError: true` 保持区分 |

当证据只包含一次成功的工具调用时，拒绝批准。要求提供发现页、准入决定以及经过校验的结果 fixtures。
