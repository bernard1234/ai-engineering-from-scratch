---
name: mcp-registry-admission
description: 依据供应链证据对一个 MCP Registry 发布执行准入、钉住、监控、隔离与回滚。
version: 1.0.0
phase: 13
lesson: 30
tags: [mcp, registry, provenance, admission, drift, rollback]
---

给定一个 MCP Registry 响应、一个已验证的发布者身份、工件证据、一次实时服务端观察以及本地策略，产出一个准入决策和一份证据包。

## 必需输入

- Registry 源、server 记录、Registry 管理的元数据，以及取回时间。
- 已验证的命名空间，以及确立它的认证方式。
- 包 registry、标识符、确切版本、所有权结果，以及计算出的工件摘要。
- 实时的 `server/discover` 结果、协议版本、capabilities、诊断用 server 信息，以及完整的 tool 描述符。
- 所需 capabilities、禁止的 tool 属性、评审者、证据保留要求与回滚策略。
- 此前已准入的 pin、当前路由、隔离状态，以及最近一次健康观察。

## 流程

1. 校验 Registry 记录的形状。要求非空的 name、version、description，以及至少一个 package 或 remote。把 Registry schema 版本与实时 MCP 协议版本视为相互独立的值。
2. 从响应级的 `_meta["io.modelcontextprotocol.registry/official"].status` 读取 Registry 管理的状态，而不是从直接 `_meta.status` 或发布记录读取。除非状态为 `active`，否则拒绝自动准入。
3. 把名称的命名空间与可信认证所确立的命名空间精确比较。拒绝前缀相似项与空 slug。
4. 把一个声明的执行源与已验证证据关联起来。对于 package，匹配 registry 类型、标识符、确切版本和传输方式。对于仅远程的记录，把 URL 与传输方式与独立验证过的端点证据匹配。无论哪种源，都要求一个可信的 SHA-256 证据摘要。
5. 对规范化后的 Registry 记录做哈希。对关联 Registry 源、server 名称、Registry 版本、记录摘要、所选 source 与 source 证据摘要的 provenance 对象做哈希。
6. 观察实时端点。要求一个被接受的协议版本、所需的 capabilities，以及完整的 tool 描述符。只在展示、日志与调试中保留结果里的 `_meta["io.modelcontextprotocol/serverInfo"]`。永远不要用自报的 `serverInfo`（包括仅作为直接别名的形式）作为准入或安全权威。
7. 只归一化语义上无序的集合。对完整的归一化描述符表面做哈希，使 name、description、schema、annotation 或 tool-set 的变化都会造成 drift。
8. 应用本地的授权、数据、网络与评审策略。Registry 发布是证据，不是本地审批。
9. 在批准时，存储一个不可变的 pin，包含记录、执行源、provenance 与 toolset 摘要。把审批状态与活跃路由状态分开。
10. 把决策、原因、证据引用、上一条账本哈希与当前条目哈希追加到准入账本。在存储证据之前对凭据与敏感参数脱敏。
11. 按计划并在激活之前协调 Registry 状态与实时描述符。当状态变为 deprecated 或 deleted、源证据发生变化，或实时行为不同时，隔离并停用该 pin。被隔离的 pin 永远不是回滚目标。
12. 只回滚到一个此前已准入、当前仍合格、健康且未被隔离的 pin。把路由恢复记为一条新事件。永远不要重写旧的发布或准入决策。

## 硬性拒绝

- 仅凭熟悉的展示名称或 Registry 中的存在性推导出的信任。
- `startswith` 式的命名空间检查，或仅由提交记录声明的命名空间。
- `latest`、版本区间，或没有工件摘要的包坐标。
- 模仿 Registry 管理状态或验证的发布者字段。
- 缺失或格式错误的协议、capability 或描述符证据。
- 把自报的 `serverInfo` 当作命名空间、provenance、端点或准入权威。
- 在 drift 之后静默更新描述符 pin。
- 激活 deprecated、deleted、未知或被隔离的版本。
- 回滚到一个没有完整准入证据的目标。
- 证据中含 bearer token、cookie、包凭据，或不必要的 tool 参数。

## 产出

返回以下各节：

1. Decision：`approve`、`reject` 或 `quarantine`，并附稳定的原因码。
2. Namespace Proof：已验证的命名空间、认证来源，以及精确的名称比较。
3. Publication Pin：Registry 源、server 名称、确切版本、状态、schema 版本与记录摘要。
4. Source Pin：包坐标与传输方式，或远程 URL 与传输方式，所有权结果引用，以及 source 证据摘要。
5. Runtime Pin：被接受的协议版本、所需 capabilities、toolset 摘要，以及可选的诊断 `serverInfo`。
6. Provenance Join：规范化字段与所得的 provenance 摘要。
7. Policy Results：每一项通过、失败与不适用的控制。
8. Ledger Event：序号、时间、事件、结果、原因码、证据引用、上一哈希与条目哈希。
9. Reconciliation Plan：下一次状态、工件、发现、描述符与健康检查。
10. Rollback Plan：合格的先前 pin、校验步骤、路由变更、健康窗口，以及需要保留的证据。

最后以那个最能改变决策的单一缺失事实收尾。如果没有必需的缺失事实，就说明下一次计划的 drift 检查时间。
