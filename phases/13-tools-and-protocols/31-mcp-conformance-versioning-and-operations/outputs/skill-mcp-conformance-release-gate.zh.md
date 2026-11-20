---
name: mcp-conformance-release-gate
description: 构建 MCP conformance 矩阵，并给出有证据支撑的 promote、hold 或 rollback 决策。
version: 1.0.0
phase: 13
lesson: 31
tags: [mcp, conformance, versioning, transcripts, proxy, operations]
---

给定一个 MCP 客户端、服务端、网关、SDK 或传输变更，产出一套 wire 级 conformance 套件，以及一个附带脱敏证据的发布决策。

## 必需输入

- 受支持的现代与旧版协议版本，以及每个部署目标的策略。
- SDK 解码之前的原始请求与响应捕获点。
- 镜像 HTTP 头、JSON-RPC body、状态、content type，以及中间层拓扑。
- 已声明的客户端、服务端与扩展 capabilities。
- SDK 名称、版本、归一化值与异常。
- 健康阈值、canary 窗口、最小样本数与基线测量。
- 确切的回滚版本、准入证据摘要、SHA-256 工件与描述符 pin、Registry 状态、当前健康、可信发布签名者，以及针对完整回滚载荷的 attestation。
- 脱敏、保留与证据访问策略。

## 流程

1. 定义明确的协议纪元。在现代分支中要求确切的 `io.modelcontextprotocol/protocolVersion` 与 `io.modelcontextprotocol/clientCapabilities` 键。把直到 `2025-11-25` 的初始化纪元行为放进独立的旧版适配器。
2. 为每个目标选择严格或有界回退策略。一次成功的 `server/discover` 或一个已被识别的现代错误即可证明现代分支。超时或空响应什么也证明不了。只对已配置或列入 allowlist 的端点允许旧版探测，并且只有在针对所钉住的旧版修订校验出一个正向 `initialize` 结果之后，才选择旧版。永远不要在 `-32020`、`-32021` 或 `-32022` 之后降级。
3. 为被接受的请求、有效的方法特定结果、已声明的扩展结果、所选旧版行为和通知无响应不变量创建黄金 transcript。
4. 为格式错误的信封、响应版本或 ID 不匹配、result 与 error 的排他性、格式错误的错误、错误的 HTTP 映射、缺失元数据、头与 body 不匹配、缺少服务端错误响应、不受支持的版本、缺少现代 `resultType`、格式错误的方法载荷、未知或未被声明的结果类型，以及被禁止的通知响应创建负向 transcript。只要本地校验观察到 `HeaderMismatch`，就自动要求并结构性地校验真实的 HTTP 400 JSON-RPC `-32020` 响应。仅有一个本地异常永远不能通过该用例。
5. 先校验 JSON-RPC 元数据类型。按大小写不敏感匹配 HTTP 头名称，拒绝相互冲突的重复项，为不安全的 `Mcp-Name` 值解码确切的 Base64 sentinel，然后在检查已匹配值的支持情况之前，把 `MCP-Protocol-Version`、`Mcp-Method` 和适用的 `Mcp-Name` 值与 body 比较。把前导或尾随空白视为不安全，并在其以原始形式发送时予以拒绝，即使它与 body 值相等。
6. 接受已知的现代 `complete` 与 `input_required` 结果。只有在扩展判别符的 capability 已被声明时才接受它。拒绝每一个未知或未被声明的 `resultType`。然后校验方法载荷，包括 `tools/list` 的完整 tool 描述符、task 结果所需的生命周期字段，以及 `completion/complete` 的有界字符串值 completion 对象。
7. 在证据中保留原始的增量结果与 `_meta` 字段。显式决定每个组件是可以忽略它们还是必须转发它们。
8. 对每个交付的 SDK 运行每一份高风险 transcript。把原始 wire 语义与归一化返回值比较，并报告每一个被合成、提升、剥离或改变的字段。
9. 既直接执行套件，也通过每一个生产中间层执行。捕获脱敏后的 ingress、origin 与 egress 证据。检测状态压平、JSON-RPC body 重写、路由头不匹配、缓冲和内容协商变化。
10. 在序列化、哈希、日志或上传之前应用脱敏。对字段名与头名称做大小写折叠并移除分隔符，使 camelCase、连字符、下划线和点号变体共用同一份拒绝名单，然后移除诸如 `Authorization`、`Set-Cookie`、`X-Api-Key`、`accessToken`、`clientSecret` 和 `registrationAccessToken` 之类的凭据，以及方法特定的敏感参数。对脱敏后的证据包做哈希。
11. 依据非空的确定性 transcript、SDK 差分与代理证据，外加一个预先声明、含正数最小样本数的健康窗口，评估候选版本。要求每个来源都提供有效的证据摘要。一条被省略的边界就是一道失败的门禁，而不是一个通过的空列表。
12. 在提升之前验证一个确切的、已准入、已钉住、active 且健康的回滚目标。校验确切的字段类型与 SHA-256 摘要，然后针对可信的 release-controller 身份以密码学方式验证其 attestation。只有当 conformance、SDK、代理、健康与回滚就绪证据全部通过时才提升。候选版本失败时，只回滚到那个已验证的目标。否则暂停。

## 必需矩阵

对于每个用例，都要报告：

- 稳定的用例名与规范性不变量
- 协议纪元与选择证据
- 客户端、服务端、SDK、代理与构建版本
- 预期状态、响应形状、结果类型或错误码
- 观察到的 ingress、origin 与 egress 证据摘要
- SDK 归一化差异
- 每条边界上的通过或失败
- 脱敏策略版本
- 最终原因码

至少包含以下用例：

- 黄金的现代发现或方法调用
- 黄金的、带增量字段的已知完整结果
- 黄金的、在所选旧版纪元中缺失 `resultType` 的旧版结果
- 黄金的已声明扩展结果
- 黄金的有效 `completion/complete` 结果
- 黄金的、不产生 JSON-RPC 响应的通知
- 负向的头与 body 不匹配
- 负向的缺失 capabilities
- 负向的已匹配但不受支持的版本
- 负向的缺少现代 `resultType`
- 负向的未知或未被声明的 `resultType`
- 负向的代理状态或 body 变换
- 负向的 SDK 语义字段丢失
- 负向的格式错误 `completion/complete` 结果

## 硬性拒绝

- 仅凭 SDK 返回值宣称 conformance，而没有原始 wire 证据。
- 用一个解析器静默接受现代与旧版两种形状。
- 在已被识别的现代错误之后回退到旧版。
- 仅基于超时、沉默、连接关闭或无法识别的响应回退到旧版。
- 在没有捕获并校验服务端错误响应的情况下通过一个负向请求用例。
- 在本地检测到 `HeaderMismatch` 之后，仍把 HTTP 400 JSON-RPC `-32020` 证据当作可选。
- 在选择旧版纪元之前就把缺失的 `resultType` 推断为完整。
- 把未知判别符当作完整。
- 在没有保留字段理由的情况下拒绝所有增量未知字段。
- 对任何通知发送 JSON-RPC 响应。
- 在接受一个已知 `resultType` 时没有校验方法特定的载荷。
- 在未检查与 body 相等的情况下授权镜像头。
- 把 HTTP 字段名当作大小写敏感，或在没有精确 sentinel 解码的情况下比较一个被编码的 `Mcp-Name`。
- 接受带前导或尾随空白的原始 `Mcp-Name`，而不是要求 sentinel 编码。
- 在没有有效的有界字符串值 completion 对象时接受一个 completion 结果。
- 把代理生成的 500 等同于源站协议错误。
- 把 bearer token、cookie、密钥或敏感参数写入证据。
- 使用会让 camelCase 或分隔符变体绕过规范化凭据拒绝名单的脱敏归一化。
- 宣布一个零样本的 canary 为健康。
- 把空的 transcript、SDK 或代理证据当作通过的边界。
- 把真值字符串或未经认证的回滚字典当作已验证证据。
- 回滚到一个没有确切准入、pin、状态与健康证据的版本。
- 在证明了一个健康的回滚目标之前就提升一个生产候选版本。

## 产出

返回以下各节：

1. Era Policy：现代证明、严格目标、有界回退触发条件，以及被禁止的降级信号。
2. Transcript Matrix：带有预期 wire 结果的黄金与负向用例。
3. Result Compatibility：核心判别符、已声明的扩展、增量字段策略，以及旧版推断边界。
4. SDK Differential：原始与归一化摘要，以及被提升、剥离、合成和改变的字段。
5. Proxy Evidence：ingress、origin 与 egress 结果，以及确切失败的那一跳。
6. Redaction Report：策略版本、被移除的字段类别，以及脱敏后的证据摘要。
7. Health Window：样本、错误率、延迟、饱和度、时长、阈值与基线比较。
8. Rollback Proof：确切目标、准入摘要、pin、Registry 状态、健康、签名者身份、已验证 attestation 与路由恢复计划。
9. Decision：`promote`、`hold` 或 `rollback`，并附稳定的原因码与完整的证据摘要。

最后以第一条失败的边界收尾。如果所有边界都通过，就说明授权完全提升的 canary 完成条件。
