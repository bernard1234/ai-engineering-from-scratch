# FIPA-ACL 与 speech act 的遗产

> 在 MCP 之前，在 A2A 之前，就已经有 FIPA-ACL。2000 年，IEEE Foundation for Intelligent Physical Agents 批准了一种 agent 通信语言，其中包含二十个 performative、两种内容语言，以及一组交互协议——contract net、subscribe/notify、request-when。它因 ontology 开销对 web 而言过于沉重而淡出产业界，但 multi-agent 系统的 LLM 复兴正在悄悄重新实现同样的想法，只是去掉了形式语义：JSON 约定代替 performative，自然语言代替 ontology。本课认真研读 FIPA-ACL，让你看清 2026 年哪些协议决策是重造轮子、哪些才是真正的新意，以及当前这波浪潮将在哪些地方重新发现 2000 年代已经解决过的问题。

**Type:** Learn
**Languages:** Python (stdlib)
**Prerequisites:** 第 16 阶段，第 01 课（Why Multi-Agent）
**Time:** ~60 分钟

## 问题场景

2026 年的 agent 协议版图很热闹：MCP 面向工具，A2A 面向 agent，ACP 面向企业审计，ANP 面向去中心化信任，NLIP 面向自然语言内容，再加上 CA-MCP 和二十多个研究提案。每个规范都宣称自己是奠基性的。

诚实的解读是：它们中的大多数都在重新发现一棵非常具体的、二十年前就有的决策树。Austin（1962）和 Searle（1969）的 speech act 理论给了我们“话语即行动”。KQML（1993）把它变成有线协议。FIPA-ACL（2000 年批准）产出了参考标准：二十个 performative、内容语言 SL0/SL1、用于 contract-net 和 subscribe-notify 的交互协议。JADE 和 JACK 是 Java 参考平台。这项努力在 2010 年前后淡出，因为 ontology 开销太重，而 web 正在胜出。

当你看到 MCP 的 `tools/call`、A2A 的任务生命周期，或 CA-MCP 的共享 context 存储时，你看到的是对 FIPA 决策的、更柔和且 JSON 原生的重炒。了解这段遗产能告诉你两件事：哪些新“创新”其实是重造，以及新规范将会重新发现哪些旧的失败模式。

## 核心概念

### 用一段话讲清 speech act

Austin 注意到，有些句子不是在描述世界——而是在改变世界。“我承诺。”“我请求。”“我宣布。”他把这些称为施为性话语（performative utterance）。Searle 将它们形式化为五类：assertive、directive、commissive、expressive、declarative。KQML（Finin 等，1993）让这一切对软件 agent 可操作：一条消息就是一个 performative（动作）加上 content（动作所关于的内容）。FIPA-ACL 补上了 KQML 的缺口，并围绕二十个 performative 完成标准化。

### 二十个 FIPA performative（部分列表）

| Performative | 意图 |
|---|---|
| `inform` | “我告诉你 P 为真” |
| `request` | “我请求你做 X” |
| `query-if` | “P 为真吗？” |
| `query-ref` | “X 的值是多少？” |
| `propose` | “我提议我们做 X” |
| `accept-proposal` | “我接受该提议” |
| `reject-proposal` | “我拒绝该提议” |
| `agree` | “我同意做 X” |
| `refuse` | “我拒绝做 X” |
| `confirm` | “我确认 P 为真” |
| `disconfirm` | “我否认 P” |
| `not-understood` | “你的消息无法解析” |
| `cfp` | “就 X 征集提案” |
| `subscribe` | “X 变化时通知我” |
| `cancel` | “取消正在进行的 X” |
| `failure` | “我尝试了 X 但失败了” |

完整列表见 `fipa00037.pdf`（FIPA ACL Message Structure）。重点不在于背诵它——而在于：其中每一个都对应一个 LLM 协议最终会重新加回的 primitive。

### 标准的 FIPA-ACL 消息

```
(inform
  :sender       agent1@platform
  :receiver     agent2@platform
  :content      "((price IBM 83))"
  :language     SL0
  :ontology     finance
  :protocol     fipa-request
  :conversation-id   conv-42
  :reply-with   msg-17
)
```

七个字段承载协议信封；一个字段（`content`）承载负载。其余字段正是每次你在 JSON 协议上硬加重试、线程和 ontology 时都要重造的东西。

### 两个遗留平台

**JADE**（Java Agent DEvelopment framework，1999–2020s）是使用最广的 FIPA 兼容运行时。agent 扩展一个基类，交换 ACL 消息，运行在容器中，并用“behaviors”协调。它的交互协议库随附 contract-net、subscribe-notify、request-when 和 propose-accept。

**JACK**（Agent Oriented Software，商业产品）强调在 FIPA 消息之上做 BDI（Belief-Desire-Intention）推理。更形式化，采用者更少。

随着 web 技术栈吞掉了 multi-agent 的用例，两者都衰落了。MCP 和 A2A 是 2026 年的运行时“容器”。

### FIPA 为何淡出

- **Ontology 开销。** FIPA 要求共享 ontology 才能解析 `content`。就 ontology 达成一致是耗时数年的标准流程。而 web 只用 HTTP + JSON。
- **没人使用的形式语义。** SL（Semantic Language）给出了严谨的真值条件，但多数生产系统使用自由形式的内容，无视这套形式化。
- **工具链锁定。** JADE 仅限 Java；JACK 是商业产品。多语言团队绕开了两者。
- **互联网赢得了技术栈。** REST、然后是 JSON-RPC、再是 gRPC，取代了 ACL 的传输层。

### LLM 复兴是 FIPA-lite

把一个 FIPA `request` 与一个 MCP `tools/call` 对比：

```
(request                                {
  :sender  agent1                         "jsonrpc": "2.0",
  :receiver tool-server                   "method":  "tools/call",
  :content "(lookup stock IBM)"           "params":  {"name":"lookup_stock",
  :ontology finance                                   "arguments":{"symbol":"IBM"}},
  :conversation-id c42                    "id": 42
)                                        }
```

同样的信封，不同的语法。两者都承载：谁、对谁、意图、负载、关联 id。谁都不是对方的革命——它们是同一设计上的不同权衡。

Liu 等人 2025 年的综述（“A Survey of Agent Interoperability Protocols: MCP, ACP, A2A, ANP”，arXiv:2505.02279）明确指出了这条谱系：MCP 对应工具使用的 speech act，A2A 对应 agent 对等的 speech act，ACP 对应审计追踪的 speech act，ANP 对应去中心化身份的扩展。新规范是 ACL 的后代，只是换成了 JSON 语法和更宽松的语义。

### 直白地说清权衡

**FIPA 给了你、而现代规范丢掉的东西：**

- 形式语义——你可以证明 `inform` 蕴含发送者相信其内容。
- 一份规范的 performative 目录——你不必再争论“我们是否该有 `cancel`？”。
- 数十年的交互协议模式——contract-net、subscribe-notify、propose-accept——带有已知的正确性属性。

**现代规范给了你、而 FIPA 没有的东西：**

- JSON 原生负载，兼容所有现代工具。
- LLM 无需手工编码的 ontology 即可解释的自然语言内容。
- web 技术栈传输（HTTP、SSE、WebSocket）。
- 通过实时 MCP `server/discover` 和 A2A Agent Card 进行能力发现。

更宽松的意图语义，换取更简单的实现。这就是那笔确切的交换。

### 值得移植的交互协议

FIPA 交付了约 15 个交互协议。其中三个值得带入 LLM multi-agent 系统：

1. **Contract Net Protocol（CNP）。** 管理者发出 `cfp`（call for proposals）；投标者以 `propose` 回应；管理者接受/拒绝。这是经典的任务市场模式（第 16 阶段，第 16 课 Negotiation）。
2. **Subscribe/Notify。** 订阅者发送 `subscribe`；发布者在主题变化时发送 `inform`。这就是 2026 年的每一个事件总线。
3. **Request-When。** “当条件 Y 成立时做 X。”带前置条件的延迟动作。2026 年的对应物是持久化工作流引擎中的延迟任务（第 16 阶段，第 22 课 Production Scaling）。

每一个都能干净地映射到现代消息队列、HTTP + 轮询或 SSE 流式传输。

### 丢掉 ontology 之后会出什么问题

没有共享 ontology，agent 从自然语言内容中推断含义。2026 年有记录的失败模式是 **semantic drift**：两个 agent 把同一个词（`"customer"`）用于微妙不同的概念，接收方的 agent 按错误的理解行动，而没有任何 schema 校验器能拦住它。FIPA 的 ontology 要求本会在解析阶段就拒绝该消息。

在不引入完整 ontology 的前提下的缓解手段：

- 对 `content` 使用 JSON Schema——在线路上拒绝结构性错误。
- 类型化产物（A2A）——拒绝错误的模态。
- 信封中显式的 performative——即使内容是自然语言，也让意图明确无歧义。

### 2026 年的规范，映射到 speech act 遗产

| 现代规范 | FIPA 对应物 | 它保留了什么 | 它丢掉了什么 |
|---|---|---|---|
| MCP `tools/call` | `request` | 显式意图、关联 id | 形式语义、ontology |
| MCP `resources/read` | `query-ref` | 显式意图、关联 id | 形式语义 |
| A2A Task 生命周期 | contract-net + request-when | 异步生命周期、状态转换 | 形式化完整性保证 |
| A2A 流式事件 | subscribe/notify | 异步推送 | 类型化谓词订阅 |
| CA-MCP 共享 context | blackboard（Hayes-Roth 1985） | 多写者共享内存 | 逻辑一致性模型 |
| NLIP | 自然语言内容 | LLM 原生 | schema |

从上到下读这张表，模式是：保留结构性的 primitive，丢掉形式化，让 LLM 去掩盖歧义。

```figure
sw-contract-net
```

## Build It

`code/main.py` 实现了一个纯 stdlib 的 FIPA-ACL 翻译器。它对标准 ACL 信封进行编码和解码，并展示每个 MCP / A2A 消息形态如何归约为同样的七个字段。演示会：

- 把五条 MCP 风格和 A2A 风格的消息编码成 FIPA-ACL。
- 把 FIPA-ACL 解码回现代等价形式。
- 使用 `cfp`、`propose`、`accept-proposal`、`reject-proposal`，在一个管理者和三个投标者之间运行一个玩具级 Contract Net 协商。

运行：

```
python3 code/main.py
```

输出是一份并排追踪，展示每条现代消息的 2026 JSON 形式和 FIPA-ACL 形式，然后是一次 contract-net 投标的往返。同样的协议 primitive 经受住往返；只是语法不同。

## Use It

`outputs/skill-fipa-mapper.md` 是一个 skill，能读取任何 agent 协议规范并产出 FIPA-ACL 映射。在采纳新协议之前使用它来回答：“这真的是新东西，还是套着 JSON 语法的 `inform`？”

## Ship It

不要把 FIPA-ACL 带回来。把它那份检查清单带回来：

- 每条消息的意图 primitive（performative）是什么？
- 是否有用于请求-响应和取消的关联 id？
- 是否有明确的内容语言（JSON-RPC、纯文本、结构化类型化产物）？
- 交互协议是不是一等公民，还是你在从零重实现 contract-net？
- 当两个 agent 对内容含义产生分歧（semantic drift）时会发生什么？

在把任何新协议投入生产之前，为它记录这五个问题。

## Exercises

1. 运行 `code/main.py`。观察往返编码。指出哪个 FIPA performative 对应 `tools/call`、`resources/read` 和 A2A 任务创建。
2. 用一个 `cancel` performative 扩展 contract-net 演示，让管理者能在投标过程中撤回任务。`cancel` 解决了只有重试无法解决的哪个失败场景？
3. 阅读 FIPA ACL Message Structure（http://www.fipa.org/specs/fipa00037/）第 4.1–4.3 节。挑一个本课未涵盖的 performative，描述它对应的现代 JSON-RPC 形式。
4. 阅读 Liu 等人，arXiv:2505.02279。对 MCP、A2A、ACP、ANP 中的每一个，列出它们保留和丢弃的 FIPA performative 家族。
5. 为你自己系统中 `request` performative 的 `content` 字段设计一个最小 JSON-Schema。这个 schema 给了你纯自然语言所没有的什么，又付出了什么代价？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Speech act | “一种会做事的话语” | Austin/Searle：话语即行动。ACL 的理论之父。 |
| FIPA | “那个老掉牙的 XML 东西” | IEEE Foundation for Intelligent Physical Agents。2000 年标准化了 ACL。 |
| ACL | “Agent Communication Language” | FIPA 的信封格式：performative + content + 元数据。 |
| Performative | “那个动词” | 消息的意图类别：`inform`、`request`、`propose`、`cfp` 等。 |
| KQML | “FIPA 的前身” | Knowledge Query and Manipulation Language（1993）。更简单，覆盖更窄。 |
| Ontology | “共享词汇表” | 对内容语言所谈论概念的形式化定义。 |
| SL0 / SL1 | “FIPA 的内容语言” | Semantic Language 的第 0 级和第 1 级——形式化内容语言家族。 |
| Contract Net | “任务市场” | 管理者发出 cfp；投标者 propose；管理者 accept。经典的交互协议。 |
| Interaction protocol | “消息的模式” | 具有已知正确性的 performative 序列：request-when、subscribe-notify 等。 |

## Further Reading

- [Liu et al. — A Survey of Agent Interoperability Protocols: MCP, ACP, A2A, ANP](https://arxiv.org/html/2505.02279v1)——把现代规范与 FIPA 遗产联系起来的 2025 年权威综述
- [FIPA ACL Message Structure Specification (fipa00037)](http://www.fipa.org/specs/fipa00037/)——2000 年批准的信封格式
- [FIPA Communicative Act Library Specification (fipa00037)](http://www.fipa.org/specs/fipa00037/)——完整的 performative 目录
- [MCP specification 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28)——当前无状态的、等价于 `request`/`query-ref` 的工具使用规范
- [A2A specification](https://a2a-protocol.org/latest/specification/)——现代 agent 对等的、等价于 contract-net 和 subscribe-notify 的规范
