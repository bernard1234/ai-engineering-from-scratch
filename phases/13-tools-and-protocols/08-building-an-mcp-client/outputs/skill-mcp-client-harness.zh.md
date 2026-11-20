---
name: mcp-client-harness
description: 搭建一个多 server 的 MCP client，具备现代元数据、安全的时代协商、确定性合并与路由。
version: 2.1.0
phase: 13
lesson: 08
tags: [mcp, client, stateless, compatibility, routing]
---

给定一组 MCP server 传输，产出一个 client harness：它优先使用 MCP `2026-07-28`，并把旧版兼容隔离出来。

产出：

1. Peer 配置。把稳定的 server 名映射到固定的命令或端点、参数、环境变量允许列表、授权上下文、传输类型，以及一个默认值为 false 的显式 `allow_legacy` 标志。
2. 现代请求构建器。在序列化之前，立即把协议版本、当前客户端 capabilities 与推荐的客户端身份打入每个 `params._meta`。
3. stdio 时代探测。先发送 `server/discover`。接受合法的 DiscoverResult，在双方共同支持的现代版本上重试 `-32022`，并把 `-32020` 与 `-32021` 视为可纠正的现代错误。
4. 旧版兼容探测。把无法识别的错误、超时、连接关闭或空响应视为模糊信号。仅当该确切 peer 具有 `allow_legacy: true` 时，才发送一次受期限约束的 `initialize`。只有在收到一个可关联的 JSON-RPC 成功、且其中包含已配置的旧版修订版本、对象型 capabilities 与非空 server 身份之后，才选择旧版。否则按失败关闭处理。
5. Tool 缓存。在协商好的授权上下文中遵守 `ttlMs` 与 `cacheScope`。把旧版缺失的 `resultType` 视为 `"complete"`。
6. 命名空间合并。对 peer 与 tool 排序。对冲突加前缀或拒绝。禁止静默覆盖。
7. 路由器。把规范 tool 名映射到 peer 加本地名，创建新的请求 id，发送符合时代的请求，并校验响应 id。
8. 恢复。在传输丢失时，让在途工作失败、重启或重连、重复发现与列表、重新打开订阅，并且只重试安全策略允许的操作。

硬性拒绝：

- 发送不带当前 `_meta` 的现代请求。
- 在可识别的现代错误之后回退到初始化。
- 向未显式列入旧版兼容允许列表的 peer 发送 `initialize`。
- 把超时、连接关闭、空响应、无法识别的错误、格式错误的结果或不受支持的修订版本当作旧版行为的证明。
- 把进程、连接或 `Mcp-Session-Id` 当作现代协议状态。
- 跨授权上下文共享私有缓存列表。
- 静默覆盖重复的 tool 名。
- 接受没有 `resultType` 的现代成功结果。

拒绝规则：

- 拒绝在固定允许列表之外启动命令。
- 当拥有者不明确时，拒绝路由该 tool。
- 没有应用层幂等键或用户决定时，拒绝自动重试非幂等调用。

输出一个完整的 Python harness、至少六个一致性测试，以及一份启动报告，列出 peer、已选时代、已选版本、缓存范围与规范 tool 名。
