# 案例研究与 2026 年 SOTA

> 三个生产级参考，端到端研读，各自照亮多 agent 工程的一个不同切面。**Anthropic 的 Research 系统**（orchestrator-worker、15x token、较 single-agent Opus 4 提升 +90.2%、rainbow 部署）是正典的 supervisor 案例。**MetaGPT / ChatDev**（把软件工程 SOP 编码成角色专精；ChatDev 的"communicative dehallucination"；MacNet 通过 DAG 扩展到 >1000 个 agent，arXiv:2406.07155）是正典的角色分解案例。**OpenClaw / Moltbook**（最初是 Peter Steinberger 于 2025 年 11 月创建的 Clawdbot；改名两次；到 2026 年 3 月拥有 247k GitHub star；本地 ReAct-loop agent；Moltbook 作为仅 agent 可用的社交网络，上线数天内约 230 万 agent 账号，2026-03-10 被 Meta 收购）展示了群体规模下会发生什么：涌现的经济活动、prompt injection 风险、国家层面的监管（中国于 2026 年 3 月限制政府电脑上使用 OpenClaw）。**2026 年 4 月的框架格局：** LangGraph 与 CrewAI 在生产中领先；AG2 是社区版 AutoGen 的延续；Microsoft AutoGen 处于维护模式（并入 Microsoft Agent Framework，2026 年 2 月 RC）；OpenAI Agents SDK 是生产版 Swarm 的后继者；Google ADK（2025 年 4 月）是 A2A 原生入场者。如今每个主流框架都支持 MCP；大多数支持 A2A。本课端到端读每个案例，提炼共同模式，让你能为下一个生产系统挑对参考。

**Type:** Learn (capstone)
**Languages:** —
**Prerequisites:** 第 16 阶段全部（第 01-24 课）
**Time:** ~90 分钟

## 问题场景

多 agent 工程是一门年轻的学科。生产参考很少，而且各自覆盖空间的不同部分。逐个读有用；把它们作为一组来比较更有用。本课把 2026 年的三个正典案例研究当作一份端到端阅读清单，钉住共同模式，并梳理框架格局，让你基于知识而非营销来做框架选择。

## 核心概念

### Anthropic Research 系统

生产级 supervisor-worker 案例。Claude Opus 4 负责规划与综合；Claude Sonnet 4 子 agent 并行研究。已发布的工程博客：https://www.anthropic.com/engineering/multi-agent-research-system。

关键实测结果：

- 在内部研究 eval 上，较 single-agent Opus 4 提升 **+90.2%**。
- **BrowseComp 方差的 80%** 仅由 **token 用量**解释 —— 多 agent 之所以赢，很大程度上是因为每个子 agent 都拿到全新的 context window。
- 相比 single-agent，每次查询消耗 **15x token**。
- 采用 **rainbow 部署**，因为 agent 长时间运行且有状态。

总结出的设计经验：

1. **按查询复杂度伸缩投入。** 简单 → 1 个 agent、3-10 次 tool call。中等 → 3 个 agent。复杂研究 → 10+ 个子 agent。
2. **先广后深。** 子 agent 做广域搜索；主 agent 综合；后续子 agent 做定向深挖。
3. **rainbow 部署。** 让旧运行时版本保持存活，直到其进行中的 agent 完成。
4. **验证不是可选项。** 观察到在没有显式验证器角色时系统会产生幻觉。

这是 supervisor-worker 拓扑（第 16 阶段 · 05）在生产规模下的参考案例。

### MetaGPT / ChatDev

生产级 SOP 角色分解案例。覆盖 arXiv:2308.00352（MetaGPT）与 arXiv:2307.07924（ChatDev）。

MetaGPT 把软件工程 SOP 编码成角色 prompt：产品经理、架构师、项目经理、工程师、QA 工程师。论文的表述是：`Code = SOP(Team)`。每个角色都有窄而专精的 prompt；角色间交接携带结构化产物（PRD 文档、架构文档、代码）。

ChatDev 的贡献：**communicative dehallucination**。Agent 在回答前先索要具体信息 —— 设计师 agent 在勾画 UI 前先问程序员打算用什么语言，而不是猜测。论文报告这在多 agent 流水线中可测地减少了幻觉。

MacNet（arXiv:2406.07155）通过 **DAG 把 ChatDev 扩展到 >1000 个 agent**。每个 DAG 节点是一个角色专精；边编码交接契约。之所以能到这种规模，是因为路由是显式的、可离线计算的。

设计经验：

1. **结构比规模更重要。** 一个紧凑的 5 角色 SOP 团队胜过一个 50 agent 的无结构群体。
2. **交接契约要写下来。** 角色之间传递的产物遵循 schema。
3. **communicative dehallucination** 是一个廉价且承重的模式。
4. **DAG 比聊天扩展得更远。** 当流程可知时，就把它编码出来。

这是角色专精（第 16 阶段 · 08）与结构化拓扑（第 16 阶段 · 15）的参考案例。

### OpenClaw / Moltbook 生态

生产级群体规模案例。时间线：

- **2025 年 11 月：** Clawdbot（Peter Steinberger 的本地 ReAct-loop 编码 agent）发布。
- **2025 年 12 月 – 2026 年 3 月：** 改名两次（Clawdbot → OpenClaw → 继续以 OpenClaw 之名）。
- **2026 年 2 月：** Moltbook 基于同样的原语上线，作为仅 agent 可用的社交网络；数天内约 230 万 agent 账号。
- **2026 年 3 月（2026-03-10）：** Meta 收购 Moltbook。
- **2026 年 3 月：** 中国限制政府电脑上使用 OpenClaw。
- **2026 年 3 月：** OpenClaw 的 GitHub star 突破 247k。

这就是把数百万 agent 放在同一基底上时，多 agent 的样子：

- **涌现的经济活动。** Agent 之间用 token 支付买卖与互相服务。
- **群体规模下的 prompt injection 风险。** 一个病毒式传播的 agent 档案中的一条恶意 prompt，会在数小时内扩散到成千上万次 agent 间交互。
- **国家层面的监管反应。** 上线数周内，监管就触及该生态。

这个案例的设计经验一部分是技术性的，一部分是治理性的：

1. **群体规模的多 agent 是一种新体制。** 单系统的最佳实践（验证、角色清晰）仍适用，但不充分。
2. **prompt injection 是新的 XSS。** 默认把 agent 档案与 agent 间消息当作不可信输入。
3. **监管比设计周期更快。** 要提前规划。
4. **开源 + 病毒式规模会叠加。** 约 4 个月 247k star 并不常见；要为部署突发负载而设计。

生态细节见 [OpenClaw 维基百科](https://en.wikipedia.org/wiki/OpenClaw) 与 CNBC / Palo Alto Networks 的报道。技术上，Clawdbot / OpenClaw 仓库公开了本地 ReAct loop；Moltbook 的公开帖子揭示了其上的社交图架构。

### 2026 年 4 月的框架格局

| 框架 | 状态 | 最适合 | 备注 |
|---|---|---|---|
| **LangGraph**（LangChain） | 生产领跑者 | 结构化 graph + checkpointing + human-in-the-loop | 生产的推荐默认项 |
| **CrewAI** | 生产领跑者 | 基于角色的 crew，Sequential/Hierarchical 流程 | 角色分解很强 |
| **AG2** | 社区维护 | GroupChat + speaker selection | AutoGen v0.2 的延续 |
| **Microsoft AutoGen** | 维护模式（2026 年 2 月） | — | 并入 Microsoft Agent Framework RC |
| **Microsoft Agent Framework** | RC（2026 年 2 月） | 编排模式 + 企业集成 | 新入场者；关注 |
| **OpenAI Agents SDK** | 生产 | Swarm 后继者 | tool-return handoff 模式 |
| **Google ADK** | 生产（2025 年 4 月） | A2A 原生 | Google Cloud 集成 |
| **Anthropic Claude Agent SDK** | 生产 | single-agent + Research 扩展 | 见 Research 系统博客 |

如今每个主流框架都支持 **MCP**；大多数支持 **A2A**。协议兼容性不再是差异化因素。

### 三个案例的共同模式

1. **Orchestrator + workers**（Anthropic 显式 supervisor、MetaGPT 以 PM 作 supervisor、OpenClaw 单个 agent + 网络效应）。
2. **结构化交接契约**（Anthropic 的子 agent 任务描述、MetaGPT 的 PRD/架构文档、OpenClaw 的 A2A 产物）。
3. **验证作为一等角色**（Anthropic 的验证器、MetaGPT 的 QA 工程师、OpenClaw 的网络内验证者）。
4. **扩展靠拓扑 + 基底，而不只是更多 agent**（rainbow 部署、MacNet DAG、群体规模基底）。
5. **成本是实质性的且要披露**（15x token、MetaGPT 的按角色预算、Moltbook 的按交互定价）。
6. **安全姿态是显式的**（Anthropic 的沙箱、MetaGPT 的角色限制、OpenClaw 把 prompt injection 作为已知攻击面）。

### 为下一个项目挑参考

- **生产研究 / 知识任务 → Anthropic Research。** Fresh-context 子 agent 占优。
- **工程 / 工具链工作流 → MetaGPT / ChatDev。** 角色 + SOP + 交接契约。
- **网络效应社交产品 → OpenClaw / Moltbook。** 基底 + 涌现经济。
- **经典企业自动化 → CrewAI 或 LangGraph**（生产领跑者、运行时稳定）。

### 2026 年 SOTA 总结

2026 年 4 月该领域的位势：

- **框架正在收敛。** MCP + A2A 支持是基本门槛。交接语义是剩下的设计选择。
- **评估正在变硬。** SWE-bench Pro、MARBLE、STRATUS 缓解型 benchmark。Pro 是当前抗污染的现实检验。
- **生产失效率是可测的**（Cemri 2025 MAST；真实 MAS 上 41-86.7%）。该领域已走出"demo 里看着很棒"的时代。
- **成本是核心工程约束。** 每任务 token 成本、每交互墙钟时间、rainbow 部署开销。多 agent 在准确率上赢、在成本上输 —— 这个权衡就是商业决策。
- **监管是近期输入，而非背景关切。** 各司法辖区的动作比单个部署周期更快。

```figure
a5-orchestrator-scale
```

## Use It

`outputs/skill-case-study-mapper.md` 是一个 skill，读取拟议的多 agent 系统设计并映射到最接近的案例研究，呈现该案例研究已经验证过的设计决策。

## Ship It

2026 年生产多 agent 的起步规则：

- **从案例研究起步，而不是从零。** 挑 Anthropic Research / MetaGPT / OpenClaw 中最接近的并做适配。
- **采用 MCP + A2A。** 跨框架可移植性有价值；协议支持是免费的。
- **对照 SWE-bench Pro 或你的内部 Pro 等价物来衡量。** Verified 已被污染。
- **支付验证税。** 一个独立验证器消耗约 20-30% 的 token 预算，换来可测的正确性。
- **长时间运行的 agent 用 rainbow 部署。** 预期多小时 agent run 会成为常态。
- **读 WMAC 2026 与 MAST 的后续工作。** 这门学科进展很快。

## Exercises

1. 端到端读 Anthropic Research 系统博客。指出三个设计决策：若把 Opus 4 换成更小的模型（例如 Haiku 4），它们会如何改变？
2. 读 MetaGPT 第 3-4 节（arXiv:2308.00352）。把你所在领域（非软件）的一条 SOP 编码成角色 prompt。这条 SOP 隐含了多少个角色？
3. 读 ChatDev（arXiv:2307.07924）。指出"communicative dehallucination"的机制。在你现有的某个多 agent 系统中实现它。
4. 阅读关于 OpenClaw 与 Moltbook 的资料。挑一个在群体规模下涌现、但在 5 agent 系统中不会出现的具体失效模式。你会如何针对它做工程防护？
5. 挑你当前的多 agent 项目。三个案例研究中哪个是最接近的参考？该案例研究的哪些设计决策你尚未采用？写下你这个季度将采用的一个。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Anthropic Research | "supervisor 参考" | Claude Opus 4 + Sonnet 4 子 agent；15x token；较 single-agent 提升 +90.2%。 |
| MetaGPT | "SOP 即 prompt" | 面向软件工程的角色分解；`Code = SOP(Team)`。 |
| ChatDev | "agent 即角色" | 设计师 / 程序员 / 评审 / 测试；communicative dehallucination。 |
| MacNet | "用 DAG 扩展 ChatDev" | arXiv:2406.07155；通过显式 DAG 路由扩展到 1000+ agent。 |
| OpenClaw | "本地 ReAct-loop agent" | Steinberger 的项目；到 2026 年 3 月 247k star。 |
| Moltbook | "仅 agent 的社交网络" | 230 万 agent 账号；2026 年 3 月被 Meta 收购。 |
| Rainbow deploy | "多版本并存" | 为进行中的长时 agent 保留旧运行时版本。 |
| Communicative dehallucination | "先问再答" | Agent 向同伴索要具体信息，而非猜测。 |
| WMAC 2026 | "那个 AAAI workshop" | 2026 年 4 月多 agent 协调的社区焦点。 |

## Further Reading

- [Anthropic —— 我们如何构建多 agent 研究系统](https://www.anthropic.com/engineering/multi-agent-research-system) —— supervisor-worker 生产参考
- [MetaGPT —— 多 agent 协作框架的元编程](https://arxiv.org/abs/2308.00352) —— SOP-角色分解
- [ChatDev —— 用于软件开发的对话式 agent](https://arxiv.org/abs/2307.07924) —— communicative dehallucination
- [MacNet —— 把基于角色的 agent 扩展到 1000+](https://arxiv.org/abs/2406.07155) —— 基于 DAG 的规模
- [维基百科上的 OpenClaw](https://en.wikipedia.org/wiki/OpenClaw) —— 生态概览
- [WMAC 2026](https://multiagents.org/2026/) —— AAAI 2026 Bridge Program 多 agent 协调 workshop
- [LangGraph 文档](https://docs.langchain.com/oss/python/langgraph/workflows-agents) —— 生产领跑者
- [CrewAI 文档](https://docs.crewai.com/en/introduction) —— 基于角色的框架
