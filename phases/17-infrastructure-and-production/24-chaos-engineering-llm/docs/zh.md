# LLM 生产环境的 Chaos Engineering

> 2026 年，LLM 的 chaos engineering 已成为一门独立的学科。在生产环境运行实验前的前置条件：已定义的 SLI/SLO、trace+metric+log 可观测性、自动回滚、runbook、on-call。架构分为四个平面：control（实验调度器）、target（服务、基础设施、数据存储）、safety（守卫 + 中止 + 流量过滤）、observability（metrics + traces + logs）、feedback（回流到 SLO 调整）。护栏是强制的：当日 error-budget 燃烧超过期望的 2 倍时，burn-rate 告警暂停实验；抑制窗口 + trace-ID 关联对告警噪音去重。节奏：每周小规模 canary + SLO 评审；每月 game day + postmortem；每季度跨团队韧性审计 + 依赖映射。LLM 专属实验：内存过载、网络失败、供应商宕机、畸形 prompt、KV cache 驱逐风暴。工具：Harness Chaos Engineering（LLM 衍生的建议、blast-radius 降规模、MCP 工具集成）；LitmusChaos（CNCF）；Chaos Mesh（CNCF Kubernetes 原生）。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级 chaos 实验运行器)
**Prerequisites:** 第 17 阶段，第 23 课（SRE for AI），第 13 课（Observability）
**Time:** ~60 分钟

## Learning Objectives

- 说出 chaos engineering 的五个前置条件（SLI/SLO、可观测性、回滚、runbook、on-call），并解释为什么跳过任何一个都会让实践失效。
- 画出四个平面（control、target、safety、observability）以及回流到 SLO 的反馈环。
- 列举五个 LLM 专属实验（内存过载、网络失败、供应商宕机、畸形 prompt、KV 驱逐风暴）。
- 给定技术栈，挑选工具 —— Harness、LitmusChaos、Chaos Mesh。

## 问题场景

传统技术栈里的 chaos 测试已经成熟。LLM 技术栈又叠加了新的失败模式。一个带毒字符的 4K-token prompt 会让 tokenizer 卡住 12 秒。上游供应商返回 429；你的 gateway 重试；你的服务在重试放大的并发下 OOM。突发负载下的 KV cache 驱逐风暴引发重新 prefill 的级联，打满算力。

这些都不会出现在单元测试里。chaos engineering 就是你在用户之前发现它们的方式。

## 核心概念

### 前置条件

没有以下条件，就不要在生产环境运行 chaos：

1. **SLI/SLO** —— 已定义的服务级指示器与目标。
2. **可观测性** —— 接入看板的 traces、metrics、logs。
3. **自动回滚** —— Phase 17 · 20 的 policy-flag 回滚。
4. **Runbook** —— 结构化的，Phase 17 · 23。
5. **On-call** —— 有人响应。

缺少任何一个，chaos 就会变成真实的故障。

### 四个平面 + 反馈

**控制平面（Control plane）** —— 实验调度器（Litmus workflow、Chaos Mesh schedule、Harness UI）。

**目标平面（Target plane）** —— 服务、pod、节点、负载均衡器、数据存储。

**安全平面（Safety plane）** —— kill switch、抑制窗口、blast-radius 限制、error-budget 闸门。

**可观测平面（Observability plane）** —— 常规 metrics + trace-ID 关联，用以区分 chaos 引发的故障与自然故障。

**反馈环（Feedback loop）** —— 发现回流到 SLO 调整、runbook 更新、代码修复。

### 护栏是强制的

- **Burn-rate 告警**：如果日 error-budget 燃烧超过期望的 2 倍，暂停实验。
- **抑制窗口**：实验期间，静默 blast radius 内与实验无关的告警。
- **Trace-ID 关联**：实验引发的所有错误都带一个 tag，供 on-call 去重。

### 五个 LLM 专属实验

1. **内存过载** —— 通过高并发发送长上下文请求，强制制造 KV cache 抢占风暴。观察：服务是优雅降载还是崩溃？

2. **网络失败** —— 切断 inference gateway 与供应商之间的连通性。观察：fallback 是否在 SLA 内生效？（Phase 17 · 19）

3. **供应商宕机模拟** —— 让 OpenAI 返回 100% 429。观察：路由是否 failover 到 Anthropic？（Phase 17 · 16、19）

4. **畸形 prompt** —— 注入使 tokenizer 卡住的 payload（例如深度嵌套的 unicode、巨大的 UTF-8 codepoint）。观察：单个请求是否锁死一个 worker？

5. **KV 驱逐风暴** —— 通过打满 vLLM block budget 强制驱逐。观察：LMCache 能否恢复，还是服务退化？

### 节奏

- **每周** —— 在预发环境做小规模 canary 实验，也许生产 5%。
- **每月** —— 针对特定场景的定时 game day；跨团队参与；postmortem。
- **每季度** —— 跨团队韧性审计；更新依赖图。

### 工具

- **Harness Chaos Engineering** —— 商业产品；AI 衍生的实验建议；blast-radius 降规模；MCP 工具集成。
- **LitmusChaos** —— CNCF 毕业项目；基于 Kubernetes workflow。
- **Chaos Mesh** —— CNCF sandbox；Kubernetes 原生 CRD 风格。
- **Gremlin** —— 商业产品；支持面广。
- **AWS FIS** / **Azure Chaos Studio** —— 托管云方案。

### 从小的开始

第一个实验：在稳定流量下 pod-kill 一个 decode 副本。观察重路由与恢复。如果这能奏效且看起来安全，再升级到网络 chaos。

第一个 LLM 专属实验：注入一次持续 5 分钟的供应商 429。观察 fallback。大多数团队会发现自己那套 fallback 从未被完整测试过。

### 需要记住的数字

- 四个平面：control、target、safety、observability。
- Burn-rate 暂停：期望日均预算燃烧的 2 倍。
- 节奏：每周 canary、每月 game day、每季度审计。
- 五个 LLM 实验：内存、网络、供应商、畸形 prompt、KV 风暴。

```figure
i4-chaos-guard
```

## Use It

`code/main.py` 模拟三个带 safety 平面闸门的 chaos 实验。报告哪些实验会触发 burn-rate 中止。

## Ship It

本课产出 `outputs/skill-chaos-plan.md`。给定技术栈与成熟度，挑选前三个实验与工具。

## Exercises

1. 运行 `code/main.py`。哪个实验触发了 burn-rate 闸门，为什么？
2. 为一个基于 vLLM 的 RAG 服务设计前五个 chaos 实验。包含成功标准。
3. 你的 burn-rate 告警暂停了一个实验。你如何判定根因 —— 是 chaos 还是自然故障？
4. 论证 chaos 应该在生产运行还是只在预发运行。什么时候生产才是正确答案？
5. 说出三个通用网络 chaos 无法复现的 LLM 专属失败模式。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| SLI / SLO | “服务目标” | 指示器 + 目标；必需的前置条件 |
| Blast radius | “范围” | 实验影响到的服务 / 用户集合 |
| Burn-rate alert | “预算闸门” | 当 error-budget 燃烧率 > 期望的 2 倍时触发 |
| Game day | “每月演练” | 定时的跨团队 chaos 演练 |
| LitmusChaos | “CNCF workflow” | 已毕业的 CNCF Kubernetes chaos 工具 |
| Chaos Mesh | “CNCF CRD” | CNCF sandbox 的 Kubernetes 原生 chaos |
| Harness CE | “商业 AI 辅助” | 带 AI 建议的 Harness chaos |
| Malformed prompt | “tokenizer 炸弹” | 使分词停滞的输入 |
| KV eviction storm | “抢占级联” | 大规模驱逐触发重新 prefill |

## Further Reading

- [DevSecOps School —— Chaos Engineering 2026 指南](https://devsecopsschool.com/blog/chaos-engineering/)
- [Ankush Sharma —— LLM 可观测性（书）](https://www.amazon.com/Observability-Large-Language-Models-Engineering-ebook/dp/B0DJSR65TR)
- [LitmusChaos（CNCF）](https://litmuschaos.io/)
- [Chaos Mesh（CNCF）](https://chaos-mesh.org/)
- [Harness Chaos Engineering](https://www.harness.io/products/chaos-engineering)
- [AWS FIS](https://aws.amazon.com/fis/)
