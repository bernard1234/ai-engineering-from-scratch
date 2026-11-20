---
name: gateway-bootstrap
description: 设计一个无状态的 MCP 2026-07-28 gateway，涵盖 registry 准入、策略、路由和兼容性边界。
version: 2.0.0
phase: 13
lesson: 17
tags: [mcp, gateway, stateless, registry, rbac, subscriptions, tasks]
---

给定 client、backend、授权要求和合规约束，产出一份 gateway 设计。

## 所需输入

- 公开 gateway 的 resource URI、接受的协议版本和 transport。
- 已认证的 principal 与角色模型。
- backend endpoint、issuer、resource、registry 记录、发布者证据和已批准的 descriptor。
- tool 可见性、参数策略、成本类别和数据敏感度。
- 流式、变更通知、MRTR 和 Tasks 需求。
- 审计、保留、trace 和脱敏要求。

## 产出

1. 无状态 ingress。单一 POST endpoint、每请求的版本与 capabilities、匹配的 method 与 name header、JSON 或请求作用域 SSE，以及对现代 GET 和 DELETE 返回 405。在版本支持之前先校验 header 一致性。明确 HTTP 400 `-32020`、带精确 supported 与 requested data 的 HTTP 400 `-32022`、HTTP 404 `-32601`、可选错误 data 的序列化，以及 202 空 body 的 notification 处理。
2. Discovery 方案。实现 gateway 的 `server/discover`，发现每个 backend，只暴露安全的端到端 capability 交集，并包含当前的 `resultType`、`ttlMs`、`cacheScope` 和 server 身份 metadata。
3. 准入表。将官方 Registry `server.json` 的发布结构以及 `com.example/*` 风格的名称与安全准入分开校验。对每个 backend，把记录与外部已验证的发布者命名空间、来源、endpoint、版本策略、descriptor 摘要、issuer、resource、审批和过期状态关联起来。
4. 命名空间映射。为每个 backend tool 指定稳定的限定公开名称，并在每个 `tools/list` descriptor 上保留合法的对象根 `inputSchema`。拒绝按顺序挑选冲突项。
5. 授权矩阵。把 principal 和角色映射到公开 tool、resource、arguments 和 scope。保持外层与 backend 凭据分离，并绑定到 issuer。
6. 转发契约。构造全新的自包含 backend 请求，只声明被中介的 client capabilities，校验 backend 结果，并保持 trace 关联。
7. 缓存方案。让依赖 principal 的 discovery 和列表保持私有。设置有界的 TTL 和失效行为。
8. 限流与审计策略。按 principal、issuer、resource、tool、成本类别和时间作为限流键。脱敏凭据和不必要的敏感参数。
9. 交互路由。描述请求作用域 SSE、`subscriptions/listen` 的确认与重连行为、逐字节精确的 MRTR 状态转发，以及在 `Mcp-Name` 中按 task id 路由 Tasks。
10. Transport adapter。如果 gateway 接收已解析的请求和 header，就把它标注为进程内协议模型，并接到第 09 课，以执行 JSON Content-Type 以及 JSON 加 SSE Accept 的约束。
11. 兼容性 adapter。把较旧的 initialization、session id、GET 流、resource 订阅和实验性 task method 隔离在现代 gateway 核心之外。

## 硬性拒绝

- 把 session 亲和性、session 存储或 session id 重写说成 2026-07-28 所必需的。
- 在没有准入证据的情况下信任 registry 中的存在性或展示名称。
- 静默的 tool 冲突，或未经重新审批就更新 descriptor pin。
- 在 backend 处复用外层 bearer token，或在其他 issuer 或 resource 处复用 backend token。
- 对按 principal 过滤的列表进行公开缓存。
- 独立的现代 GET 事件流、Last-Event-ID 重放或 resource subscribe method。
- 新的 `tasks/list` 或 `tasks/result` 行为。
- 仅以已移除的协议 session 为键的限流。
- 在 `server.json` 内臆造安全验证，而不是单独的已验证准入与来源状态。
- 省略 `inputSchema` 的命名空间化 tool descriptor。

## 输出格式

返回名为 Ingress、Discovery、Admission、Namespace Map、Authorization、Forwarding、Cache、Rate Limits、Audit、Interactions 和 Legacy Adapter 的章节。结尾指出需要最强验收测试的那一条路由。
