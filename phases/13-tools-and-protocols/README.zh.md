# Phase 13: 工具与协议

> AI 与真实世界之间的接口。

这一阶段从函数调用与工具 schema 出发，进入可互操作的协议、Agent Skills、安全与生产治理。数字顺序便于浏览，下面按主题划分的聚焦路线才是可靠的学习顺序。

## 在 GitHub 上开始这一阶段

**Prerequisites:** Phase 11 LLM 补全 API。对于 MCP 或 Agent Skills，请使用下面的聚焦路线，不要假设按课程编号顺序学习。

**第一课（完整阶段）：** [工具接口](01-the-tool-interface/)

在仓库根目录运行这条命令：

```bash
python3 phases/13-tools-and-protocols/01-the-tool-interface/code/main.py
```

记住命令本身、退出码、describe-decide-execute-observe 轨迹、被拒绝输入的证据，以及一句解释轮次上限的话。

**下一步：** 继续学习 [函数调用深入解析](02-function-calling-deep-dive/)，或在下面选择 Model Context Protocol（MCP）或 Agent Skills 路线。

浏览[完整的 Phase 13 课程列表](../../README.md#phase-13)或[跨阶段路线图](../../ROADMAP.md)。

## Model Context Protocol (MCP) 路线

聚焦的 MCP 路线包含 17 节课，约 23 小时 15 分钟。它沿着 MCP `2026-07-28` 从一个自描述 JSON-RPC 请求走到可运行的一致性门禁。

| 阶段 | 课程 | 你证明什么 | 时间 |
|---|---|---|---:|
| 核心 | [06](06-mcp-fundamentals/)、[07](07-building-an-mcp-server/)、[08](08-building-an-mcp-client/)、[09](09-mcp-transports/)、[10](10-mcp-resources-and-prompts/) | 信封、发现、客户端与服务端行为、传输、资源与 prompt。 | 5 小时 50 分钟 |
| 双向 | [11](11-mcp-sampling/)、[12](12-mcp-roots-and-elicitation/)、[13](13-mcp-async-tasks/)、[14](14-mcp-apps/) | MRTR 输入、显式 scope、持久任务，以及不依赖服务端发起请求的应用边界。 | 5 小时 |
| 安全 | [15](15-mcp-security-tool-poisoning/)、[16](16-mcp-security-oauth-2-1/)、[18](18-mcp-auth-production/)、[17](17-mcp-gateways-and-registries/) | 投毒防御、授权、生产 token、网关路由与注册表准入。 | 5 小时 15 分钟 |
| 进阶 | [28](28-mcp-tool-contracts-and-content/)、[29](29-mcp-reliability-cancellation-and-flow-control/)、[30](30-mcp-registry-supply-chain-and-drift/)、[31](31-mcp-conformance-versioning-and-operations/) | 契约保真、取消竞态、供应链漂移与发布证据。 | 7 小时 10 分钟 |

确切顺序是 06、07、08、09、10、11、12、13、14、15、16、18、17、28、29、30、31。它定义在 [`learning-paths/model-context-protocol.json`](../../learning-paths/model-context-protocol.json)。导师会创建 `MCP-LEARNING.md`，每次调用只教一节课，并记录每个检查点要求的请求、响应、命令、工作目录、退出码与脱敏边界证据。

从你的宿主机支持的调用方式开始：

| 宿主机 | 调用方式 |
|---|---|
| Codex | `learn-mcp`，或从 `/skills` 中选择它 |
| Claude Code | `/learn-mcp` |
| 其他兼容宿主机 | `Use learn-mcp to start or resume the Model Context Protocol (MCP) path.` |

### 你的前十分钟

在仓库根目录运行第 06 课的无状态会话记录：

```bash
python3 phases/13-tools-and-protocols/06-mcp-fundamentals/code/main.py
```

在输出里找四样东西：重复出现的请求元数据、完整的 `server/discover` 结果、针对不受支持版本返回的错误 `-32022`，以及一次不会创建或终止 MCP 协议会话的传输关闭。这份会话记录是第一个检查点，不只是一个演示。

如果仓库或 Python 3 不可用，请阅读[第 06 课](06-mcp-fundamentals/)，并手工追踪一个请求与响应。把该检查点标记为概念性完成，同时把运行时、传输、授权与部署证据留为待办。

在任何非 loopback 绑定、共享入口、托管端点或注册表发布之前，先完成第 15 课的可执行安全检查点。审查外部目标与请求的权限，然后显式确认部署动作。完成教程并不授予部署权限。

较早的 `initialize`、`Mcp-Session-Id`、独立 SSE `GET`、会话 `DELETE` 以及服务端发起请求流程，只出现在明确的兼容性说明中。现代请求在 `params._meta` 中声明协议版本与客户端能力，使用 `server/discover`，并携带足够的信息以便被独立校验、授权、路由与重试。

[第 23 课](23-capstone-tool-ecosystem/) 是 MCP 路线中唯一的可选结业项目。开始它之前，先完成 17 节必修课以及[第 19 课](19-a2a-protocol/)和[第 20 课](20-opentelemetry-genai/)。

## Agent Skills 快速路径

这条聚焦路线包含五节课，约 9 小时 30 分钟：

| 步骤 | 课程 | 收获 | 时间 |
|---:|---|---|---:|
| 1 | [22：可移植契约与运行时边界](22-skills-and-agent-sdks/) | 创建、安装、调用、验证并卸载一个完整的 skill 包。 | 90 分钟 |
| 2 | [24：发现与渐进式披露](24-skill-discovery-and-progressive-disclosure/) | 追踪发现、编目、激活与资源加载。 | 105 分钟 |
| 3 | [25：调用与路由](25-skill-invocation-and-routing/) | 控制显式、隐式、人工、模型与弃权路径。 | 105 分钟 |
| 4 | [26：权限、沙箱与信任](26-skill-permissions-sandboxes-and-trust/) | 区分指令、权限、隔离与验证。 | 120 分钟 |
| 5 | [27：评估、打包与可移植性](27-skill-evals-packaging-and-portability/) | 构建发布门禁，并在真实宿主机中证明行为。 | 150 分钟 |

从你的宿主机支持的调用方式开始：

| 宿主机 | 调用方式 |
|---|---|
| Codex | `learn-agent-skills`，或从 `/skills` 中选择它 |
| Claude Code | `/learn-agent-skills` |
| 其他兼容宿主机 | `Use learn-agent-skills to start or resume the Agent Skills Engineering path.` |

导师会创建或恢复 `AGENT-SKILLS-LEARNING.md`，每次调用只教一节课，并记录每个检查点要求的证据。这条路线定义在 [`learning-paths/agent-skills.json`](../../learning-paths/agent-skills.json)。

如果你更喜欢先阅读，请从[第 22 课](22-skills-and-agent-sdks/)开始。它的第一个实验大约十分钟就能把一个 skill 装进真实宿主机。

### 前置条件快车道

- 真实实验需要 `node`、`npx`、`python3`、一个选定且支持 skill 的宿主机，以及对所选项目或用户 skill 作用域的写权限。安装前先用 `node --version`、`npx --version` 和 `python3 --version` 验证这三条命令。
- 如果这项预检不可用，请使用网站或手动阅读每篇 `docs/en.md`。你可以完成概念部分，但要把发现、调用、脚本、更新与卸载证据标记为待办。
- 如果工具契约对你来说是新的，请先略读[第 01 课](01-the-tool-interface/)和[第 05 课](05-tool-schema-design/)。
- 在第 26 课之前，确认你能解释工具投毒与不可信指令。[第 15 课](15-mcp-security-tool-poisoning/)是这项预检的可选复习材料，不是这条路线的第六节必修课。
- [第 23 课](23-capstone-tool-ecosystem/)是可选的系统结业项目，不是第 22 课之后的下一节 Agent Skills 课程。参加它之前，先完成第 06 到第 20 课。

## 完整阶段

完整课程计划见 [ROADMAP.md](../../ROADMAP.md)。
