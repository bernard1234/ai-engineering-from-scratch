---
name: vllm-stack-decider
description: 给定负载与集群规模，决定 vLLM 的部署布局——production-stack Helm chart、KV offload（原生 CPU 或 LMCache）、router/可观测性集成。
version: 1.0.0
phase: 17
lesson: 18
tags: [vllm, production-stack, lmcache, kv-offload, connector-api]
---

给定负载（prompt 形态、并发、前缀复用模式）、集群（engine 数、GPU 型号）与运维场景（Kubernetes 原生、多租户、预算），产出一份 vLLM 栈计划。

产出：

1. 技术栈。使用 vLLM production-stack Helm chart（推荐用于新部署），或自建。说明适用哪些 operator/CRD。
2. KV offload。选择：
   - 不用（短 prompt、低并发——开销超过收益）。
   - 原生 vLLM CPU offload（单 engine HBM 压力，简单）。
   - LMCache connector（多 engine 前缀复用、preemption 频繁，或多租户共享 prompt）。
3. HBM 利用率监控。设置 `--gpu-memory-utilization` 并留出余量；在持续 92%+ 时告警，作为 preemption 的前置信号。
4. Router 集成。cache-aware router（第 17 阶段 · 11）。确认 KV 事件通道已配置。
5. 可观测性。每个 engine 的 Prometheus 抓取、OTel GenAI 属性（第 17 阶段 · 13）、来自 production-stack 的 Grafana dashboard 模板。
6. 预期影响。量化相对当前的预期吞吐增益——参考 16x H100 benchmark 的形态（当 KV 占用超过 HBM 时 LMCache 有帮助）。

硬性拒绝：
- 在没有共享前缀或 preemption 的情况下部署 LMCache。拒绝——只有开销，没有收益。
- 在没有 HBM 压力监控的情况下运行 vLLM。拒绝——第一次 preemption 会是个意外。
- 在 Helm chart 已覆盖用例时自建 production-stack。拒绝——重复造轮子的成本。

拒绝规则：
- 如果集群 <2 个 engine，拒绝 LMCache——跨 engine 复用才是重点；单 engine 用原生。
- 如果负载的 prompt < 1K tokens 且并发 < 100，拒绝任何形式的 offload——HBM 余量足够。
- 如果团队不具备 K8s 能力，拒绝 production-stack——先从单 engine vLLM + 简单代理起步。

输出：一页纸的计划，写明技术栈、KV offload 选择、HBM 监控、router 集成、可观测性、预期影响。结尾给出唯一闸门：最近 24 小时的 HBM 利用率 P99。
