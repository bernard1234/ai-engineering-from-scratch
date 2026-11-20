# AI 的 SRE——Multi-Agent 事故响应、Runbook 与预测性检测

> AI SRE 通过 RAG 让 LLM 基于基础设施数据（日志、runbook、服务拓扑）来自动化调查、文档与协调阶段。2026 年的架构模式是 multi-agent 编排——由 supervisor 协调专门化的 agent（日志、指标、runbook）；AI 提出假设与查询，人类批准判断性决策。Datadog Bits AI 和 Azure SRE Agent 以托管产品形态交付这套能力。Runbook 正在演进：NeuBird Hawkeye 使用对抗式评估（两个模型分析同一事故；一致 = 有信心，分歧 = 不确定）；运维记忆在团队更替后仍能延续。自动修复保持谨慎：AI 建议，人类批准。完全自主的动作范围很窄（重启 pod、回滚特定部署），并有严格护栏——任何兜售“设好就不用管”的人都是在过度承诺。新兴前沿：事故前预测。MIT 的研究报告显示，一个基于历史日志 + GPU 温度 + API 错误模式训练的 LLM 提前 10-15 分钟预测了 89% 的故障。预测：到 2026 年底，95% 的企业 LLM 都具备自动 failover。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级 multi-agent 事故分诊模拟器)
**Prerequisites:** 第 17 阶段，第 13 课（Observability）、第 24 课（Chaos Engineering）
**Time:** ~60 分钟

## Learning Objectives

- 画出 multi-agent AI SRE 架构：supervisor + 专门化 agent（日志、指标、runbook）+ 人工审批 gate。
- 解释为什么自动修复的范围要窄（重启 pod、回滚部署）而不是宽（重构服务）。
- 说出对抗式评估模式（NeuBird Hawkeye）：两个模型一致 = 有信心；不一致 = 升级。
- 引用 MIT 89% 早期检测结果及其运维约束：没有执行动作的预测只是 dashboard。

## 问题场景

一名 on-call 工程师凌晨 3 点被呼叫。“checkout 错误率高。”他去查 Datadog、Loki、三份 runbook、部署日志。30 分钟后他发现根因是 KV cache 飙升导致的 vLLM OOM。他重启 pod，错误消失。

2026 年，这项调查的前 20 分钟是可以自动化的。按服务聚合日志、关联到最近的部署、与 runbook 匹配——全都是 RAG + tool use。一个受监督的 agent 可以在人类打开 Datadog 之前完成首轮分诊并给出假设。

完全自主的修复是另一个问题。重启 pod：安全。扩容 GPU 池：若策略允许则安全。重构服务：绝对不行。纪律在于划出这条窄线。

## 核心概念

### Multi-agent 架构

```
          Incident
             │
             ▼
        Supervisor
        /    |    \
       ▼     ▼     ▼
  Log agent  Metric agent  Runbook agent
       │     │     │
       └─────┴─────┘
             │
             ▼
        Hypothesis + evidence
             │
             ▼
        Human approval
             │
             ▼
        Action (narrow set)
```

Supervisor 把事故拆成子查询。专门化 agent 拥有工具权限（日志搜索、PromQL、文档检索）。Supervisor 综合后，把假设 + 证据呈现给人类。人类批准或重定向。

### 自动修复的边界

**安全（窄）**：重启 pod、回滚特定部署、在预先批准的范围内扩容池、启用预先批准的 feature flag。

**不安全（宽）**：改变服务拓扑、修改资源限额、部署新代码、更改 IAM、改动数据库。

任何兜售“设好就不用管”的人都是在过度承诺。随着 AI SRE 成熟，安全集合会扩大，但边界真实存在。

### 对抗式评估（NeuBird Hawkeye）

两个模型独立分析同一事故。如果它们在根因上一致，置信度就高。如果不一致，就把两个假设都展示给人类并升级。模式简单，却是对抗幻觉根因的有效过滤器。

### 运维记忆

团队更替是传统 SRE 的无声杀手——部落知识随人离开。AI SRE 把 runbook + post-mortem 存进向量 DB；agent 在每次新事故时检索。新工程师加入时，AI 已有完整历史。

### 事故前预测

MIT 2025 年的研究：在历史日志、GPU 温度和 API 错误模式上训练的 LLM，在测试集上提前 10-15 分钟预测了 89% 的故障。

现实检验：没有执行动作的预测只是 dashboard。运维要问的是“预测到之后我们做什么？”预先排空？呼叫？自动扩缩？答案取决于具体策略。

### 2026 年的产品

- **Datadog Bits AI**——Datadog 内部的托管 SRE copilot。
- **Azure SRE Agent**——Azure 原生。
- **NeuBird Hawkeye**——对抗式 eval + 运维记忆。
- **PagerDuty AIOps**——分诊 + 去重。
- **Incident.io Autopilot**——事故指挥 + 协调。

### Runbook 即代码

Runbook 从 Confluence 页面演进为版本化的 markdown，包含结构化章节（symptom、hypothesis、verify、act）。结构化的 runbook 能喂出更好的 RAG 检索。任何 AI-SRE 落地都应从把非结构化 runbook 转成结构化开始。

### 你应该记住的数字

- MIT 早期检测：89% 的故障，提前 10-15 分钟。
- Multi-agent 分诊：supervisor +（日志、指标、runbook）+ 人类。
- 安全的自动修复集合：重启 pod、回滚部署、在边界内扩缩。
- 对抗式 eval：两个模型独立；一致 = 有信心。

```figure
i4-incident-agents
```

## Use It

`code/main.py` 模拟 multi-agent 分诊：log agent 找到错误，metric agent 找到 CPU 飙升，runbook agent 匹配到已知问题。Supervisor 对假设排序。

## Ship It

本课产出 `outputs/skill-ai-sre-plan.md`。给定当前 on-call、事故量、团队成熟度，设计一次 AI SRE 落地。

## Exercises

1. 运行 `code/main.py`。如果 log agent 与 metric agent 意见不一致会怎样？Supervisor 如何解决？
2. 为你的服务定义三个“安全”的自动修复动作。逐一说明理由。
3. 写一个结构化 runbook 模板：章节、必填字段、验证命令。
4. 预测性检测在提前 12 分钟时触发。你的策略是什么——呼叫、预先排空，还是两者都做？
5. 论证一个 3 人团队在 2026 年该不该上 AI SRE 还是再等等。考虑成熟度、事故量、风险。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| AI SRE | “on-call 的 agent” | LLM 驱动的事故调查 + 协调 |
| Supervisor agent | “那个 orchestrator” | 把事故拆成子查询的顶层 agent |
| Specialized agent | “领域 agent” | 拥有工具权限（日志、指标、runbook）的子 agent |
| Auto-remediation | “AI 来修” | 预先批准的窄动作；绝非大范围重构 |
| Operational memory | “向量 runbook” | post-mortem + runbook 存入向量 DB 供 RAG |
| Adversarial eval | “双模型检查” | 独立分析；一致 = 有信心 |
| NeuBird Hawkeye | “那个对抗式的” | 采用对抗式 eval + 记忆模式的产品 |
| Bits AI | “Datadog 的 SRE agent” | Datadog 托管的 AI SRE |
| Pre-incident prediction | “早期检测” | 提前 10-15 分钟预测故障 |

## Further Reading

- [incident.io — AI SRE Complete Guide 2026](https://incident.io/blog/what-is-ai-sre-complete-guide-2026)
- [InfoQ — Human-Centred AI for SRE](https://www.infoq.com/news/2026/01/opsworker-ai-sre/)
- [DZone — AI in SRE 2026](https://dzone.com/articles/ai-in-sre-whats-actually-coming-in-2026)
- [Datadog Bits AI](https://www.datadoghq.com/product/bits-ai/)
- [NeuBird Hawkeye](https://www.neubird.ai/)
- [awesome-ai-sre](https://github.com/agamm/awesome-ai-sre)
