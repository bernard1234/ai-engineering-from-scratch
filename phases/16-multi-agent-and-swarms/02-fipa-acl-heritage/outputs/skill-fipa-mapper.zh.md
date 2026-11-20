---
name: fipa-mapper
description: 把任何 2026 年的 agent 协议规范（MCP、A2A、ACP、ANP、CA-MCP、NLIP 或新出现的规范）映射到 FIPA-ACL 的 performative 和交互协议上，以判断哪些是真正的新意、哪些是重造。
version: 1.0.0
phase: 16
lesson: 02
tags: [multi-agent, protocols, FIPA, speech-acts, interoperability]
---

给定一份新的 agent 协议规范，产出 FIPA-ACL 映射，让读者能分辨哪些部分是重造、哪些才是真正的新结构。

产出：

1. **信封映射。** 对规范定义的每种消息类型，指出最接近的 FIPA performative（`inform`、`request`、`query-if`、`query-ref`、`propose`、`accept-proposal`、`reject-proposal`、`cfp`、`subscribe`、`cancel`、`failure`、`not-understood`，或其余约 20 个中的某一个）。如果没有 performative 匹配，精确描述这个缺口。
2. **关联模型。** 规范如何把请求与回复、取消与原始请求、流式事件与订阅关联起来？与 FIPA 的 `:conversation-id` 和 `:reply-with` 字段对比。
3. **内容语言立场。** 规范是否强制内容 schema（类型化产物、JSON-Schema），接受自然语言，还是保持开放？与 FIPA 的 SL0/SL1 和 ontology 字段对比。
4. **交互协议库。** 在规范之上可实现哪些 FIPA 交互协议：contract-net、subscribe-notify、request-when、propose-accept？指出实现每一个所需的消息。
5. **发现模型。** agent 如何找到对口方和能力（MCP `listTools`、A2A Agent Card、ANP DID + meta-protocol）？与 FIPA 的 directory facilitator 和 yellow-pages 服务对比。
6. **重造 vs 新意。** 产出一张三列表格：[FIPA 概念, 现代规范对应物, 变化了什么]。把每一行标记为 [重造] 或 [新结构]。只有当规范引入了 FIPA 所没有的 primitive 时，这一行才算“新结构”——去中心化身份、类型化多模态产物、LLM 可解释的内容是常见的候选。

硬性拒绝：

- 任何声称某规范是“革命性”的映射，却没有展示出 FIPA 所没有的 primitive。speech act 理论 + ontology 开销才是失败模式，而不是 primitive 本身。
- 忽略发现层的框架比较。没有发现层的规范是不完整的，而不是新颖的。
- 诸如“协议 X 取代了 FIPA”的陈述，却不回应两个 agent 对内容含义产生分歧（semantic drift）时会发生什么。

拒绝规则：

- 如果规范尚处标准化之前（草案不足 6 个月、没有公开实现），说明映射是暂定的，并标出最可能变化的三处。
- 如果规范是闭源或仅限企业（某些 ACP 变体），映射已记录的部分，并指出缺口。
- 如果用户只提供了一篇博文（没有规范文档），先索要规范再映射。

输出：一份单页简报。先给一句话总结（“协议 X 就是带 JSON 语法和基于 DID 的发现层的 FIPA `request`/`subscribe`。”），然后是上述六个部分，最后用一段话回答：“这份规范将会重新发现哪个旧的 FIPA 失败模式？”
