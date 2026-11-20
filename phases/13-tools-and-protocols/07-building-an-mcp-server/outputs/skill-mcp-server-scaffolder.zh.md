---
name: mcp-server-scaffolder
description: 设计一个无状态的 MCP 2026-07-28 server，具备发现、请求校验与确定性原语。
version: 2.0.0
phase: 13
lesson: 07
tags: [mcp, server, stateless, discovery, scaffold]
---

给定一个业务领域，产出一份现代 MCP server 方案。保持应用状态显式，保持协议行为无状态。

产出：

1. 原语划分。定义原子 tool、URI 寻址的 resource 与有用的 prompt。当某个领域并没有诚实的用途时，就省略该原语。
2. 发现结果。提供 `supportedVersions`、server capabilities、可选的 instructions、`resultType: "complete"`、缓存提示，以及结果 `_meta` 中的 server 身份。
3. 请求校验器。在每个 `params._meta` 中要求协议版本与客户端 capabilities。校验存在时的推荐客户端身份。版本不匹配时返回 `-32022`，并携带请求版本与支持版本。
4. 结果包装器。为每个成功结果添加 `resultType: "complete"` 与 server 身份。为发现、列表、模板与资源读取添加 `ttlMs` 与 `cacheScope`。
5. 排序策略。为每个列表响应定义稳定的排序键。
6. 状态策略。把持久状态放进数据库，或作为普通 tool 参数返回一个显式的不透明句柄。绝不要把状态藏在协议会话里。
7. 兼容边界。如果需要旧版支持，隔离出一个 `2025-11-25` initialize 适配器。仅对旧版流量选择它，并独立测试两个时代。

硬性拒绝：

- 一个现代 server 的首个合法方法必须是 `initialize`。
- 复用更早请求中的 capabilities、身份或版本。
- 在现代 HTTP 流量上返回 `Mcp-Session-Id`。
- 返回不带缓存提示的列表或资源读取结果。
- 把注解当作授权控制。
- 由 server 发起独立的 JSON-RPC 请求。

拒绝规则：

- 如果某个被请求的 resource 会在没有授权的情况下暴露机密，停止并要求访问策略。
- 如果某个领域没有只读数据，就省略 resources，而不是凭空发明。
- 如果某个领域没有可复用模板，就省略 prompts，而不是交付填充物。

输出一页式架构、方法表、校验伪代码、结果示例、确定性排序规则，以及至少六个一致性测试。最后给出应用状态与协议状态之间的边界。
