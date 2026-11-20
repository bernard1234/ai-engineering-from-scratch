---
name: devops-agent
description: 构建一个 Kubernetes 排障 agent，遍历集群知识图谱、对根因排序，并把每一次修复都经 Slack 把关。
version: 1.0.0
phase: 19
lesson: 06
tags: [capstone, devops, sre, kubernetes, langgraph, fastmcp, aiops]
---

给定一个 K8s 集群和告警来源（PagerDuty 或 Alertmanager），构建一个 agent，在五分钟内产出排序的根因假设，并把每一次修复都经 Slack 审批卡片把关。

构建计划：

1. 每 30s 把 kube-state-metrics 摄取进 Neo4j 或 kuzu。构建 Pod、Deployment、Service、Node、PVC、HPA 的图，加上指向 Prometheus、Loki、Tempo 来源的遥测覆盖边。
2. 为 PagerDuty 与 Alertmanager 搭建一个 FastAPI webhook 接收器。
3. 通过 StreamableHTTP 传输用 FastMCP 暴露只读工具：kubectl get/describe、promql、logql、traceql。
4. 构建一个 LangGraph 根因 agent，含三个节点：`sample`（拉取 15 分钟遥测）、`walk`（遍历图谱邻居）、`hypothesize`（按 recency × specificity × citation 数对候选排序）。
5. 把排序前 3 的假设连同图路径可视化发到 Slack，并带审批按钮。
6. 把破坏性工具（scale、rollback、delete）放到独立的 FastMCP 服务器上，处于一个只有 Slack 签字后 agent 才获得的审批 token 之后。
7. 维护一个仅追加的审计日志：每个 *考虑过* 的命令、是否批准、是否执行、谁批准。
8. 构建 20 个合成事故场景（OOMKill、DNS 抖动、HPA 抖动、PVC 写满、吵闹邻居、故障 sidecar、ConfigMap 糟糕发布、证书轮换、镜像拉取退避、探针失败，以及另外 10 个）。按 RCA 准确率与假设产出时间给 agent 打分。

评估评分表：

| 权重 | 标准 | 衡量方式 |
|:-:|---|---|
| 25 | 场景套件上的 RCA 准确率 | 20 个合成事故中根因正确率至少 80% |
| 20 | 安全性 | 审计日志显示破坏性动作守卫在无 Slack 批准时从不触发 |
| 20 | 假设产出时间 | 从告警到 Slack 简报的 p50 低于 5 分钟 |
| 20 | 可解释性 | 每个假设都有图路径与遥测引用 |
| 15 | 集成完整度 | PagerDuty、Slack、ArgoCD、Prometheus 端到端可用 |

硬性驳回：

- 用单个 MCP 服务器混合只读与破坏性工具的 agent。
- 任何缺少遥测引用的 RCA。无引用的假设必须被驳回。
- 只记录执行的审计日志。它们必须记录每一个考虑过的命令。
- 没有在带种子的 20 场景套件上运行 agent 就声称准确率。

拒绝规则：

- 没有当班人类通过 Slack 批准就拒绝修复。即使假设显而易见。
- 拒绝通过只读 MCP 暴露 `kubectl exec`、`kubectl port-forward` 或任何交互式工具。它们在效果上是破坏性的。
- 没有逐 deployment 的审批卡片，拒绝跨多个 deployment 批量应用修复。

产出：一个仓库，包含 FastAPI 接收器、LangGraph agent、只读与破坏性 MCP 服务器、Slack 集成、20 场景测试套件、与 AWS DevOps Agent 在三个共享事故上的并排对比，以及一份关于一周观察窗口内险情命令（agent *考虑过* 但未执行）的总结。
