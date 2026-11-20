---
name: disaggregation-decider
description: 针对给定负载与集群，判断是否采用 disaggregated prefill/decode（Dynamo 或 llm-d）。量化 prefill:decode 配比、KV 传输成本与预期节省。
version: 1.0.0
phase: 17
lesson: 17
tags: [disaggregated-serving, dynamo, llm-d, nixl, kv-transfer, prefill-decode]
---

给定负载画像（prompt/输出长度分布、模型、并发）、集群拓扑（GPU、fabric、RDMA 可用性）与当前 serving 成本，产出一份 disaggregation 决策。

产出：

1. 是否 Disaggregate？Yes / No，附编号理由。基线：prompt > 512 且输出 > 200。Fabric：有 RDMA 更好；仅 TCP 会把盈亏平衡点推得更远。
2. 技术栈选择。NVIDIA Dynamo（位于 vLLM/SGLang/TRT-LLM 之上的托管 orchestrator）或 llm-d（Kubernetes 原生 Service）。与运维场景匹配。
3. Prefill:decode 配比。使用 Dynamo Planner Profiler 的读数，或从负载形态推算（prefill TFLOPS vs decode bytes/sec）。例如，RAG 偏重时 2 prefill : 1 decode；输出偏重时 1:2。
4. KV 传输方案。写明传输方式（NIXL over InfiniBand / RDMA / TCP 回退）。计算你 prompt P99 下的每请求传输税。
5. Router 集成。cache-aware router（第 17 阶段 · 11）必须置于前端——没有前缀匹配的 disaggregation 会丢掉缓存收益。
6. 预期节省。与 colocated 基线对比计算；引用已公开的案例（相同 SLA 下 30-40%）。

硬性拒绝：
- 对短 prompt 负载（<512 tokens）做 disaggregation。拒绝——传输税占主导。
- 在没有 cache-aware router 的情况下部署。拒绝——盲目路由会抵消 KV 局部性。
- 忽略拓扑（机架打包）。拒绝——跨机架跳转的 KV 传输比同机架 RDMA 更贵。

拒绝规则：
- 如果集群 < 4 张 GPU，拒绝——池子多样性不足以让 disaggregation 划算。
- 如果没有 RDMA/InfiniBand 也没有相关计划，说明 TCP 会把盈亏平衡推到 prompt >2K；重新评估。
- 如果团队无法运维两个按角色伸缩的 GPU 池，拒绝 llm-d，要求改用托管的 Dynamo。

输出：一页纸的决策，包含是否 disaggregate、技术栈选择、配比、传输方式、router、预期节省。结尾给出要验证的唯一指标：KV transfer P99 latency；以超过计划指定的阈值为闸门。
