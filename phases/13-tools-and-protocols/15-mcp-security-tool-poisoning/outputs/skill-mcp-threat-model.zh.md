---
name: mcp-threat-model
description: 针对元数据、路由、授权、MRTR 与兼容边界，对 MCP 2026-07-28 部署做威胁建模。
version: 2.0.0
phase: 13
lesson: 15
tags: [mcp, security, stateless, tool-poisoning, mrtr]
---

给定一个 MCP 部署，产出基于证据的威胁模型。假设任何 server、包、缓存、registry 条目或 gateway 路由都可能被攻陷。

## 所需输入

- Client、gateway、server、授权服务器和 registry 的信任边界。
- 完整的归一化工具描述符与已批准摘要。
- 认证 principal、签发方、受众、scope 和工具策略。
- 当前与旧版接受的协议版本。
- MRTR 操作、输入 schema、状态保护和重放策略。
- 缓存范围、TTL、订阅路由和审计保留。

## 产出

1. Wire 校验。先校验逐请求的版本与能力，再在版本支持判断之前校验路由头是否相等。要求：不一致时返回 HTTP 400 `-32020`；匹配到的版本不受支持时返回 HTTP 400 `-32022` 并给出精确的 supported 与 requested 数据；方法未知时返回 HTTP 404 `-32601`；被接受的 notification 返回 202 与空 body。
2. 描述符审查。报告投毒迹象、整描述符摘要变更、未知工具，以及 schema 或注解变更。
3. 命名空间映射。为每个后端工具给出一个限定公开名称，拒绝静默的冲突消解。
4. 授权矩阵。把已认证 principal 与签发方映射到资源、工具、参数约束和 scope。不要把 `clientInfo` 或 `serverInfo` 当作身份。
5. MRTR 审查。确认每个 `inputRequests` 条目都是完整的、受 client 已声明能力支持的内嵌请求。把 `elicitation: {}` 视为隐式 form 支持，把 `elicitation: {form: {}}` 视为显式 form 支持。对仅 URL 的 elicitation 用 HTTP 400 `-32021` 和 `data.requiredCapabilities.elicitation.form` 拒绝。把受保护的 `requestState` 绑定到方法、工具、精确参数、principal、用途、过期时间和 nonce。在由每个处理器实例共享的有界、按 TTL 修剪的重放存储中原子消费 nonce 之前，按 key 匹配并校验每一个 `inputResponses` 条目。
6. 风险轴审查。标记任何同时结合不可信输入、敏感数据和有后果动作的自动步骤。
7. 缓存与订阅审查。确保依赖用户的结果为 private，长期 notification 使用 `subscriptions/listen`。
8. 兼容边界。把任何较早的握手、会话、GET 流、server 回调或实验性任务行为隔离在显式的版本门控之后。
9. 传输边界。识别实现是完整的 HTTP 适配器还是进程内协议模型。把模型接到第 09 课，做 JSON Content-Type 与 JSON 加 SSE 的 Accept 校验。
10. 修复顺序。给出三个杠杆最大的修复，附负责人和验收证据。

## 硬性拒绝

- 静默的工具覆盖，或按 discovery 顺序选择路由。
- 未经人工或策略重新批准就更新描述符摘要。
- 把自报的 client 或 server 信息当作认证。
- 把已声明能力当作权限。
- 对一项有后果的动作信任明文或未签名的 `requestState`。
- 把唯一的重放台账留在一个 gateway 或 server 实例内。
- 只按 `Mcp-Session-Id` 为限速或审批状态建键。
- 把已弃用的 Sampling、Roots、Logging 或旧的 HTTP 加 SSE 呈现为新的实现路径。

## 输出格式

返回以下命名的章节：Trust Boundaries、Wire Findings、Descriptor Findings、Route Map、Authorization Matrix、MRTR Findings、Compatibility Findings 和 Remediation。把已确认的证据与假设分开。最后给出当前跨越边界最多的那条攻击路径。
