# 基于角色的智能体团队——角色、任务、流程

> 四个原语：Agent、Task、Crew、Process。两种顶层形态：Crew（自主、基于角色的协作）与 Flow（事件驱动、确定性）。CrewAI 是 2026 年的参考实现，而且它的文档说得很直白：「对任何生产就绪的应用，从 Flow 开始。」

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 12 (Workflow Patterns), Phase 14 · 14 (Actor Model)
**Time:** ~75 minutes

## 学习目标

- 说出 CrewAI 的四个原语（Agent、Task、Crew、Process）以及各自拥有什么。
- 区分 Sequential、Hierarchical 与规划中的 Consensus 流程；按工作负载各挑一个。
- 区分 Crew（自主、基于角色）与 Flow（事件驱动、确定性），并解释文档的生产建议。
- 用 `@tool` 装饰器和 `BaseTool` 子类接工具；就「结构化输出 vs 自由文本」做推理。
- 说出四种 CrewAI 记忆类型以及各自何时回本。
- 用标准库实现一个三智能体 crew（研究员、写手、编辑），产出一份简报。
- 识别 CrewAI 的三种失败模式：prompt 膨胀、manager-LLM 税、脆弱的交接。

## 问题

采用多智能体框架的团队会撞上同一堵墙。「自主协作」在演示里听起来很棒。然后一个客户报了 bug，你需要确定性重放。或者财务问一个 LLM 路由的 crew 每次运行花多少钱。或者 on-call 需要知道凌晨 3 点是哪个智能体卡住了。

自由形式的 LLM 路由 crew 对这些问题一个都答不干净。纯 DAG 全都答得上，但丢掉了头脑风暴智能体需要的探索形态。

CrewAI 的切分诚实地面对了这个取舍。Crew 用于协作式、基于角色、探索性的工作。Flow 用于事件驱动、代码拥有、可审计的生产。同一个框架，两种形态，按表面各取所需。

## 概念

### 四个原语

CrewAI 的表面很小。记住这个，剩下的都是配置。

- **Agent。** `role + goal + backstory + tools + (可选) llm`。backstory 是承重的。它塑造语气、判断、智能体何时停下。Tools 是智能体可以调用的函数（下文详述）。
- **Task。** `description + expected_output + agent + (可选) context + (可选) output_pydantic`。一个可复用的工作单元。`expected_output` 是契约。`context` 列出其输出会被传进来的上游任务。`output_pydantic` 强制结构化形状。
- **Crew。** 容器。拥有 `agents` 列表、`tasks` 列表、`process`，以及可选的 `memory` + `verbose` + `manager_llm` 设置。
- **Process。** 执行策略。Sequential、Hierarchical、Consensus（规划中）。决定运行的形状。

智能体彼此不直接相见。Task 引用智能体。Crew 编排任务的顺序。Process 决定谁来挑下一个任务。这就是整个心智模型。

> **已针对** CrewAI 0.86（2026-05）验证。更新的版本可能重命名或合并流程类型；在依赖某个具体形状之前，查 [CrewAI Processes 文档](https://docs.crewai.com/concepts/processes)。

### Sequential vs Hierarchical vs Consensus

- **Sequential。** 任务按声明顺序运行。任务 N 的输出作为 `context` 提供给任务 N+1。成本最低。最可预测。顺序固定时使用。
- **Hierarchical。** 一个 manager 智能体（单独的 LLM 调用）在专家之间路由。CrewAI 从你的 `manager_llm` 配置或一个默认值里 spawn 出 manager。manager 每轮挑选下一个任务，可以拒绝或重新路由。当你有四个或更多专家、且顺序确实依赖先前的输出时使用。
- **Consensus。** 规划中，尚未在公共 API 中实现。文档为未来一个基于投票的流程预留了这个名字。今天不要依赖它。

Hierarchical 在每一次专家调用之上再加一次每轮的 LLM 调用（manager）。五步运行中 token 成本可能变成三倍。只有当你需要这个路由时才付这笔钱。

### Crews vs Flows

这是文档在 2026 年主打的分框架。

- **Crew。** LLM 驱动的自主。框架在运行时挑选形状。适合：研究、头脑风暴、初稿，任何「路径本身就是答案一部分」的地方。难重放。难测试。原型便宜。
- **Flow。** 你拥有的事件驱动图。`@start` 标记入口。`@listen(topic)` 标记一个步骤，当另一个步骤发出该 topic 时触发。每个步骤都是普通 Python（可以在内部调用一个 Crew）。适合：生产。可观测。可测试。确定性。

文档 2026 年的生产建议：从 Flow 开始。当自主性物有所值时，把 Crew 作为 Flow 步骤里的 `Crew.kickoff()` 调用折叠进来。Flow 给你审计轨迹，Crew 给你探索。组合，而不是二选一。

### 工具集成

给智能体接工具的三种方式。挑最简单且合适的那一种。

1. **`@tool` 装饰器。** 纯函数变成工具。签名是 schema；docstring 是 LLM 看到的描述。最适合一次性辅助函数。

   ```python
   from crewai.tools import tool

   @tool("Search the web")
   def search(query: str) -> str:
       """Return top results for the query."""
       return run_search(query)
   ```

2. **`BaseTool` 子类。** 基于类的工具，带显式参数 schema、异步支持、重试。当工具有状态（一个客户端、一个缓存）或需要结构化参数时使用。

   ```python
   from crewai.tools import BaseTool
   from pydantic import BaseModel

   class SearchArgs(BaseModel):
       query: str
       limit: int = 10

   class SearchTool(BaseTool):
       name = "web_search"
       description = "Search the web and return top results."
       args_schema = SearchArgs

       def _run(self, query: str, limit: int = 10) -> str:
           return self.client.search(query, limit=limit)
   ```

3. **内置工具包。** CrewAI 提供第一方适配器：`SerperDevTool`、`FileReadTool`、`DirectoryReadTool`、`CodeInterpreterTool`、`RagTool`、`WebsiteSearchTool`。一次 import 接好。

结构化输出用 Pydantic。在 Task 上传 `output_pydantic=MyModel`。CrewAI 对照模型校验 LLM 的响应，要么强制转换、要么重试。配一个紧致的 `expected_output` 字符串一起用。自由文本输出对草稿没问题；结构化输出才是下游 Flow 能消费的东西。

### 记忆钩子

CrewAI 开箱提供四种记忆类型。它们可组合：一个 Crew 可以同时启用全部四种。

> **已针对** CrewAI 0.86（2026-05）验证。近期版本把所有东西都路由到一个统一的 `Memory` 系统，包裹这四个存储。下面的概念模型仍然成立，但公共类表面在更新版本里可能坍缩成一个 `Memory` 入口点；查 [CrewAI memory 文档](https://docs.crewai.com/concepts/memory)获取当前 API。

- **短期（Short-term）。** 单次运行内的对话缓冲。结束时清空。
- **长期（Long-term）。** 跨运行持久化。存在一个向量数据库里（默认 Chroma，可换）。按与当前任务的相似度检索。
- **实体（Entity）。** 每个实体的事实。「客户 X 在企业版套餐上。」按实体键控，而非按相似度。跨运行存活。
- **上下文（Contextual）。** 装配时的检索。在智能体需要的那一刻拉取相关记忆，而非预加载。

在 Crew 上用 `memory=True` 或按类型配置启用。背靠一个你配置的 embeddings 提供商（默认 OpenAI，可换成本地）。记忆是 CrewAI 相对更薄框架回本的地方之一；纯 LangGraph 要求你自己逐个接好这些。

### 基于角色的团队适合什么

- 三到六个有命名角色、协作式工作流的智能体。起草、评审、规划、头脑风暴。
- LLM 对下一步的判断本身就是价值一部分的路由（Hierarchical）。
- 团队读 `role + goal + backstory` 比读图定义更顺手的任何地方。

### 不适合什么

- 严格排序的确定性 DAG。用 LangGraph（第 13 课）。图形状才是对的抽象；CrewAI 的角色框架是摩擦。
- 亚秒级延迟预算。Hierarchical 增加往返。即便 Sequential 也会把包含 backstory 和先前输出的 prompt 串行化。
- 单智能体循环。跳过框架；一个 agent loop（第 1 课）加一个工具注册表更短。

第 17 课（Agent Framework Tradeoffs）用一个矩阵讲了这个。简短版：CrewAI 坐在「协作式、基于角色」这个角落。

### 依赖形态

独立于 LangChain。Python 3.10 到 3.13。用 `uv`。star 数：见 [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI)（2026-05 快照）。AWS Bedrock 集成有文档；厂商基准报告在 QA 工作负载上相对 LangGraph 有可观提速，但方法论（数据集、硬件、评估指标）没有公开，所以把框架厂商的数字只当作方向性参考。

### 这个模式在哪里会出问题

- **backstory 导致的 prompt 膨胀。** 每个智能体 2000 字的 backstory，加一个五智能体 crew，在第一次工具调用之前就烧光了上下文预算。把 backstory 压在 200 字以内。跨智能体复用措辞；不要把行文规范重复五遍。
- **manager-LLM 的 token 税。** Hierarchical 流程在每次专家调用之前都加一次 manager LLM 调用。一个五任务的 crew 是六次 LLM 调用而不是五次，而且 manager 调用携带完整任务清单加先前输出。除非路由依赖输出，否则换 Sequential。
- **脆弱的交接。** 任务 N 的 `expected_output` 是「一份大纲」。任务 N+1 把它作为 `context` 读进来，试图解析三个小节。LLM 产出了四个。下游智能体即兴发挥。在任务 N 上用 `output_pydantic` 修复，让任务 N+1 读到的是一个类型化对象，而不是自由文本。
- **把 Crew 直接上生产。** 没有 Flow 包裹的自由形式 Crew 直接上生产。输出变异性高；重放不可能；on-call 无法把一次坏的运行与一次好的运行做 diff。用 Flow 包裹。

```figure
ae-crew-vs-flow
```

## Build It

`code/main.py` 实现两种形态的标准库版本，加一个三智能体 crew。

形态：

- `Agent`、`Task` 数据类，匹配 CrewAI 的表面。
- `SequentialCrew.kickoff(inputs)` 按声明顺序运行任务，把输出作为 `context` 穿针引线。
- `HierarchicalCrew.kickoff(topic)` 加一个 manager 智能体，每轮挑选下一个专家，遇到「done」停止。
- `Flow`，带 `@start` 和 `@listen(topic)` 装饰器、一个微型事件循环和一条 trace。
- `tool(name)` 装饰器，镜像 CrewAI 的 `@tool` 形态。
- `Memory`，带 `short_term`、`long_term`、`entity` 存储；模拟的相似度用 numpy。
- 模拟 LLM 响应是硬编码字符串，按 role 加输入前缀键控。无网络。确定性。

具体演示：研究员、写手、编辑 crew 产出一份关于「agent engineering 2026」的简报。研究员拉取（模拟的）来源。写手起草。编辑收紧。同一个 crew 跑过一个 Flow，展示确定性形态。

运行它：

```bash
python3 code/main.py
```

trace 覆盖：sequential crew 通过 `context` 穿针引线输出，hierarchical crew 带 manager 挑选（研究员、写手、编辑，然后「done」），flow 用显式 topic（`researched`、`drafted`、`edited`）跑同样三步，工具调用经 `@tool` 路由，长期记忆跨两次 kickoff 存活。

Crew 的 trace 是流动的；manager 原则上可以重新排序。Flow 的 trace 是固定的。这个选择就是本课。

## Use It

- **CrewAI Flow** 用于生产。即便 Flow 只有一步、且那一步调用 `Crew.kickoff()`。Flow 给出审计边界。
- **CrewAI Crew（Sequential）** 用于顺序清晰的协作工作，尤其是初稿和评审循环。
- **CrewAI Crew（Hierarchical）** 当路由依赖输出、且你有四个或更多专家时。
- **LangGraph**（第 13 课）用于显式状态机、持久恢复、严格排序。
- **AutoGen v0.4**（第 14 课）用于 actor 模型并发和故障隔离。
- **OpenAI Agents SDK**（第 16 课）用于带 handoff 和 guardrail 的 OpenAI 优先产品。
- **Claude Agent SDK**（第 17 课）用于带 subagent 和 session store 的 Claude 优先产品。

## Ship It

`outputs/skill-crew-or-flow.md` 为任务挑选 Crew vs Flow，并脚手架出最小实现。硬拒绝：没有 backstory 的 Crew、没有显式 topic 的 Flow、少于三个专家的 Hierarchical。

## 陷阱

- **把 backstory 当点缀。** 它塑造输出。每个智能体测三个变体；方差是真实的。挑一个，冻结它。
- **跳过 `expected_output`。** 没有逐任务契约，下游任务捡到的是 LLM 产出的任何东西。Crew 跑完了；审计失败了。
- **记忆常开。** 长期记忆每次运行都写。向量数据库膨胀。检索变嘈杂。把写入范围限定在事实持久的任务上。
- **manager prompt 漂移。** Hierarchical 的 manager prompt 是隐式的。如果路由变怪了，在 verbose 模式下把它 dump 出来读。
- **Crew 里的工具副作用。** 一个 Crew 调用工具的次数可能超预期。POST、DELETE、付款属于 Flow 步骤，绝不属于 Crew 工具。

## 练习

1. 把 Sequential crew 转成 Flow。数一下变异性下降的触点。记一下可读性下降的地方。
2. 给 crew 加实体记忆：关于客户的事实跨 kickoff 持久化。验证检索拉对了实体。
3. 实现一个 Hierarchical 流程，manager 在写手输出至少三段之前拒绝把任务路由给编辑。追踪这次重试。
4. 为一个（模拟的）网页搜索接一个 `BaseTool` 子类。对比与 `@tool` 装饰器版本的 trace 形状。
5. 给编辑任务加 `output_pydantic=Brief`，其中 `Brief` 有 `title`、`summary`、`sections`。让写手任务输出一次畸形 JSON；在 trace 里验证 CrewAI 的重试行为。
6. 读 CrewAI 文档简介。把玩具移植到真正的 `crewai` API。标准库版本跳过了哪些保证？
7. 把 AgentOps 或 Langfuse（第 24 课）接到一次真实运行。标准库版本里你漏掉了哪些 trace？

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| Agent | 「人设」 | role + goal + backstory + tools |
| Task | 「工作单元」 | 描述 + 期望输出 + 负责人 + 可选结构化输出 |
| Crew | 「智能体团队」 | Agent + Task + Process 的容器 |
| Process | 「执行策略」 | Sequential / Hierarchical / Consensus（规划中） |
| Flow | 「确定性工作流」 | 事件驱动、代码拥有、可测试 |
| Backstory | 「人设 prompt」 | 智能体的语气与判断塑造器 |
| `@tool` | 「函数工具」 | 把函数变成智能体可调用工具的装饰器 |
| `BaseTool` | 「类工具」 | 带参数 schema、重试、异步支持的基于类的工具 |
| Entity memory | 「逐实体事实」 | 限定在客户 / 账户 / 工单上的记忆 |
| Long-term memory | 「跨运行记忆」 | 在 kickoff 之间存活的向量背靠记忆 |
| Contextual memory | 「即时检索」 | 在智能体需要的那一刻拉取的记忆 |
| Manager LLM | 「路由智能体」 | Hierarchical 流程里挑选下一个任务的额外 LLM |
| `expected_output` | 「任务契约」 | 告诉智能体（和审计）该返回什么形状的字符串 |

## 延伸阅读

- [CrewAI docs introduction](https://docs.crewai.com/en/introduction)：概念与推荐的生产路径
- [CrewAI Flows guide](https://docs.crewai.com/en/concepts/flows)：事件驱动形态、`@start`、`@listen`
- [CrewAI tools reference](https://docs.crewai.com/en/concepts/tools)：`@tool`、`BaseTool`、内置工具包
- [CrewAI memory](https://docs.crewai.com/en/concepts/memory)：短期、长期、实体、上下文
- [Anthropic，Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)：多智能体什么时候有用、什么时候没用
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)：状态机替代