# Capstone 06 — 面向 Kubernetes 的 DevOps 排障 Agent

> AWS 的 DevOps Agent 正式 GA，Resolve AI 公开了它的 K8s playbook，NeuBird 演示了语义监控，Metoro 把 AI SRE 绑定到逐服务 SLO。生产形态已经定型：告警 webhook 触发，agent 读取遥测，遍历 K8s 对象图，对根因假设排序，并向 Slack 发一条带审批按钮的简报。默认只读。每一次修复都由人把关。本 capstone 就是这个 agent，在 20 个合成事故上评估，并在三个共享案例上与 AWS 的 Agent 对比。

**Type:** Capstone
**Languages:** Python（agent）、TypeScript（Slack 集成）
**Prerequisites:** 第 11 阶段（LLM engineering）、第 13 阶段（tools and MCP）、第 14 阶段（agents）、第 15 阶段（autonomous）、第 17 阶段（infrastructure）、第 18 阶段（safety）
**Phases exercised:** P11 · P13 · P14 · P15 · P17 · P18
**Time:** 30 小时

## 问题场景

2025-2026 年的 SRE 叙事变成了：“AI agent 分诊事故，人类批准修复。”AWS DevOps Agent、Resolve AI、NeuBird、Metoro、PagerDuty AIOps 都在生产中以这个形态交付。agent 读取 Prometheus 指标、Loki 日志、Tempo trace、kube-state-metrics，以及一张 K8s 对象知识图谱。它在五分钟内产出一个带遥测引用的排序根因假设。没有经 Slack 的明确人工批准，它绝不执行破坏性命令。

大部分硬功夫在于范围界定与安全，而不是推理。agent 需要默认只读的 RBAC 面、一个加固的 MCP 工具服务器，以及每个“考虑过”与“已执行”命令的审计日志。它需要知道何时已超出自身能力并升级。它还要跑得足够便宜，以免 OOM-kill 级联产生一张 $5k 的 agent 账单。

## 核心概念

该 agent 在一张知识图谱上运作。节点是 K8s 对象（Pod、Deployment、Service、Node、HPA、PVC）加上遥测来源（Prometheus 序列、Loki 流、Tempo trace）。边编码归属（Pod -> ReplicaSet -> Deployment）、调度（Pod -> Node）与观测（Pod -> Prometheus 序列）。图谱由 kube-state-metrics 同步保持新鲜，并在每次告警时重新采样。

告警触发时，agent 从受影响对象出发做根因分析。它遍历边，拉取相关遥测切片（最近 15 分钟），并起草一个假设。假设按证据排序：有多少条遥测引用支撑它、有多新、有多具体。前 3 个假设连同图路径可视化与修复动作的审批按钮一起进入 Slack。

修复是被把关的。允许的默认动作是只读。破坏性动作（缩容、回滚、删除 Pod）需要 Slack 批准；ArgoCD 回滚钩子需要一个 agent 从不持有的 auth token。审计日志记录 agent *考虑过*的每一个命令——而不只是已执行的——这样复核流程能抓住险情。

## 架构

```
PagerDuty / Alertmanager webhook
           |
           v
     FastAPI receiver
           |
           v
   LangGraph root-cause agent
           |
           +---- read-only MCP tools ----+
           |                             |
           v                             v
   K8s knowledge graph              telemetry slices
     (Neo4j / kuzu)              Prometheus, Loki, Tempo
   ownership + scheduling          last 15m, scoped
           |
           v
   hypothesis ranking (evidence weight)
           |
           v
   Slack brief + approval buttons
           |
           v (approved)
   ArgoCD rollback hook / PagerDuty escalate
           |
           v
   audit log: considered vs executed, every command
```

## 技术栈

- 遥测来源：Prometheus、Loki、Tempo、kube-state-metrics
- 知识图谱：K8s 对象 + 遥测边的 Neo4j（托管）或 kuzu（嵌入式）
- Agent：LangGraph，带逐工具 allow-list，默认只读
- 工具传输：FastMCP over StreamableHTTP；破坏性工具另起一个服务器，置于审批关卡之后
- 模型：Claude Sonnet 4.7 做根因推理，Gemini 2.5 Flash 做日志摘要
- 修复：ArgoCD rollback webhook、PagerDuty 升级、Slack 审批卡片
- 审计：仅追加的结构化日志（considered、executed、approved、outcome）
- 部署：K8s deployment，自带一个窄 RBAC 角色；独立 namespace

```figure
ce-rootcause-walk
```

## Build It

1. **图谱摄取。** 每 30s 把 kube-state-metrics 同步进 Neo4j/kuzu。节点：Pod、Deployment、Node、Service、PVC、HPA。边：OWNED_BY、SCHEDULED_ON、EXPOSES、MOUNTS、SCALES。遥测覆盖边：OBSERVED_BY（一个 Pod 被某条 Prometheus 序列观测）。

2. **告警接收器。** 一个 FastAPI 端点，接受 PagerDuty 或 Alertmanager webhook。提取受影响对象与 SLO 违约。

3. **只读工具面。** 通过 FastMCP 包装 kubectl、Prometheus 查询、Loki logql、Tempo traceql。每个工具只有很窄的 RBAC 动词（“get”、“list”、“describe”）。默认服务器中没有“delete”、“exec”、“scale”。

4. **根因 agent。** LangGraph 带三个节点：`sample` 拉取最近 15 分钟的遥测切片，`walk` 查询图谱中的邻居对象，`hypothesize` 起草带遥测引用的排序根因候选。

5. **证据打分。** 每个假设有一个分数 = recency * specificity * graph-path 长度倒数 * citation 数。返回前 3 个。

6. **Slack 简报。** 发布一条带假设、图路径可视化（服务端渲染的子图图像）以及最多一个修复动作审批按钮的 attachment。

7. **修复关卡。** 破坏性工具（缩容、回滚、删除）位于第二个 MCP 服务器上，处于审批 token 之后。只有 Slack 卡片被人批准后，agent 才能调用它们。

8. **审计日志。** 仅追加的 JSONL：对每个候选命令，记录它是否被考虑、是否被执行、谁批准。每日投递到 S3。

9. **合成事故套件。** 构建 20 个场景：OOMKill 级联、DNS 抖动、HPA 抖动、PVC 写满、吵闹邻居、故障 sidecar、糟糕的 ConfigMap 发布、证书轮换、镜像拉取退避等。按根因准确率与假设产出时间给 agent 打分。

## Use It

```
webhook: alert.pagerduty.com -> checkout-api SLO breach, error rate 14%
[graph]   affected: Deployment checkout-api (3 Pods, Node ip-10-2-3-4)
[walk]    neighbors: ReplicaSet checkout-api-abc, Service checkout-api,
           recent rollout 14m ago
[sample]  prometheus error_rate 14%, up-trend; loki 500s on /api/v2/pay
[hypo]    #1 bad rollout: latest image checkout-api:v2.41 fails /healthz
          citations: deploy.yaml (rev 42), prometheus errorRate, loki 500 stack
[slack]   [ROLL BACK to v2.40]  [ESCALATE]  [IGNORE]
          (approval required; agent does not roll back unilaterally)
```

## Ship It

`outputs/skill-devops-agent.md` 是交付物。给定一个 K8s 集群与告警来源，该 agent 产出排序的根因假设与一条经 Slack 把关的修复流程。

| 权重 | 标准 | 如何衡量 |
|:-:|---|---|
| 25 | 场景套件上的 RCA 准确率 | 20 个合成事故中根因正确率 ≥80% |
| 20 | 安全性 | 审计日志显示破坏性动作守卫在无 Slack 批准时从不触发 |
| 20 | 假设产出时间 | 从告警到 Slack 简报的 p50 低于 5 分钟 |
| 20 | 可解释性 | 每个假设都有图路径与遥测引用 |
| 15 | 集成完整度 | PagerDuty、Slack、ArgoCD、Prometheus 端到端可用 |
| **100** | | |

## Exercises

1. 在 AWS 的 DevOps Agent 演示所用的同样三个事故上运行你的 agent。发布并排对比。报告 agent 出现分歧的地方。

2. 加一个“险情”审计，标记 agent *考虑过*、若无批准就会成为破坏性的任何命令。测量一周内的险情率。

3. 把假设模型从 Claude Sonnet 4.7 换成自托管的 Llama 3.3 70B。测量 RCA 准确率差值与单次事故成本。

4. 构建一个因果过滤器：区分相关的遥测尖峰与真正的根因。在 20 个场景标签上训练一个小分类器。

5. 加一个回滚演练：用同一份 manifest 对 staging 集群做 ArgoCD 回滚。在 Slack 审批按钮之前，先在活集群中验证回滚方案。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| K8s knowledge graph | “集群图” | 节点 = K8s 对象 + 遥测序列；边 = 归属、调度、观测 |
| Read-only-by-default | “受限 RBAC” | agent 的 service account 只有 get/list/describe 动词；破坏性动词位于审批关卡之后的独立服务器 |
| Audit log | “considered vs executed” | 每个候选命令的仅追加记录：是否运行、谁批准 |
| Hypothesis ranking | “证据分数” | recency × specificity × graph-path 长度倒数 × citation 数 |
| Slack approval card | “HITL 关卡” | 带修复按钮的交互式 Slack 消息；人类点击前 agent 无法继续 |
| Telemetry citation | “证据指针” | 支撑某个论断的 Prometheus 查询、Loki selector 或 Tempo trace URL |
| MTTR | “解决时间” | 从告警触发到 SLO 恢复的墙钟时间 |

## Further Reading

- [AWS DevOps Agent GA](https://aws.amazon.com/blogs/aws/aws-devops-agent-helps-you-accelerate-incident-response-and-improve-system-reliability-preview/) — 2026 年的权威参考
- [Resolve AI K8s troubleshooting](https://resolve.ai/blog/kubernetes-troubleshooting-in-resolve-ai) — 竞品参考
- [NeuBird semantic monitoring](https://www.neubird.ai) — 语义图谱路线
- [Metoro AI SRE](https://metoro.io) — SLO 优先的生产框架
- [kube-state-metrics](https://github.com/kubernetes/kube-state-metrics) — 集群状态来源
- [LangGraph](https://langchain-ai.github.io/langgraph/) — 参考 agent 编排器
- [FastMCP](https://github.com/jlowin/fastmcp) — Python MCP 服务器框架
- [ArgoCD rollback](https://argo-cd.readthedocs.io/en/stable/user-guide/commands/argocd_app_rollback/) — 被把关的修复目标
